import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { jwtVerify } from "https://deno.land/x/jose@v5.9.6/index.ts";
import bcrypt from "npm:bcryptjs@3.0.2";

const headers = { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" };
const hashPattern = /^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$/;
const encoder = new TextEncoder();

Deno.serve(async (req) => {
  const requestId = crypto.randomUUID();
  const reply = (status: number, body: object) => new Response(JSON.stringify({ ...body, requestId }), { status, headers });
  const fail = (status: number, error: string) => reply(status, { ok: false, error });
  if (req.method !== "POST") return fail(405, "Método no permitido.");
  try {
    const url = Deno.env.get("SUPABASE_URL");
    const key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    const secret = Deno.env.get("AXIA_MOBILE_JWT_SECRET");
    if (!url || !key || !secret || secret.length < 32) throw new Error("CONFIGURATION");
    const token = req.headers.get("authorization")?.match(/^Bearer\s+(\S+)$/i)?.[1];
    if (!token || token.length > 8192) return fail(401, "Sesión inválida.");
    let id: number;
    try {
      const { payload } = await jwtVerify(token, encoder.encode(secret), { issuer: "axia-field", audience: "axia-mobile", algorithms: ["HS256"], requiredClaims: ["sub", "exp", "iat"] });
      id = Number(payload.axia_user_id);
      if (!Number.isSafeInteger(id) || id <= 0 || payload.sub !== String(id) || payload.role !== "authenticated") return fail(401, "Sesión inválida.");
    } catch { return fail(401, "Sesión inválida."); }
    const reader = req.body?.getReader();
    if (!reader) return fail(400, "Solicitud inválida.");
    const decoder = new TextDecoder("utf-8", { fatal: true });
    let raw = "", length = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        length += value.byteLength;
        if (length > 4096) { await reader.cancel(); return fail(413, "Solicitud demasiado grande."); }
        raw += decoder.decode(value, { stream: true });
      }
      raw += decoder.decode();
    } catch { return fail(400, "Solicitud inválida."); }
    let body;
    try { body = JSON.parse(raw); } catch { return fail(400, "JSON inválido."); }
    if (!body || typeof body !== "object" || Array.isArray(body) || Object.keys(body).length !== 2 || typeof body.passwordActual !== "string" || typeof body.passwordNuevo !== "string") return fail(400, "Solicitud inválida.");
    const actual = body.passwordActual;
    const nuevo = body.passwordNuevo;
    if (!actual || encoder.encode(actual).length > 72 || /[\x00-\x1f\x7f]/.test(actual)) return fail(400, "Contraseña actual inválida.");
    if (nuevo.length < 10 || encoder.encode(nuevo).length > 72 || !/[A-Z]/.test(nuevo) || !/[a-z]/.test(nuevo) || !/[0-9]/.test(nuevo) || !/[^A-Za-z0-9]/.test(nuevo) || /[\x00-\x1f\x7f]/.test(nuevo) || actual === nuevo) return fail(400, "La contraseña nueva no cumple los requisitos.");
    const db = createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false } });
    const actor = await db.from("db_usuarios").select("id_usuario,usu_nickname,usu_password,usu_tipo,usu_activo,usu_acceso_habilitado,usu_fecha_baja").eq("id_usuario", id).maybeSingle();
    if (actor.error) throw new Error("ACTOR_LOOKUP");
    const u = actor.data;
    if (!u || u.usu_activo !== true || u.usu_acceso_habilitado !== true || u.usu_fecha_baja != null || !Number.isInteger(Number(u.usu_tipo)) || Number(u.usu_tipo) < 1 || Number(u.usu_tipo) > 10 || !String(u.usu_nickname ?? "").trim()) return fail(401, "Sesión inválida.");
    const limit = await db.rpc("axia_mobile_auth_take_attempt", { p_nickname: u.usu_nickname });
    if (limit.error || typeof limit.data !== "boolean") throw new Error("RATE_LIMIT_UNAVAILABLE");
    if (!limit.data) return fail(429, "Demasiados intentos. Intenta más tarde.");
    const anterior = String(u.usu_password ?? "");
    if (!hashPattern.test(anterior)) return fail(409, "La cuenta requiere revisión de soporte.");
    if (!await bcrypt.compare(actual, anterior)) return fail(403, "La contraseña actual no es correcta.");
    const siguiente = await bcrypt.hash(nuevo, 12);
    if (!await bcrypt.compare(nuevo, siguiente)) throw new Error("HASH_VALIDATION");
    const result = await db.rpc("axia_desktop_cambiar_password", { p_usuario: id, p_hash_anterior: anterior, p_hash_nuevo: siguiente });
    if (result.error || typeof result.data !== "boolean") throw new Error("PASSWORD_TRANSACTION");
    if (!result.data) return fail(409, "La cuenta cambió durante la solicitud. Inicia sesión nuevamente.");
    return reply(200, { ok: true, data: { cambiado: true } });
  } catch {
    console.error(JSON.stringify({ event: "desktop-password-change-error", requestId, code: "INTERNAL_ERROR" }));
    return fail(500, "No fue posible confirmar el cambio de contraseña.");
  }
});
