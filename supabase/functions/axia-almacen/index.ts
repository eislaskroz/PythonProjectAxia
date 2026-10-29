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
      const {data: allowed, error: limitError} = await db.rpc('axia_almacen_lab_login_permitido',
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
        const {error: badAttemptError} = await db.rpc('axia_almacen_lab_registrar_login',
          {p_nickname:nickname,p_correcto:false});
        if (badAttemptError) throw badAttemptError;
        return reply(401, {ok:false, error:'Credenciales incorrectas, rol no autorizado o contraseña antigua no migrada.'});
      }
      const { data: reset, error: resetError } = await db.rpc('axia_almacen_lab_registrar_login',
        { p_nickname: nickname, p_correcto: true });
      if (resetError) throw resetError;
      if (!reset) return reply(429, {ok:false, error:'Cuenta bloqueada temporalmente.'});
      return reply(200, {ok:true, resultado: {id_usuario: String(usuario.id_usuario), token: await emitirToken(String(usuario.id_usuario))}});
    }
    const session = await verificarToken(String(request.headers.get('x-axia-almacen-session') ?? ''));
    const usuario = await obtenerUsuarioPorId(session.uid);
    const laboratorio = accion.endsWith('_lab');
    const accionBase = laboratorio ? accion.slice(0,-4) : accion;
    const tablaProductos = laboratorio ? 'axia_almacen_lab_productos' : 'axia_almacen_productos';
    const tablaMovimientos = laboratorio ? 'axia_almacen_lab_movimientos' : 'axia_almacen_movimientos';
    // Gestión del catálogo: sesión AXIA validada, sin claves privilegiadas en DESKTOP.
    // Producción requiere además aprobación explícita del catálogo.
    if (['crear_producto','editar_producto','desactivar_producto','reactivar_producto'].includes(accionBase)) {
      if (!laboratorio) {
        const { data: config, error: ec } = await db.from('axia_almacen_config')
          .select('catalogo_autorizado').eq('id',1).single();
        if (ec) throw ec;
        if (!config?.catalogo_autorizado)
          return reply(403,{ok:false,error:'El catálogo real no está autorizado. Trabaja en simulador o laboratorio.'});
      }
      const codigo = String(data.codigo ?? (data.producto as Record<string, unknown> | null)?.codigo ?? '').trim();
      if (codigo.length < 1 || codigo.length > 120)
        return reply(400,{ok:false,error:'Código inválido.'});

      if (['crear_producto','editar_producto'].includes(accionBase)) {
        const p = (data.producto ?? {}) as Record<string,unknown>;
        const nombre = String(p.producto ?? '').trim();
        const departamento = String(p.departamento ?? 'SIN DEPARTAMENTO').trim();
        const numero = (v: unknown, decimales: number): number | null => {
          const str = String(v ?? '0').trim();
          if (!/^\d+(?:\.\d+)?$/.test(str)) return null;
          const n = Number(str);
          if (!Number.isFinite(n) || n < 0 || n > 999999999999 ||
              Math.abs(n * 10**decimales - Math.round(n * 10**decimales)) > 0.0001) return null;
          return n;
        };
        const costo = numero(p.costo,2), venta = numero(p.venta,2);
        const minimo = numero(p.minimo,3), maximo = numero(p.maximo,3);
        if (!nombre || nombre.length > 500 || !departamento || departamento.length > 150 ||
            [costo,venta,minimo,maximo].some((n)=>n===null) ||
            String(p.codigo ?? '').trim() !== codigo)
          return reply(400,{ok:false,error:'Datos del producto incorrectos. Revisa nombre y valores numéricos.'});
        const changes = {nombre,departamento,costo,precio_venta:venta,minimo,maximo,actualizado_en:new Date().toISOString()};
        if (accionBase === 'crear_producto') {
          const {data: inserted,error: ei} = await db.from(tablaProductos)
            .insert({codigo,...changes}).select('codigo,nombre').single();
          if (ei) {
            if (ei.code === '23505') return reply(409,{ok:false,error:'Ya existe ese código, incluso si está desactivado.'});
            throw ei;
          }
          return reply(200,{ok:true,resultado: inserted});
        }
        const {data: updated,error: eu} = await db.from(tablaProductos)
          .update(changes).eq('codigo',codigo).eq('activo',true).select('codigo,nombre').maybeSingle();
        if (eu) throw eu;
        if (!updated) return reply(404,{ok:false,error:'Producto no localizado o desactivado.'});
        return reply(200,{ok:true,resultado:updated});
      }
      if (accionBase === 'desactivar_producto') {
        // RPC serializa con movimientos sobre la misma fila; jamás borrar historial.
        const {data: disabled,error: ed} = await db.rpc(
          laboratorio ? 'axia_almacen_lab_desactivar_producto' : 'axia_almacen_desactivar_producto',
          {p_codigo:codigo});
        if (ed) {
          if (String(ed.message).includes('SALDO_NO_CERO'))
            return reply(409,{ok:false,error:'No puedes quitar un producto con existencia. Regulariza primero el saldo.'});
          if (String(ed.message).includes('PRODUCTO_NO_ENCONTRADO'))
            return reply(404,{ok:false,error:'Producto no localizado o ya desactivado.'});
          throw ed;
        }
        return reply(200,{ok:true,resultado:{codigo,activo:false,actualizado:Boolean(disabled)}});
      }
      const {data: restored,error: er} = await db.from(tablaProductos)
        .update({activo:true,actualizado_en:new Date().toISOString()})
        .eq('codigo',codigo).eq('activo',false).select('codigo').maybeSingle();
      if (er) throw er;
      if (!restored) return reply(404,{ok:false,error:'Producto no localizado o ya activo.'});
      return reply(200,{ok:true,resultado:{codigo,activo:true}});
    }

    // La consulta de OT es SOLO lectura. No descuenta artículos automáticamente:
    // requiere correspondencia exacta de código/SKU y aprobación en DESKTOP.
    if (accionBase === 'consultar_ot') {
      const folio = String(data.folio ?? '').trim().toUpperCase();
      if (folio.length < 1 || folio.length > 120)
        return reply(400,{ok:false,error:'Indica un folio de OT válido.'});
      const {data: ot,error} = await db.from('db_ordenes_trabajo')
        .select('ot_folio,ot_cliente,ot_asunto,ot_partidas_json')
        .eq('ot_folio',folio).limit(1).maybeSingle();
      if (error) throw error;
      if (!ot) return reply(404,{ok:false,error:'No se encontró esa Orden de Trabajo.'});
      let partidas: unknown = ot.ot_partidas_json ?? [];
      if (typeof partidas === 'string') {
        try { partidas = JSON.parse(partidas); } catch { partidas = []; }
      }
      return reply(200,{ok:true,resultado:{folio:ot.ot_folio,cliente:ot.ot_cliente,
        asunto:ot.ot_asunto,partidas:Array.isArray(partidas) ? partidas : []}});
    }
    if (accionBase === 'salida_ot') {
      const folio = String(data.folio ?? '').trim().toUpperCase();
      const destinatario = String(data.destinatario ?? '').trim();
      const motivo = String(data.motivo ?? '').trim();
      const idempotencia = String(data.idempotencia ?? '');
      const partidas = data.partidas;
      if (folio.length < 1 || folio.length > 120 || destinatario.length < 1 || destinatario.length > 120 ||
          motivo.length < 1 || motivo.length > 250 || !Array.isArray(partidas) ||
          partidas.length < 1 || partidas.length > 80 ||
          !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(idempotencia) ||
          partidas.some((p) => typeof p !== 'object' || p === null ||
            !String(p.codigo ?? '').trim() || String(p.codigo ?? '').length > 120 ||
            !Number.isFinite(Number(p.cantidad)) || Number(p.cantidad) <= 0 ||
            Number(p.cantidad) > 1000000 ||
            Math.abs(Number(p.cantidad)*1000-Math.round(Number(p.cantidad)*1000)) > 0.000001)) {
        return reply(400,{ok:false,error:'Entrega por OT inválida.'});
      }
      const {data: salida,error} = await db.rpc(
        laboratorio ? 'axia_almacen_lab_registrar_salida_ot' : 'axia_almacen_registrar_salida_ot',
        {p_folio:folio,p_partidas:partidas,p_destinatario:destinatario,p_motivo:motivo,
         p_responsable_id:String(usuario.id_usuario),
         p_responsable:String(usuario.usu_nickname || ''),p_idempotencia:idempotencia});
      if (error) {
        const msg = String(error.message ?? '');
        if (msg.includes('NO_HABILITADO')) return reply(409,{ok:false,error:'Movimientos de almacén deshabilitados.'});
        if (msg.includes('OT_NO_ENCONTRADA')) return reply(404,{ok:false,error:'No existe la OT indicada.'});
        if (msg.includes('EXISTENCIA_INSUFICIENTE')) return reply(409,{ok:false,error:'No hay existencia suficiente para entregar toda la OT. Ningún artículo fue descontado.'});
        if (msg.includes('IDEMPOTENCIA_CON_DATOS_DISTINTOS')) return reply(409,{ok:false,error:'Solicitud repetida con datos distintos.'});
        if (msg.includes('PRODUCTO_NO_ENCONTRADO') || msg.includes('ENTREGA_OT_INVALIDA') || msg.includes('PARTIDA_OT_INVALIDA'))
          return reply(400,{ok:false,error:'La entrega contiene una partida o un artículo inválido.'});
        throw error;
      }
      return reply(200,{ok:true,resultado:salida});
    }
    if (accionBase === 'catalogo') {
      const incluirInactivos = data.incluir_inactivos === true;
      const listado: Record<string, unknown>[] = [];
      for (let start = 0; start < 20000; start += 1000) {
        let query = db.from(tablaProductos)
          .select(laboratorio ? 'codigo,nombre,departamento,costo,precio_venta,minimo,maximo,saldo,saldo_exportado,activo' : 'codigo,nombre,departamento,costo,precio_venta,minimo,maximo,saldo,activo');
        if (!incluirInactivos) query = query.eq('activo',true);
        const {data: rows, error} = await query.order('codigo').range(start, start + 999);
        if (error) throw error;
        listado.push(...(rows ?? []));
        if (!rows || rows.length < 1000) break;
      }
      const result = listado.map((p) => ({
        codigo: p.codigo, producto: p.nombre, departamento: p.departamento,
        costo: p.costo, venta: p.precio_venta, minimo:p.minimo, maximo:p.maximo,
        saldo:p.saldo, saldo_exportado: laboratorio ? p.saldo_exportado : null, activo:p.activo,
      }));
      return reply(200, {ok:true, resultado: result});
    }
    if (accionBase === 'kardex') {
      const codigo = String(data.codigo ?? '').trim();
      const pagina = Number(data.pagina ?? 1);
      const limite = Number(data.limite ?? 200);
      if (!Number.isInteger(pagina) || pagina < 1 || pagina > 100000 ||
          !Number.isInteger(limite) || limite < 1 || limite > 200 || codigo.length > 120)
        return reply(400,{ok:false,error:'Filtro o página de Kárdex inválidos.'});
      const inicio = (pagina - 1)*limite;
      let query = db.from(tablaMovimientos)
        .select('id,tipo,cantidad,saldo_anterior,saldo_nuevo,motivo,referencia,destinatario,responsable_id,responsable,fecha,producto_id')
        .order('fecha', {ascending:false}).order('id', {ascending:false})
        .range(inicio,inicio+limite-1);
      if (codigo) {
        if (codigo.toUpperCase().startsWith('OT-')) {
          query = query.eq('referencia',codigo.toUpperCase());
        } else {
          const {data: product, error} = await db.from(tablaProductos).select('id').eq('codigo', codigo).maybeSingle();
          if (error) throw error;
          if (!product) return reply(200,{ok:true,resultado:[]});
          query = query.eq('producto_id', product.id);
        }
      }
      const { data: rows, error } = await query;
      if (error) throw error;
      const ids = [...new Set((rows ?? []).map((r) => r.producto_id))];
      const { data: products, error: pe } = ids.length ? await db.from(tablaProductos).select('id,codigo,nombre').in('id',ids)
        : {data:[],error:null};
      if (pe) throw pe;
      const index = new Map<string,{codigo:string,nombre:string}>(
        (products ?? []).map((p) => [String(p.id),{codigo:String(p.codigo??''),nombre:String(p.nombre??'')}])
      );
      return reply(200, {ok:true, resultado:(rows ?? []).map((r) => ({
        ...r, codigo:index.get(String(r.producto_id))?.codigo ?? '',
        producto:index.get(String(r.producto_id))?.nombre ?? '',
      }))});
    }
    if (accionBase === 'registrar') {
      const codigo = String(data.codigo ?? '').trim();
      const tipo = String(data.tipo ?? '').trim().toUpperCase();
      const cantidad = Number(data.cantidad);
      const motivo = String(data.motivo ?? '').trim();
      const referencia = String(data.referencia ?? '').trim();
      const destinatario = String(data.destinatario ?? '').trim();
      const idempotencia = String(data.idempotencia ?? '');
      if (!codigo || codigo.length > 120 || !['ENTRADA','SALIDA'].includes(tipo) ||
          !Number.isFinite(cantidad) || cantidad <= 0 || cantidad > 1000000 ||
          Math.abs(Math.round(cantidad*1000) - cantidad*1000) > 0.0000001 ||
          !motivo || motivo.length > 250 || referencia.length > 120 || destinatario.length > 120 ||
          (tipo === 'SALIDA' && !destinatario) ||
          !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(idempotencia)) {
        return reply(400, {ok:false,error:'Datos incompletos o inválidos.'});
      }
      const {data: productActivo, error: ap} = await db.from(tablaProductos)
        .select('activo').eq('codigo',codigo).maybeSingle();
      if (ap) throw ap;
      if (!productActivo?.activo) return reply(409,{ok:false,error:'El producto no existe o fue desactivado.'});
      const {data: registrado, error} = await db.rpc(
        laboratorio ? 'axia_almacen_lab_registrar_movimiento' : 'axia_almacen_registrar_movimiento', {
        p_codigo:codigo,p_tipo:tipo,p_cantidad:cantidad,p_motivo:motivo,
        p_referencia:referencia,p_destinatario:destinatario,
        p_responsable_id:String(usuario.id_usuario),
        p_responsable:String(usuario.usu_nickname || ''),p_idempotencia:idempotencia,
      });
      if (error) {
        const msg = String(error.message ?? '');
        if (msg.includes('LAB_NO_HABILITADO')) return reply(409,{ok:false,error:'El laboratorio no está habilitado. Activa la configuración de PRUEBAS después de validar la instalación.'});
        if (msg.includes('ALMACEN_NO_HABILITADO')) return reply(409,{ok:false,error:'Los movimientos reales aún NO están autorizados. Se necesita catálogo validado y fecha de corte.'});
        if (msg.includes('EXISTENCIA_INSUFICIENTE')) return reply(409,{ok:false,error:'Existencia insuficiente para la salida solicitada.'});
        if (msg.includes('IDEMPOTENCIA_CON_DATOS_DISTINTOS')) return reply(409,{ok:false,error:'Solicitud duplicada con datos diferentes.'});
        if (msg.includes('MOVIMIENTO_INVALIDO') || msg.includes('PRODUCTO_NO_ENCONTRADO') || msg.includes('PRODUCTO_INACTIVO')) return reply(400,{ok:false,error:'Movimiento o producto inválido.'});
        throw error;
      }
      return reply(200, {ok:true,resultado:{...registrado,codigo,tipo,producto:'',
        saldo_nuevo:registrado.saldo_nuevo, saldo_anterior:registrado.saldo_anterior}});
    }
    return reply(400, {ok:false, error:'Acción desconocida.'});
  } catch (err) {
    if (err instanceof Error && err.message === 'SESSION_INVALID') return reply(401,{ok:false,error:'Sesión inválida o vencida. Vuelve a autenticarte.'});
    console.error('axia-almacen', err instanceof Error ? err.message : String(err));
    return reply(500,{ok:false,error:'No fue posible completar la operación. No intentes duplicarla sin verificar el Kardex.'});
  }
});
