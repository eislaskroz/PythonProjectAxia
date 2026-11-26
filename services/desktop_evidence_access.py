from __future__ import annotations

import os
import re
from urllib.parse import urlsplit

import requests


class EvidenciaNoDisponible(RuntimeError):
    pass


def descargar_evidencia_field(storage_path: str) -> bytes:
    from app_context import obtener_usuario_actual
    from services.sesion_axia_compartida import obtener_sesion
    from supabase_config import SUPABASE_URL, SUPABASE_KEY

    if not re.fullmatch(r"LEV-\d{5,}/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp|pdf)", storage_path, re.I):
        raise EvidenciaNoDisponible("Ruta de evidencia inválida.")
    usuario = obtener_usuario_actual()
    token = obtener_sesion(usuario.get("id_usuario"))
    if not token:
        raise EvidenciaNoDisponible("Inicia sesión nuevamente en AXIA DESKTOP para recuperar las evidencias.")
    base = str(SUPABASE_URL).rstrip("/")
    origin = urlsplit(base)
    if origin.scheme != "https" or not origin.hostname:
        raise EvidenciaNoDisponible("Configuración HTTPS de Supabase inválida.")
    headers = {"Authorization": f"Bearer {token}", "apikey": str(SUPABASE_KEY), "Content-Type": "application/json"}
    grant = os.getenv("AXIA_DESKTOP_EVIDENCE_GRANT", "").strip()
    if grant:
        if not re.fullmatch(r"[a-f0-9]{64}", grant):
            raise EvidenciaNoDisponible("Autorización corporativa de evidencias inválida.")
        headers["X-AXIA-Desktop-Grant"] = grant
    try:
        response = requests.post(base + "/functions/v1/desktop-evidence-access", headers=headers,
            json={"bucket": "levantamientos-evidencias", "storagePath": storage_path}, timeout=(6, 15), allow_redirects=False)
        if response.status_code == 401:
            raise EvidenciaNoDisponible("Sesión vencida. Inicia sesión nuevamente.")
        if response.status_code in (403, 404):
            raise EvidenciaNoDisponible("Evidencia no disponible o sin autorización corporativa.")
        if response.status_code != 200:
            raise EvidenciaNoDisponible(f"El servicio de evidencias respondió HTTP {response.status_code}.")
        data = response.json()
        signed = data.get("signedUrl") if data.get("ok") is True else None
        if not isinstance(signed, str):
            raise EvidenciaNoDisponible("El servicio no devolvió una evidencia autorizada.")
        parsed = urlsplit(signed)
        if (parsed.scheme, parsed.netloc) != (origin.scheme, origin.netloc) or not parsed.path.startswith("/storage/v1/object/sign/levantamientos-evidencias/"):
            raise EvidenciaNoDisponible("El servicio devolvió una dirección de evidencia inválida.")
        with requests.get(signed, timeout=(6, 25), allow_redirects=False, stream=True) as file_response:
            if file_response.status_code != 200:
                raise EvidenciaNoDisponible("No fue posible descargar la evidencia autorizada.")
            chunks = bytearray()
            for chunk in file_response.iter_content(65536):
                chunks.extend(chunk)
                if len(chunks) > 30 * 1024 * 1024:
                    raise EvidenciaNoDisponible("La evidencia excede el límite de descarga de 30 MiB.")
        if not chunks:
            raise EvidenciaNoDisponible("La evidencia está vacía.")
        return bytes(chunks)
    except EvidenciaNoDisponible:
        raise
    except (requests.RequestException, ValueError, AttributeError, TypeError):
        raise EvidenciaNoDisponible("No fue posible conectar con el servicio seguro de evidencias.") from None
