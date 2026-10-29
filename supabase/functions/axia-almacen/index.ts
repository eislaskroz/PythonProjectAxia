/** AXIA ALMACÉN: pasarela protegida para un login propio de db_usuarios.
 * Necesita SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (sólo servidor),
 * AXIA_ALMACEN_JWT_SECRET (aleatorio >=32 caracteres). Desplegar --no-verify-jwt.
 * Nunca distribuir la clave de servicio ni el secreto de sesión en Desktop.
 */
import { createClient } from 'npm:@supabase/supabase-js@2';
import bcrypt from 'npm:bcryptjs@2.4.3';

const headers = {
  'Content-Type': 'application/json; charset=utf-8',
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'apikey,content-type,x-axia-almacen-session',
};
const reply = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers });
const encoder = new TextEncoder();
const secret = String(Deno.env.get('AXIA_ALMACEN_JWT_SECRET') ?? '');
const url = String(Deno.env.get('SUPABASE_URL') ?? '');
const serviceKey = String(Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '');
if (secret.length < 32 || !url || !serviceKey) throw new Error('Falta configuración segura de axia-almacen');
const db = createClient(url, serviceKey, { auth: { persistSession: false, autoRefreshToken: false } });
const hmacKey = await crypto.subtle.importKey('raw', encoder.encode(secret),
  { name: 'HMAC', hash: 'SHA-256' }, false, ['sign', 'verify']);

const encode = (data: Uint8Array): string => btoa(String.fromCharCode(...data)).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
const decode = (data: string): Uint8Array => {
  const raw = atob(data.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - data.length % 4) % 4));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
};
async function emitirToken(id: string): Promise<string> {
  const payload = { uid: id, iat: Math.floor(Date.now()/1000), exp: Math.floor(Date.now()/1000) + 900 };
  const header = encode(encoder.encode(JSON.stringify({ alg: 'HS256', typ: 'JWT' })));
  const body = encode(encoder.encode(JSON.stringify(payload)));
  const content = `${header}.${body}`;
  const signature = new Uint8Array(await crypto.subtle.sign('HMAC', hmacKey, encoder.encode(content)));
  return `${content}.${encode(signature)}`;
}
async function verificarToken(value: string): Promise<{ uid: string }> {
  const parts = value.split('.');
  if (parts.length !== 3 || parts.some((x) => x.length > 2000)) throw new Error('SESSION_INVALID');
  let signature: Uint8Array;
  try { signature = decode(parts[2]); } catch { throw new Error('SESSION_INVALID'); }
  const verified = await crypto.subtle.verify('HMAC', hmacKey, signature, encoder.encode(`${parts[0]}.${parts[1]}`));
  if (!verified) throw new Error('SESSION_INVALID');
  let header: Record<string, unknown>;
  let payload: Record<string, unknown>;
  try {
    header = JSON.parse(new TextDecoder().decode(decode(parts[0])));
    payload = JSON.parse(new TextDecoder().decode(decode(parts[1])));
  } catch { throw new Error('SESSION_INVALID'); }
  if (header.alg !== 'HS256' || typeof payload.uid !== 'string' || !payload.uid ||
      !Number.isInteger(payload.exp) || payload.exp <= Date.now()/1000 ||
      !Number.isInteger(payload.iat) || payload.iat > Date.now()/1000 + 60 ||
      payload.exp - payload.iat > 900) throw new Error('SESSION_INVALID');
  return { uid: payload.uid };
}
async function obtenerUsuarioPorId(id: string) {
  const { data, error } = await db.from('db_usuarios')
    .select('id_usuario,usu_nickname,usu_nombre,usu_apellido,usu_tipo').eq('id_usuario', id).maybeSingle();
  if (error || !data || ![1,8].includes(Number(data.usu_tipo))) throw new Error('SESSION_INVALID');
  return data;
}


const uuidValido = (v:string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v);
const errorMovimiento = (error:{message?:string}) => {
  const msg=String(error.message??'');
  if(msg.includes('EXISTENCIA_INSUFICIENTE'))return reply(409,{ok:false,error:'Existencia insuficiente. No se registró la salida.'});
  if(msg.includes('OT_NO_ENCONTRADA'))return reply(404,{ok:false,error:'La OT no existe.'});
  if(msg.includes('PRODUCTO_NO_ENCONTRADO'))return reply(404,{ok:false,error:'Artículo no encontrado o inactivo.'});
  if(msg.includes('IDEMPOTENCIA_CON_DATOS_DISTINTOS'))return reply(409,{ok:false,error:'Solicitud repetida con datos diferentes.'});
  if(msg.includes('SALDO_NO_CERO'))return reply(409,{ok:false,error:'El producto tiene existencias; no puede darse de baja.'});
  if(msg.includes('MOVIMIENTO_INVALIDO')||msg.includes('ENTREGA_OT_INVALIDA')||msg.includes('PARTIDA_OT_INVALIDA'))
    return reply(400,{ok:false,error:'Datos de movimiento no válidos.'});
  console.error('Almacén RPC:',msg);
  return reply(500,{ok:false,error:'No fue posible confirmar la operación. Consulta Kárdex.'});
};

Deno.serve(async (request: Request) => {
  if (request.method === 'OPTIONS') return new Response('ok', { headers });
  if (request.method !== 'POST') return reply(405, { ok:false, error: 'Método no permitido.' });
  try {
    const text = await request.text();
    if (text.length > 16000) return reply(413, {ok:false, error:'Solicitud demasiado extensa.'});
    let data: Record<string, unknown>;
    try { data = JSON.parse(text); } catch { return reply(400, {ok:false, error:'Solicitud inválida.'}); }
    const accion = String(data.accion ?? '');
    if (accion === 'login') {
      const nickname = String(data.nickname ?? '').trim();
      const password = String(data.password ?? '');
      if (!nickname || nickname.length > 120 || password.length < 1 || password.length > 1024)
        return reply(400, {ok:false, error:'Credenciales inválidas.'});
      // El control de intentos solo penaliza credenciales fallidas (no cada acceso).
      const {data: allowed, error: limitError} = await db.rpc('axia_almacen_login_permitido',
        {p_nickname:nickname});
      if (limitError) throw limitError;
      if (!allowed) return reply(429,{ok:false,error:'Demasiados intentos. Reintenta después de 15 minutos.'});
      const { data: usuario, error } = await db.from('db_usuarios')
        .select('id_usuario,usu_nickname,usu_nombre,usu_apellido,usu_tipo,usu_password')
        .ilike('usu_nickname', nickname.replace(/[%_\\]/g, '\\$&')).limit(1).maybeSingle();
      if (error) throw error;
      let valid = false;
      if (usuario && [1,8].includes(Number(usuario.usu_tipo))) {
        const hash = String(usuario.usu_password || '');
        // El servidor NO admite SHA-256 ni texto plano heredados.
        if (/^\$2[aby]\$/.test(hash)) {
          valid = await bcrypt.compare(password, hash.replace(/^\$2y\$/, '$2a$'));
        }
      }
      if (!valid) {
        const {error: badAttemptError} = await db.rpc('axia_almacen_registrar_login',
          {p_nickname:nickname,p_correcto:false});
        if (badAttemptError) throw badAttemptError;
        return reply(401, {ok:false, error:'Credenciales incorrectas, rol no autorizado o contraseña antigua no migrada.'});
      }
      const { data: reset, error: resetError } = await db.rpc('axia_almacen_registrar_login',
        { p_nickname: nickname, p_correcto: true });
      if (resetError) throw resetError;
      if (!reset) return reply(429, {ok:false, error:'Cuenta bloqueada temporalmente.'});
      return reply(200, {ok:true, resultado: {id_usuario: String(usuario.id_usuario), token: await emitirToken(String(usuario.id_usuario))}});
    }
    const session = await verificarToken(String(request.headers.get('x-axia-almacen-session') ?? ''));
    const usuario = await obtenerUsuarioPorId(session.uid);
    // CATALOGO UNICO. La tabla creada desde el Excel es la base operativa real.
    const tabla = 'axia_almacen_catalogo';
    if (accion === 'catalogo') {
      const incluirInactivos = data.incluir_inactivos === true;
      const listado: Record<string, unknown>[] = [];
      for (let inicio=0;inicio<20000;inicio+=1000) {
        let query=db.from(tabla).select('*').order('codigo_axia').range(inicio,inicio+999);
        if (!incluirInactivos) query=query.eq('activo',true);
        const {data: filas,error}=await query;
        if(error) throw error;
        listado.push(...(filas??[]));
        if(!filas || filas.length<1000) break;
      }
      return reply(200,{ok:true,resultado:listado.map((p)=>({
        ...p,codigo:p.codigo_axia,nombre:p.producto,
        departamento:p.departamento_origen??'', costo:p.p_costo,venta:p.p_venta,
        minimo:p.inv_minimo,maximo:p.inv_maximo,saldo:p.saldo_actual,
        saldo_exportado:p.existencia_eleventa,
      }))});
    }
    if (accion === 'kardex') {
      const codigo=String(data.codigo??'').trim();
      const pagina=Number(data.pagina??1),limite=Number(data.limite??200);
      if (!Number.isInteger(pagina)||pagina<1||pagina>100000||
          !Number.isInteger(limite)||limite<1||limite>200||codigo.length>120)
        return reply(400,{ok:false,error:'Filtro inválido.'});
      let query=db.from('axia_almacen_maestro_movimientos').select('*')
        .order('fecha',{ascending:false}).order('id',{ascending:false})
        .range((pagina-1)*limite,pagina*limite-1);
      if (codigo) {
        if (codigo.toUpperCase().startsWith('OT-')) query=query.eq('referencia',codigo.toUpperCase());
        else query=query.eq('codigo_axia',codigo);
      }
      const {data:rows,error}=await query;
      if(error) throw error;
      return reply(200,{ok:true,resultado:(rows??[]).map((m)=>({...m,codigo:m.codigo_axia}))});
    }
    if (accion === 'consultar_ot') {
      const folio=String(data.folio??'').trim().toUpperCase();
      if(folio.length<1||folio.length>120) return reply(400,{ok:false,error:'Folio de OT inválido.'});
      const {data:ot,error}=await db.from('db_ordenes_trabajo')
        .select('ot_folio,ot_cliente,ot_asunto,ot_partidas_json').eq('ot_folio',folio).maybeSingle();
      if(error) throw error;
      if(!ot) return reply(404,{ok:false,error:'No se encontró la OT.'});
      let partidas:unknown=ot.ot_partidas_json??[];
      if(typeof partidas==='string') {try{partidas=JSON.parse(partidas);}catch{partidas=[];}}
      return reply(200,{ok:true,resultado:{folio:ot.ot_folio,cliente:ot.ot_cliente,
        asunto:ot.ot_asunto,partidas:Array.isArray(partidas)?partidas:[]}});
    }
    if (accion === 'registrar') {
      const codigo=String(data.codigo??'').trim(),tipo=String(data.tipo??'').trim().toUpperCase();
      const cantidad=Number(data.cantidad),motivo=String(data.motivo??'').trim();
      const referencia=String(data.referencia??'').trim(),destinatario=String(data.destinatario??'').trim();
      const idempotencia=String(data.idempotencia??'');
      if(codigo.length<1||codigo.length>120||!['ENTRADA','SALIDA'].includes(tipo)||
         !Number.isFinite(cantidad)||cantidad<=0||cantidad>1000000||
         Math.abs(cantidad*1000-Math.round(cantidad*1000))>0.000001||
         motivo.length<1||motivo.length>250||referencia.length>120||destinatario.length>120||
         (tipo==='SALIDA'&&!destinatario)||!uuidValido(idempotencia))
        return reply(400,{ok:false,error:'Movimiento inválido.'});
      const {data:mov,error}=await db.rpc('axia_almacen_maestro_registrar_movimiento',{
        p_codigo:codigo,p_tipo:tipo,p_cantidad:cantidad,p_motivo:motivo,
        p_referencia:referencia,p_destinatario:destinatario,
        p_responsable_id:String(usuario.id_usuario),
        p_responsable:String(usuario.usu_nickname??''),p_idempotencia:idempotencia,
      });
      if(error) return errorMovimiento(error);
      return reply(200,{ok:true,resultado:mov});
    }
    if (accion === 'salida_ot') {
      const folio=String(data.folio??'').trim().toUpperCase();
      const destinatario=String(data.destinatario??'').trim(),motivo=String(data.motivo??'').trim();
      const idempotencia=String(data.idempotencia??'');
      const partidas=data.partidas;
      if (folio.length<1||folio.length>120||destinatario.length<1||destinatario.length>120||
          motivo.length<1||motivo.length>250||!uuidValido(idempotencia)||
          !Array.isArray(partidas)||partidas.length<1||partidas.length>80||
          partidas.some((p)=>typeof p!=='object'||p===null||
            !String(p.codigo??'').trim()||String(p.codigo??'').length>120||
            !Number.isFinite(Number(p.cantidad))||Number(p.cantidad)<=0||
            Math.abs(Number(p.cantidad)*1000-Math.round(Number(p.cantidad)*1000))>0.000001))
        return reply(400,{ok:false,error:'Entrega por OT inválida.'});
      const {data:resultado,error}=await db.rpc('axia_almacen_maestro_registrar_salida_ot',{
        p_folio:folio,p_partidas:partidas,p_destinatario:destinatario,p_motivo:motivo,
        p_responsable_id:String(usuario.id_usuario),p_responsable:String(usuario.usu_nickname??''),
        p_idempotencia:idempotencia,
      });
      if(error) return errorMovimiento(error);
      return reply(200,{ok:true,resultado});
    }
    if (['crear_producto','editar_producto','desactivar_producto','reactivar_producto'].includes(accion)) {
      // En el ALTA, el código AXIA se genera exclusivamente en Supabase.
      const codigo=String(data.codigo??'').trim();
      if(accion!=='crear_producto'&&!/^[A-Z]{3}-[A-Z]{3}-[0-9]{5}$/.test(codigo))
        return reply(400,{ok:false,error:'Código AXIA inválido.'});
      if(accion==='desactivar_producto') {
        const {data:ok,error}=await db.rpc('axia_almacen_maestro_desactivar_producto',{p_codigo:codigo});
        if(error) return errorMovimiento(error);
        return reply(200,{ok:true,resultado:{codigo,activo:!ok}});
      }
      if(accion==='reactivar_producto') {
        const {data:res,error}=await db.from(tabla).update({activo:true,actualizado_el:new Date().toISOString()})
          .eq('codigo_axia',codigo).eq('activo',false).select('codigo_axia').maybeSingle();
        if(error) throw error;
        if(!res)return reply(404,{ok:false,error:'Producto no localizado o ya activo.'});
        return reply(200,{ok:true,resultado:{codigo,activo:true}});
      }
      const datos=(data.producto??{}) as Record<string,unknown>;
      const safeText=(field:string,max:number,required=false):string|null=>{
        const value=String(datos[field]??'').trim();
        if(value.length>max||(required&&!value)) throw new Error('FICHA_INVALIDA:'+field);
        return value||null;
      };
      const parseNumero=(field:string):number=>{
        const raw=String(datos[field]??'0').replace(/[$,]/g,'').trim();
        if(!/^\d+(?:\.\d{1,6})?$/.test(raw))throw new Error('FICHA_INVALIDA:'+field);
        const n=Number(raw);
        if(!Number.isFinite(n)||n<0||n>999999999999)throw new Error('FICHA_INVALIDA:'+field);
        return n;
      };
      let cambios:Record<string,unknown>;
      try {
        cambios={
          producto:safeText('producto',500,true),
          departamento_origen:safeText('departamento',150),
          categoria_axia:safeText('categoria_axia',150,true),
          familia_axia:safeText('familia_axia',200,true),
          proveedor:safeText('proveedor',200),
          codigo_proveedor:safeText('codigo_proveedor',160),
          unidad_inventario:safeText('unidad_inventario',100),
          seguimiento_sugerido:safeText('seguimiento_sugerido',150),
          estado_clasificacion:safeText('estado_clasificacion',150),
          posible_equivalencia:safeText('posible_equivalencia',300),
          p_costo:parseNumero('costo'),p_venta:parseNumero('venta'),
          p_mayoreo:parseNumero('p_mayoreo'),inv_minimo:parseNumero('minimo'),
          inv_maximo:parseNumero('maximo'),
        };
      } catch {
        return reply(400,{ok:false,error:'La ficha tiene campos inválidos o demasiado largos.'});
      }
      if(accion==='editar_producto') {
        const {data:updated,error}=await db.from(tabla).update({...cambios,actualizado_el:new Date().toISOString()})
          .eq('codigo_axia',codigo).eq('activo',true).select('codigo_axia').maybeSingle();
        if(error)throw error;
        if(!updated)return reply(404,{ok:false,error:'Artículo no localizado o inactivo.'});
        return reply(200,{ok:true,resultado:{codigo}});
      }
      const solicitud=String(datos.solicitud_id??'');
      if(!uuidValido(solicitud))return reply(400,{ok:false,error:'Identificador de alta inválido.'});
      const {data:creado,error}=await db.rpc('axia_almacen_maestro_crear_producto',{
        p_datos:cambios,p_idempotencia:solicitud,
      });
      if(error){
        const mensaje=String(error.message??'');
        if(mensaje.includes('FAMILIA_NO_REGISTRADA'))return reply(400,{ok:false,error:'Selecciona una categoría y familia oficiales del catálogo.'});
        if(mensaje.includes('IDEMPOTENCIA_CON_DATOS_DISTINTOS'))return reply(409,{ok:false,error:'Esta solicitud ya se utilizó para otros datos. Cancela y abre un alta nueva.'});
        if(mensaje.includes('CONSECUTIVO_AGOTADO'))return reply(409,{ok:false,error:'Esta familia agotó sus consecutivos. Contacta a TI.'});
        if(mensaje.includes('23505')||error.code==='23505')return reply(409,{ok:false,error:'Ya existe ese código o identificador de alta.'});
        throw error;
      }
      return reply(200,{ok:true,resultado:creado});
    }
    return reply(400,{ok:false,error:'Acción desconocida.'});
  } catch(err) {
    if(err instanceof Error&&err.message==='SESSION_INVALID')
      return reply(401,{ok:false,error:'Sesión inválida o vencida. Autentícate de nuevo.'});
    console.error('axia-almacen',err instanceof Error?err.message:String(err));
    return reply(500,{ok:false,error:'No se pudo confirmar la operación. Revisa el Kárdex antes de repetir.'});
  }
});
