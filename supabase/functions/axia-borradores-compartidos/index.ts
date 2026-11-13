import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { jwtVerify } from "https://deno.land/x/jose@v5.9.6/index.ts";

const response = (status: number, body: unknown) => new Response(JSON.stringify(body), {
  status, headers: { "content-type": "application/json", "cache-control": "no-store" },
});
const TABLE = "axia_borradores_compartidos";
const MODULOS = new Set(["LEVANTAMIENTO", "BITACORA", "ORDEN_SERVICIO", "REPORTE_FOTOGRAFICO"]);
const MAX_BYTES = 512 * 1024;

Deno.serve(async (req) => {
  if (req.method !== "POST") return response(405, { ok: false, error: "Método no permitido" });
  try {
    const secret = Deno.env.get("AXIA_MOBILE_JWT_SECRET");
    const url = Deno.env.get("SUPABASE_URL");
    const key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!secret || !url || !key) throw new Error("Configuración del servidor incompleta");
    const bearer = /^Bearer\s+(.+)$/i.exec(req.headers.get("authorization") ?? "")?.[1];
    if (!bearer) return response(401, { ok: false, error: "Sesión requerida" });
    let claims;
    try {
      const verified = await jwtVerify(bearer, new TextEncoder().encode(secret), {
        issuer: "axia-field", audience: "axia-mobile", algorithms: ["HS256"],
      });
      claims = verified.payload;
    } catch {
      return response(401, { ok: false, error: "Sesión vencida o inválida" });
    }
    const userId = Number(claims.axia_user_id);
    if (!Number.isSafeInteger(userId) || userId < 1 || String(claims.sub) !== String(userId)) {
      return response(403, { ok: false, error: "Identidad inválida" });
    }
    const admin = createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false } });
    const { data: user, error: userError } = await admin.from("db_usuarios")
      .select("id_usuario,usu_tipo").eq("id_usuario", userId).maybeSingle();
    if (userError || !user || Number(user.usu_tipo) !== Number(claims.axia_user_type)) {
      return response(403, { ok: false, error: "Acceso no autorizado" });
    }
    const raw = await req.text();
    if (new TextEncoder().encode(raw).length > MAX_BYTES) {
      return response(413, { ok: false, error: "Borrador demasiado grande; adjuntos deben sincronizarse por separado" });
    }
    const body = JSON.parse(raw);
    const accion = String(body.accion ?? "");
    const modulo = String(body.modulo ?? "LEVANTAMIENTO");
    if (!MODULOS.has(modulo)) return response(400, { ok: false, error: "Módulo inválido" });
    if (accion === "listar") {
      const { data, error } = await admin.from(TABLE)
        .select("clave_cliente,modulo,origen,esquema,revision,actualizado_en,datos")
        .eq("usuario_id", userId).eq("modulo", modulo).is("eliminado_en", null)
        .order("actualizado_en", { ascending: false }).limit(100);
      if (error) throw error;
      return response(200, { ok: true, borradores: data ?? [] });
    }
    const clave = String(body.clave_cliente ?? "");
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(clave)) {
      return response(400, { ok: false, error: "Identificador de borrador inválido" });
    }
    const filtro = () => admin.from(TABLE).select("revision,eliminado_en")
      .eq("usuario_id", userId).eq("modulo", modulo).eq("clave_cliente", clave);
    const { data: current, error: readError } = await filtro().maybeSingle();
    if (readError) throw readError;
    if (accion === "eliminar") {
      if (!current || current.eliminado_en) return response(200, { ok: true, eliminado: true });
      const revision = Number(body.revision);
      if (revision !== Number(current.revision)) return response(409, { ok: false, error: "Conflicto: el borrador cambió en otro dispositivo", revision: current.revision });
      const { error } = await admin.from(TABLE).update({ eliminado_en: new Date().toISOString(), revision: revision + 1 })
        .eq("usuario_id", userId).eq("modulo", modulo).eq("clave_cliente", clave)
        .eq("revision", revision).is("eliminado_en", null);
      if (error) throw error;
      return response(200, { ok: true, eliminado: true });
    }
    if (accion !== "guardar") return response(400, { ok: false, error: "Acción inválida" });
    if (body.origen !== "DESKTOP" && body.origen !== "FIELD") return response(400, { ok: false, error: "Origen inválido" });
    if (!body.datos || typeof body.datos !== "object" || Array.isArray(body.datos)) {
      return response(400, { ok: false, error: "Datos inválidos" });
    }
    if (body.datos?.schema !== "axia.draft.v1" || body.datos?.module !== modulo) {
      return response(400, { ok: false, error: "Formato compartido no reconocido" });
    }
    if (current) {
      if (current.eliminado_en) return response(409, { ok: false, error: "El borrador fue eliminado en otro dispositivo" });
      if (Number(body.revision) !== Number(current.revision)) {
        return response(409, { ok: false, error: "Conflicto de revisiones", revision: current.revision });
      }
      const { data, error } = await admin.from(TABLE).update({
        datos: body.datos, origen: body.origen, revision: current.revision + 1,
        actualizado_en: new Date().toISOString(),
      }).eq("usuario_id", userId).eq("modulo", modulo).eq("clave_cliente", clave)
        .eq("revision", current.revision).is("eliminado_en", null)
        .select("revision").maybeSingle();
      if (error) throw error;
      if (!data) return response(409, { ok: false, error: "Otro dispositivo actualizó el borrador" });
      return response(200, { ok: true, revision: data.revision });
    }
    if (body.revision !== 0) return response(409, { ok: false, error: "Borrador desconocido; requiere revisión 0" });
    const { data, error } = await admin.from(TABLE).insert({
      usuario_id: userId, modulo, clave_cliente: clave, origen: body.origen, datos: body.datos,
    }).select("revision").single();
    if (error) {
      if (error.code === "23505") return response(409, { ok: false, error: "Conflicto de creación" });
      throw error;
    }
    return response(200, { ok: true, revision: data.revision });
  } catch (error) {
    console.error("axia-borradores-compartidos", error);
    return response(500, { ok: false, error: "No se pudo completar la operación" });
  }
});
