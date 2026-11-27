import json
import os
import re
import uuid
from urllib.parse import urlsplit

import requests

from core.app_paths import user_data_dir
from core.logger import configurar_logger

logger = configurar_logger(__name__)


def _carpeta(actor):
    ruta = user_data_dir() / 'audit_pending_v2' / str(int(actor))
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def _conservar(actor, evento):
    from security.data_encryption import cifrar_valor, esta_cifrado
    contenido = cifrar_valor(json.dumps({'actor': int(actor), **evento}, ensure_ascii=False, separators=(',', ':')))
    if not esta_cifrado(contenido):
        raise RuntimeError('Cola de auditoría sin cifrado')
    destino = _carpeta(actor) / (evento['evento_id'] + '.enc')
    temporal = destino.with_suffix('.tmp')
    with temporal.open('x', encoding='utf-8') as archivo:
        archivo.write(contenido)
        archivo.flush()
        os.fsync(archivo.fileno())
    os.replace(temporal, destino)
    return destino


def _enviar(actor, evento):
    from services.sesion_axia_compartida import obtener_sesion
    from supabase_config import SUPABASE_URL, SUPABASE_KEY
    token = obtener_sesion(actor)
    if not token:
        return 'PENDIENTE'
    base = str(SUPABASE_URL).rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        return 'PENDIENTE'
    try:
        respuesta = requests.post(f'{base}/functions/v1/desktop-audit-write', json=evento, headers={'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}, timeout=(3, 8), allow_redirects=False)
        body = respuesta.json()
    except (requests.RequestException, ValueError):
        return 'PENDIENTE'
    data = body.get('data') if isinstance(body, dict) else None
    if respuesta.status_code == 200 and isinstance(body, dict) and body.get('ok') is True and isinstance(data, dict) and data.get('evento_id') == evento['evento_id'] and type(data.get('id_movimiento')) is int and data['id_movimiento'] > 0 and type(data.get('recuperado')) is bool:
        return 'OK'
    logger.warning('Evento de auditoría no confirmado. UUID=%s HTTP=%s', evento['evento_id'], respuesta.status_code)
    return 'RECHAZADO' if respuesta.status_code in (400, 403, 409, 413) else 'PENDIENTE'


def _resolver(ruta, estado):
    if ruta is None:
        return
    try:
        if estado == 'OK':
            ruta.unlink(missing_ok=True)
        elif estado == 'RECHAZADO':
            destino = ruta.parent / 'rechazados'
            destino.mkdir(exist_ok=True)
            os.replace(ruta, destino / ruta.name)
    except OSError:
        logger.warning('No fue posible actualizar la cola local de auditoría.')


def reintentar_uno(actor, excluir=None):
    from security.data_encryption import descifrar_valor, esta_cifrado
    try:
        for ruta in sorted(_carpeta(actor).glob('*.enc'), key=lambda p: p.stat().st_mtime):
            if ruta == excluir:
                continue
            try:
                contenido = ruta.read_text(encoding='utf-8')
                if not esta_cifrado(contenido):
                    continue
                evento = json.loads(descifrar_valor(contenido))
                if evento.pop('actor', None) != int(actor) or evento.get('evento_id') != ruta.stem or str(uuid.UUID(ruta.stem)) != ruta.stem or set(evento) != {'evento_id','evento'}:
                    continue
            except Exception:
                logger.warning('Evento pendiente ilegible; se conserva para revisión.')
                continue
            estado = _enviar(actor, evento)
            _resolver(ruta, estado)
            return estado == 'OK'
    except Exception:
        logger.warning('No fue posible recuperar un evento de auditoría pendiente.')
    return False


def registrar_evento(actor, datos):
    try:
        actor = int(actor)
        if actor <= 0:
            return False
    except (ValueError, TypeError):
        return False
    limites = {'modulo': 160, 'accion': 64, 'descripcion': 2000, 'registro_afectado': 512, 'equipo': 160, 'ip_local': 160, 'latitud': 160, 'longitud': 160, 'ciudad': 160, 'region': 160, 'pais': 160}
    campos = {k: None if datos.get(k) is None else re.sub(r'[\x00-\x1f\x7f]', ' ', str(datos[k]))[:n] for k, n in limites.items()}
    evento = {'evento_id': str(uuid.uuid4()), 'evento': campos}
    ruta = None
    try:
        ruta = _conservar(actor, evento)
    except Exception:
        logger.warning('No fue posible conservar el evento cifrado localmente. UUID=%s', evento['evento_id'])
    try:
        estado = _enviar(actor, evento)
    except Exception:
        logger.warning('No se pudo enviar el evento de auditoría. UUID=%s', evento['evento_id'])
        estado = 'PENDIENTE'
    _resolver(ruta, estado)
    if estado == 'OK':
        reintentar_uno(actor, excluir=ruta)
    return estado == 'OK'
