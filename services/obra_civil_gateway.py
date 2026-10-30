"""Pasarela de Obra Civil con sesión de empleado verificada por Edge Function.

Nunca se envía una service_role key desde DESKTOP. Todos los reintentos
conservan el obc_request_id del borrador original.
"""
from __future__ import annotations

import uuid
import requests

from supabase_config import SUPABASE_URL, SUPABASE_KEY
from services.levantamiento_catalogo_axia import obtener_token_sesion_catalogo

ENDPOINT = SUPABASE_URL.rstrip('/') + '/functions/v1/axia-obras-civiles'


class SesionObraCivilInvalida(PermissionError):
    """Se necesita renovar la sesión del empleado antes de guardar."""


def peticion_obra_civil(accion: str, solicitud: str, *, usuario_id: object, datos: dict | None = None):
    """Consultar o guardar; no se permite ninguna acción que modifique obras existentes."""
    if accion not in ('consultar', 'guardar'):
        raise ValueError('Acción de Obra Civil no autorizada.')
    token = obtener_token_sesion_catalogo(usuario_id)
    if not token:
        raise SesionObraCivilInvalida('La sesión segura de AXIA no está disponible. Inicia sesión nuevamente.')
    solicitud = str(uuid.UUID(str(solicitud)))
    payload = {'accion': accion, 'solicitud': solicitud}
    if accion == 'guardar':
        payload['datos'] = dict(datos or {})
    try:
        respuesta = requests.post(
            ENDPOINT,
            headers={'apikey': SUPABASE_KEY, 'Content-Type': 'application/json',
                     'X-Axia-Almacen-Session': token},
            json=payload,
            timeout=(10, 65),
        )
        result = respuesta.json()
    except (requests.RequestException, ValueError) as exc:
        raise ConnectionError('No se pudo confirmar el resultado con Supabase. Conserva el borrador.') from exc
    if respuesta.status_code in (401, 403):
        raise SesionObraCivilInvalida(str(result.get('error') or 'La sesión debe renovarse.'))
    if respuesta.status_code >= 400 or not result.get('ok'):
        raise RuntimeError(str(result.get('error') or 'Supabase rechazó el registro de Obra Civil.'))
    data = result.get('resultado')
    if data is not None and (not isinstance(data, dict) or
        not data.get('obc_folio') or not data.get('obc_id') or
        str(data.get('obc_request_id') or '') != solicitud):
        raise RuntimeError('La respuesta de Supabase no contiene un folio confirmado para esta solicitud.')
    return data


def gestionar_obra_civil(accion: str, *, usuario_id: object, folio: str = '',
                        busqueda: str = '', cambios: dict | None = None,
                        solicitud: str = ''):
    """Listado, modificación y validación de OBC por servidor, sin RLS público.

    La identidad y el permiso de cada acción se verifican nuevamente en Edge.
    Nunca se incluye una service_role key en DESKTOP.
    """
    if accion not in ('listar', 'detalle', 'actualizar', 'validar'):
        raise ValueError('Operación administrativa de Obra Civil desconocida.')
    token = obtener_token_sesion_catalogo(usuario_id)
    if not token:
        raise SesionObraCivilInvalida(
            'La sesión segura AXIA no está disponible. Cierra sesión e ingresa nuevamente.')
    payload = {'accion': accion}
    if accion == 'listar':
        payload['busqueda'] = str(busqueda or '').strip()[:120]
    else:
        payload['folio'] = str(folio or '').strip().upper()
        if not payload['folio'].startswith('OBC-'):
            raise ValueError('Selecciona un folio OBC válido.')
    if accion == 'actualizar':
        payload['cambios'] = dict(cambios or {})
        payload['solicitud'] = str(uuid.UUID(solicitud)) if solicitud else str(uuid.uuid4())
    try:
        respuesta = requests.post(
            ENDPOINT,
            headers={'apikey': SUPABASE_KEY, 'Content-Type': 'application/json',
                     'X-Axia-Almacen-Session': token},
            json=payload, timeout=(10, 65),
        )
        resultado = respuesta.json()
    except (requests.RequestException, ValueError) as exc:
        raise ConnectionError('No fue posible consultar Obra Civil. No se realizó otro guardado.') from exc
    if respuesta.status_code in (401, 403):
        raise SesionObraCivilInvalida(str(resultado.get('error') or 'Acceso no autorizado.'))
    if respuesta.status_code >= 400 or not resultado.get('ok'):
        raise RuntimeError(str(resultado.get('error') or 'Operación no confirmada en Supabase.'))
    return resultado.get('resultado')
