from __future__ import annotations

import io
import json
import os
import re
from pathlib import PurePosixPath
from collections.abc import Mapping
from urllib.parse import unquote, urlsplit

from ui.pdf_progress import progreso_pdf

import requests
from PIL import Image
from services.desktop_evidence_access import EvidenciaNoDisponible
from services.desktop_operational_evidence import FotoOperativaPrivada

BUCKET = 'bitacoras-evidencias'
_PREFIXES = ('bitacoras/', 'ordenes-servicio/', 'levantamientos/', 'levantamientos-archivos/', 'obras-civiles/', 'obras-civiles-archivos/')
_PATH = re.compile(r'(bitacoras/BIT|ordenes-servicio/OS|levantamientos(?:-archivos)?/LEV|obras-civiles(?:-archivos)?/OBC)-[0-9]{4,}/[0-9a-f]{32}_[A-Za-z0-9_.-]+\.(?:jpg|jpeg|png|webp|pdf|dwg|dxf)', re.I)
_MAX = 30 * 1024 * 1024


def consulta_historica_activa():
    return os.getenv('AXIA_HISTORICAL_EVIDENCE_SECURE', '').strip() == '1'


def _ruta_valida(path, folio):
    if isinstance(path, str) and isinstance(folio, str) and re.fullmatch(r'OBC-[0-9]{4,}', folio):
        uuid = r'[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
        patron = rf'obras-civiles(?:-archivos)?/(?:OBC-[0-9]{{4,}}|(?:SOLICITUD|EDICION)-{uuid})/(?:[0-9a-f]{{32}}|{uuid})_[A-Za-z0-9_.-]+\.(?:jpg|jpeg|png|webp|pdf|dwg|dxf)'
        if re.fullmatch(patron, path, re.I):
            carpeta = path.split('/')[1]
            if carpeta.startswith(('SOLICITUD-', 'EDICION-')) or carpeta == folio:
                return path
    if not isinstance(path, str) or not _PATH.fullmatch(path) or path.split('/')[1] != folio or (not folio.startswith('OBC-') and len(folio.split('-')[-1]) < 5):
        raise EvidenciaNoDisponible('La ruta histórica no corresponde al documento.')
    return path


def ruta_historica(item, folio, base):
    origin = urlsplit(base)
    if isinstance(item, Mapping):
        bucket = str(item.get('bucket') or '').strip()
        path = str(item.get('storage_path') or item.get('storagePath') or '').strip()
        values = [item.get(k) for k in ('url', 'public_url', 'publicUrl', 'ruta', 'path')]
    else:
        bucket, path, values = '', '', [item]
    candidates = []
    if path and (bucket == BUCKET or path.startswith(_PREFIXES)):
        candidates.append(_ruta_valida(path, folio))
    for value in values:
        if not isinstance(value, str):
            continue
        value = value.strip()
        if value.lower().startswith('url:'):
            value = value[4:].strip()
        if value.startswith(_PREFIXES):
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
        if bucket == BUCKET:
            raise EvidenciaNoDisponible("Referencia histórica sin ruta válida.")
        return None
    if (bucket and bucket != BUCKET) or (path and path != candidates[0]) or any(p != candidates[0] for p in candidates):
        raise EvidenciaNoDisponible('Referencias históricas inconsistentes.')
    return candidates[0]


def descargar_archivo_historico(path, folio):
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
        response = requests.post(base + '/functions/v1/desktop-historical-evidence-access', headers=headers, json={'bucket': BUCKET, 'storagePath': path, **({'folio': folio} if folio.startswith('OBC-') else {})}, timeout=(6, 20), allow_redirects=False)
        if response.status_code != 200:
            referencia = ''
            try:
                request_id = str(response.json().get('requestId') or '')
                if re.fullmatch(r'[a-f0-9-]{36}', request_id, re.I):
                    referencia = f'\nSolicitud: {request_id}'
            except (AttributeError, ValueError, TypeError):
                pass
            mensajes = {401: 'Sesión inválida o vencida. Inicia sesión nuevamente.',
                        403: 'Tu perfil o autorización corporativa no permite consultar esta evidencia.',
                        404: 'La evidencia no está disponible o no pertenece al documento.'}
            motivo = mensajes.get(response.status_code, 'No se pudo consultar la evidencia histórica.')
            raise EvidenciaNoDisponible(f'{motivo} (HTTP {response.status_code}).{referencia}')
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
        extension = PurePosixPath(path).suffix.lower()
        if extension == '.pdf':
            from pypdf import PdfReader
            if not raw.startswith(b'%PDF-') or not len(PdfReader(io.BytesIO(raw)).pages):
                raise EvidenciaNoDisponible('PDF adjunto inválido o vacío.')
        elif extension == '.dwg':
            if not re.match(rb'AC10[0-9]{2}', raw):
                raise EvidenciaNoDisponible('Archivo DWG inválido.')
        elif extension == '.dxf':
            if not (raw.startswith(b'AutoCAD Binary DXF') or re.match(rb'\s*0\s*SECTION\b', raw, re.I)):
                raise EvidenciaNoDisponible('Archivo DXF inválido.')
        else:
            with Image.open(io.BytesIO(raw)) as img:
                expected = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.webp': 'WEBP'}
                if img.format != expected.get(extension) or img.width * img.height > 25_000_000:
                    raise EvidenciaNoDisponible('Formato o dimensiones de evidencia inválidos.')
                img.load()
        return bytes(raw)
    except EvidenciaNoDisponible:
        raise
    except Exception:
        raise EvidenciaNoDisponible('No fue posible validar la evidencia histórica.') from None


def descargar_foto_historica(path, folio):
    if PurePosixPath(path).suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
        raise EvidenciaNoDisponible('La evidencia no es una fotografía.')
    return descargar_archivo_historico(path, folio)


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
    progreso_pdf("Verificando evidencias fotográficas…", 0, len(raw))
    for i, item in enumerate(raw, 1):
        path = ruta_historica(item, folio, str(SUPABASE_URL).rstrip('/'))
        if path is None:
            result.append(item)
            progreso_pdf("Verificando evidencias fotográficas…", i, len(raw))
            continue
        if path not in cache:
            cache[path] = descargar_foto_historica(path, folio)
        name = str(item.get('nombre') or PurePosixPath(path).name) if isinstance(item, Mapping) else PurePosixPath(path).name
        result.append(FotoOperativaPrivada(name, cache[path]))
        progreso_pdf("Verificando evidencias fotográficas…", i, len(raw))
    return {**datos, 'Evidencia Fotográfica': result}


def preparar_evidencias_obra_civil(items, folio, *, archivos=False):
    from supabase_config import SUPABASE_URL

    if isinstance(items, str):
        try:
            items = json.loads(items)
        except ValueError:
            items = [items]
    if isinstance(items, Mapping):
        items = [items]
    if not isinstance(items, (list, tuple)):
        raise EvidenciaNoDisponible('Lista de evidencias de Obra Civil inválida.')
    resultado = []
    cache = {}
    etapa = "Verificando archivos adjuntos…" if archivos else "Verificando evidencias fotográficas…"
    progreso_pdf(etapa, 0, len(items))
    for i, item in enumerate(items, 1):
        if isinstance(item, FotoOperativaPrivada):
            resultado.append(item)
            progreso_pdf(etapa, i, len(items))
            continue
        path = ruta_historica(item, folio, str(SUPABASE_URL).rstrip('/'))
        if path is None:
            if isinstance(item, Mapping) and item.get('storage_path'):
                raise EvidenciaNoDisponible('Referencia de Obra Civil no autorizada.')
            resultado.append(item)
            progreso_pdf(etapa, i, len(items))
            continue
        if path not in cache:
            cache[path] = descargar_archivo_historico(path, folio) if archivos else descargar_foto_historica(path, folio)
        if archivos:
            resultado.append(item)
        else:
            name = str(item.get('nombre') or PurePosixPath(path).name) if isinstance(item, Mapping) else PurePosixPath(path).name
            resultado.append(FotoOperativaPrivada(name, cache[path]))
        progreso_pdf(etapa, i, len(items))
    return resultado
