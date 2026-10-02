import nodemailer from "npm:nodemailer@6.9.16";

const headers = {
  "Content-Type": "application/json; charset=utf-8",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-axia-client, x-axia-mail-token",
};
const out = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers });
const MAX_ATTACHMENT_BYTES = 12 * 1024 * 1024;
const MAX_TOTAL_BYTES = 16 * 1024 * 1024;
const FLOWS = new Set(["levantamiento_registrado", "levantamiento_validacion_ventas", "operational", "field_lift", "ticket_internal", "ticket_customer"]);
const SERVER_FLOWS = new Set(["field_lift", "ticket_internal", "ticket_customer"]);
const DESKTOP_FLOWS = new Set(["levantamiento_registrado", "levantamiento_validacion_ventas", "operational"]);

function list(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((x) => String(x ?? "").trim().toLowerCase()).filter(Boolean);
}
function envList(name: string): string[] {
  return String(Deno.env.get(name) ?? "").split(/[;,]/).map((x) => x.trim().toLowerCase()).filter(Boolean);
}
function validEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}
function decodeBase64(value: string): Uint8Array {
  const raw = atob(value);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
  return bytes;
}

Deno.serve(async (req) => {
  const requestId = crypto.randomUUID();
  if (req.method === "OPTIONS") return new Response("ok", { headers });
  if (req.method !== "POST") return out(405, { ok: false, requestId, error: "Método no permitido" });

  try {
    const body = await req.json();
    const flow = String(body?.flow ?? "operational").trim();
    if (!FLOWS.has(flow)) return out(400, { ok: false, requestId, error: "Flujo de correo no permitido" });

    // Dos niveles de acceso:
    // 1) DESKTOP usa la clave pública de Supabase, pero queda limitado a flows de
    //    escritorio + allowlist estricta. La clave pública nunca se trata como secreto.
    // 2) FIELD/TICKETS son server-to-server y deben presentar un secreto independiente
    //    que jamás se distribuye en APK/PC.
    const expectedAnon = String(Deno.env.get("SUPABASE_ANON_KEY") ?? "").trim();
    const apiKey = String(req.headers.get("apikey") ?? "").trim();
    const expectedServiceToken = String(Deno.env.get("AXIA_MAIL_SERVICE_TOKEN") ?? "").trim();
    const serviceToken = String(req.headers.get("x-axia-mail-token") ?? "").trim();
    const serverAuthorized = expectedServiceToken.length >= 32 && serviceToken === expectedServiceToken;
    const desktopAuthorized = expectedAnon.length > 0 && apiKey === expectedAnon;
    if (SERVER_FLOWS.has(flow) && !serverAuthorized) return out(401, { ok: false, requestId, error: "Servicio no autorizado" });
    if (DESKTOP_FLOWS.has(flow) && !desktopAuthorized) return out(401, { ok: false, requestId, error: "Cliente no autorizado" });

    const subject = String(body?.subject ?? "").trim().slice(0, 240);
    const text = String(body?.text ?? "");
    const to = list(body?.to);
    const cc = list(body?.cc);
    if (!subject || !text || !to.length) return out(400, { ok: false, requestId, error: "Correo incompleto" });
    if (text.length > 100_000) return out(413, { ok: false, requestId, error: "Contenido demasiado grande" });

    const allowed = new Set(envList("AXIA_MAIL_ALLOWED_RECIPIENTS"));
    const allRequested = [...to, ...cc];
    if (allRequested.length > 4 || allRequested.some((x) => !validEmail(x))) {
      return out(400, { ok: false, requestId, error: "Destinatarios inválidos" });
    }
    // Sólo ticket_customer puede dirigirse a un correo externo y únicamente cuando
    // la solicitud viene de una Edge Function autenticada con el secreto servidor.
    // Todos los demás flows permanecen encerrados en la allowlist del servidor.
    if (flow === "ticket_customer") {
      if (!serverAuthorized || to.length !== 1 || cc.length !== 0) return out(403, { ok: false, requestId, error: "Destinatario de ticket no autorizado" });
    } else {
      if (!allowed.size) throw new Error("AXIA_MAIL_ALLOWED_RECIPIENTS_NOT_CONFIGURED");
      if (allRequested.some((x) => !allowed.has(x))) return out(403, { ok: false, requestId, error: "Destinatario no autorizado por el relay" });
    }

    const rawAttachments = Array.isArray(body?.attachments) ? body.attachments : [];
    if (rawAttachments.length > 3) return out(413, { ok: false, requestId, error: "Demasiados adjuntos" });
    let total = 0;
    const attachments = rawAttachments.map((item: Record<string, unknown>) => {
      const filename = String(item?.filename ?? "archivo.pdf").replace(/[^A-Za-z0-9._ -]/g, "_").slice(0, 120);
      const contentType = String(item?.contentType ?? "application/octet-stream").toLowerCase();
      if (contentType !== "application/pdf") throw new Error("ATTACHMENT_TYPE_NOT_ALLOWED");
      const bytes = decodeBase64(String(item?.contentBase64 ?? ""));
      if (!bytes.length || bytes.length > MAX_ATTACHMENT_BYTES) throw new Error("ATTACHMENT_SIZE_INVALID");
      total += bytes.length;
      return { filename, content: bytes, contentType };
    });
    if (total > MAX_TOTAL_BYTES) return out(413, { ok: false, requestId, error: "Adjuntos demasiado grandes" });

    const host = String(Deno.env.get("AXIA_SMTP_HOST") ?? "").trim();
    const port = Number(Deno.env.get("AXIA_SMTP_PORT") ?? "587");
    const user = String(Deno.env.get("AXIA_SMTP_USER") ?? "").trim();
    const password = String(Deno.env.get("AXIA_SMTP_PASSWORD") ?? "");
    const from = String(Deno.env.get("AXIA_MAIL_FROM") ?? user).trim();
    const fromName = String(Deno.env.get("AXIA_MAIL_FROM_NAME") ?? "AXIA Comunicaciones").trim();
    const secure = String(Deno.env.get("AXIA_SMTP_SSL") ?? "0") === "1" || port === 465;
    if (!host || !port || !user || !password || !from) throw new Error("SMTP_SERVER_CONFIGURATION");

    const auditBcc = envList("AXIA_MAIL_BCC");
    const transporter = nodemailer.createTransport({
      host, port, secure,
      auth: { user, pass: password },
      requireTLS: !secure,
      connectionTimeout: 12000,
      greetingTimeout: 12000,
      socketTimeout: 20000,
    });

    const info = await transporter.sendMail({
      from: { name: fromName, address: from },
      to, cc, bcc: auditBcc,
      subject, text, attachments,
      headers: { "X-AXIA-Request-ID": requestId, "X-AXIA-Flow": flow },
    });
    console.log(JSON.stringify({ event: "axia-mail-sent", requestId, flow, to, cc, messageId: info.messageId }));
    return out(200, { ok: true, requestId });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(JSON.stringify({ event: "axia-mail-error", requestId, message }));
    if (message === "ATTACHMENT_TYPE_NOT_ALLOWED") return out(415, { ok: false, requestId, error: "Sólo se permiten PDFs" });
    if (message === "ATTACHMENT_SIZE_INVALID") return out(413, { ok: false, requestId, error: "Adjunto inválido o demasiado grande" });
    return out(500, { ok: false, requestId, error: "No fue posible enviar el correo" });
  }
});
