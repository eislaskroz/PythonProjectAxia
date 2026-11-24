import { createClient } from 'npm:@supabase/supabase-js@2';

const enc = new TextEncoder();
const dec = new TextDecoder();
const secret = Deno.env.get('AXIA_ALMACEN_JWT_SECRET') ?? '';
const url = Deno.env.get('SUPABASE_URL') ?? '';
const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '';
if (secret.length < 32 || !url || !serviceKey) throw new Error('Configuración segura incompleta');
const db = createClient(url, serviceKey, {auth: {persistSession:false, autoRefreshToken:false}});
const key = await crypto.subtle.importKey('raw', enc.encode(secret), {name:'HMAC',hash:'SHA-256'},false,['verify']);
const headers = {
  'Content-Type':'application/json; charset=utf-8',
  'Access-Control-Allow-Origin':'*',
  'Access-Control-Allow-Methods':'POST, OPTIONS',
  'Access-Control-Allow-Headers':'apikey,authorization,content-type,x-axia-almacen-session',
};
const response = (status:number, body:unknown) => new Response(JSON.stringify(body),{status,headers});
const decode = (s:string):Uint8Array => {
  const padded=s.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-s.length%4)%4);
  return Uint8Array.from(atob(padded),c=>c.charCodeAt(0));
};

async function identity(token:string):Promise<{id:number,rol:number}> {
  if (!token || token.length>5000) throw new Error('SESION_INVALIDA');
  const parts=token.split('.');
  if (parts.length!==3 || parts.some(p=>!p || p.length>2500)) throw new Error('SESION_INVALIDA');
  const signed=enc.encode(`${parts[0]}.${parts[1]}`);
  let head:Record<string,unknown>, payload:Record<string,unknown>;
  try {
    const sig=decode(parts[2]);
    if (!await crypto.subtle.verify('HMAC',key,sig,signed)) throw new Error('SESION_INVALIDA');
    head=JSON.parse(dec.decode(decode(parts[0])));
    payload=JSON.parse(dec.decode(decode(parts[1])));
  } catch {throw new Error('SESION_INVALIDA');}
  const now=Math.floor(Date.now()/1000);
  if(head.alg!=='HS256' || head.typ!=='JWT' || payload.alcance!=='levantamientos_lectura' ||
    typeof payload.uid!=='string' || !/^\d{1,18}$/.test(payload.uid) ||
    typeof payload.iat!=='number' || !Number.isInteger(payload.iat) ||
    typeof payload.exp!=='number' || !Number.isInteger(payload.exp) ||
    payload.iat>now+60 || payload.exp<=now || payload.exp-payload.iat>43200) throw new Error('SESION_INVALIDA');
  const id=Number(payload.uid);
  if(!Number.isSafeInteger(id)) throw new Error('SESION_INVALIDA');
  const {data:usuario,error}=await db.from('db_usuarios').select('id_usuario,usu_tipo').eq('id_usuario',id).maybeSingle();
  if(error || !usuario) throw new Error('SESION_INVALIDA');
  return {id,rol:Number(usuario.usu_tipo)};
}

Deno.serve(async req=>{
  if(req.method==='OPTIONS') return new Response('ok',{headers});
  if(req.method!=='POST') return response(405,{ok:false,error:'Método no permitido.'});
  try {
    const raw=await req.text();
    if(raw.length>9000000) return response(413,{ok:false,error:'Datos demasiado grandes.'});
    let entrada:Record<string,unknown>;
    try {entrada=JSON.parse(raw);} catch {return response(400,{ok:false,error:'JSON inválido.'});}
    if(!entrada || typeof entrada!=='object' || Array.isArray(entrada)) return response(400,{ok:false,error:'Solicitud inválida.'});
    const actor=await identity(req.headers.get('x-axia-almacen-session')??'');
    const accion=String(entrada.accion??'');
    if(!['solicitar','listar_pendientes','resolver','permiso_vigente','guardar_revision',
      'solicitar_obc','listar_pendientes_obc','resolver_obc','permiso_vigente_obc','guardar_revision_obc'].includes(accion))
      return response(400,{ok:false,error:'Acción desconocida.'});
    if((accion==='guardar_revision' && JSON.stringify(entrada.datos??{}).length>1600000) ||
      (accion==='guardar_revision_obc' && JSON.stringify(entrada.datos??{}).length>8000000))
      return response(413,{ok:false,error:'El formulario excede el tamaño permitido.'});
    const funcion=accion.endsWith('_obc')?'axia_esi_obc_operacion_segura':'axia_esi_operacion_segura';
    const {data,error}=await db.rpc(funcion,{
      p_accion:accion,p_actor:actor.id,p_rol:actor.rol,p_entrada:entrada,
    });
    if(error) {
      const msg=String(error.message??'');
      const code=String(error.code??'');
      if(code==='42501' || /SIN_AUTORIZACION|SOLO_ESI|ROL_NO_AUTORIZADO|AUTOAUTORIZACION|SESION_SIN_PERMISO/.test(msg))
        return response(403,{ok:false,error:'No tienes autorización vigente para esta operación.'});
      if(/LEV_EN_COTIZACION|LEV_YA_VALIDADO|LEV_TIENE_VERSION|OBC_EN_COTIZACION|OBC_YA_VALIDADA|OBC_TIENE_VERSION|SOLICITUD_YA_RESUELTA|SOLICITUD_ACTIVA|23505/.test(msg) || code==='23505')
        return response(409,{ok:false,error:'El levantamiento ya fue validado, enviado a cotización, versionado o tiene una solicitud activa.'});
      if(/INVALIDO|INVALIDA|NO_ENCONTRAD|CAMPOS_NO_AUTORIZADOS|DATOS_DEMASIADO|FOLIO_OBC_NO_GENERADO/.test(msg))
        return response(400,{ok:false,error:'Los datos o el folio no son válidos.'});
      console.error('AXIA ESI RPC',code,msg);
      return response(500,{ok:false,error:'No fue posible completar la operación.'});
    }
    return response(200,{ok:true,resultado:data});
  } catch(e) {
    if(e instanceof Error && e.message==='SESION_INVALIDA')
      return response(401,{ok:false,error:'Sesión vencida o inválida. Vuelve a iniciar sesión en AXIA.'});
    console.error('AXIA ESI',e instanceof Error?e.message:String(e));
    return response(500,{ok:false,error:'Error de servidor. La operación no fue confirmada.'});
  }
});
