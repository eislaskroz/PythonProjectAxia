import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const headers = {
  "Content-Type": "application/json; charset=utf-8",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
};
const out = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers });

function metadataList(value: unknown): Record<string, unknown>[] {
  if (Array.isArray(value)) return value.filter((item) => item && typeof item === "object") as Record<string, unknown>[];
  if (typeof value === "string" && value.trim()) {
    try { return metadataList(JSON.parse(value)); } catch { return []; }
  }
  return [];
}

Deno.serve(async (req) => {
  const requestId = crypto.randomUUID();
  if (req.method === "OPTIONS") return new Response("ok", { headers });
  if (req.method !== "POST") return out(405, { ok: false, requestId, error: "Método no permitido" });

  try {
    const body = await req.json();
    const bucket = String(body?.bucket ?? "").trim();
    const storagePath = String(body?.storagePath ?? "").trim();
    if (bucket !== "levantamientos-evidencias") return out(403, { ok: false, requestId, error: "Bucket no permitido" });
    if (!/^LEV-\d{5}\/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp|pdf)$/i.test(storagePath)) {
      return out(400, { ok: false, requestId, error: "Ruta inválida" });
    }

    const url = Deno.env.get("SUPABASE_URL");
    const serviceRole = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!url || !serviceRole) throw new Error("SERVER_CONFIGURATION");
    const admin = createClient(url, serviceRole, { auth: { persistSession: false, autoRefreshToken: false } });
    const folio = storagePath.split("/", 1)[0];
    const result = await admin
      .from("db_levantamientos")
      .select("lev_evidencias_json")
      .eq("lev_folio", folio)
      .maybeSingle();
    if (result.error) throw result.error;
    const registered = metadataList(result.data?.lev_evidencias_json)
      .some((item) => String(item.storage_path ?? "") === storagePath && String(item.bucket ?? bucket) === bucket);
    if (!registered) return out(404, { ok: false, requestId, error: "El archivo no pertenece al levantamiento" });

    const signed = await admin.storage.from(bucket).createSignedUrl(storagePath, 120);
    if (signed.error || !signed.data?.signedUrl) throw signed.error ?? new Error("SIGNED_URL_EMPTY");
    return out(200, { ok: true, requestId, signedUrl: signed.data.signedUrl, expiresIn: 120 });
  } catch (error) {
    console.error(JSON.stringify({ event: "mobile-evidence-access-error", requestId, message: error instanceof Error ? error.message : String(error) }));
    return out(500, { ok: false, requestId, error: "No fue posible autorizar el complemento" });
  }
});
