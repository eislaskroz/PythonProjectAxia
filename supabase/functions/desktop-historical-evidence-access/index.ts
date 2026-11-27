import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { jwtVerify } from "https://deno.land/x/jose@v5.9.6/index.ts";

const BUCKET = "bitacoras-evidencias";
const MODULES: Record<string, { table: string; folio: string; field: string; prefix: string }> = {
  "bitacoras": {table:"db_bitacoras",folio:"bit_folio",field:"bit_fotos",prefix:"BIT"},
  "ordenes-servicio": {table:"db_ordenes_servicio",folio:"os_folio",field:"os_fotos",prefix:"OS"},
  "levantamientos": {table:"db_levantamientos",folio:"lev_folio",field:"lev_evidencias_json",prefix:"LEV"},
  "levantamientos-archivos": {table:"db_levantamientos",folio:"lev_folio",field:"lev_archivos_adjuntos_json",prefix:"LEV"},
  "obras-civiles": {table:"db_obras_civiles",folio:"obc_folio",field:"obc_evidencias_json",prefix:"OBC"},
  "obras-civiles-archivos": {table:"db_obras_civiles",folio:"obc_folio",field:"obc_archivos_adjuntos_json",prefix:"OBC"},
};

function referenceMatches(value: unknown, path: string, origin: string, depth = 0): boolean {
  if (depth > 24) return false;
  if (typeof value === "string") {
    const s = value.trim();
    if (s === path) return true;
    if (s.startsWith("[") || s.startsWith("{")) {
      try { return referenceMatches(JSON.parse(s), path, origin, depth + 1); } catch { return false; }
    }
    try {
      const u = new URL(s);
      if (u.origin !== origin || u.username || u.password) return false;
      const p = decodeURIComponent(u.pathname);
      return ["public", "sign", "authenticated"].some(kind => p === `/storage/v1/object/${kind}/${BUCKET}/${path}`);
    } catch { return false; }
  }
  if (Array.isArray(value)) return value.some(v => referenceMatches(v,path,origin,depth+1));
  if (value && typeof value === "object") {
    const item = value as Record<string,unknown>;
    if (typeof item.bucket === "string" && item.bucket !== BUCKET) return false;
    const keys = ["storage_path","storagePath","url","public_url","publicUrl","ruta","path"];
    if (keys.some(k => typeof item[k] === "string" && referenceMatches(item[k],path,origin,depth+1))) return true;
    return Object.values(item).some(v => v !== null && typeof v === "object" && referenceMatches(v,path,origin,depth+1));
  }
  return false;
}

Deno.serve(async (req: Request) => {
  const requestId = crypto.randomUUID();
  const out = (status: number, body: object) => new Response(JSON.stringify({requestId,...body}), {status,headers:{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store"}});
  const fail = (status:number,error:string) => out(status,{ok:false,error});
  if (req.method !== "POST") return fail(405,"Método no permitido.");
  try {
    const secret = Deno.env.get("AXIA_MOBILE_JWT_SECRET"), url = Deno.env.get("SUPABASE_URL"), service = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!secret || !url || !service) throw Error("CONFIG");
    let userId: number;
    try {
      const token = req.headers.get("authorization")?.match(/^Bearer\s+(\S+)$/i)?.[1];
      if (!token) throw Error();
      const {payload} = await jwtVerify(token,new TextEncoder().encode(secret),{algorithms:["HS256"],issuer:"axia-field",audience:"axia-mobile",requiredClaims:["sub","exp","iat"]});
      userId = Number(payload.axia_user_id);
      if (!Number.isSafeInteger(userId) || userId <= 0 || payload.sub !== String(userId)) throw Error();
    } catch { return fail(401,"Sesión inválida."); }
    const grant = req.headers.get("x-axia-desktop-grant") ?? "";
    if (!/^[a-f0-9]{64}$/.test(grant)) return fail(403,"Autorización corporativa requerida.");
    const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(grant))),b=>b.toString(16).padStart(2,"0")).join("");
    const grants = JSON.parse(Deno.env.get("AXIA_DESKTOP_EVIDENCE_GRANTS") ?? "{}");
    if (!grants || typeof grants !== "object" || Array.isArray(grants) || !Object.prototype.hasOwnProperty.call(grants,hash) || !Array.isArray(grants[hash]) || !grants[hash].includes(userId)) return fail(403,"Autorización corporativa requerida.");
    const db = createClient(url,service,{auth:{persistSession:false,autoRefreshToken:false}});
    const actor = await db.from("db_usuarios").select("usu_tipo,usu_activo,usu_acceso_habilitado,usu_fecha_baja").eq("id_usuario",userId).maybeSingle();
    if (actor.error) throw actor.error;
    if (!actor.data || Number(actor.data.usu_tipo) !== 1 || actor.data.usu_activo !== true || actor.data.usu_acceso_habilitado !== true || actor.data.usu_fecha_baja !== null) return fail(403,"Acceso no autorizado.");
    let body; try { body = await req.json(); } catch { return fail(400,"Solicitud inválida."); }
    const path = body?.storagePath;
    if (body?.bucket !== BUCKET || typeof path !== "string" || path.length > 512) return fail(400,"Evidencia inválida.");
    const parts = path.split("/");
    if (parts.length !== 3) return fail(400,"Evidencia inválida.");
    const [module,folder,file] = parts;
    const isObc = module === "obras-civiles" || module === "obras-civiles-archivos";
    const folio = isObc && typeof body?.folio === "string" ? body.folio : folder;
    if (!Object.prototype.hasOwnProperty.call(MODULES,module)) return fail(400,"Evidencia inválida.");
    const config = MODULES[module];
    const folderIsFolio = new RegExp(`^${config.prefix}-[0-9]{${isObc ? 4 : 5},}$`).test(folder);
    const folderIsRequest = isObc && /^(SOLICITUD|EDICION)-[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(folder);
    const fileValid = /^[0-9a-f]{32}_[A-Za-z0-9_.-]+\.(jpg|jpeg|png|webp|pdf|dwg|dxf)$/i.test(file) || (isObc && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}_[A-Za-z0-9_.-]+\.(jpg|jpeg|png|webp|pdf|dwg|dxf)$/i.test(file));
    if (!new RegExp(`^${config.prefix}-[0-9]{${isObc ? 4 : 5},}$`).test(folio) || (!folderIsFolio && !folderIsRequest) || !fileValid) return fail(400,"Evidencia inválida.");
    const document = await db.from(config.table).select(config.field).eq(config.folio,folio).maybeSingle();
    if (document.error) throw document.error;
    if (!document.data || !referenceMatches((document.data as unknown as Record<string,unknown>)[config.field],path,new URL(url).origin)) return fail(404,"Evidencia no disponible.");
    const signed = await db.storage.from(BUCKET).createSignedUrl(path,120);
    if (signed.error || !signed.data?.signedUrl) return fail(503,"Evidencia no disponible.");
    console.log(JSON.stringify({event:"desktop-historical-evidence-authorized",requestId,userId,folio,module}));
    return out(200,{ok:true,bucket:BUCKET,storagePath:path,signedUrl:signed.data.signedUrl,expiresIn:120});
  } catch {
    console.error(JSON.stringify({event:"desktop-historical-evidence-error",requestId}));
    return fail(503,"No fue posible recuperar la evidencia.");
  }
});
