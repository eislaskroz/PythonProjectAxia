/** AXIA admin-registros: control real de rol 1 en servidor.
 * Requiere despliegue con SUPABASE_SERVICE_ROLE_KEY COMO SECRETO DE EDGE,
 * nunca dentro del proyecto Windows. La contraseña viaja solo por HTTPS.
 */
import { createClient } from 'npm:@supabase/supabase-js@2';
import bcrypt from 'npm:bcryptjs@2.4.3';

const URL = Deno.env.get('SUPABASE_URL') ?? '';
const SERVICE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '';
const db = createClient(URL, SERVICE_KEY, {auth:{persistSession:false,autoRefreshToken:false}});
const SPECS: Record<string,{pk:string,folio:string,cliente:string,fecha:string,estado:string,campos:string[]}> = {
  db_acos: {pk:'id_aco',folio:'aco_numero',cliente:'aco_cliente',fecha:'fecha_registro',estado:'aco_estatus',campos:['aco_numero','aco_cliente','aco_responsable','aco_descripcion']},
  db_levantamientos: {pk:'id_levantamiento',folio:'lev_folio',cliente:'lev_cliente',fecha:'fecha_registro',estado:'lev_estatus',campos:['lev_folio','lev_aco_numero','lev_cliente','lev_tipo']},
  db_ordenes_trabajo: {pk:'ot_id',folio:'ot_folio',cliente:'ot_cliente',fecha:'fecha_registro',estado:'ot_estatus',campos:['ot_folio','ot_aco_numero','ot_cliente','ot_asunto']},
  db_ordenes_servicio: {pk:'id_orden',folio:'os_folio',cliente:'os_cliente',fecha:'fecha_registro',estado:'os_estatus',campos:['os_folio','os_aco_numero','os_cliente','os_descripcion']},
  db_bitacoras: {pk:'id_bitacora',folio:'bit_folio',cliente:'bit_cliente',fecha:'fecha_registro',estado:'bit_estatus',campos:['bit_folio','bit_aco_numero','bit_cliente','bit_descripcion']},
};
function respond(body:unknown,status=200) {
 return new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
}
Deno.serve(async (req)=>{
 if(req.method!=='POST')return respond({error:'Método no admitido'},405);
 if(!URL||!SERVICE_KEY)return respond({error:'Servicio no configurado'},503);
 let body:any;
 try { body=await req.json(); } catch {return respond({error:'JSON inválido'},400);}
 if(!body||typeof body!=='object')return respond({error:'Solicitud incorrecta'},400);
 const username=String(body.usuario??'').trim().slice(0,120);
 const password=String(body.contrasena??'');
 if(!username||!password||password.length>256)return respond({error:'Credenciales necesarias'},401);
 try {
   const {data:users,error:authError}=await db.from('db_usuarios')
      .select('id_usuario,usu_nickname,usu_tipo,usu_password').ilike('usu_nickname',username).limit(1);
   if(authError)throw authError;
   const actor=users?.[0];
   const hash=String(actor?.usu_password??'');
   // Solo bcrypt: para claves heredadas, iniciar sesión una vez en Desktop las migra.
   const verified=hash.startsWith('$2') && await bcrypt.compare(password,hash);
   if(!verified||Number(actor?.usu_tipo)!==1)return respond({error:'Se requiere una cuenta Administrador con contraseña válida'},403);
   const tabla=String(body.tabla??''); const spec=SPECS[tabla];
   if(!spec)return respond({error:'Tipo de registro no autorizado'},400);
   const accion=String(body.accion??'');
   if(accion==='listar') {
      const pagina=Math.max(1,Math.min(100000,Math.trunc(Number(body.pagina)||1)));
      const cantidad=50;const desde=(pagina-1)*cantidad;
      const cols=[spec.pk,spec.folio,spec.cliente,spec.fecha,spec.estado].join(',');
      let q=db.from(tabla).select(cols,{count:'exact'}).order(spec.fecha,{ascending:false}).range(desde,desde+cantidad-1);
      const termino=String(body.buscar??'').trim().slice(0,80).replace(/[%_,.()\\*]/g,' ').trim();
      if(termino)q=q.or(spec.campos.map(c=>`${c}.ilike.%${termino}%`).join(','));
      const {data,error,count}=await q;
      if(error)throw error;
      return respond({registros:data??[],total:count??0,pagina,cantidad});
   }
   if(accion==='obtener') {
      const id=String(body.id??'').slice(0,128);
      if(!id)return respond({error:'ID obligatorio'},400);
      const {data,error}=await db.from(tabla).select('*').eq(spec.pk,id).maybeSingle();
      if(error)throw error;
      if(!data)return respond({error:'Registro no encontrado'},404);
      return respond({registro:data});
   }
   if(accion==='auditoria') {
      const {data,error}=await db.from('axia_admin_registros_historial')
        .select('id,fecha,actor_usuario,registro_id,accion,motivo,anterior').eq('tabla',tabla)
        .order('fecha',{ascending:false}).limit(75);
      if(error)throw error;
      return respond({historial:(data??[]).map((r:any)=>({
        id:r.id,fecha:r.fecha,actor_usuario:r.actor_usuario,registro_id:r.registro_id,
        folio:r.anterior?.[spec.folio]??'',accion:r.accion,motivo:r.motivo,
      }))});
   }
   if(accion==='historial') {
      const id=String(body.id??'').slice(0,128);
      if(!id)return respond({error:'ID obligatorio'},400);
      const {data,error}=await db.from('axia_admin_registros_historial')
        .select('id,fecha,actor_usuario,accion,motivo').eq('tabla',tabla).eq('registro_id',id)
        .order('fecha',{ascending:false}).limit(30);
      if(error)throw error;
      return respond({historial:data??[]});
   }
   if(accion==='editar'||accion==='eliminar') {
      const id=String(body.id??'').slice(0,128);
      const motivo=String(body.motivo??'').trim().slice(0,1000);
      if(!id||motivo.length<8||!body.antes||typeof body.antes!=='object'||Array.isArray(body.antes))
        return respond({error:'Registro, copia original y motivo (mínimo 8 caracteres) requeridos'},400);
      if(accion==='eliminar'&&String(body.confirmacion??'')!==String(body.antes?.[spec.folio]??''))
        return respond({error:'Para eliminar, escribe exactamente el folio del registro'},400);
      if(accion==='editar'&&(!body.cambios||typeof body.cambios!=='object'||Array.isArray(body.cambios)))
        return respond({error:'Cambios inválidos'},400);
      const {data,error}=await db.rpc('axia_admin_mutar_registro',{
        p_tabla:tabla,p_id:id,p_antes:body.antes,p_cambios:accion==='editar'?body.cambios:{},
        p_accion:accion==='editar'?'EDITAR':'ELIMINAR',p_actor_id:Number(actor.id_usuario),
        p_actor_usuario:String(actor.usu_nickname),p_motivo:motivo,
      });
      if(error)throw error;
      return respond({resultado:data});
   }
   return respond({error:'Operación desconocida'},400);
 }catch(err){
   // Nunca registrar ni reflejar contraseñas/payloads en logs.
   const message=err instanceof Error?err.message:String(err);
   return respond({error:message.slice(0,400)},409);
 }
});
