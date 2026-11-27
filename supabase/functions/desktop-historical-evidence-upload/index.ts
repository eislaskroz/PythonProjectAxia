import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { jwtVerify } from "https://deno.land/x/jose@v5.9.6/index.ts";

const BUCKET = "bitacoras-evidencias";
const LIMIT = 10485760;
const MODULES: Record<string, {table:string; folio:string; prefix:string; technical:boolean}> = {
  "bitacoras": {table:"db_bitacoras",folio:"bit_folio",prefix:"BIT",technical:false},
  "ordenes-servicio": {table:"db_ordenes_servicio",folio:"os_folio",prefix:"OS",technical:false},
  "levantamientos": {table:"db_levantamientos",folio:"lev_folio",prefix:"LEV",technical:false},
  "levantamientos-archivos": {table:"db_levantamientos",folio:"lev_folio",prefix:"LEV",technical:true},
};
const MIME: Record<string,string> = {jpg:"image/jpeg",jpeg:"image/jpeg",png:"image/png",webp:"image/webp",pdf:"application/pdf",dwg:"image/vnd.dwg",dxf:"image/vnd.dxf"};
const hex = (bytes: Uint8Array) => Array.from(bytes,b=>b.toString(16).padStart(2,"0")).join("");
const sha256 = async (bytes: Uint8Array) => hex(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes)));

function formatMatches(ext:string, bytes:Uint8Array):boolean {
  if (bytes.length < 12) return false;
  const at = (offset:number, s:string) => Array.from(s).every((c,i)=>bytes[offset+i]===c.charCodeAt(0));
  if (ext === "jpg" || ext === "jpeg") return bytes[0]===255 && bytes[1]===216 && bytes[2]===255 && bytes[bytes.length-2]===255 && bytes[bytes.length-1]===217;
  if (ext === "png") return [137,80,78,71,13,10,26,10].every((v,i)=>bytes[i]===v) && at(12,"IHDR");
  if (ext === "webp") return at(0,"RIFF") && at(8,"WEBP");
  if (ext === "pdf") return at(0,"%PDF-");
  if (ext === "dwg") return /^AC10[0-9]{2}/.test(new TextDecoder().decode(bytes.subarray(0,6)));
  if (ext === "dxf") return at(0,"AutoCAD Binary DXF") || /^\s*0\s*SECTION\b/i.test(new TextDecoder().decode(bytes.subarray(0,512)));
  return false;
}

async function readBounded(req:Request):Promise<Uint8Array> {
  const declared = req.headers.get("content-length");
  if (declared !== null && (!/^\d+$/.test(declared) || Number(declared)>LIMIT)) throw Error("SIZE");
  if (!req.body) throw Error("EMPTY");
  const reader = req.body.getReader();
  const chunks:Uint8Array[] = [];
  let size=0;
  try {
    for (;;) {
      const {done,value}=await reader.read();
      if (done) break;
      size+=value.byteLength;
      if (size>LIMIT) { await reader.cancel(); throw Error("SIZE"); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  if (!size || (declared!==null && size!==Number(declared))) throw Error("EMPTY");
  const bytes=new Uint8Array(size);
  let offset=0;
  for (const chunk of chunks) {bytes.set(chunk,offset);offset+=chunk.byteLength;}
  return bytes;
}

Deno.serve(async (req:Request) => {
  const requestId=crypto.randomUUID();
  const out=(status:number,body:object)=>new Response(JSON.stringify({requestId,...body}),{status,headers:{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store"}});
  const fail=(status:number,error:string)=>out(status,{ok:false,error});
  if (req.method!=="POST") return fail(405,"Método no permitido.");
  try {
    const secret=Deno.env.get("AXIA_MOBILE_JWT_SECRET"),url=Deno.env.get("SUPABASE_URL"),service=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!secret || !url || !service) throw Error("CONFIG");
    let userId:number;
    try {
      const token=req.headers.get("authorization")?.match(/^Bearer\s+(\S+)$/i)?.[1];
      if (!token) throw Error();
      const {payload}=await jwtVerify(token,new TextEncoder().encode(secret),{algorithms:["HS256"],issuer:"axia-field",audience:"axia-mobile",requiredClaims:["sub","exp","iat"]});
      userId=Number(payload.axia_user_id);
      if (!Number.isSafeInteger(userId) || userId<=0 || payload.sub!==String(userId)) throw Error();
    } catch { return fail(401,"Sesión inválida."); }
    const grant=req.headers.get("x-axia-desktop-grant")??"";
    if (!/^[a-f0-9]{64}$/.test(grant)) return fail(403,"Autorización corporativa requerida.");
    const hash=await sha256(new TextEncoder().encode(grant));
    const grants=JSON.parse(Deno.env.get("AXIA_DESKTOP_EVIDENCE_GRANTS")??"{}");
    if (!grants || typeof grants!=="object" || Array.isArray(grants) || !Object.prototype.hasOwnProperty.call(grants,hash) || !Array.isArray(grants[hash]) || !grants[hash].includes(userId)) return fail(403,"Autorización corporativa requerida.");
    const db=createClient(url,service,{auth:{persistSession:false,autoRefreshToken:false}});
    const actor=await db.from("db_usuarios").select("usu_tipo,usu_activo,usu_acceso_habilitado,usu_fecha_baja").eq("id_usuario",userId).maybeSingle();
    if (actor.error) throw actor.error;
    if (!actor.data || Number(actor.data.usu_tipo)!==1 || actor.data.usu_activo!==true || actor.data.usu_acceso_habilitado!==true || actor.data.usu_fecha_baja!==null) return fail(403,"Acceso no autorizado.");
    const module=req.headers.get("x-axia-module")??"",folio=req.headers.get("x-axia-folio")??"",fileId=req.headers.get("x-axia-file-id")??"",ext=req.headers.get("x-axia-extension")??"",expected=req.headers.get("x-axia-sha256")??"";
    if (!Object.prototype.hasOwnProperty.call(MODULES,module)) return fail(400,"Módulo de carga no permitido.");
    const cfg=MODULES[module];
    if (!new RegExp(`^${cfg.prefix}-[0-9]{5,15}$`).test(folio) || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(fileId) || !/^[a-f0-9]{64}$/.test(expected) || !Object.prototype.hasOwnProperty.call(MIME,ext)) return fail(400,"Datos de evidencia inválidos.");
    if (!cfg.technical && !["jpg","jpeg","png","webp"].includes(ext)) return fail(415,"Formato no permitido.");
    const mime=MIME[ext];
    if (req.headers.get("content-type")!==mime) return fail(415,"Tipo de contenido no permitido.");
    const document=await db.from(cfg.table).select(cfg.folio).eq(cfg.folio,folio).maybeSingle();
    if (document.error) throw document.error;
    if (!document.data) return fail(404,"Documento no disponible.");
    let bytes:Uint8Array;
    try {bytes=await readBounded(req);} catch(e) {return e instanceof Error && e.message==="SIZE"?fail(413,"Archivo superior a 10 MiB."):fail(400,"Archivo vacío o incompleto.");}
    if (!formatMatches(ext,bytes)) return fail(415,"El contenido no coincide con el formato declarado.");
    if (await sha256(bytes)!==expected) return fail(422,"La integridad del archivo no coincide.");
    const path=`${module}/${folio}/${fileId.replaceAll("-","")}_archivo.${ext}`;
    const bucket=db.storage.from(BUCKET);
    const upload=await bucket.upload(path,bytes,{contentType:mime,upsert:false});
    if (upload.error) {
      const existing=await bucket.download(path);
      if (existing.error || !existing.data) return fail(503,"No se pudo confirmar la carga.");
      if (existing.data.size!==bytes.length || await sha256(new Uint8Array(await existing.data.arrayBuffer()))!==expected) return fail(409,"Ya existe un archivo diferente con esa ruta.");
      console.log(JSON.stringify({event:"desktop-historical-upload-replay",requestId,userId,module,folio}));
      return out(200,{ok:true,bucket:BUCKET,storagePath:path,mime,sha256:expected,sizeBytes:bytes.length,alreadyUploaded:true});
    }
    console.log(JSON.stringify({event:"desktop-historical-upload",requestId,userId,module,folio}));
    return out(201,{ok:true,bucket:BUCKET,storagePath:path,mime,sha256:expected,sizeBytes:bytes.length,alreadyUploaded:false});
  } catch {
    console.error(JSON.stringify({event:"desktop-historical-upload-error",requestId}));
    return fail(503,"No fue posible confirmar la carga de evidencia.");
  }
});
