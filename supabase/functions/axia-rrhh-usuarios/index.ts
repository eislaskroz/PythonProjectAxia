/** AXIA RRHH rol 10: consulta, actualización, alta laboral y baja lógica auditada.
 * Los roles/contraseñas quedan a cargo de un Administrador. Requiere SQL de altas/bajas.
 * La service_role_key se usa SOLO en Edge Functions, nunca en Desktop.
 */
import { createClient } from 'npm:@supabase/supabase-js@2';
import bcrypt from 'npm:bcryptjs@2.4.3';
const url = Deno.env.get('SUPABASE_URL') ?? '';
const key = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '';
const db = createClient(url, key, {auth:{persistSession:false,autoRefreshToken:false}});
const FIELDS = [
 'usu_nombre','usu_apellido','usu_rfc','usu_curp','usu_imss','usu_ine',
 'usu_fechanac','usu_telefono','usu_correo','usu_depto','usu_puesto',
 'usu_calle','usu_numero','usu_colonia','usu_municipio','usu_estado',
 'usu_cp','usu_regimen'
];
const SELECT = ['id_usuario','usu_nickname','usu_tipo','usu_activo','usu_acceso_habilitado',...FIELDS].join(',');
function answer(body:unknown,status=200):Response {
 return new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
}
function validObject(x:unknown):x is Record<string,unknown> {
 return x!==null && typeof x==='object' && !Array.isArray(x);
}
function randomSecret():string {
 const bytes = crypto.getRandomValues(new Uint8Array(32));
 return Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
}
Deno.serve(async(req)=>{
 if(req.method!=='POST') return answer({error:'Método no permitido'},405);
 if(!url || !key) return answer({error:'Servicio sin configuración'},503);
 let body:any;
 try { body=await req.json(); } catch {return answer({error:'JSON inválido'},400);}
 if(!validObject(body)) return answer({error:'Solicitud inválida'},400);
 const usuario=String(body.usuario??'').trim().slice(0,120);
 const password=String(body.contrasena??'');
 const actorId=Number(body.actor_id);
 if(!usuario || !password || password.length>256 || !Number.isSafeInteger(actorId) || actorId<1)
   return answer({error:'Credenciales necesarias'},401);
 try {
   const {data:actors,error:authError}=await db.from('db_usuarios')
      .select('id_usuario,usu_nickname,usu_tipo,usu_password,usu_activo,usu_acceso_habilitado')
      .ilike('usu_nickname',usuario).limit(1);
   if(authError) throw authError;
   const actor=actors?.[0]; const hash=String(actor?.usu_password??'');
   const valida=hash.startsWith('$2') && await bcrypt.compare(password,hash);
   if(!valida || Number(actor?.usu_tipo)!==10 || Number(actor?.id_usuario)!==actorId ||
      actor?.usu_activo!==true || actor?.usu_acceso_habilitado!==true)
     return answer({error:'Se requiere cuenta activa de Recursos Humanos y contraseña válida'},403);
   const action=String(body.accion??'');
   if(action==='listar'){
     const termino=String(body.buscar??'').trim().slice(0,90);
     if(termino.length<2) return answer({error:'Escribe al menos dos caracteres para buscar empleados'},400);
     const limpio=termino.replace(/[,()%.*\\]/g,' ').trim();
     if(!limpio) return answer({error:'Búsqueda inválida'},400);
     const pagina=Math.max(1,Math.min(10000,Math.trunc(Number(body.pagina)||1)));
     const inicio=(pagina-1)*50;
     const {data,error,count}=await db.from('db_usuarios').select(SELECT,{count:'exact'})
       .or(`usu_nickname.ilike.%${limpio}%,usu_nombre.ilike.%${limpio}%,usu_apellido.ilike.%${limpio}%`)
       .order('usu_nickname').range(inicio,inicio+49);
     if(error) throw error;
     return answer({registros:data??[],total:count??0});
   }
   if(action==='actualizar'){
     const id=Number(body.id_usuario);
     const cambios=body.cambios, antes=body.antes;
     const motivo=String(body.motivo??'').trim().slice(0,500);
     if(!Number.isSafeInteger(id) || id<1 || motivo.length<8 || !validObject(cambios) || !validObject(antes))
       return answer({error:'ID, motivo y campos válidos son obligatorios'},400);
     const keys=Object.keys(cambios);
     if(!keys.length || keys.some(k=>!FIELDS.includes(k) || !Object.prototype.hasOwnProperty.call(antes,k)))
       return answer({error:'Se intentó modificar un campo no autorizado'},403);
     const {data,error}=await db.rpc('axia_rrhh_actualizar_usuario',{
       p_id:id,p_actor_id:actorId,p_actor_usuario:String(actor.usu_nickname),
       p_motivo:motivo,p_antes:antes,p_cambios:cambios
     });
     if(error) throw error;
     return answer({resultado:data});
   }
   if(action==='alta'){
     const nickname=String(body.nickname??'').trim();
     const motivo=String(body.motivo??'').trim().slice(0,500);
     const datos=body.datos;
     if(!/^[A-Za-z0-9._-]{3,40}$/.test(nickname) || motivo.length<8 || !validObject(datos))
       return answer({error:'Usuario, expediente y motivo de alta son obligatorios'},400);
     if(Object.keys(datos).some(k=>!FIELDS.includes(k)) ||
        !String(datos.usu_nombre??'').trim() || !String(datos.usu_apellido??'').trim())
       return answer({error:'La solicitud de alta contiene campos no autorizados o incompletos'},403);
     // No se entrega contraseña a RRHH: la habilitación posterior compete al Admin.
     const hashInutilizable=await bcrypt.hash(randomSecret(),12);
     const {data,error}=await db.rpc('axia_rrhh_alta_usuario',{
       p_actor_id:actorId,p_actor_usuario:String(actor.usu_nickname),p_nickname:nickname,
       p_hash_inutilizable:hashInutilizable,p_datos:datos,p_motivo:motivo
     });
     if(error) throw error;
     return answer({resultado:data});
   }
   if(action==='baja'){
     const id=Number(body.id_usuario);
     const motivo=String(body.motivo??'').trim().slice(0,500);
     if(!Number.isSafeInteger(id) || id<1 || motivo.length<8 || body.activo_esperado!==true)
       return answer({error:'ID, estado confirmado y motivo de baja son obligatorios'},400);
     const revocado=await bcrypt.hash(randomSecret(),12);
     const {data,error}=await db.rpc('axia_rrhh_baja_usuario',{
       p_id:id,p_actor_id:actorId,p_actor_usuario:String(actor.usu_nickname),
       p_motivo:motivo,p_hash_revocado:revocado,p_estado_esperado:true
     });
     if(error) throw error;
     return answer({resultado:data});
   }
   return answer({error:'Acción no permitida'},400);
 }catch(err){
   // Nunca imprimir credenciales ni expediente en logs.
   const code=validObject(err) && 'code' in err ? String(err.code):'';
   const msg=validObject(err) && 'message' in err ? String(err.message):'';
   const safeMessage=/^(El nombre de usuario ya está registrado|Nombre y apellido son obligatorios|RH no puede dar de baja Administradores ni cuentas de RH|Empleado no encontrado|Estado actualizado por otro usuario: vuelve a consultar|Actor RRHH no autorizado)$/i.test(msg)
      ? msg : (code==='PGRST202'?'Falta instalar la migración SQL de altas y bajas de RH':
        'No se pudo completar la operación de RH. Verifica los permisos, el estado del empleado y la instalación SQL.');
   return answer({error:safeMessage},409);
 }
});
