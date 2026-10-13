"""Cliente del relay de correo de AXIA.

AXIA DESKTOP NO conoce credenciales SMTP. Todos los envíos salen por la Edge
Function ``axia-mail-relay`` de Supabase. Las credenciales y el remitente se
configuran exclusivamente como secretos del lado servidor.
"""
from __future__ import annotations

import base64
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests

from core.environment import cargar_entorno
from core.logger import configurar_logger

logger = configurar_logger(__name__)

_TRUE_VALUES = {"1", "true", "yes", "si", "sí", "on"}
_AUTORIZACION_LEVANTAMIENTOS = "gte.ventas@axiacomunicaciones.mx"
_RELAY_FUNCTION = "axia-mail-relay"
_MAX_ATTACHMENT_BYTES = 12 * 1024 * 1024


@dataclass(frozen=True)
class MailResult:
    sent: bool
    status: str
    detail: str = ""


def _env_bool(nombre: str, default: bool = False) -> bool:
    valor = os.getenv(nombre)
    if valor is None:
        return default
    return valor.strip().lower() in _TRUE_VALUES


def _split_addresses(value: str | None) -> list[str]:
    if not value:
        return []
    normalizado = value.replace(";", ",")
    return [item.strip() for item in normalizado.split(",") if item.strip()]


def _relay_config() -> dict:
    cargar_entorno()
    supabase_url = (os.getenv("SUPABASE_URL") or "").strip()
    base = supabase_url.rstrip("/")
    endpoint = (os.getenv("AXIA_MAIL_RELAY_URL") or "").strip()
    if not endpoint and base:
        endpoint = f"{base}/functions/v1/{_RELAY_FUNCTION}"
    return {
        "enabled": _env_bool("AXIA_MAIL_ENABLED", True),
        "endpoint": endpoint,
        "timeout": max(5, int((os.getenv("AXIA_MAIL_RELAY_TIMEOUT") or "30").strip())),
    }


def _validar_config(config: dict) -> str | None:
    if not config["enabled"]:
        return "El envío automático de correo está desactivado."
    if not config["endpoint"]:
        return "No fue posible construir la URL del relay de correo."
    if not (os.getenv("SUPABASE_KEY") or "").strip():
        return "Falta la clave pública de Supabase requerida para invocar el relay."
    return None


def _attachment_payload(ruta: Path) -> dict:
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el adjunto: {ruta}")
    size = ruta.stat().st_size
    if size > _MAX_ATTACHMENT_BYTES:
        raise ValueError(f"El adjunto {ruta.name} excede el máximo de 12 MB.")
    mime = mimetypes.guess_type(ruta.name)[0] or "application/octet-stream"
    return {
        "filename": ruta.name,
        "contentType": mime,
        "contentBase64": base64.b64encode(ruta.read_bytes()).decode("ascii"),
    }


def enviar_correo(
    *,
    subject: str,
    body: str,
    attachments: Iterable[str | Path] = (),
    to: Iterable[str] | None = None,
    cc: Iterable[str] | None = None,
    bcc: Iterable[str] | None = None,
    flow: str = "operational",
) -> MailResult:
    """Solicita al relay central de AXIA el envío de un correo.

    La aplicación sólo transmite contenido y destinatarios. El servidor aplica
    una allowlist de destinatarios y es el único componente que conoce SMTP,
    contraseña, remitente y BCC de auditoría.
    """
    try:
        config = _relay_config()
    except Exception as exc:
        logger.exception("Configuración del relay de correo inválida.")
        return MailResult(False, "CONFIG_ERROR", str(exc))

    error_config = _validar_config(config)
    if error_config:
        logger.warning("Correo AXIA no enviado: %s", error_config)
        return MailResult(False, "NOT_CONFIGURED", error_config)

    destinatarios = [str(x).strip() for x in (to or []) if str(x).strip()]
    copias = [str(x).strip() for x in (cc or []) if str(x).strip()]
    # BCC deliberadamente no se transmite: se controla sólo en el servidor.
    if bcc:
        logger.info("BCC solicitado por cliente ignorado; el relay controla BCC de auditoría.")

    if not destinatarios:
        return MailResult(False, "NO_RECIPIENTS", "No hay destinatarios para el correo.")

    try:
        adjuntos = [_attachment_payload(Path(archivo)) for archivo in attachments]
    except FileNotFoundError as exc:
        return MailResult(False, "ATTACHMENT_MISSING", str(exc))
    except ValueError as exc:
        return MailResult(False, "ATTACHMENT_TOO_LARGE", str(exc))
    except Exception as exc:
        logger.exception("No fue posible preparar los adjuntos del correo.")
        return MailResult(False, "ATTACHMENT_ERROR", str(exc))

    payload = {
        "flow": str(flow or "operational")[:64],
        "subject": str(subject or "")[:240],
        "text": str(body or ""),
        "to": destinatarios,
        "cc": copias,
        "attachments": adjuntos,
    }
    public_key = (os.getenv("SUPABASE_KEY") or "").strip()
    headers = {
        "Authorization": f"Bearer {public_key}",
        "apikey": public_key,
        "Content-Type": "application/json",
        "X-AXIA-Client": "desktop",
    }

    try:
        response = requests.post(
            config["endpoint"], headers=headers, json=payload, timeout=config["timeout"]
        )
        try:
            data = response.json()
        except Exception:
            data = {}
        if response.ok and data.get("ok"):
            request_id = str(data.get("requestId") or "")
            logger.info("Correo AXIA aceptado por relay. Asunto=%s requestId=%s", subject, request_id)
            return MailResult(True, "SENT", f"Envío central aceptado. ID: {request_id}".strip())

        detail = str(data.get("error") or data.get("detail") or response.text or f"HTTP {response.status_code}")
        logger.error("Relay AXIA rechazó correo. HTTP=%s detalle=%s", response.status_code, detail)
        status = "RELAY_NOT_DEPLOYED" if response.status_code == 404 else "RELAY_ERROR"
        return MailResult(False, status, detail[:500])
    except requests.Timeout:
        logger.exception("Timeout invocando relay de correo AXIA.")
        return MailResult(False, "TIMEOUT", "El relay de correo no respondió a tiempo.")
    except requests.RequestException as exc:
        logger.exception("No fue posible conectar con el relay de correo AXIA.")
        return MailResult(False, "SEND_ERROR", str(exc))
    except Exception as exc:
        logger.exception("Error inesperado invocando relay de correo AXIA.")
        return MailResult(False, "UNEXPECTED_ERROR", str(exc))


def enviar_levantamiento_pdf(
    registro: dict,
    ruta_pdf: str | Path,
    *,
    actualizado: bool = False,
    usuario: str = "",
    folio_origen: str = "",
) -> MailResult:
    folio = str(registro.get("lev_folio") or "SIN-FOLIO").strip().upper()
    cliente = str(registro.get("lev_cliente") or "Sin cliente").strip()
    tipo = str(registro.get("lev_tipo_levantamiento") or registro.get("lev_tipo") or "Levantamiento").strip()
    modalidad = str(registro.get("lev_modalidad_operativa") or "").strip()
    fecha = str(registro.get("lev_fecha_programada") or registro.get("lev_fecha_realizacion") or "").strip()
    tecnico = str(registro.get("lev_tecnico") or "").strip()
    accion = "Nueva versión de levantamiento" if actualizado else "Nuevo levantamiento registrado"

    subject = f"AXIA | {accion} | {folio} | {cliente} | {tipo}"
    lineas = [
        f"{accion} en AXIA DESKTOP.", "", f"Folio: {folio}",
        *([f"Versión generada a partir de: {folio_origen}"] if actualizado and folio_origen else []),
        f"Cliente: {cliente}", f"Tipo: {tipo}",
    ]
    if modalidad: lineas.append(f"Modalidad: {modalidad}")
    if fecha: lineas.append(f"Fecha de levantamiento: {fecha}")
    if tecnico: lineas.append(f"Técnico: {tecnico}")
    if usuario: lineas.append(f"Registrado por: {usuario}")
    lineas.extend(["", "Se adjunta el PDF generado automáticamente por AXIA DESKTOP.", "", "Este es un mensaje automático; favor de no responder a esta cuenta."])

    return enviar_correo(
        subject=subject, body="\n".join(lineas), attachments=[ruta_pdf],
        to=[_AUTORIZACION_LEVANTAMIENTOS], cc=[], flow="levantamiento_registrado",
    )


def enviar_levantamiento_validacion_ventas(
    registro: dict,
    ruta_pdf: str | Path,
    *,
    usuario: str = "",
) -> MailResult:
    folio = str(registro.get("lev_folio") or "SIN-FOLIO").strip().upper()
    cliente = str(registro.get("lev_cliente") or "Sin cliente").strip()
    tipo = str(registro.get("lev_tipo_levantamiento") or registro.get("lev_tipo") or "Levantamiento").strip()
    modalidad = str(registro.get("lev_modalidad_operativa") or "").strip()
    fecha = str(registro.get("lev_fecha_programada") or registro.get("lev_fecha_realizacion") or "").strip()

    subject = f"AXIA | Levantamiento para validar/cotizar | {folio} | {cliente} | {tipo}"
    lineas = [
        "Se envía un levantamiento validado desde AXIA DESKTOP para revisión del área de Ventas.", "",
        f"Folio: {folio}", f"Cliente: {cliente}", f"Tipo: {tipo}",
    ]
    if modalidad: lineas.append(f"Modalidad: {modalidad}")
    if fecha: lineas.append(f"Fecha de levantamiento: {fecha}")
    if usuario: lineas.append(f"Validado por: {usuario}")
    lineas.extend(["", "Se adjunta el PDF del levantamiento para su revisión y proceso de cotización.", "", "Este es un mensaje automático; favor de no responder a esta cuenta."])

    return enviar_correo(
        subject=subject, body="\n".join(lineas), attachments=[ruta_pdf],
        to=[_AUTORIZACION_LEVANTAMIENTOS], cc=[], flow="levantamiento_validacion_ventas",
    )
