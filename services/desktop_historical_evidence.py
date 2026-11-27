from __future__ import annotations

import io
import json
import os
import re
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

import requests
from PIL import Image
from services.desktop_evidence_access import EvidenciaNoDisponible
from services.desktop_operational_evidence import FotoOperativaPrivada

BUCKET = 'bitacoras-evidencias'
_PATH = re.compile(r'(bitacoras/BIT|ordenes-servicio/OS)-[0-9]{5,}/[0-9a-f]{32}_[A-Za-z0-9_.-]+\.(?:jpg|jpeg|png|webp)', re.I)
_MAX = 30 * 1024 * 1024


def consulta_historica_activa():
    return os.getenv('AXIA_HISTORICAL_EVIDENCE_SECURE', '').strip() == '1'


def _ruta_valida(path, folio):
    if not isinstance(path, str) or not _PATH.fullmatch(path) or path.split('/')[1] != folio:
        raise EvidenciaNoDisponible('La ruta histórica no corresponde al documento.')
    return path


def ruta_historica(item, folio, base):
    origin = urlsplit(base)
    if isinstance(item, dict):
        bucket = str(item.get('bucket') or '').strip()
        path = str(item.get('storage_path') or item.get('storagePath') or '').strip()
        values = [item.get(k) for k in ('url', 'public_url', 'publicUrl', 'ruta', 'path')]
    else:
        bucket, path, values = '', '', [item]
    candidates = []
    if bucket == BUCKET or path.startswith(('bitacoras/', 'ordenes-servicio/')):
        candidates.append(_ruta_valida(path, folio))
    for value in values:
        if not isinstance(value, str):
            continue
        value = value.strip()
        if value.lower().startswith('url:'):
            value = value[4:].strip()
        if value.startswith(('bitacoras/', 'ordenes-servicio/')):
            candidates.append(_ruta_valida(value, folio))
            continue
        if not value.lower().startswith(('https://', 'http://')):
            continue
        u = urlsplit(value)
        decoded = unquote(u.path)
        match = re.fullmatch(r'/storage/v1/object/(?:public|sign|authenticated)/bitacoras-evidencias/(.+)', decoded)
        if not match:
            if BUCKET in decoded:
                raise EvidenciaNoDisponible('Referencia histórica inválida.')
            continue
        if (u.scheme, u.netloc) != (origin.scheme, origin.netloc) or u.fragment:
            raise EvidenciaNoDisponible('Origen de evidencia histórica no autorizado.')
        candidates.append(_ruta_valida(match.group(1), folio))
    if not candidates:
        return None
    if (bucket and bucket != BUCKET) or (path and path != candidates[0]) or any(p != candidates[0] for p in candidates):
        raise EvidenciaNoDisponible('Referencias históricas inconsistentes.')
    return candidates[0]


def descargar_foto_historica(path, folio):
    from app_context import obtener_usuario_actual
    from services.sesion_axia_compartida import obtener_sesion
    from supabase_config import SUPABASE_URL, SUPABASE_KEY

    path = _ruta_valida(path, folio)
    token = obtener_sesion(obtener_usuario_actual().get('id_usuario'))
    grant = os.getenv('AXIA_DESKTOP_EVIDENCE_GRANT', '').strip()
    if not token or not re.fullmatch(r'[a-f0-9]{64}', grant):
        raise EvidenciaNoDisponible('Inicia sesión con la autorización corporativa de evidencias.')
    base = str(SUPABASE_URL).rstrip('/')
    origin = urlsplit(base)
    if origin.scheme != 'https' or not origin.hostname or origin.username or origin.password or origin.path or origin.query or origin.fragment:
        raise EvidenciaNoDisponible('Configuración HTTPS de Supabase inválida.')
    headers = {'Authorization': f'Bearer {token}', 'apikey': str(SUPABASE_KEY), 'X-AXIA-Desktop-Grant': grant, 'Content-Type': 'application/json'}
    try:
        response = requests.post(base + '/functions/v1/desktop-historical-evidence-access', headers=headers, json={'bucket': BUCKET, 'storagePath': path}, timeout=(6, 20), allow_redirects=False)
        if response.status_code != 200:
            raise EvidenciaNoDisponible(f'Consulta histórica no autorizada o no disponible (HTTP {response.status_code}).')
        data = response.json()
        signed = data.get('signedUrl')
        if data.get('ok') is not True or data.get('bucket') != BUCKET or data.get('storagePath') != path or data.get('expiresIn') != 120 or not isinstance(signed, str):
            raise EvidenciaNoDisponible('Respuesta de evidencia histórica inválida.')
        u = urlsplit(signed)
        if (u.scheme, u.netloc) != (origin.scheme, origin.netloc) or unquote(u.path) != f'/storage/v1/object/sign/{BUCKET}/{path}' or not u.query or u.fragment:
            raise EvidenciaNoDisponible('Dirección firmada de evidencia histórica inválida.')
        raw = bytearray()
        with requests.get(signed, timeout=(6, 25), stream=True, allow_redirects=False) as download:
            if download.status_code != 200:
                raise EvidenciaNoDisponible('No fue posible descargar la evidencia histórica.')
            for chunk in download.iter_content(65536):
                raw.extend(chunk)
                if len(raw) > _MAX:
                    raise EvidenciaNoDisponible('La evidencia excede el límite de descarga.')
        if not raw:
            raise EvidenciaNoDisponible('La evidencia está vacía.')
        with Image.open(io.BytesIO(raw)) as img:
            if img.format not in {'JPEG', 'PNG', 'WEBP'} or img.width * img.height > 25_000_000:
                raise EvidenciaNoDisponible('Formato o dimensiones de evidencia inválidos.')
            img.load()
        return bytes(raw)
    except EvidenciaNoDisponible:
        raise
    except Exception:
        raise EvidenciaNoDisponible('No fue posible validar la evidencia histórica.') from None


def preparar_fotos_historicas(datos, folio):
    from supabase_config import SUPABASE_URL

    raw = datos.get('Evidencia Fotográfica') or datos.get('Evidencias Fotográficas') or datos.get('Fotos') or []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = [raw]
    if isinstance(raw, (str, dict)):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        raise EvidenciaNoDisponible('Lista de evidencias inválida.')
    result = []
    cache = {}
    for item in raw:
        path = ruta_historica(item, folio, str(SUPABASE_URL).rstrip('/'))
        if path is None:
            result.append(item)
            continue
        if path not in cache:
            cache[path] = descargar_foto_historica(path, folio)
        name = str(item.get('nombre') or PurePosixPath(path).name) if isinstance(item, dict) else PurePosixPath(path).name
        result.append(FotoOperativaPrivada(name, cache[path]))
    return {**datos, 'Evidencia Fotográfica': result}
