"""Servicio de correo saliente para documentos operativos AXIA.

El módulo usa únicamente la librería estándar de Python y toma toda la
configuración SMTP desde variables de entorno. Ninguna contraseña se almacena
en el código fuente.
"""
from __future__ import annotations

import mimetypes
import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

from core.environment import cargar_entorno
from core.logger import configurar_logger

logger = configurar_logger(__name__)


_TRUE_VALUES = {"1", "true", "yes", "si", "sí", "on"}


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


def _mail_config() -> dict:
    cargar_entorno()
    return {
        "enabled": _env_bool("AXIA_MAIL_ENABLED", True),
        "host": (os.getenv("AXIA_SMTP_HOST") or "").strip(),
        "port": int((os.getenv("AXIA_SMTP_PORT") or "587").strip()),
        "user": (os.getenv("AXIA_SMTP_USER") or os.getenv("AXIA_MAIL_FROM") or "").strip(),
        "password": os.getenv("AXIA_SMTP_PASSWORD") or "",
        "sender": (os.getenv("AXIA_MAIL_FROM") or os.getenv("AXIA_SMTP_USER") or "").strip(),
        "to": _split_addresses(os.getenv("AXIA_MAIL_TO")),
        "cc": _split_addresses(os.getenv("AXIA_MAIL_CC")),
        "use_ssl": _env_bool("AXIA_SMTP_SSL", False),
        "use_starttls": _env_bool("AXIA_SMTP_STARTTLS", True),
        "timeout": max(3, int((os.getenv("AXIA_SMTP_TIMEOUT") or "12").strip())),
    }


def _validar_config(config: dict) -> str | None:
    if not config["enabled"]:
        return "El envío automático de correo está desactivado."
    if not config["host"]:
        return "Falta configurar AXIA_SMTP_HOST en el archivo .env."
    if not config["sender"]:
        return "Falta configurar AXIA_MAIL_FROM en el archivo .env."
    if not config["to"]:
        return "Falta configurar AXIA_MAIL_TO en el archivo .env."
    if config["user"] and not config["password"]:
        return "Falta configurar AXIA_SMTP_PASSWORD en el archivo .env."
    return None


def _adjuntar_archivo(msg: EmailMessage, ruta: Path) -> None:
    mime, _encoding = mimetypes.guess_type(ruta.name)
    if mime:
        maintype, subtype = mime.split("/", 1)
    else:
        maintype, subtype = "application", "octet-stream"
    msg.add_attachment(ruta.read_bytes(), maintype=maintype, subtype=subtype, filename=ruta.name)


def enviar_correo(
    *,
    subject: str,
    body: str,
    attachments: Iterable[str | Path] = (),
    to: Iterable[str] | None = None,
    cc: Iterable[str] | None = None,
) -> MailResult:
    """Envía un correo por SMTP sin comprometer el flujo principal de AXIA.

    Devuelve un resultado estructurado; las excepciones de red/autenticación se
    registran y se convierten en ``MailResult(sent=False)`` para que el guardado
    del documento nunca se revierta por una falla del correo.
    """
    try:
        config = _mail_config()
    except Exception as exc:
        logger.exception("Configuración SMTP inválida.")
        return MailResult(False, "CONFIG_ERROR", str(exc))

    error_config = _validar_config(config)
    if error_config:
        logger.warning("Correo AXIA no enviado: %s", error_config)
        return MailResult(False, "NOT_CONFIGURED", error_config)

    destinatarios = list(to) if to is not None else list(config["to"])
    copias = list(cc) if cc is not None else list(config["cc"])
    destinatarios = [str(x).strip() for x in destinatarios if str(x).strip()]
    copias = [str(x).strip() for x in copias if str(x).strip()]

    msg = EmailMessage()
    msg["From"] = config["sender"]
    msg["To"] = ", ".join(destinatarios)
    if copias:
        msg["Cc"] = ", ".join(copias)
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        for archivo in attachments:
            ruta = Path(archivo)
            if not ruta.is_file():
                return MailResult(False, "ATTACHMENT_MISSING", f"No existe el adjunto: {ruta}")
            _adjuntar_archivo(msg, ruta)

        receptores = destinatarios + copias
        context = ssl.create_default_context()
        if config["use_ssl"]:
            smtp = smtplib.SMTP_SSL(
                config["host"], config["port"], timeout=config["timeout"], context=context
            )
        else:
            smtp = smtplib.SMTP(config["host"], config["port"], timeout=config["timeout"])

        with smtp:
            smtp.ehlo()
            if not config["use_ssl"] and config["use_starttls"]:
                smtp.starttls(context=context)
                smtp.ehlo()
            if config["user"]:
                smtp.login(config["user"], config["password"])
            smtp.send_message(msg, from_addr=config["sender"], to_addrs=receptores)

        logger.info(
            "Correo AXIA enviado. Asunto=%s Para=%s CC=%s",
            subject, ",".join(destinatarios), ",".join(copias),
        )
        return MailResult(True, "SENT", f"Enviado a {', '.join(destinatarios)}")
    except smtplib.SMTPAuthenticationError as exc:
        logger.exception("Falló la autenticación SMTP de AXIA.")
        return MailResult(False, "AUTH_ERROR", f"El servidor rechazó las credenciales SMTP ({exc.smtp_code}).")
    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        logger.exception("No fue posible enviar el correo SMTP de AXIA.")
        return MailResult(False, "SEND_ERROR", str(exc))
    except Exception as exc:
        logger.exception("Error inesperado enviando correo AXIA.")
        return MailResult(False, "UNEXPECTED_ERROR", str(exc))


def enviar_levantamiento_pdf(
    registro: dict,
    ruta_pdf: str | Path,
    *,
    actualizado: bool = False,
    usuario: str = "",
    folio_origen: str = "",
) -> MailResult:
    """Envía el PDF de un levantamiento recién guardado o actualizado."""
    folio = str(registro.get("lev_folio") or "SIN-FOLIO").strip().upper()
    cliente = str(registro.get("lev_cliente") or "Sin cliente").strip()
    tipo = str(registro.get("lev_tipo_levantamiento") or registro.get("lev_tipo") or "Levantamiento").strip()
    modalidad = str(registro.get("lev_modalidad_operativa") or "").strip()
    fecha = str(registro.get("lev_fecha_programada") or registro.get("lev_fecha_realizacion") or "").strip()
    tecnico = str(registro.get("lev_tecnico") or "").strip()
    accion = "Nueva versión de levantamiento" if actualizado else "Nuevo levantamiento registrado"

    subject = f"AXIA | {accion} | {folio} | {cliente} | {tipo}"
    lineas = [
        f"{accion} en AXIA DESKTOP.",
        "",
        f"Folio: {folio}",
        *([f"Versión generada a partir de: {folio_origen}"] if actualizado and folio_origen else []),
        f"Cliente: {cliente}",
        f"Tipo: {tipo}",
    ]
    if modalidad:
        lineas.append(f"Modalidad: {modalidad}")
    if fecha:
        lineas.append(f"Fecha de levantamiento: {fecha}")
    if tecnico:
        lineas.append(f"Técnico: {tecnico}")
    if usuario:
        lineas.append(f"Registrado por: {usuario}")
    lineas.extend([
        "",
        "Se adjunta el PDF generado automáticamente por AXIA DESKTOP.",
        "",
        "Este es un mensaje automático; favor de no responder a esta cuenta.",
    ])

    return enviar_correo(subject=subject, body="\n".join(lineas), attachments=[ruta_pdf])


def enviar_levantamiento_validacion_ventas(
    registro: dict,
    ruta_pdf: str | Path,
    *,
    usuario: str = "",
) -> MailResult:
    """Envía un levantamiento a Ventas para su revisión/cotización.

    El destinatario de este flujo es deliberadamente fijo para evitar que una
    variable general de notificaciones desvíe una validación comercial.
    """
    folio = str(registro.get("lev_folio") or "SIN-FOLIO").strip().upper()
    cliente = str(registro.get("lev_cliente") or "Sin cliente").strip()
    tipo = str(registro.get("lev_tipo_levantamiento") or registro.get("lev_tipo") or "Levantamiento").strip()
    modalidad = str(registro.get("lev_modalidad_operativa") or "").strip()
    fecha = str(registro.get("lev_fecha_programada") or registro.get("lev_fecha_realizacion") or "").strip()

    subject = f"AXIA | Levantamiento para validar/cotizar | {folio} | {cliente} | {tipo}"
    lineas = [
        "Se envía un levantamiento validado desde AXIA DESKTOP para revisión del área de Ventas.",
        "",
        f"Folio: {folio}",
        f"Cliente: {cliente}",
        f"Tipo: {tipo}",
    ]
    if modalidad:
        lineas.append(f"Modalidad: {modalidad}")
    if fecha:
        lineas.append(f"Fecha de levantamiento: {fecha}")
    if usuario:
        lineas.append(f"Validado por: {usuario}")
    lineas.extend([
        "",
        "Se adjunta el PDF del levantamiento para su revisión y proceso de cotización.",
        "",
        "Este es un mensaje automático; favor de no responder a esta cuenta.",
    ])

    return enviar_correo(
        subject=subject,
        body="\n".join(lineas),
        attachments=[ruta_pdf],
        to=["gte.ventas@axiacomunicaciones.mx"],
        cc=["eislaskroz@gmail.com"],
    )
