/** AXIA RRHH: acceso controlado a expedientes, sin gestión de cuentas.
 * Requiere SUPABASE_SERVICE_ROLE_KEY en secretos de Supabase Edge Functions;
 * NUNCA guardar esta clave en Windows.
 * Desplegar con Verify JWT legacy ON si el cliente usa anon key legacy.
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
const SELECT = ['id_usuario','usu_nickname','usu_tipo',...FIELDS].join(',');
function answer(body:unknown,status=200):Response {
 return new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
}
Deno.serve(async(req)=>{
 if(req.method!=='POST') return answer({error:'Método no permitido'},405);
 if(!url || !key) return answer({error:'Servicio sin configuración'},503);
 let body:any;
 try { body=await req.json(); } catch {return answer({error:'JSON inválido'},400);}
 if(!body || typeof body!=='object' || Array.isArray(body)) return answer({error:'Solicitud inválida'},400);
 const usuario=String(body.usuario??'').trim().slice(0,120);
 const password=String(body.contrasena??'');
 const actorId=Number(body.actor_id);
 if(!usuario || !password || password.length>256 || !Number.isSafeInteger(actorId))
   return answer({error:'Credenciales necesarias'},401);
 try {
   const {data:actors,error:authError}=await db.from('db_usuarios')
      .select('id_usuario,usu_nickname,usu_tipo,usu_password')
      .ilike('usu_nickname',usuario).limit(1);
   if(authError) throw authError;
   const actor=actors?.[0]; const hash=String(actor?.usu_password??'');
   const valida=hash.startsWith('$2') && await bcrypt.compare(password,hash);
   if(!valida || Number(actor?.usu_tipo)!==10 || Number(actor?.id_usuario)!==actorId)
     return answer({error:'Se requiere usuario de Recursos Humanos (rol 10) y contraseña válida'},403);
   if(body.accion==='listar'){
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
   if(body.accion==='actualizar'){
     const id=Number(body.id_usuario);
     const cambios=body.cambios, antes=body.antes;
     const motivo=String(body.motivo??'').trim().slice(0,500);
     if(!Number.isSafeInteger(id) || id<1 || motivo.length<8 || !cambios || !antes ||
       Array.isArray(cambios) || typeof cambios!=='object' || Array.isArray(antes) || typeof antes!=='object')
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
   return answer({error:'Acción no permitida'},400);
 }catch(err){
   // No exponer PII, claves ni contenido de solicitudes en mensajes o logs.
   const code=typeof err==='object' && err !== null && 'code' in err ? String((err as any).code):'';
   return answer({error:code==='PGRST202'?'Falta instalar la migración SQL de Recursos Humanos':
      'No se completó la operación. Verifica permisos, consistencia del registro y configuración del servicio.'},409);
 }
});
