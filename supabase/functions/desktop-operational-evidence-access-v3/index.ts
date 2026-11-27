import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { jwtVerify } from "https://deno.land/x/jose@v5.9.6/index.ts";
const BUCKET = "axia-operational-evidence";
// Read-only pilot: only the two confirmed test documents. Never use a client-supplied storage path.
const PILOT: Record<string,{type:string,sync:string,owner:number,ot:string}> = {
  "BIT-00024": {type:"BITACORA",sync:"aa197e09-b4da-4204-bc41-a9aee893656f",owner:20,ot:"OT-00009"},
  "OS-00005": {type:"ORDEN_SERVICIO",sync:"2cc3d2ba-7b0c-4731-9bca-512d69adb4ec",owner:20,ot:"OT-00009"},
};
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
Deno.serve(async (req:Request) => {
  const requestId=crypto.randomUUID();
  const out=(status:number,body:object)=>new Response(JSON.stringify({requestId,...body}),{status,headers:{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store"}});
  const fail=(status:number,error:string)=>out(status,{ok:false,error});
  if(req.method!=="POST")return fail(405,"Método no permitido.");
  try {
    const secret=Deno.env.get("AXIA_MOBILE_JWT_SECRET"),url=Deno.env.get("SUPABASE_URL"),key=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if(!secret||!url||!key)throw Error("CONFIG");
    let id:number;
    try {
      const token=req.headers.get("authorization")?.match(/^Bearer\s+(\S+)$/i)?.[1];
      if(!token)throw Error();
      const {payload}=await jwtVerify(token,new TextEncoder().encode(secret),{algorithms:["HS256"],issuer:"axia-field",audience:"axia-mobile",requiredClaims:["sub","exp","iat"]});
      id=Number(payload.axia_user_id);
      if(!Number.isSafeInteger(id)||id<=0||payload.sub!==String(id))throw Error();
    }catch{return fail(401,"Sesión inválida.");}
    const grant=req.headers.get("x-axia-desktop-grant")??"";
    if(!/^[a-f0-9]{64}$/.test(grant))return fail(403,"Autorización corporativa requerida.");
    const hash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(grant))),b=>b.toString(16).padStart(2,"0")).join("");
    const grants=JSON.parse(Deno.env.get("AXIA_DESKTOP_EVIDENCE_GRANTS")??"{}");
    if(!grants||typeof grants!=="object"||Array.isArray(grants)||!Object.prototype.hasOwnProperty.call(grants,hash)||!Array.isArray(grants[hash])||!grants[hash].includes(id))return fail(403,"Autorización corporativa requerida.");
    const db=createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false}});
    const actor=await db.from("db_usuarios").select("usu_tipo,usu_activo,usu_acceso_habilitado,usu_fecha_baja").eq("id_usuario",id).maybeSingle();
    if(actor.error)throw actor.error;
    if(!actor.data||Number(actor.data.usu_tipo)!==1||actor.data.usu_activo!==true||actor.data.usu_acceso_habilitado!==true||actor.data.usu_fecha_baja!==null)return fail(403,"Solo administrador autorizado para este piloto.");
    let body;try{body=await req.json();}catch{return fail(400,"Solicitud inválida.");}
    const folio=body?.folio;
    if(typeof folio!=="string"||!Object.prototype.hasOwnProperty.call(PILOT,folio))return fail(404,"Documento fuera del piloto.");
    const p=PILOT[folio], bit=p.type==="BITACORA";
    const doc=await db.from(bit?"db_bitacoras":"db_ordenes_servicio").select(bit?"id_bitacora,ot_id,bit_ot_folio,creado_por_id":"id_orden,ot_id,os_folio_ot,creado_por_id").eq(bit?"bit_folio":"os_folio",folio).maybeSingle();
    if(doc.error)throw doc.error;
    const d=doc.data as Record<string,unknown>|null;
    if(!d||d.creado_por_id!==p.owner||d[bit?"bit_ot_folio":"os_folio_ot"]!==p.ot)return fail(404,"Documento no disponible.");
    const sync=await db.from("axia_operational_sync").select("estado,folio,document_type").eq("id_usuario",p.owner).eq("sync_id",p.sync).maybeSingle();
    if(sync.error)throw sync.error;
    if(!sync.data||sync.data.estado!=="COMPLETADO"||sync.data.folio!==folio||sync.data.document_type!==p.type)return fail(409,"Documento no confirmado.");
    const manifest=await db.from("axia_operational_manifest_v3").select("ot_id,document_type,photo_ids").eq("id_usuario",p.owner).eq("sync_id",p.sync).maybeSingle();
    if(manifest.error)throw manifest.error;
    const ids=manifest.data?.photo_ids;
    if(!manifest.data||manifest.data.ot_id!==d.ot_id||manifest.data.document_type!==p.type||!Array.isArray(ids)||ids.length!==2||new Set(ids).size!==ids.length||!ids.every(x=>typeof x==="string"&&UUID.test(x)))return fail(409,"Manifiesto de prueba inconsistente.");
    const evidence=await db.from("axia_operational_evidence").select("photo_id,ot_id,document_type,storage_path,sha256,mime_type,size_bytes,estado,id_bitacora,id_orden").eq("id_usuario",p.owner).eq("sync_id",p.sync);
    if(evidence.error)throw evidence.error;
    const rows=evidence.data??[];
    if(rows.length!==ids.length)return fail(409,"Vinculación incompleta.");
    const photos=[];
    for(const photo of ids){
      const e=rows.find(x=>x.photo_id===photo),path=`v3/${p.owner}/${p.ot}/${p.type}/${p.sync}/${photo}`;
      if(!e||e.estado!=="VINCULADA"||e.ot_id!==d.ot_id||e.document_type!==p.type||e.storage_path!==path||e.id_bitacora!==(bit?d.id_bitacora:null)||e.id_orden!==(bit?null:d.id_orden)||!(/^[a-f0-9]{64}$/).test(e.sha256)||!["image/jpeg","image/png","image/webp"].includes(e.mime_type)||!Number.isSafeInteger(e.size_bytes)||e.size_bytes<1||e.size_bytes>10485760)return fail(409,"Evidencia inconsistente.");
      const signed=await db.storage.from(BUCKET).createSignedUrl(path,120);
      if(signed.error||!signed.data?.signedUrl)return fail(503,"Evidencia privada no disponible.");
      photos.push({photoId:photo,storagePath:path,sha256:e.sha256,mimeType:e.mime_type,sizeBytes:e.size_bytes,signedUrl:signed.data.signedUrl});
    }
    console.log(JSON.stringify({event:"desktop-operational-evidence-authorized",requestId,userId:id,folio,count:photos.length}));
    return out(200,{ok:true,folio,expiresIn:120,photos});
  }catch{console.error(JSON.stringify({event:"desktop-operational-evidence-error",requestId}));return fail(503,"No fue posible recuperar las evidencias.");}
});
