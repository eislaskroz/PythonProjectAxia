/**
 * AXIA Draft Media, Etapa 2C — private upload/download for transfer-ready draft files.
 * Deploy with verify_jwt=false ONLY because this function validates AXIA HS256 internally.
 * Never expose SUPABASE_SERVICE_ROLE_KEY in a client.
 */
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { jwtVerify } from "https://deno.land/x/jose@v5.9.6/index.ts";

const BUCKET = "axia-borradores-medios";
const MAX_FILE_BYTES = 8 * 1024 * 1024;
const MIME_EXT: Record<string, string> = {
  "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "application/pdf": "pdf",
};
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const json = (status: number, value: unknown) => new Response(JSON.stringify(value), {
  status, headers: { "content-type": "application/json", "cache-control": "no-store" },
});
const sha256 = async (bytes: Uint8Array) => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)))
  .map(b => b.toString(16).padStart(2, "0")).join("");

Deno.serve(async (req) => {
  if (req.method !== "POST" && req.method !== "GET") return json(405, { ok: false, error: "Método no permitido" });
  try {
    const secret = Deno.env.get("AXIA_MOBILE_JWT_SECRET");
    const url = Deno.env.get("SUPABASE_URL");
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!secret || !url || !serviceKey) return json(503, { ok: false, error: "Servidor sin configurar" });
    const token = /^Bearer\s+(.+)$/i.exec(req.headers.get("authorization") || "")?.[1];
    if (!token) return json(401, { ok: false, error: "Sesión requerida" });
    let claims;
    try {
      ({ payload: claims } = await jwtVerify(token, new TextEncoder().encode(secret), {
        issuer: "axia-field", audience: "axia-mobile", algorithms: ["HS256"],
      }));
    } catch { return json(401, { ok: false, error: "Sesión inválida o vencida" }); }
    const userId = Number(claims.axia_user_id);
    if (!Number.isSafeInteger(userId) || userId <= 0 || String(claims.sub) !== String(userId)) {
      return json(403, { ok: false, error: "Identidad inválida" });
    }
    const db = createClient(url, serviceKey, { auth: { persistSession: false, autoRefreshToken: false } });
    const { data: user, error: userError } = await db.from("db_usuarios")
      .select("id_usuario,usu_tipo").eq("id_usuario", userId).maybeSingle();
    if (userError || !user || Number(user.usu_tipo) !== Number(claims.axia_user_type)) {
      return json(403, { ok: false, error: "Usuario no autorizado" });
    }
    const parsed = new URL(req.url);
    const draftKey = parsed.searchParams.get("borrador") || "";
    if (!UUID.test(draftKey)) return json(400, { ok: false, error: "Identificador de borrador inválido" });
    const prefix = `${userId}/${draftKey}/`;
    // Prevent arbitrary orphan uploads. Create a cloud draft first, then upload its media.
    const { data: draft, error: draftError } = await db.from("axia_borradores_compartidos")
      .select("clave_cliente").eq("usuario_id", userId).eq("modulo", "LEVANTAMIENTO")
      .eq("clave_cliente", draftKey).is("eliminado_en", null).maybeSingle();
    if (draftError || !draft) return json(404, { ok: false, error: "Borrador inexistente o no autorizado" });
    if (req.method === "POST") {
      // This route only accepts raw binary. Neither filename nor object path comes from the caller.
      const mediaType = (req.headers.get("content-type") || "").split(";", 1)[0].toLowerCase();
      const ext = MIME_EXT[mediaType];
      if (!ext) return json(415, { ok: false, error: "Formato no admitido" });
      const length = Number(req.headers.get("content-length") || 0);
      if (length > MAX_FILE_BYTES) return json(413, { ok: false, error: "Archivo demasiado grande" });
      // Extra byte catches chunked bodies without Content-Length.
      const body = new Uint8Array(await req.arrayBuffer());
      if (!body.length || body.length > MAX_FILE_BYTES) return json(413, { ok: false, error: "Archivo vacío o demasiado grande" });
      // Verify file signature, not merely the caller's claimed MIME type.
      const jpeg = body.length >= 3 && body[0] === 0xff && body[1] === 0xd8 && body[2] === 0xff;
      const png = body.length >= 8 && [137,80,78,71,13,10,26,10].every((b,i) => body[i] === b);
      const webp = body.length >= 12 && new TextDecoder().decode(body.subarray(0,4)) === "RIFF" &&
        new TextDecoder().decode(body.subarray(8,12)) === "WEBP";
      const pdf = body.length >= 5 && new TextDecoder().decode(body.subarray(0,5)) === "%PDF-";
      if (!(mediaType === "image/jpeg" && jpeg || mediaType === "image/png" && png ||
            mediaType === "image/webp" && webp || mediaType === "application/pdf" && pdf)) {
        return json(415, { ok: false, error: "Firma de archivo no coincide con su formato" });
      }
      const digest = await sha256(body);
      const expected = req.headers.get("x-axia-sha256")?.toLowerCase();
      if (expected && expected !== digest) return json(422, { ok: false, error: "Contenido alterado durante la transferencia" });
      const path = `${prefix}${crypto.randomUUID()}.${ext}`;
      const { error } = await db.storage.from(BUCKET).upload(path, body, {
        contentType: mediaType, upsert: false, cacheControl: "0",
      });
      if (error) { console.error("storage upload", error.message); return json(502, { ok: false, error: "No fue posible guardar el archivo" }); }
      return json(200, { ok: true, media: { bucket: BUCKET, path, sha256: digest, size: body.length, mime: mediaType } });
    }
    const path = parsed.searchParams.get("ruta") || "";
    // Download is deliberately restricted to the caller's own draft prefix and generated object IDs.
    if (!path.startsWith(prefix) || !new RegExp(`^${userId}/${draftKey}/[0-9a-f-]{36}\\.(jpg|png|webp|pdf)$`, "i").test(path)) {
      return json(403, { ok: false, error: "Archivo no autorizado" });
    }
    const { data, error } = await db.storage.from(BUCKET).download(path);
    if (error || !data) return json(404, { ok: false, error: "Archivo no encontrado" });
    const bytes = new Uint8Array(await data.arrayBuffer());
    if (bytes.length > MAX_FILE_BYTES) return json(413, { ok: false, error: "Archivo demasiado grande" });
    const digest = await sha256(bytes);
    const mime = path.endsWith(".pdf") ? "application/pdf" : path.endsWith(".png") ? "image/png" :
      path.endsWith(".webp") ? "image/webp" : "image/jpeg";
    return new Response(bytes, { status: 200, headers: {
      "content-type": mime, "cache-control": "private, no-store", "x-axia-sha256": digest,
      "content-length": String(bytes.length), "x-content-type-options": "nosniff",
    }});
  } catch (err) {
    console.error("axia-borradores-medios", err);
    return json(500, { ok: false, error: "No se pudo procesar el archivo" });
  }
});
