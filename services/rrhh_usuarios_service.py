"""Acceso de RRHH a expedientes mediante una Edge Function con control de rol 10.

La UI nunca envía una clave service_role ni puede administrar cuentas desde esta API.
"""
from __future__ import annotations

import requests

from app_context import obtener_usuario_actual
from security.permissions import puede_editar_expedientes_rrhh
from security.data_encryption import cifrar_diccionario, descifrar_diccionario
from supabase_config import SUPABASE_URL, SUPABASE_KEY
from services.usuarios_service import UsuarioServiceError

CAMPOS_RRHH = frozenset((
    'usu_nombre', 'usu_apellido', 'usu_rfc', 'usu_curp', 'usu_imss', 'usu_ine',
    'usu_fechanac', 'usu_telefono', 'usu_correo', 'usu_depto', 'usu_puesto',
    'usu_calle', 'usu_numero', 'usu_colonia', 'usu_municipio', 'usu_estado',
    'usu_cp', 'usu_regimen',
))
CAMPOS_CIFRADOS_RRHH = frozenset((
    'usu_rfc', 'usu_curp', 'usu_imss', 'usu_ine', 'usu_fechanac',
    'usu_telefono', 'usu_calle', 'usu_numero', 'usu_colonia',
    'usu_municipio', 'usu_estado', 'usu_cp', 'usu_regimen',
))


def _ejecutar(accion: str, contrasena: str, **argumentos) -> dict:
    actor = obtener_usuario_actual()
    if not puede_editar_expedientes_rrhh(actor):
        raise UsuarioServiceError('Acceso reservado a Recursos Humanos (rol 10).')
    if not contrasena:
        raise UsuarioServiceError('Confirma tu contraseña para acceder a expedientes.')
    if not str(SUPABASE_URL).lower().startswith('https://'):
        raise UsuarioServiceError('La consulta de expedientes exige HTTPS.')
    payload = {
        'accion': accion, 'usuario': actor.get('usuario'),
        'actor_id': actor.get('id_usuario'), 'contrasena': contrasena,
        **argumentos,
    }
    try:
        resultado = requests.post(
            SUPABASE_URL.rstrip('/') + '/functions/v1/axia-rrhh-usuarios',
            headers={'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}',
                     'content-type': 'application/json'},
            json=payload, timeout=(8, 35), allow_redirects=False,
        )
        respuesta = resultado.json()
    except (requests.RequestException, ValueError) as exc:
        raise UsuarioServiceError('No se pudo conectar con el servicio de Recursos Humanos.') from exc
    if not resultado.ok or not isinstance(respuesta, dict) or respuesta.get('error'):
        mensaje = respuesta.get('error', '') if isinstance(respuesta, dict) else ''
        raise UsuarioServiceError(str(mensaje)[:300] or 'La solicitud de RRHH fue rechazada.')
    return respuesta


def buscar_usuarios_rrhh(termino: str, contrasena: str) -> list[dict]:
    datos = _ejecutar('listar', contrasena, buscar=str(termino).strip())
    resultado = []
    for bruto in datos.get('registros', []):
        if not isinstance(bruto, dict):
            continue
        # Se conserva el valor original cifrado SOLO para la comparación optimista.
        descifrado = descifrar_diccionario(bruto, CAMPOS_CIFRADOS_RRHH)
        descifrado['_axia_original_cifrado'] = {k: bruto.get(k) for k in CAMPOS_RRHH}
        resultado.append(descifrado)
    return resultado


def actualizar_usuario_rrhh(id_usuario, datos: dict, seleccionado: dict,
                            contrasena: str, motivo: str):
    """Envía únicamente campos modificados, nunca rol, nickname ni password."""
    try:
        if not isinstance(seleccionado, dict) or not seleccionado.get('id_usuario'):
            return False, 'Selecciona un empleado existente.', None
        if str(id_usuario) != str(seleccionado['id_usuario']):
            return False, 'El empleado seleccionado cambió; vuelve a buscarlo.', None
        if len(str(motivo or '').strip()) < 8:
            return False, 'Describe el motivo del cambio (mínimo 8 caracteres).', None
        originales = seleccionado.get('_axia_original_cifrado')
        if not isinstance(originales, dict):
            return False, 'Vuelve a consultar al empleado antes de actualizar.', None
        cambios = {}
        for campo in CAMPOS_RRHH:
            valor = str(datos.get(campo) or '').strip()
            previo = str(seleccionado.get(campo) or '').strip()
            if valor != previo:
                if campo in {'usu_rfc', 'usu_curp', 'usu_imss', 'usu_ine'}:
                    valor = valor.upper()
                if campo == 'usu_correo':
                    valor = valor.lower()
                cambios[campo] = valor if valor else None
        if not cambios:
            return False, 'No hay datos modificados para guardar.', None
        if 'usu_correo' in cambios and cambios['usu_correo']:
            correo = cambios['usu_correo']
            if '@' not in correo or '.' not in correo.rsplit('@', 1)[-1]:
                return False, 'El correo corporativo no tiene un formato válido.', None
        cambios_cifrados = cifrar_diccionario(cambios, CAMPOS_CIFRADOS_RRHH)
        antes = {campo: originales.get(campo) for campo in cambios}
        resultado = _ejecutar('actualizar', contrasena, id_usuario=id_usuario,
                             cambios=cambios_cifrados, antes=antes, motivo=motivo)
        return True, 'Datos del expediente actualizados y auditados.', resultado.get('resultado')
    except UsuarioServiceError as error:
        return False, str(error), None
    except Exception:
        return False, 'No se completó la actualización de RRHH. No se confirmó el cambio.', None
