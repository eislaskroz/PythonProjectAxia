"""Reporte centralizado de errores para soporte de AXIA."""
from __future__ import annotations

import re
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from tkinter import messagebox

from core.logger import configurar_logger

logger = configurar_logger(__name__)
_state = threading.local()

@dataclass
class ErrorReport:
    incident_id: str
    operation: str
    exception_type: str
    technical_message: str
    timestamp: str

_SENSITIVE_PATTERNS = (
    re.compile(r"(?i)(password|contrase(?:ñ|n)a|secret|token|api[_-]?key|service[_-]?role|anon[_-]?key)\s*[:=]\s*[^,;\s]+"),
    re.compile(r"(?i)bearer\s+[a-z0-9._-]+"),
    re.compile(r"eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{10,}"),
)

def _sanitize(value: object) -> str:
    text = str(value or "").strip() or "Sin detalle técnico proporcionado."
    for pattern in _SENSITIVE_PATTERNS:
        text = pattern.sub("[DATO PROTEGIDO]", text)
    return text[:1800]

def _extract(error: BaseException) -> str:
    parts=[]
    for attr in ("message", "code", "details", "hint"):
        value=getattr(error, attr, None)
        if value:
            parts.append(f"{attr}: {value}")
    if getattr(error, "args", None):
        first=error.args[0]
        if isinstance(first, dict):
            for key in ("message", "code", "details", "hint"):
                if first.get(key):
                    parts.append(f"{key}: {first[key]}")
    if not parts:
        parts.append(str(error))
    return _sanitize(" | ".join(dict.fromkeys(parts)))

def register_error(error: BaseException, operation: str) -> ErrorReport:
    report=ErrorReport(
        incident_id=f"AX-{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}",
        operation=operation,
        exception_type=type(error).__name__,
        technical_message=_extract(error),
        timestamp=datetime.now().isoformat(timespec="seconds"),
    )
    _state.last_error=report
    logger.error(
        "Incidencia %s | operación=%s | tipo=%s | detalle=%s",
        report.incident_id, operation, report.exception_type, report.technical_message,
        exc_info=(type(error), error, error.__traceback__),
    )
    return report

def get_last_error() -> ErrorReport | None:
    return getattr(_state, "last_error", None)

def clear_last_error() -> None:
    _state.last_error=None

def show_operation_error(title: str, operation: str, error: BaseException | None = None, parent=None) -> ErrorReport:
    report = register_error(error, operation) if error is not None else get_last_error()
    if report is None:
        report=ErrorReport(
            incident_id=f"AX-{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}",
            operation=operation,
            exception_type="ErrorNoEspecificado",
            technical_message="La operación no devolvió resultado y el servicio no proporcionó una excepción.",
            timestamp=datetime.now().isoformat(timespec="seconds"),
        )
        _state.last_error=report
        logger.error("Incidencia %s sin excepción asociada | operación=%s", report.incident_id, operation)
    message=(
        f"No fue posible completar: {operation}.\n\n"
        f"Motivo técnico:\n{report.technical_message}\n\n"
        f"Tipo: {report.exception_type}\n"
        f"Código de incidencia: {report.incident_id}\n\n"
        "Toma una captura de esta ventana y compártela con soporte. "
        "El detalle completo quedó guardado en axia_errors.log."
    )
    messagebox.showerror(title, message, parent=parent)
    return report
