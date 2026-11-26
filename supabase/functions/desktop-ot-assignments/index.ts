import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { jwtVerify } from "https://deno.land/x/jose@v5.9.6/index.ts";
const out=(status:number,body:unknown)=>new Response(JSON.stringify(body),{status,headers:{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store"}});
const validId=(v:unknown)=>typeof v==="number"&&Number.isSafeInteger(v)&&v>0;
Deno.serve(async(req)=>{
 const requestId=crypto.randomUUID();
 const fail=(status:number,error:string)=>out(status,{ok:false,error,requestId});
 if(req.method!=="POST")return fail(405,"Método no permitido");
 try {
  const match=/^Bearer\s+(\S+)$/i.exec(req.headers.get("authorization")??"");
  const secret=Deno.env.get("AXIA_MOBILE_JWT_SECRET");
  if(!secret)throw new Error("CONFIG");
  if(!match)return fail(401,"Sesión inválida");
  let id:number;
  try {const {payload}=await jwtVerify(match[1],new TextEncoder().encode(secret),{algorithms:["HS256"],issuer:"axia-field",audience:"axia-mobile",requiredClaims:["sub","iat","exp"]});id=Number(payload.axia_user_id);if(!validId(id)||payload.sub!==String(id))return fail(401,"Sesión inválida");}catch{return fail(401,"Sesión inválida");}
  const grant=req.headers.get("x-axia-desktop-grant")??"";
  if(!/^[a-f0-9]{64}$/.test(grant))return fail(403,"Autorización corporativa requerida");
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(grant))),b=>b.toString(16).padStart(2,"0")).join("");
  const grants=JSON.parse(Deno.env.get("AXIA_DESKTOP_EVIDENCE_GRANTS")??"{}");
  if(!grants||!Object.prototype.hasOwnProperty.call(grants,hash)||!Array.isArray(grants[hash])||!grants[hash].includes(id))return fail(403,"Autorización corporativa requerida");
  const url=Deno.env.get("SUPABASE_URL"),key=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");if(!url||!key)throw new Error("CONFIG");
  const db=createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false}});
  const actor=await db.from("db_usuarios").select("usu_tipo,usu_activo,usu_acceso_habilitado,usu_fecha_baja").eq("id_usuario",id).maybeSingle();
  if(actor.error)throw actor.error;
  if(!actor.data||Number(actor.data.usu_tipo)!==1||actor.data.usu_activo!==true||actor.data.usu_acceso_habilitado!==true||actor.data.usu_fecha_baja!==null)return fail(403,"Solo administrador autorizado");
  let p;try{p=await req.json();}catch{return fail(400,"Solicitud inválida");}
  if(!validId(p?.ot_id)||!["list","save"].includes(p?.action))return fail(400,"Solicitud inválida");
  if(p.action==="save"){
   if(!Array.isArray(p.expected)||!Array.isArray(p.users)||p.expected.length>1000||p.users.length>100||!p.expected.every(validId)||!p.users.every(validId))return fail(400,"Selección inválida");
   const r=await db.rpc("axia_desktop_save_ot_assignments",{p_actor:id,p_ot:p.ot_id,p_expected:p.expected,p_users:p.users});
   if(r.error){if(r.error.code==="40001")return fail(409,"Las asignaciones cambiaron. Cierra y vuelve a abrir.");if(r.error.code==="42501")return fail(403,"No autorizado");if(r.error.code==="22023")return fail(422,"OT cerrada o personal no válido. Revisa la selección.");throw r.error;}
   return out(200,{ok:true,requestId});
  }
  const ot=await db.from("db_ordenes_trabajo").select("ot_id,ot_folio,ot_estatus,ot_jefe_operacion,ot_supervisor").eq("ot_id",p.ot_id).maybeSingle();if(ot.error)throw ot.error;if(!ot.data)return fail(404,"OT no encontrada");
  const users=await db.from("db_usuarios").select("id_usuario,usu_nickname,usu_nombre,usu_apellido,usu_tipo").in("usu_tipo",[2,3,4]).eq("usu_activo",true).eq("usu_acceso_habilitado",true).is("usu_fecha_baja",null).order("id_usuario").limit(1000);if(users.error)throw users.error;
  const rows=await db.from("axia_ot_asignaciones").select("id_asignacion,id_usuario,rol_operativo,activo,asignado_en,asignado_por_id,desactivado_en,desactivado_por_id").eq("ot_id",p.ot_id).order("activo",{ascending:false}).order("id_asignacion",{ascending:false}).limit(1000);if(rows.error)throw rows.error;
  if((users.data?.length??0)>=1000||(rows.data?.length??0)>=1000)return fail(409,"Límite de consulta alcanzado; solicita revisión a TI");
  return out(200,{ok:true,requestId,ot:ot.data,users:users.data,assignments:rows.data});
 }catch{console.error(JSON.stringify({event:"desktop-ot-assignments-error",requestId}));return fail(500,"No fue posible procesar asignaciones");}
});
