/**
 * AXIA Obra Civil: guardado y recuperación idempotente con sesión firmada.
 * La sesión `levantamientos_lectura` es emitida por axia-almacen tras verificar
 * la contraseña del empleado (bcrypt). Esta función usa EL MISMO secreto HMAC.
 * Secrets: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, AXIA_ALMACEN_JWT_SECRET.
 * Desplegar con Verify JWT with legacy secret = OFF (la firma se valida aquí).
 * No abrir INSERT/SELECT públicos en db_obras_civiles.
 */
import { createClient } from 'npm:@supabase/supabase-js@2';

const secret = String(Deno.env.get('AXIA_ALMACEN_JWT_SECRET') ?? '');
const url = String(Deno.env.get('SUPABASE_URL') ?? '');
const role = String(Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '');
if (secret.length < 32 || !url || !role) throw new Error('Configuración segura de Obra Civil incompleta');
const db = createClient(url, role, { auth: {persistSession: false, autoRefreshToken: false} });
const encoder = new TextEncoder();
const key = await crypto.subtle.importKey('raw', encoder.encode(secret), {name:'HMAC', hash:'SHA-256'}, false, ['verify']);
const headers = {
  'Content-Type':'application/json; charset=utf-8',
  'Access-Control-Allow-Origin':'*',
  'Access-Control-Allow-Methods':'POST, OPTIONS',
  'Access-Control-Allow-Headers':'apikey,content-type,x-axia-almacen-session',
};
const reply = (status: number, body: unknown) => new Response(JSON.stringify(body), {status,headers});
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const decode = (input: string): Uint8Array => {
  const value = atob(input.replace(/-/g,'+').replace(/_/g,'/') + '='.repeat((4-input.length%4)%4));
  return Uint8Array.from(value, ch => ch.charCodeAt(0));
};
async function usuarioAutorizado(header: string) {
  const p = header.split('.');
  if (p.length !== 3 || p.some(x=>x.length===0 || x.length>2000)) throw new Error('SESION_INVALIDA');
  let verified = false; let cab: Record<string,unknown>; let claims: Record<string,unknown>;
  try {
    verified = await crypto.subtle.verify('HMAC',key,decode(p[2]),encoder.encode(`${p[0]}.${p[1]}`));
    cab = JSON.parse(new TextDecoder().decode(decode(p[0])));
    claims = JSON.parse(new TextDecoder().decode(decode(p[1])));
  } catch { throw new Error('SESION_INVALIDA'); }
  const now = Math.floor(Date.now()/1000);
  if (!verified || cab!.alg !== 'HS256' ||
      claims!.alcance !== 'levantamientos_lectura' ||
      typeof claims!.uid !== 'string' || !claims!.uid ||
      !Number.isInteger(claims!.iat) || !Number.isInteger(claims!.exp) ||
      Number(claims!.iat)>now+60 || Number(claims!.exp)<=now ||
      Number(claims!.exp)-Number(claims!.iat)>43200) throw new Error('SESION_INVALIDA');
  const { data, error } = await db.from('db_usuarios')
    .select('id_usuario,usu_nickname,usu_tipo')
    .eq('id_usuario',claims!.uid).maybeSingle();
  if (error || !data || ![1,2,3,4,5,6].includes(Number(data.usu_tipo)))
    throw new Error('SESION_INVALIDA');
  return { id: String(data.id_usuario), nickname:String(data.usu_nickname||''), tipo: Number(data.usu_tipo) };
}

// Lista explícita: no admitir campos nuevos, obc_folio, obc_id, IDs del sistema ni creado_por desde cliente.
const permitidos = new Set([
  'id_aco','id_sucursal','id_contacto','obc_fecha','obc_aco_numero',
  'obc_cliente','obc_contacto','obc_sucursal','obc_direccion','obc_responsable_axia',
  'obc_supervisor','obc_dias_trabajo','obc_personas_considerar','obc_tipo_giro',
  'obc_nombre_proyecto','obc_superficie_disponible','obc_superficie_adecuada',
  'obc_planos_arquitectonicos','obc_requiere_maquinaria','obc_permisos',
  'obc_observaciones_iniciales','obc_ejecucion_json','obc_planos_acabados',
  'obc_generacion_planos','obc_etapa_acabados','obc_obra_blanca',
  'obc_evidencias_json','obc_archivos_adjuntos_json','obc_anotacion_plano_json',
  'obc_observaciones_finales',
]);
const tabla = 'db_obras_civiles';
async function buscarSolicitud(solicitud: string, nickname: string) {
  const {data,error} = await db.from(tabla)
    .select('obc_id,obc_folio,obc_request_id,creado_por')
    .eq('obc_request_id',solicitud).maybeSingle();
  if (error) throw error;
  if (!data) return null;
  if (String(data.creado_por||'').toLowerCase()!==nickname.toLowerCase())
    throw new Error('SOLICITUD_AJENA');
  return {obc_id:data.obc_id,obc_folio:data.obc_folio,obc_request_id:data.obc_request_id};
}

Deno.serve(async (request: Request) => {
  if (request.method==='OPTIONS') return new Response('ok',{headers});
  if (request.method!=='POST') return reply(405,{ok:false,error:'Método no permitido.'});
  try {
    const user=await usuarioAutorizado(request.headers.get('x-axia-almacen-session')||'');
    const text=await request.text();
    if (text.length>9_000_000) return reply(413,{ok:false,error:'La solicitud excede el tamaño permitido.'});
    let payload: Record<string,unknown>;
    try { payload=JSON.parse(text); } catch { return reply(400,{ok:false,error:'JSON inválido.'}); }
    if (!payload || typeof payload !== 'object' || Array.isArray(payload))
      return reply(400,{ok:false,error:'Solicitud inválida.'});
    const accion=String(payload.accion||'');
    // La ventana universal consulta Obra Civil por un canal distinto del INSERT.
    // Autorizar cada acción en el servidor: ocultar controles no constituye seguridad.
    if (accion === 'listar' || accion === 'detalle') {
      if (![1,2,3,5].includes(user.tipo)) return reply(403,{ok:false,error:'No puedes consultar Obras Civiles desde esta ventana.'});
      if (accion === 'detalle') {
        const folio=String(payload.folio||'').trim().toUpperCase();
        if (!/^OBC-[0-9]{4,}$/.test(folio)) return reply(400,{ok:false,error:'Folio de Obra Civil inválido.'});
        const {data,error}=await db.from(tabla).select('*').eq('obc_folio',folio).maybeSingle();
        if (error) throw error;
        if (!data) return reply(404,{ok:false,error:'La Obra Civil no existe.'});
        return reply(200,{ok:true,resultado:data});
      }
      const termino=String(payload.busqueda||'').trim().slice(0,120);
      // Evita descargar anexos y fotografías de 100 OBC en una sola petición.
      let consulta=db.from(tabla).select('obc_id,obc_folio,obc_cliente,obc_nombre_proyecto,obc_fecha,obc_estatus,obc_validado_ventas,fecha_registro').order('fecha_registro',{ascending:false}).limit(100);
      if (termino) {
        // El término se trata como texto, no como expresión de PostgREST.
        const limpio=termino.replace(/[^\p{L}\p{N}\s-]/gu,' ').trim();
        if (limpio) consulta=consulta.or(`obc_folio.ilike.%${limpio}%,obc_cliente.ilike.%${limpio}%,obc_nombre_proyecto.ilike.%${limpio}%`);
      }
      const {data,error}=await consulta;
      if (error) throw error;
      return reply(200,{ok:true,resultado:data||[]});
    }
    if (accion === 'actualizar' || accion === 'validar') {
      const folio=String(payload.folio||'').trim().toUpperCase();
      if (!/^OBC-[0-9]{4,}$/.test(folio)) return reply(400,{ok:false,error:'Folio de Obra Civil inválido.'});
      const permitidoEditar=[1,2,3,5].includes(user.tipo);
      if ((accion==='actualizar' && !permitidoEditar) || (accion==='validar' && user.tipo!==5))
        return reply(403,{ok:false,error:'Tu rol no está autorizado para esta operación.'});
      // La validación sí requiere encontrar el folio actual. La actualización
      // tiene un RPC idempotente que admite reintentar con el folio anterior.
      if (accion==='validar') {
        const {data:actual,error:lecturaError}=await db.from(tabla)
          .select('obc_id,obc_folio,obc_validado_ventas').eq('obc_folio',folio).maybeSingle();
        if (lecturaError) throw lecturaError;
        if (!actual) return reply(404,{ok:false,error:'No se encontró la Obra Civil solicitada.'});
        if (actual.obc_validado_ventas) return reply(409,{ok:false,error:'La Obra Civil ya fue validada.'});
        const {data,error}=await db.from(tabla).update({
          obc_validado_ventas:true, obc_validado_por:user.nickname,
          obc_fecha_validacion:new Date().toISOString(),
        }).eq('obc_id',actual.obc_id).eq('obc_validado_ventas',false)
          .select('obc_id,obc_folio,obc_validado_ventas,obc_validado_por').maybeSingle();
        if (error) throw error;
        if (!data) return reply(409,{ok:false,error:'La obra ya fue validada por otro usuario.'});
        return reply(200,{ok:true,resultado:data});
      }
      const raw=payload.cambios;
      if (!raw || typeof raw!=='object' || Array.isArray(raw))
        return reply(400,{ok:false,error:'Faltan cambios para guardar.'});
      const editables=new Set(['obc_cliente','obc_contacto','obc_direccion','obc_sucursal',
        'obc_supervisor','obc_fecha','obc_nombre_proyecto','obc_tipo_giro',
        'obc_observaciones_iniciales','obc_observaciones_finales','obc_ejecucion_json',
        'obc_responsable_axia','obc_dias_trabajo','obc_personas_considerar',
        'obc_superficie_disponible','obc_superficie_adecuada','obc_planos_arquitectonicos',
        'obc_requiere_maquinaria','obc_permisos','obc_planos_acabados',
        'obc_generacion_planos','obc_etapa_acabados','obc_obra_blanca',
        'obc_anotacion_plano_json','obc_evidencias_json','obc_archivos_adjuntos_json']);
      const entradas=Object.entries(raw as Record<string,unknown>);
      if (!entradas.length || entradas.some(([k])=>!editables.has(k)))
        return reply(400,{ok:false,error:'Se intentó modificar un campo protegido.'});
      if (entradas.some(([k,v])=> ((k==='obc_dias_trabajo'||k==='obc_personas_considerar')
        ? (typeof v!=='number' || !Number.isInteger(v) || v<0 || v>100000)
        : (typeof v!=='string' || (v as string).length>(k==='obc_anotacion_plano_json'?7_000_000:120000)))))
        return reply(400,{ok:false,error:'Hay textos no válidos o demasiado largos.'});
      const cambios=Object.fromEntries(entradas);
      if ('obc_cliente' in cambios && !String(cambios.obc_cliente||'').trim())
        return reply(400,{ok:false,error:'Cliente obligatorio.'});
      if ('obc_nombre_proyecto' in cambios && !String(cambios.obc_nombre_proyecto||'').trim())
        return reply(400,{ok:false,error:'Nombre del proyecto obligatorio.'});
      for (const campoJson of ['obc_ejecucion_json','obc_anotacion_plano_json','obc_evidencias_json','obc_archivos_adjuntos_json']) {
        if (campoJson in cambios) {
          try { const detalle=JSON.parse(cambios[campoJson] as string);
            const esAnexos=['obc_evidencias_json','obc_archivos_adjuntos_json'].includes(campoJson);
            if (esAnexos ? !Array.isArray(detalle) : (!detalle || typeof detalle!=='object' || Array.isArray(detalle)))
              throw new Error('JSON inválido');
          } catch { return reply(400,{ok:false,error:`${campoJson}: estructura inválida.`}); }
        }
      }
      // ÚNICAMENTE un RPC PostgreSQL atómico actualiza la obra y le asigna
      // otro folio de la secuencia global. Sin INSERT ni cambio de obc_id.
      const solicitud=String(payload.solicitud||'').trim();
      if (!uuid.test(solicitud))
        return reply(400,{ok:false,error:'Identificador de edición inválido.'});
      const {data,error}=await db.rpc('axia_obc_actualizar_versionada',{
        p_folio_anterior:folio,p_cambios:cambios,
        p_usuario:user.nickname,p_solicitud:solicitud,
      });
      if (error) {
        const msg=String(error.message||'');
        if (/FOLIO_DESACTUALIZADO|EDICION_CONFLICTO|OBRA_VALIDADA_NO_EDITABLE/.test(msg))
          return reply(409,{ok:false,error:'Esta obra cambió o fue validada por otro usuario. Vuelve a abrirla.'});
        throw error;
      }
      if (!data?.obc_id || !data?.obc_folio)
        throw new Error('RESPUESTA_VERSION_NO_CONFIRMADA');
      return reply(200,{ok:true,resultado:data});
    }
    const solicitud=String(payload.solicitud||'').trim();
    if (!uuid.test(solicitud)) return reply(400,{ok:false,error:'Identificador de captura inválido.'});
    if (accion !== 'consultar' && accion !== 'guardar') return reply(400,{ok:false,error:'Acción desconocida.'});
    const previo=await buscarSolicitud(solicitud,user.nickname);
    if (previo) return reply(200,{ok:true,resultado:previo,recuperado:true});
    if (accion==='consultar') return reply(200,{ok:true,resultado:null});
    const datos=payload.datos;
    if (!datos || typeof datos!=='object' || Array.isArray(datos)) return reply(400,{ok:false,error:'Faltan datos de Obra Civil.'});
    const raw=datos as Record<string,unknown>;
    if (Object.keys(raw).some(campo => !permitidos.has(campo)))
      return reply(400,{ok:false,error:'La solicitud contiene campos no autorizados.'});
    if (!String(raw.obc_cliente||'').trim() || !String(raw.obc_nombre_proyecto||'').trim())
      return reply(400,{ok:false,error:'Cliente y nombre del proyecto son obligatorios.'});
    const registro={...raw,obc_request_id:solicitud,creado_por:user.nickname,obc_estatus:1};
    const {data:creado,error}=await db.from(tabla).insert(registro)
      .select('obc_id,obc_folio,obc_request_id').single();
    if (error) {
      // Otro intento con el mismo UUID pudo guardarse mientras éste estaba en vuelo.
      if (error.code==='23505') {
        const repetido=await buscarSolicitud(solicitud,user.nickname);
        if (repetido) return reply(200,{ok:true,resultado:repetido,recuperado:true});
        return reply(409,{ok:false,error:'Conflicto de folio o identificador. No se generó otro registro.'});
      }
      throw error;
    }
    return reply(200,{ok:true,resultado:creado,recuperado:false});
  } catch (err) {
    const code=err instanceof Error?err.message:String(err);
    if (code==='SESION_INVALIDA') return reply(401,{ok:false,error:'La sesión de AXIA expiró o no está autorizada. Vuelve a autenticarte.'});
    if (code==='SOLICITUD_AJENA') return reply(403,{ok:false,error:'El identificador pertenece a otro empleado.'});
    console.error('AXIA Obra Civil:',code);
    return reply(500,{ok:false,error:'No se pudo confirmar la Obra Civil. Conserva el borrador y verifica la conexión.'});
  }
});
