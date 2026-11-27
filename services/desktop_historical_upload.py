from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID
from services.evidence_image_format import preparar_imagen, EXTENSIONS

import requests

BUCKET = 'bitacoras-evidencias'
MAX_BYTES = 10485760
MODULES = {'bitacoras': 'BIT', 'ordenes-servicio': 'OS', 'levantamientos': 'LEV', 'levantamientos-archivos': 'LEV'}


def carga_historica_activa():
    return os.getenv('AXIA_HISTORICAL_EVIDENCE_SECURE', '').strip() == '1'


def cargar_archivo_historico(modulo, folio, archivo, mime):
    from app_context import obtener_usuario_actual
    from services.sesion_axia_compartida import obtener_sesion
    from supabase_config import SUPABASE_URL, SUPABASE_KEY

    archivo = Path(archivo)
    if modulo not in MODULES or not re.fullmatch(MODULES[modulo] + r'-[0-9]{5,15}', folio):
        raise RuntimeError('Módulo o folio no habilitado para carga segura.')
    token = obtener_sesion(obtener_usuario_actual().get('id_usuario'))
    grant = os.getenv('AXIA_DESKTOP_EVIDENCE_GRANT', '').strip()
    if not token or not re.fullmatch(r'[a-f0-9]{64}', grant):
        raise RuntimeError('Inicia sesión con la autorización corporativa de evidencias.')
    base = str(SUPABASE_URL).rstrip('/')
    origin = urlsplit(base)
    if origin.scheme != 'https' or not origin.hostname or origin.username or origin.password or origin.path or origin.query or origin.fragment:
        raise RuntimeError('Configuración HTTPS de Supabase inválida.')
    if archivo.suffix.lower() in EXTENSIONS or modulo != 'levantamientos-archivos':
        raw, nombre, ext, mime = preparar_imagen(archivo)
    else:
        with archivo.open('rb') as fh:
            raw = fh.read(MAX_BYTES + 1)
        nombre, ext = archivo.name, archivo.suffix.lower().lstrip('.')
    if not 0 < len(raw) <= MAX_BYTES:
        raise RuntimeError('El archivo está vacío o supera 10 MiB.')
    digest = hashlib.sha256(raw).hexdigest()
    identity = hashlib.sha256(('\0'.join((modulo, folio, nombre, digest))).encode('utf-8')).digest()
    file_id = UUID(bytes=identity[:16], version=4)
    expected = f'{modulo}/{folio}/{file_id.hex}_archivo.{ext}'
    headers = {'Authorization': f'Bearer {token}', 'apikey': str(SUPABASE_KEY), 'X-AXIA-Desktop-Grant': grant, 'X-AXIA-Module': modulo, 'X-AXIA-Folio': folio, 'X-AXIA-File-Id': str(file_id), 'X-AXIA-Extension': ext, 'X-AXIA-SHA256': digest, 'Content-Type': mime}
    try:
        response = requests.post(base + '/functions/v1/desktop-historical-evidence-upload', headers=headers, data=raw, timeout=(6, 60), allow_redirects=False)
        if response.status_code not in (200, 201):
            try:
                failure = response.json()
            except (ValueError, AttributeError):
                failure = {}
            if not isinstance(failure, dict):
                failure = {}
            message = failure.get('error')
            detail = str(message)[:250] if isinstance(message, str) else 'No se confirmó la carga.'
            request_id = str(failure.get('requestId') or '')
            if not re.fullmatch(r'[0-9a-fA-F-]{36}', request_id):
                request_id = ''
            raise RuntimeError(f'Carga segura rechazada (HTTP {response.status_code}). {detail}' + (f' Solicitud: {request_id}' if request_id else ''))
        data = response.json()
        if data.get('ok') is not True or data.get('bucket') != BUCKET or data.get('storagePath') != expected or data.get('mime') != mime or data.get('sha256') != digest or data.get('sizeBytes') != len(raw) or type(data.get('alreadyUploaded')) is not bool:
            raise RuntimeError('No se confirmó la integridad de la carga segura.')
    except requests.RequestException:
        raise RuntimeError('No se pudo confirmar la carga segura. Reintenta con el mismo archivo.') from None
    return {'nombre': nombre, 'storage_path': expected, 'bucket': BUCKET, 'url': '', 'mime': mime, 'sha256': digest, 'size_bytes': len(raw)}
