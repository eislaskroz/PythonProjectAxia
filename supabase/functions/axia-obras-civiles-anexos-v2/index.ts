import { createClient } from 'npm:@supabase/supabase-js@2';
import { jwtVerify } from 'https://deno.land/x/jose@v5.9.6/index.ts';

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const hashPattern = /^[a-f0-9]{64}$/;
const encoder = new TextEncoder();
const sha = async (b: Uint8Array) => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', b)), v => v.toString(16).padStart(2,'0')).join('');
const formats: Record<string,string> = {'image/jpeg':'jpg','image/png':'png','image/webp':'webp','application/pdf':'pdf','image/vnd.dwg':'dwg','image/vnd.dxf':'dxf'};
const isObject = (v: unknown): v is Record<string,unknown> => !!v && typeof v === 'object' && !Array.isArray(v);
class Fault extends Error { constructor(public status: number, message: string) {super(message);} }
function formatMatches(mime: string, bytes: Uint8Array): boolean {
  if (bytes.length < 12) return false;
  const at = (offset:number,s:string) => Array.from(s).every((c,i)=>bytes[offset+i]===c.charCodeAt(0));
  switch(mime) {
    case 'image/jpeg': return bytes[0]===255 && bytes[1]===216 && bytes[2]===255 && bytes[bytes.length-2]===255 && bytes[bytes.length-1]===217;
    case 'image/png': return [137,80,78,71,13,10,26,10].every((v,i)=>bytes[i]===v) && at(12,'IHDR');
    case 'image/webp': return at(0,'RIFF') && at(8,'WEBP');
    case 'application/pdf': return at(0,'%PDF-');
    case 'image/vnd.dwg': return /^AC10[0-9]{2}/.test(new TextDecoder().decode(bytes.subarray(0,6)));
    case 'image/vnd.dxf': return at(0,'AutoCAD Binary DXF') || /^\s*0\s*SECTION\b/i.test(new TextDecoder().decode(bytes.subarray(0,512)));
    default: return false;
  }
}
async function bounded(response: Request | Response, limit:number): Promise<Uint8Array> {
  const n=response.headers.get('content-length');
  if (n!==null && (!/^\d+$/.test(n) || Number(n)>limit)) throw new Fault(413,'Tamaño no permitido.');
  if (!response.body) throw new Fault(400,'Contenido vacío.');
  const reader=response.body.getReader(); const chunks:Uint8Array[]=[]; let total=0;
  try { for (;;) { const {done,value}=await reader.read(); if(done) break; total+=value.length; if(total>limit) {await reader.cancel(); throw new Fault(413,'Tamaño no permitido.');} chunks.push(value); } }
  finally {reader.releaseLock();}
  if(!total) throw new Fault(400,'Contenido vacío.');
  const bytes=new Uint8Array(total); let offset=0; for(const c of chunks){bytes.set(c,offset);offset+=c.length;} return bytes;
}
function rpcFault(e: any): never {
  const code=String(e?.code??'');
  if(code==='42501') throw new Fault(403,'Operación no autorizada.');
  if(code==='22023' || code==='22P02' || code==='23502') throw new Fault(400,'Datos no válidos o incompletos.');
  if(['P0001','23505','23503','23514','40001','40P01'].includes(code)) throw new Fault(409,'Conflicto de sesión, anexos o estado de Obra Civil.');
  throw e;
}
Deno.serve(async (req:Request)=>{
  const requestId=crypto.randomUUID(); let stage='AUTH';
  const out=(status:number,body:object)=>new Response(JSON.stringify({requestId,...body}),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'}});
  const fail=(status:number,error:string)=>out(status,{ok:false,error,supportCode:`AXF-OBC2-${stage}-${status}-${requestId.slice(0,8).toUpperCase()}`});
  if(req.method!=='POST') return fail(405,'Método no permitido.');
  try {
    const secret=Deno.env.get('AXIA_MOBILE_JWT_SECRET')??'', url=Deno.env.get('SUPABASE_URL')??'', service=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')??'';
    if(secret.length<32 || !url || !service) throw Error('CONFIG');
    let userId:number;
    try { const token=req.headers.get('authorization')?.match(/^Bearer\s+(\S+)$/i)?.[1]; if(!token) throw Error();
      const {payload}=await jwtVerify(token,encoder.encode(secret),{issuer:'axia-field',audience:'axia-mobile',algorithms:['HS256'],requiredClaims:['sub','exp','iat']});
      userId=Number(payload.axia_user_id); if(!Number.isSafeInteger(userId)||userId<=0||payload.sub!==String(userId)) throw Error();
    } catch {return fail(401,'Sesión inválida.');}
    const db=createClient(url,service,{auth:{persistSession:false,autoRefreshToken:false}});
    const actor=await db.from('db_usuarios').select('usu_tipo,usu_activo,usu_acceso_habilitado,usu_fecha_baja').eq('id_usuario',userId).maybeSingle();
    if(actor.error) throw actor.error;
    if(!actor.data || actor.data.usu_activo!==true || actor.data.usu_acceso_habilitado!==true || actor.data.usu_fecha_baja!==null || ![1,2,3,4,5,6].includes(Number(actor.data.usu_tipo))) return fail(403,'Acceso no autorizado.');
    stage='INPUT';
    let body:unknown; try {body=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(await bounded(req,9_000_000)));} catch(e){if(e instanceof Fault) throw e; return fail(400,'JSON inválido.');}
    if(!isObject(body)) return fail(400,'Solicitud inválida.');
    const accion=String(body.accion??''), solicitud=String(body.solicitud??''), operacion=String(body.operacion??'');
    if(!['abrir_sesion','preparar_anexo','confirmar_anexo','finalizar'].includes(accion)||!uuid.test(solicitud)||!['ALTA','EDICION','REVISION_ESI'].includes(operacion)) return fail(400,'Acción o identificador inválido.');
    stage='PILOT';
    if(Deno.env.get('AXIA_OBC_ANEXOS_V2_PILOT')!==`${userId}:${operacion}:${solicitud}`) return fail(403,'Operación piloto no habilitada.');
    const grant=req.headers.get('x-axia-desktop-grant');
    if(grant!==null || operacion!=='ALTA') {
      if(!grant || !hashPattern.test(grant)) return fail(403,'Autorización corporativa requerida.');
      const digest=await sha(encoder.encode(grant)); const grants=JSON.parse(Deno.env.get('AXIA_DESKTOP_EVIDENCE_GRANTS')??'{}');
      if(!isObject(grants) || !Object.prototype.hasOwnProperty.call(grants,digest) || !Array.isArray(grants[digest]) || !(grants[digest] as unknown[]).includes(userId)) return fail(403,'Autorización corporativa requerida.');
    }
    const rpc=async (name:string,args:Record<string,unknown>)=>{const r=await db.rpc(name,args); if(r.error) rpcFault(r.error); return r.data;};
    const readSession=async()=>{const r=await db.from('axia_obc_sesiones_anexos').select('*').eq('solicitud',solicitud).eq('id_usuario',userId).maybeSingle(); if(r.error) throw r.error; if(!r.data||r.data.operacion!==operacion) throw new Fault(403,'Sesión no autorizada.'); return r.data;};
    const readAnexo=async(archivo:string)=>{const r=await db.from('axia_obc_registro_anexos').select('*').eq('solicitud',solicitud).eq('archivo',archivo).maybeSingle(); if(r.error) throw r.error; if(!r.data) throw new Fault(404,'Anexo no preparado.'); return r.data;};
    const verify=async(a:any)=>{
      if(a.bucket_id!=='bitacoras-evidencias'||typeof a.storage_path!=='string'||!hashPattern.test(a.sha256)||!Object.prototype.hasOwnProperty.call(formats,a.mime_type)) throw Error('REGISTRY');
      const expected=Number(a.size_bytes), max=a.clase==='foto'?20971520:31457280;
      if(!Number.isSafeInteger(expected)||expected<1||expected>max) throw Error('REGISTRY');
      const path=a.storage_path.split('/').map(encodeURIComponent).join('/');
      const r=await fetch(`${url.replace(/\/$/,'')}/storage/v1/object/authenticated/${a.bucket_id}/${path}`,{headers:{Authorization:`Bearer ${service}`,apikey:service},redirect:'error'});
      if(!r.ok){await r.body?.cancel(); if(r.status===404||r.status===400) throw new Fault(409,'El archivo todavía no llegó a Storage.'); throw Error('STORAGE');}
      const bytes=await bounded(r,expected);
      if(bytes.length!==expected||await sha(bytes)!==a.sha256) throw new Fault(422,'La integridad del archivo no coincide.');
      if(!formatMatches(a.mime_type,bytes)) throw new Fault(415,'El contenido no coincide con el formato declarado.');
      return {p_sha256_verificado:a.sha256,p_tamano_verificado:bytes.length,p_mime_verificado:a.mime_type};
    };
    const confirm=async(a:any)=>{const checked=await verify(a); return await rpc('axia_obc_confirmar_anexo',{p_usuario:userId,p_solicitud:solicitud,p_archivo:a.archivo,...checked});};
    stage='SESSION';
    if(accion==='abrir_sesion') {
      const folio=body.folio??null, autorizacion=body.autorizacion??null;
      if((folio!==null&&(typeof folio!=='string'||!/^OBC-[0-9]{4,}$/.test(folio)))||(autorizacion!==null&&(typeof autorizacion!=='string'||!uuid.test(autorizacion)))) return fail(400,'Origen inválido.');
      const existing=await db.from('axia_obc_sesiones_anexos').select('*').eq('solicitud',solicitud).eq('id_usuario',userId).maybeSingle();
      if(existing.error) throw existing.error;
      if(existing.data?.estado==='COMPLETADA') {
        const a=existing.data;
        if(a.operacion!==operacion||a.folio_origen!==folio||a.autorizacion_esi!==autorizacion) return fail(409,'La sesión completada no coincide con la solicitud.');
        if((operacion==='EDICION'&&![1,2,3,5].includes(Number(actor.data.usu_tipo)))||(operacion==='REVISION_ESI'&&Number(actor.data.usu_tipo)!==6)) return fail(403,'Operación no autorizada.');
        return out(200,{ok:true,resultado:a});
      }
      const result=await rpc('axia_obc_abrir_sesion_anexos',{p_usuario:userId,p_solicitud:solicitud,p_operacion:operacion,p_folio:folio,p_autorizacion:autorizacion});
      return out(200,{ok:true,resultado:result});
    }
    const session=await readSession();
    if(accion==='finalizar') {
      stage='FINALIZE';
      const datos=body.datos, archivos=body.archivos;
      if(!isObject(datos)||!Array.isArray(archivos)||archivos.length>20||archivos.some(a=>typeof a!=='string'||!uuid.test(a))||new Set(archivos).size!==archivos.length) return fail(400,'Datos o manifiesto inválidos.');
      if(session.estado==='ABIERTA') {
        await rpc('axia_obc_autorizar_sesion_anexos',{p_usuario:userId,p_operacion:operacion,p_folio:session.folio_origen,p_autorizacion:session.autorizacion_esi});
        const rows=await db.from('axia_obc_registro_anexos').select('*').eq('solicitud',solicitud); if(rows.error) throw rows.error;
        if(rows.data.length!==archivos.length || rows.data.some(a=>a.estado!=='CONFIRMADA'||!archivos.includes(a.archivo))) return fail(409,'Manifiesto incompleto o anexo no confirmado.');
        for(const a of rows.data) await verify(a);
      }
      const result=await rpc('axia_obc_finalizar_anexos',{p_usuario:userId,p_solicitud:solicitud,p_datos:datos,p_archivos:archivos});
      return out(200,{ok:true,resultado:result});
    }
    if(session.estado!=='ABIERTA') return fail(409,'Sesión cerrada.');
    await rpc('axia_obc_autorizar_sesion_anexos',{p_usuario:userId,p_operacion:operacion,p_folio:session.folio_origen,p_autorizacion:session.autorizacion_esi});
    const archivo=String(body.archivo??''); if(!uuid.test(archivo)) return fail(400,'Identificador de anexo inválido.');
    if(accion==='confirmar_anexo') {stage='CONFIRM'; const a=await readAnexo(archivo);return out(200,{ok:true,resultado:await confirm(a)});}
    stage='PREPARE';
    const clase=String(body.clase??''),nombre=String(body.nombre??''),mime=String(body.mime??''),tamano=body.tamano,sha256=String(body.sha256??'');
    if(!['foto','plano'].includes(clase)||!nombre.trim()||nombre.length>160||!Object.prototype.hasOwnProperty.call(formats,mime)||!Number.isSafeInteger(tamano)||Number(tamano)<1||!hashPattern.test(sha256)) return fail(400,'Metadatos inválidos.');
    const a=await rpc('axia_obc_preparar_anexo',{p_usuario:userId,p_solicitud:solicitud,p_archivo:archivo,p_clase:clase,p_nombre:nombre,p_mime:mime,p_tamano:tamano,p_sha256:sha256});
    const bucket=db.storage.from(a.bucket_id);
    const info=await bucket.info(a.storage_path);
    if(info.data) return out(200,{ok:true,resultado:{subido:true,anexo:await confirm(a)}});
    const error=info.error as any;
    if(!error||!(String(error.statusCode??error.status??'')==='404'||/not found|not_found/i.test(String(error.message??'')))) throw error??Error('INFO');
    if(a.estado!=='PREPARADA') return fail(409,'No se encontró el anexo confirmado.');
    const signed=await bucket.createSignedUploadUrl(a.storage_path,{upsert:false});
    if(signed.error||!signed.data?.token) throw signed.error??Error('SIGN');
    return out(200,{ok:true,resultado:{subido:false,bucket:a.bucket_id,ruta:a.storage_path,token:signed.data.token}});
  } catch(e) {
    if(e instanceof Fault) return fail(e.status,e.message);
    console.error(JSON.stringify({event:'axia-obc-anexos-v2-error',requestId,stage,code:String((e as any)?.code??'INTERNAL')}));
    return fail(503,'No se pudo confirmar la operación. Conserva el borrador.');
  }
});
