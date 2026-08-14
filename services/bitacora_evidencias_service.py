"""Gestión de evidencias fotográficas para Bitácoras Operativas."""
from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from uuid import uuid4

from core.logger import configurar_logger
from supabase_config import supabase
from services.movimientos_service import registrar_movimiento_seguro

logger = configurar_logger(__name__)
BUCKET = "bitacoras-evidencias"
_EXT_PERMITIDAS = {".jpg", ".jpeg", ".png", ".webp"}


def _slug(texto: str) -> str:
    texto = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(texto or "").strip())
    return texto.strip("-.") or "archivo"


def _subir_evidencias(prefijo: str, folio: str, rutas) -> list[dict]:
    """Sube fotografías operativas al bucket existente y devuelve metadatos JSON."""
    folio = _slug(str(folio or "SIN-FOLIO").upper())
    prefijo = _slug(prefijo or "operacion")
    evidencias = []
    for ruta in rutas or []:
        archivo = Path(ruta)
        if not archivo.is_file():
            continue
        ext = archivo.suffix.lower()
        if ext not in _EXT_PERMITIDAS:
            raise ValueError(f"Formato no permitido para evidencia: {archivo.name}")
        mime = mimetypes.guess_type(archivo.name)[0] or "application/octet-stream"
        destino = f"{prefijo}/{folio}/{uuid4().hex}_{_slug(archivo.stem)}{ext}"
        with archivo.open("rb") as fh:
            supabase.storage.from_(BUCKET).upload(
                path=destino,
                file=fh,
                file_options={"content-type": mime, "upsert": "false"},
            )
        try:
            url = supabase.storage.from_(BUCKET).get_public_url(destino)
        except Exception:
            logger.debug("No fue posible obtener URL pública de %s", destino, exc_info=True)
            url = ""
        evidencias.append({
            "nombre": archivo.name,
            "storage_path": destino,
            "url": str(url or ""),
            "mime": mime,
        })
    if evidencias:
        registrar_movimiento_seguro(modulo="EVIDENCIAS", accion="SUBIR_FOTOS", descripcion=f"Se subieron {len(evidencias)} evidencia(s) para {folio}", registro_afectado=folio)
    return evidencias


def subir_evidencias_bitacora(folio: str, rutas) -> list[dict]:
    """Compatibilidad: guarda evidencias de Bitácora."""
    return _subir_evidencias("bitacoras", folio or "BIT-SIN-FOLIO", rutas)


def subir_evidencias_orden_servicio(folio: str, rutas) -> list[dict]:
    """Guarda evidencias fotográficas de una Orden de Servicio."""
    return _subir_evidencias("ordenes-servicio", folio or "OS-SIN-FOLIO", rutas)


def subir_evidencias_levantamiento(folio: str, rutas) -> list[dict]:
    """Guarda evidencias fotográficas de un Levantamiento."""
    return _subir_evidencias("levantamientos", folio or "LEV-SIN-FOLIO", rutas)


def subir_evidencias_obra_civil(folio: str, rutas) -> list[dict]:
    """Guarda evidencias fotográficas de Obra Civil."""
    return _subir_evidencias("obras-civiles", folio or "OBC-SIN-FOLIO", rutas)
