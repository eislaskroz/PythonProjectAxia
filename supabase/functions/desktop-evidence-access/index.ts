import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { jwtVerify } from "https://deno.land/x/jose@v5.9.6/index.ts";
const headers = { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" };
const out = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers });
function metadataList(value: unknown): Record<string, unknown>[] {
  if (typeof value === "string") { try { return metadataList(JSON.parse(value)); } catch { return []; } }
  if (Array.isArray(value)) return value.filter(v => v && typeof v === "object" && !Array.isArray(v)) as Record<string, unknown>[];
  return [];
}
async function identity(req: Request) {
  const match = /^Bearer\s+(\S+)$/i.exec(req.headers.get("authorization") ?? "");
  if (!match) return null;
  const secret = Deno.env.get("AXIA_MOBILE_JWT_SECRET");
  if (!secret) throw new Error("SERVER_CONFIGURATION");
  try {
    const { payload } = await jwtVerify(match[1], new TextEncoder().encode(secret), {
      algorithms: ["HS256"], issuer: "axia-field", audience: "axia-mobile", requiredClaims: ["sub", "exp", "iat"],
    });
    const id = Number(payload.axia_user_id);
    return Number.isSafeInteger(id) && id > 0 && payload.sub === String(id) ? id : null;
  } catch { return null; }
}
async function expandedAccess(req: Request, userId: number, role: number): Promise<boolean> {
  if (![1, 2, 3].includes(role)) return false;
  const key = req.headers.get("x-axia-desktop-grant") ?? "";
  if (!/^[a-f0-9]{64}$/.test(key)) return false;
  const configured = Deno.env.get("AXIA_DESKTOP_EVIDENCE_GRANTS") ?? "{}";
  const grants = JSON.parse(configured);
  if (!grants || typeof grants !== "object" || Array.isArray(grants)) throw new Error("SERVER_CONFIGURATION");
  const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(key))), b => b.toString(16).padStart(2, "0")).join("");
  if (!Object.prototype.hasOwnProperty.call(grants, hash)) return false;
  const ids = grants[hash];
  return Array.isArray(ids) && ids.some((id: unknown) => typeof id === "number" && Number.isSafeInteger(id) && id === userId);
}
Deno.serve(async req => {
  const requestId = crypto.randomUUID();
  if (req.method !== "POST") return out(405, { ok: false, requestId, error: "Método no permitido" });
  try {
    const userId = await identity(req);
    if (userId === null) return out(401, { ok: false, requestId, error: "La sesión no es válida. Inicia sesión nuevamente." });
    const url = Deno.env.get("SUPABASE_URL"), serviceRole = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!url || !serviceRole) throw new Error("SERVER_CONFIGURATION");
    const admin = createClient(url, serviceRole, { auth: { persistSession: false, autoRefreshToken: false } });
    const current = await admin.from("db_usuarios").select("usu_activo,usu_acceso_habilitado,usu_fecha_baja,usu_tipo").eq("id_usuario", userId).maybeSingle();
    if (current.error) throw current.error;
    if (!current.data || current.data.usu_activo !== true || current.data.usu_acceso_habilitado !== true || current.data.usu_fecha_baja != null)
      return out(403, { ok: false, requestId, error: "Acceso no autorizado" });
    let body; try { body = await req.json(); } catch { return out(400, { ok: false, requestId, error: "Solicitud inválida" }); }
    const bucket = body?.bucket, path = body?.storagePath;
    if (bucket !== "levantamientos-evidencias" || typeof path !== "string" || path.length > 512 || !/^LEV-\d{5,}\/[A-Za-z0-9_-]+\.(jpg|jpeg|png|webp|pdf)$/i.test(path))
      return out(400, { ok: false, requestId, error: "Evidencia inválida" });
    const folio = path.split("/")[0];
    const query = await admin.from("db_levantamientos").select("creado_por_id,lev_evidencias_json").eq("lev_folio", folio).maybeSingle();
    if (query.error) throw query.error;
    const own = query.data?.creado_por_id != null && String(query.data.creado_por_id) === String(userId);
    const authorized = !!query.data && (own || await expandedAccess(req, userId, Number(current.data.usu_tipo)));
    const registered = authorized && metadataList(query.data?.lev_evidencias_json).some(item => item.storage_path === path && (item.bucket ?? bucket) === bucket);
    if (!registered) return out(404, { ok: false, requestId, error: "Evidencia no disponible" });
    const signed = await admin.storage.from(bucket).createSignedUrl(path, 120);
    if (signed.error || !signed.data?.signedUrl) throw new Error("SIGN_FAILED");
    console.log(JSON.stringify({event:"desktop-evidence-authorized",requestId,userId,folio,scope:own?"own":"supervision"}));
    return out(200, { ok: true, requestId, signedUrl: signed.data.signedUrl, expiresIn: 120 });
  } catch {
    console.error(JSON.stringify({ event: "desktop-evidence-error", requestId }));
    return out(500, { ok: false, requestId, error: "No fue posible recuperar la evidencia" });
  }
});
