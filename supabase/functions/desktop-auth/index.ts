import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { SignJWT } from "https://deno.land/x/jose@v5.9.6/index.ts";
import bcrypt from "npm:bcryptjs@3.0.2";

const headers = { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" };
const response = (status: number, body: unknown, extra = {}) => new Response(JSON.stringify(body), { status, headers: { ...headers, ...extra } });
const dummyHash = "$2b$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy";
const hashPattern = /^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$/;
const cleanLog = (v: unknown, max: number) => String(v ?? "").replace(/[\x00-\x1f\x7f]/g, " ").trim().slice(0, max);

Deno.serve(async (req) => {
  const requestId = crypto.randomUUID();
  const fail = (status: number, error: string, retryable = false, extra = {}) => response(status, { ok: false, error, retryable, requestId }, extra);
  if (req.method !== "POST") return fail(405, "Método no permitido.");
  try {
    let body;
    try { body = await req.json(); } catch { return fail(400, "Solicitud inválida."); }
    const nickname = typeof body?.nickname === "string" ? body.nickname.trim() : "";
    const password = typeof body?.password === "string" ? body.password : "";
    if (!nickname || !password || nickname.length > 128 || password.length > 1024 || /[\x00-\x1f\x7f]/.test(nickname)) return fail(400, "Usuario y contraseña son obligatorios o inválidos.");
    const url = Deno.env.get("SUPABASE_URL");
    const key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    const jwtSecret = Deno.env.get("AXIA_MOBILE_JWT_SECRET");
    if (!url || !key || !jwtSecret || jwtSecret.length < 32) throw new Error("SERVER_CONFIGURATION");
    const admin = createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false } });
    const limit = await admin.rpc("axia_mobile_auth_take_attempt", { p_nickname: nickname });
    if (limit.error || typeof limit.data !== "boolean") throw new Error("RATE_LIMIT_UNAVAILABLE");
    if (!limit.data) return fail(429, "Demasiados intentos. Intenta nuevamente en unos minutos.", true, { "Retry-After": "300" });
    const forwarded = cleanLog(req.headers.get("x-forwarded-for")?.split(",")[0], 128);
    const deviceName = cleanLog(body?.deviceName, 128);
    const appVersion = cleanLog(body?.appVersion, 64);
    const geo = body?.ubicacion;
    const coordinate = (value: unknown, bound: number) => {
      if (typeof value !== "string" || !/^-?\d{1,3}(?:\.\d{1,7})?$/.test(value)) return "No disponible";
      const n = Number(value);
      return Number.isFinite(n) && Math.abs(n) <= bound ? n.toFixed(7) : "No disponible";
    };
    const loginContext = { direccion_ip: forwarded || "No disponible", nombre_equipo: [deviceName, appVersion ? `AXIA DESKTOP ${appVersion}` : "AXIA DESKTOP"].filter(Boolean).join(" | "), latitud: coordinate(geo?.latitud, 90), longitud: coordinate(geo?.longitud, 180), ciudad: cleanLog(geo?.ciudad, 120) || "No disponible", region: cleanLog(geo?.region, 120) || "No disponible", pais: cleanLog(geo?.pais, 120) || "No disponible" };
    const auditLogin = async (userId: number | null, auditedNickname: string, status: "CORRECTO" | "FALLIDO", description: string) => {
      try {
        const result = await admin.from("db_login").insert({ id_usuario: userId, usu_nickname: auditedNickname, fecha_hora: new Date().toISOString(), estatus: status, descripcion: description, ...loginContext });
        if (result.error) console.error(JSON.stringify({ event: "desktop-login-audit-error", requestId, code: result.error.code ?? "AUDIT_FAILED" }));
      } catch { console.error(JSON.stringify({ event: "desktop-login-audit-error", requestId, code: "AUDIT_FAILED" })); }
    };
    const literalNickname = nickname.replace(/[\\%_]/g, "\\$&");
    const result = await admin.from("db_usuarios").select("id_usuario,usu_nickname,usu_nombre,usu_apellido,usu_tipo,usu_password,usu_activo,usu_acceso_habilitado,usu_fecha_baja").ilike("usu_nickname", literalNickname).limit(2);
    if (result.error) throw new Error("USER_LOOKUP_FAILED");
    const user = result.data?.length === 1 ? result.data[0] : null;
    const storedHash = String(user?.usu_password ?? "");
    const usableHash = hashPattern.test(storedHash);
    const passwordValid = await bcrypt.compare(password, usableHash ? storedHash : dummyHash);
    const userId = Number(user?.id_usuario);
    const validId = Number.isSafeInteger(userId) && userId > 0;
    const allowed = user && validId && Number.isInteger(Number(user.usu_tipo)) && Number(user.usu_tipo) >= 1 && Number(user.usu_tipo) <= 10 && usableHash && passwordValid && user.usu_activo === true && user.usu_acceso_habilitado === true && user.usu_fecha_baja == null;
    if (!allowed) {
      await auditLogin(validId ? userId : null, String(user?.usu_nickname ?? nickname), "FALLIDO", "Usuario o contraseña incorrectos o acceso no autorizado");
      return fail(401, "Usuario o contraseña incorrectos.");
    }
    const now = Math.floor(Date.now() / 1000);
    const expires = now + 8 * 60 * 60;
    const fullName = [user.usu_nombre, user.usu_apellido].map(part => String(part ?? "").trim()).filter(Boolean).join(" ");
    const token = await new SignJWT({ role: "authenticated", nickname: user.usu_nickname, axia_full_name: fullName, axia_user_id: user.id_usuario, axia_user_type: user.usu_tipo }).setProtectedHeader({ alg: "HS256", typ: "JWT" }).setIssuer("axia-field").setAudience("axia-mobile").setSubject(String(user.id_usuario)).setIssuedAt(now).setExpirationTime(expires).sign(new TextEncoder().encode(jwtSecret));
    await auditLogin(userId, String(user.usu_nickname ?? nickname), "CORRECTO", "Inicio de sesión exitoso");
    return response(200, { ok: true, requestId, data: { id_usuario: user.id_usuario, usu_nickname: user.usu_nickname, usu_nombre: user.usu_nombre, usu_apellido: user.usu_apellido, usu_tipo: user.usu_tipo, accessToken: token, expiresAtEpochSeconds: expires } });
  } catch {
    console.error(JSON.stringify({ event: "desktop-auth-error", requestId, code: "INTERNAL_ERROR" }));
    return fail(500, "No fue posible iniciar sesión.", true);
  }
});
