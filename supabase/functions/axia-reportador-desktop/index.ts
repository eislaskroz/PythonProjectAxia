/** AXIA Reportador Fotográfico Nativo - Edge Function.
 * Sesión propia emitida SOLO al validar las credenciales ya introducidas
 * en el login de AXIA Desktop. Nunca se guarda una contraseña en Desktop.
 * Los clientes Windows usan solo anon/publishable; service_role solo en Edge.
 */
import {createClient} from 'npm:@supabase/supabase-js@2';
import bcrypt from 'npm:bcryptjs@2.4.3';
const URL=Deno.env.get('SUPABASE_URL')??'';
const SR=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')??'';
const db=createClient(URL,SR,{auth:{persistSession:false,autoRefreshToken:false}});
const BUCKET='axia-reportador';
const MAX_BASE64=1_500_000; // JPG normalizado en Desktop <~1MB
const serial=(value:unknown)=>JSON.stringify(value);
const reply=(v:unknown,status=200)=>new Response(serial(v),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff'}});
class ApiError extends Error {constructor(message:string,public status=400){super(message);}}
function check(e:unknown) { if(e){ const err=e as {message?:string,code?:string};throw new ApiError(err.message||'Error de Supabase',500);} }
async function sha(text:string){const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));return [...new Uint8Array(digest)].map(x=>x.toString(16).padStart(2,'0')).join('');}
function tokenNew(){const b=crypto.getRandomValues(new Uint8Array(32));return [...b].map(x=>x.toString(16).padStart(2,'0')).join('');}
function idPositive(v:unknown){const x=Number(v);if(!Number.isSafeInteger(x)||x<1)throw new ApiError('Identificador inválido');return x;}
function str(v:unknown,max=500){return String(v??'').trim().slice(0,max);}
function uuid(v:unknown){const s=str(v,80);if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(s))throw new ApiError('Identificador de actividad inválido');return s;}
function numberIn(v:unknown,minimum:number,maximum:number){const x=Number(v);if(!Number.isInteger(x)||x<minimum||x>maximum)throw new ApiError('Cantidad fuera de rango');return x;}
async function session(body:Record<string,unknown>){
 const token=str(body.token,128);
 if(!/^[0-9a-f]{64}$/.test(token))throw new ApiError('Sesión del Reportador no disponible: vuelve a iniciar sesión en AXIA',401);
 const {data:s,error:e}=await db.from('axia_rf_sesiones').select('usuario_id,expira_en').eq('token_hash',await sha(token)).maybeSingle();check(e);
 if(!s||Date.parse(s.expira_en)<Date.now())throw new ApiError('Sesión del Reportador vencida: vuelve a iniciar sesión en AXIA',401);
 const {data:u,error:ue}=await db.from('db_usuarios').select('id_usuario,usu_nickname,usu_nombre,usu_apellido,usu_tipo,usu_activo,usu_acceso_habilitado').eq('id_usuario',s.usuario_id).maybeSingle();check(ue);
 if(!u||u.usu_activo!==true||u.usu_acceso_habilitado!==true||![1,2,3,4].includes(Number(u.usu_tipo)))throw new ApiError('Acceso restringido a roles 1, 2, 3 y 4',403);
 return {id:Number(u.id_usuario),role:Number(u.usu_tipo),name:`${u.usu_nombre??''} ${u.usu_apellido??''}`.trim()};
}
async function owned(id:number,actor:{id:number,role:number},writable=false){
 const {data:r,error:e}=await db.from('axia_rf_reportes').select('*').eq('id_reporte',id).maybeSingle();check(e);
 if(!r||(actor.role!==1&&Number(r.usuario_creador_id)!==actor.id))throw new ApiError('Reporte no encontrado o sin permiso',404);
 if(writable&&r.estado!=='BORRADOR')throw new ApiError('Reporte finalizado: edición bloqueada',409);
 return r;
}
async function fileUpload(body:Record<string,unknown>,actor:{id:number,role:number},type:'foto'|'os'){
 const id=idPositive(body.id),r=await owned(id,actor,true);
 const numero=numberIn(body.numero,1,type==='foto'?5:4);
 const clave=type==='foto'?uuid(body.clave):null;
 if(type==='foto'){
  const {data:a,error:e}=await db.from('axia_rf_actividades').select('cantidad_fotos').eq('id_reporte',id).eq('clave',clave).maybeSingle();check(e);
  if(!a||numero>Number(a.cantidad_fotos))throw new ApiError('La foto no corresponde a una actividad o está fuera del límite');
 }else if(numero>Number(r.cantidad_os))throw new ApiError('La OS está fuera de las órdenes seleccionadas');
 const data=str(body.base64,MAX_BASE64+10);
 if(!data||data.length>MAX_BASE64||!/^[A-Za-z0-9+/]+={0,2}$/.test(data))throw new ApiError('Imagen demasiado grande o inválida (máximo ~2 MB normalizada)');
 let bytes:Uint8Array;
 try{const binary=atob(data);bytes=Uint8Array.from(binary,ch=>ch.charCodeAt(0));}
 catch{throw new ApiError('No se pudo leer la fotografía');}
 if(bytes.length<4||bytes[0]!==0xff||bytes[1]!==0xd8||bytes[bytes.length-2]!==0xff||bytes[bytes.length-1]!==0xd9)throw new ApiError('El archivo debe ser JPEG válido');
 const path=type==='foto'?`${id}/actividades/${clave}/${numero}-${crypto.randomUUID()}.jpg`:`${id}/os/${numero}-${crypto.randomUUID()}.jpg`;
 const table=type==='foto'?'axia_rf_fotos':'axia_rf_os';
 let q=db.from(table).select('ruta').eq('id_reporte',id).eq('numero',numero);
 if(type==='foto')q=q.eq('clave_actividad',clave!);
 const {data:old,error:oe}=await q.maybeSingle();check(oe);
 const {error:ue}=await db.storage.from(BUCKET).upload(path,bytes,{contentType:'image/jpeg',upsert:false});check(ue);
 const fields=type==='foto'?{id_reporte:id,clave_actividad:clave,numero,ruta:path,nombre_original:str(body.nombre,255)}:{id_reporte:id,numero,ruta:path,nombre_original:str(body.nombre,255)};
 const {error:pe}=await db.from(table).upsert(fields,{onConflict:type==='foto'?'id_reporte,clave_actividad,numero':'id_reporte,numero'});
 if(pe){await db.storage.from(BUCKET).remove([path]);check(pe);}
 if(old?.ruta&&old.ruta!==path)await db.storage.from(BUCKET).remove([old.ruta]);
 return {ok:true,ruta:path};
}
async function fileRemove(body:Record<string,unknown>,actor:{id:number,role:number}){
 const id=idPositive(body.id),type=body.tipo==='os'?'os':'foto',num=numberIn(body.numero,1,type==='os'?4:5);
 await owned(id,actor,true);
 const table=type==='os'?'axia_rf_os':'axia_rf_fotos';
 let q=db.from(table).select('ruta').eq('id_reporte',id).eq('numero',num);
 const key=type==='foto'?uuid(body.clave):null;
 if(key)q=q.eq('clave_actividad',key);
 const {data:old,error:oe}=await q.maybeSingle();check(oe);
 if(old){let d=db.from(table).delete().eq('id_reporte',id).eq('numero',num);if(key)d=d.eq('clave_actividad',key);const {error:e}=await d;check(e);await db.storage.from(BUCKET).remove([old.ruta]);}
 return {ok:true};
}
async function fileRead(body:Record<string,unknown>,actor:{id:number,role:number}){
 const id=idPositive(body.id),type=body.tipo==='os'?'os':'foto',num=numberIn(body.numero,1,type==='os'?4:5);
 await owned(id,actor);
 let q=db.from(type==='os'?'axia_rf_os':'axia_rf_fotos').select('ruta').eq('id_reporte',id).eq('numero',num);
 if(type==='foto')q=q.eq('clave_actividad',uuid(body.clave));
 const {data:item,error:e}=await q.maybeSingle();check(e);
 if(!item)throw new ApiError('Imagen no encontrada',404);
 const {data:file,error:de}=await db.storage.from(BUCKET).download(item.ruta);check(de);
 if(!file)throw new ApiError('Fotografía no disponible',404);
 const bytes=new Uint8Array(await file.arrayBuffer());let value='';
 for(let start=0;start<bytes.length;start+=16_384){value+=String.fromCharCode(...bytes.subarray(start,start+16_384));}
 return {base64:btoa(value),mime:'image/jpeg'};
}
Deno.serve(async(req)=>{
 if(req.method!=='POST')return reply({error:'Método no permitido'},405);
 if(!URL||!SR)return reply({error:'Edge Function no configurada con service_role'},503);
 try{
  const body=await req.json() as Record<string,unknown>;
  if(!body||Array.isArray(body)||typeof body!=='object')throw new ApiError('Solicitud inválida');
  const op=str(body.accion,40);
  if(op==='iniciar_sesion'){
   const username=str(body.usuario,120),pass=String(body.contrasena??'');
   if(!username||!pass||pass.length>256)throw new ApiError('Credenciales no válidas',401);
   // Se contabiliza cada solicitud *antes* de consultar el hash bcrypt; el
   // límite es atómico y compartido entre todas las instancias de Edge.
   const accountHash=await sha(username.toLocaleLowerCase('es-MX'));
   const {data:allowed,error:rateError}=await db.rpc('axia_rf_solicitud_login',{p_cuenta_hash:accountHash});check(rateError);
   if(allowed!==true)throw new ApiError('Demasiados intentos. Intenta nuevamente en 15 minutos.',429);
   // Escapa comodines de ILIKE: el nombre es una identidad, no un patrón.
   const usernamePattern=username.replace(/[\\%_]/g,'\\$&');
   const {data:users,error:e}=await db.from('db_usuarios').select('id_usuario,usu_tipo,usu_password,usu_activo,usu_acceso_habilitado').ilike('usu_nickname',usernamePattern).limit(1);check(e);
   const u=users?.[0],hash=String(u?.usu_password??'');
   if(!u||u.usu_activo!==true||u.usu_acceso_habilitado!==true||![1,2,3,4].includes(Number(u.usu_tipo))||
      !hash.startsWith('$2')||!(await bcrypt.compare(pass,hash)))throw new ApiError('Usuario no autorizado en Reportes',403);
   const token=tokenNew();
   const expira=new Date(Date.now()+16*60*60*1000).toISOString();
   const {error:se}=await db.from('axia_rf_sesiones').insert({token_hash:await sha(token),usuario_id:u.id_usuario,expira_en:expira});check(se);
   // Al autenticar exitosamente, restablece el contador de este usuario.
   await db.from('axia_rf_intentos_login').delete().eq('cuenta_hash',accountHash);
   return reply({token,expira});
  }
  const actor=await session(body);
  if(op==='acos'){
   // Consulta privada al maestro existente db_acos: nunca se expone con anon.
   const buscar=str(body.buscar,100).replace(/[^\p{L}\p{N}\s-]/gu,' ').trim();
   let q=db.from('db_acos').select('aco_numero,aco_cliente,aco_descripcion,id_sucursal')
      .order('aco_numero',{ascending:false}).limit(100);
   if(buscar)q=q.or(`aco_numero.ilike.%${buscar}%,aco_cliente.ilike.%${buscar}%`);
   const {data:acos,error:ae}=await q;check(ae);
   const ids=[...new Set((acos??[]).map(a=>a.id_sucursal).filter((id)=>id!==null&&id!==undefined))];
   const sucursales=new Map<string,string>();
   if(ids.length){
    const {data:sedes,error:se}=await db.from('db_clientes_sucursales')
       .select('suc_id,suc_nombre').in('suc_id',ids);check(se);
    for(const suc of sedes??[])sucursales.set(String(suc.suc_id),str(suc.suc_nombre,200));
   }
   return reply({acos:(acos??[]).map(a=>({
     aco_numero:str(a.aco_numero,60),
     cliente:str(a.aco_cliente,200),
     sucursal:sucursales.get(String(a.id_sucursal))??'',
     nombre_servicio:str(a.aco_descripcion,250)
   }))});
  }
  if(op==='aco_detalle'){
   const numero=str(body.numero,60);
   if(!numero)throw new ApiError('Selecciona un ACO válido');
   const {data:aco,error:ae}=await db.from('db_acos')
      .select('aco_numero,aco_cliente,aco_descripcion,id_sucursal')
      .eq('aco_numero',numero).maybeSingle();check(ae);
   if(!aco)throw new ApiError('El ACO ya no existe en AXIA',404);
   let sucursal='',servicio=str(aco.aco_descripcion,250);
   if(aco.id_sucursal!==null&&aco.id_sucursal!==undefined){
    const {data:sede,error:se}=await db.from('db_clientes_sucursales')
      .select('suc_nombre').eq('suc_id',aco.id_sucursal).maybeSingle();check(se);
    sucursal=str(sede?.suc_nombre,200);
   }
   // ACOs nuevos suelen tener aco_descripcion vacía. Utilizar datos reales
   // de OT y OS vinculadas antes de pedir captura manual de servicio/sitio.
   if(!sucursal||!servicio){
    const {data:ot,error:ote}=await db.from('db_ordenes_trabajo')
      .select('ot_asunto,ot_sucursal').eq('ot_aco_numero',numero)
      .order('fecha_registro',{ascending:false}).limit(1).maybeSingle();check(ote);
    if(!servicio)servicio=str(ot?.ot_asunto,250);
    if(!sucursal)sucursal=str(ot?.ot_sucursal,200);
   }
   if(!sucursal||!servicio){
    const {data:os,error:ose}=await db.from('db_ordenes_servicio')
      .select('os_tipo_servicio,os_actividad,os_sucursal').eq('os_aco_numero',numero)
      .order('fecha_registro',{ascending:false}).limit(1).maybeSingle();check(ose);
    if(!servicio)servicio=str(os?.os_tipo_servicio||os?.os_actividad,250);
    if(!sucursal)sucursal=str(os?.os_sucursal,200);
   }
   if(!sucursal||!servicio){
    const {data:lev,error:le}=await db.from('db_levantamientos')
      .select('lev_descripcion,lev_ubicacion').eq('lev_aco_numero',numero)
      .order('fecha_registro',{ascending:false}).limit(1).maybeSingle();check(le);
    if(!servicio&&String(lev?.lev_descripcion??'').length<=250)
      servicio=str(lev?.lev_descripcion,250);
    if(!sucursal)sucursal=str(lev?.lev_ubicacion,200);
   }
   return reply({aco:{aco_numero:str(aco.aco_numero,60),cliente:str(aco.aco_cliente,200),
     sucursal,nombre_servicio:servicio}});
  }
  if(op==='listar'){
   let q=db.from('axia_rf_reportes').select('id_reporte,aco,cliente,sucursal,nombre_servicio,fecha_servicio,estado,usuario_creador_id,actualizado_en,cantidad_os').order('actualizado_en',{ascending:false}).limit(200);
   if(actor.role!==1)q=q.eq('usuario_creador_id',actor.id);
   const search=str(body.buscar,100).replace(/[%_,.()\\*]/g,' ').trim();
   if(search)q=q.or(`aco.ilike.%${search}%,cliente.ilike.%${search}%,nombre_servicio.ilike.%${search}%`);
   const {data,error}=await q;check(error);return reply({reportes:data??[]});
  }
  if(op==='obtener'){
   const id=idPositive(body.id),r=await owned(id,actor);
   const [a,f,o,h]=await Promise.all([
     db.from('axia_rf_actividades').select('*').eq('id_reporte',id).order('orden'),
     db.from('axia_rf_fotos').select('clave_actividad,numero,nombre_original').eq('id_reporte',id),
     db.from('axia_rf_os').select('numero,nombre_original').eq('id_reporte',id).order('numero'),
     db.from('axia_rf_auditoria').select('usuario_id,accion,fecha').eq('id_reporte',id).order('fecha',{ascending:false}).limit(15)]);
   [a,f,o,h].forEach(x=>check(x.error));
   return reply({reporte:r,actividades:a.data??[],fotos:f.data??[],ordenes:o.data??[],auditoria:h.data??[]});
  }
  if(op==='guardar'){
   const id=body.id?idPositive(body.id):null;
   if(id)await owned(id,actor,true);
   const data=body.datos;
   if(!data||typeof data!=='object'||Array.isArray(data))throw new ApiError('Datos inválidos');
   const {data:created,error}=await db.rpc('axia_rf_guardar',{p_actor:actor.id,p_id:id,p_datos:data});check(error);
   return reply({id:created,ok:true});
  }
  if(op==='ordenes_cantidad'){
   const id=idPositive(body.id),qty=numberIn(body.cantidad,1,4);await owned(id,actor,true);
   const {data:updated,error:e}=await db.from('axia_rf_reportes').update({cantidad_os:qty,actualizado_en:new Date().toISOString()}).eq('id_reporte',id).eq('estado','BORRADOR').select('id_reporte');check(e);if(!updated?.length)throw new ApiError('El reporte fue finalizado durante la actualización',409);
   const {data:removed,error:re}=await db.from('axia_rf_os').select('ruta').eq('id_reporte',id).gt('numero',qty);check(re);
   const {error:de}=await db.from('axia_rf_os').delete().eq('id_reporte',id).gt('numero',qty);check(de);
   if(removed?.length)await db.storage.from(BUCKET).remove(removed.map(x=>x.ruta));
   return reply({ok:true});
  }
  if(op==='subir_foto'||op==='subir_os')return reply(await fileUpload(body,actor,op==='subir_foto'?'foto':'os'));
  if(op==='leer_imagen')return reply(await fileRead(body,actor));
  if(op==='quitar_imagen')return reply(await fileRemove(body,actor));
  if(op==='estado'){
    const id=idPositive(body.id);await owned(id,actor);
    const accion=str(body.nuevo,20);
    if(!['finalizar','reabrir'].includes(accion))throw new ApiError('Acción inválida');
    const {data,error}=await db.rpc('axia_rf_cambiar_estado',{p_actor:actor.id,p_id:id,p_accion:accion});check(error);
    return reply({estado:data,ok:true});
  }
  if(op==='autoguardar'){
    const clave=uuid(body.clave),data=body.datos;
    if(!data||typeof data!=='object'||Array.isArray(data))throw new ApiError('Borrador temporal inválido');
    if(JSON.stringify(data).length>250_000)throw new ApiError('Borrador temporal demasiado largo');
    const reportId=body.id?idPositive(body.id):null;
    if(reportId)await owned(reportId,actor,true);
    const {error}=await db.from('axia_rf_autoguardados').upsert({usuario_id:actor.id,clave,reporte_id:reportId,datos:data,actualizado_en:new Date().toISOString()},{onConflict:'usuario_id,clave'});check(error);
    return reply({ok:true});
  }
  if(op==='borradores'){
    const {data,error}=await db.from('axia_rf_autoguardados').select('clave,reporte_id,datos,actualizado_en').eq('usuario_id',actor.id).order('actualizado_en',{ascending:false}).limit(15);check(error);
    return reply({borradores:data??[]});
  }
  if(op==='borrar_autoguardado'){
    const {error}=await db.from('axia_rf_autoguardados').delete().eq('usuario_id',actor.id).eq('clave',uuid(body.clave));check(error);return reply({ok:true});
  }
  return reply({error:'Acción no permitida'},400);
 }catch(e){
   const err=e as Error;
   const status=e instanceof ApiError?e.status:500;
   if(status===500)console.error('AXIA RF Edge:',err?.message||String(e));
   return reply({error:status===500?'No se pudo completar la operación. Revisa el despliegue de Reportador y los logs de Supabase.':err?.message||'Operación no válida'},status);
 }
});
