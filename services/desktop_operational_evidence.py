from __future__ import annotations

import hashlib
import io
import os
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from ui.pdf_progress import progreso_pdf

import requests
from PIL import Image
from services.desktop_evidence_access import EvidenciaNoDisponible

PILOTO = {
    "BIT-00024": ("BITACORA", "aa197e09-b4da-4204-bc41-a9aee893656f"),
    "OS-00005": ("ORDEN_SERVICIO", "2cc3d2ba-7b0c-4731-9bca-512d69adb4ec"),
}
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
_MAX = 10 * 1024 * 1024
_FORMATOS = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


@dataclass(frozen=True)
class FotoOperativaPrivada:
    nombre: str
    contenido: bytes


def es_folio_piloto(folio):
    return str(folio or "").strip().upper() in PILOTO


def descargar_fotos_operativas(folio: str) -> list[FotoOperativaPrivada]:
    from app_context import obtener_usuario_actual
    from services.sesion_axia_compartida import obtener_sesion
    from supabase_config import SUPABASE_URL, SUPABASE_KEY

    if folio not in PILOTO:
        raise EvidenciaNoDisponible("Documento fuera del piloto de fotografías privadas.")
    tipo, sync = PILOTO[folio]
    token = obtener_sesion(obtener_usuario_actual().get("id_usuario"))
    if not token:
        raise EvidenciaNoDisponible("Inicia sesión nuevamente en AXIA DESKTOP.")
    grant = os.getenv("AXIA_DESKTOP_EVIDENCE_GRANT", "").strip()
    if not re.fullmatch(r"[a-f0-9]{64}", grant):
        raise EvidenciaNoDisponible("Autorización corporativa de evidencias requerida.")
    base = str(SUPABASE_URL).rstrip("/")
    origin = urlsplit(base)
    if origin.scheme != "https" or not origin.hostname or origin.username or origin.password:
        raise EvidenciaNoDisponible("Configuración HTTPS de Supabase inválida.")
    headers = {"Authorization": f"Bearer {token}", "apikey": str(SUPABASE_KEY), "X-AXIA-Desktop-Grant": grant, "Content-Type": "application/json"}
    try:
        response = requests.post(base + "/functions/v1/desktop-operational-evidence-access-v3", json={"folio": folio}, headers=headers, timeout=(6, 20), allow_redirects=False)
        if response.status_code != 200:
            raise EvidenciaNoDisponible(f"Consulta privada no autorizada o no disponible (HTTP {response.status_code}).")
        data = response.json()
        photos = data.get("photos")
        if data.get("ok") is not True or data.get("folio") != folio or not isinstance(photos, list) or len(photos) != 2:
            raise EvidenciaNoDisponible("El manifiesto de fotografías está incompleto.")
        result = []
        seen = set()
        progreso_pdf("Descargando evidencias privadas…", 0, len(photos))
        for i, item in enumerate(photos, 1):
            photo = item.get("photoId")
            if not isinstance(photo, str) or not _UUID.fullmatch(photo) or photo in seen:
                raise EvidenciaNoDisponible("Identificador de fotografía inválido.")
            seen.add(photo)
            path = f"v3/20/OT-00009/{tipo}/{sync}/{photo}"
            signed = item.get("signedUrl")
            if not isinstance(signed, str):
                raise EvidenciaNoDisponible("Dirección de evidencia inválida.")
            parsed = urlsplit(signed)
            if item.get("storagePath") != path or (parsed.scheme, parsed.netloc) != (origin.scheme, origin.netloc) or parsed.path != "/storage/v1/object/sign/axia-operational-evidence/" + path or not parsed.query or parsed.fragment:
                raise EvidenciaNoDisponible("Dirección de evidencia inválida.")
            size, digest, mime = item.get("sizeBytes"), item.get("sha256"), item.get("mimeType")
            if type(size) is not int or not 0 < size <= _MAX or not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest) or mime not in _FORMATOS:
                raise EvidenciaNoDisponible("Metadatos de fotografía inválidos.")
            with requests.get(signed, stream=True, timeout=(6, 20), allow_redirects=False) as download:
                if download.status_code != 200:
                    raise EvidenciaNoDisponible("No fue posible descargar la fotografía privada.")
                raw = bytearray()
                for chunk in download.iter_content(65536):
                    raw.extend(chunk)
                    if len(raw) > size:
                        raise EvidenciaNoDisponible("Tamaño de fotografía inconsistente.")
            if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
                raise EvidenciaNoDisponible("La integridad SHA-256 de la fotografía no coincide.")
            # Fully decode before passing bytes to the PDF renderer; no URL or image cache.
            with Image.open(io.BytesIO(raw)) as img:
                if img.format != _FORMATOS[mime] or img.width * img.height > 25_000_000:
                    raise EvidenciaNoDisponible("Formato o dimensiones de fotografía inválidos.")
                img.load()
            ext = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[_FORMATOS[mime]]
            result.append(FotoOperativaPrivada(f"Evidencia privada {i}.{ext}", bytes(raw)))
            progreso_pdf("Descargando evidencias privadas…", i, len(photos))
        return result
    except EvidenciaNoDisponible:
        raise
    except Exception:
        raise EvidenciaNoDisponible("No fue posible validar las fotografías privadas.") from None
