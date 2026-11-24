from __future__ import annotations

import requests

from app_context import obtener_usuario_actual
from security.permissions import obtener_tipo_usuario
from services.levantamiento_catalogo_axia import obtener_token_sesion_catalogo
from supabase_config import SUPABASE_URL, SUPABASE_KEY

RUTA = SUPABASE_URL.rstrip('/') + '/functions/v1/axia-edicion-levantamientos'


def ejecutar(accion: str, **datos):
    usuario = obtener_usuario_actual()
    identificador = usuario.get('id_usuario')
    token = obtener_token_sesion_catalogo(identificador)
    if not identificador or not token:
        raise PermissionError('No hay una sesión AXIA verificada. Cierra sesión y vuelve a entrar.')
    try:
        respuesta = requests.post(
            RUTA,
            json={'accion': accion, **datos},
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': 'Bearer ' + SUPABASE_KEY,
                'X-Axia-Almacen-Session': token,
                'Content-Type': 'application/json',
            },
            timeout=35,
        )
        cuerpo = respuesta.json()
    except (requests.RequestException, ValueError) as error:
        raise RuntimeError('No fue posible verificar la autorización con Supabase. La edición permanece bloqueada.') from error
    if respuesta.status_code >= 400 or not isinstance(cuerpo, dict) or not cuerpo.get('ok'):
        motivo = cuerpo.get('error') if isinstance(cuerpo, dict) else None
        raise PermissionError(str(motivo or 'El servidor no autorizó esta operación.'))
    return cuerpo.get('resultado')


def solicitar(registro, motivo):
    if obtener_tipo_usuario(obtener_usuario_actual()) != 6:
        raise PermissionError('Solo ESI puede solicitar esta autorización.')
    motivo = str(motivo or '').strip()
    if len(motivo) < 12 or len(motivo) > 1000:
        raise ValueError('Describe el motivo de la edición (12 a 1000 caracteres).')
    return ejecutar('solicitar', id_levantamiento=registro['id_levantamiento'], motivo=motivo)


def listar_pendientes():
    if obtener_tipo_usuario(obtener_usuario_actual()) not in (1, 2, 3):
        raise PermissionError('Solo los usuarios autorizadores pueden consultar solicitudes.')
    return ejecutar('listar_pendientes')


def resolver(solicitud_id, aprobar, comentario):
    if obtener_tipo_usuario(obtener_usuario_actual()) not in (1, 2, 3):
        raise PermissionError('No tienes permiso para resolver solicitudes.')
    return ejecutar('resolver', solicitud_id=solicitud_id, aprobar=bool(aprobar), comentario=str(comentario or '').strip())


def permiso_vigente(registro):
    if obtener_tipo_usuario(obtener_usuario_actual()) != 6:
        raise PermissionError('Esta operación solo aplica al rol ESI.')
    return ejecutar('permiso_vigente', id_levantamiento=registro['id_levantamiento'])


def guardar_revision(registro, datos, solicitud_id):
    if obtener_tipo_usuario(obtener_usuario_actual()) != 6:
        raise PermissionError('Esta operación solo aplica al rol ESI.')
    if not solicitud_id:
        raise PermissionError('La solicitud autorizada es obligatoria.')
    return ejecutar('guardar_revision', id_levantamiento=registro['id_levantamiento'], solicitud_id=solicitud_id, datos=datos)
