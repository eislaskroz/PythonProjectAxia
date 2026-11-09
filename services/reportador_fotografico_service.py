"""Módulo nativo del Reportador Fotográfico de AXIA DESKTOP.

Las operaciones con información privada se realizan exclusivamente por Edge
Function, mediante una sesión efímera emitida durante el login de AXIA.
El proyecto Windows no almacena contraseñas ni incluye service_role.
"""
from __future__ import annotations

import base64
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import requests
from PIL import Image, ImageOps

from app_context import obtener_usuario_actual
from security.permissions import obtener_tipo_usuario

PERMITIDOS = frozenset({1, 2, 3, 4})
MAX_ACTIVIDADES = 50
_TOKEN: str | None = None
_USUARIO_ID: str | None = None


class ErrorReportador(RuntimeError):
    pass


def permite_reportador(usuario=None) -> bool:
    return obtener_tipo_usuario(usuario or obtener_usuario_actual()) in PERMITIDOS


def _api(payload: dict, *, token: str | None = None, timeout: int = 45) -> dict:
    from supabase_config import SUPABASE_KEY, SUPABASE_URL
    url = f"{SUPABASE_URL.rstrip('/')}/functions/v1/axia-reportador-desktop"
    if not url.startswith('https://'):
        raise ErrorReportador('Reportador requiere comunicación HTTPS')
    headers = {"apikey": SUPABASE_KEY,
               "Authorization": f"Bearer {SUPABASE_KEY}",
               "content-type": "application/json"}
    try:
        response = requests.post(url, json={**payload, **({'token': token} if token else {})},
                                 headers=headers, timeout=(8, timeout), allow_redirects=False)
    except requests.RequestException as exc:
        raise ErrorReportador('Sin comunicación con el Reportador en Supabase') from exc
    try:
        data = response.json()
    except ValueError as exc:
        raise ErrorReportador('Respuesta no válida. Verifica el despliegue de axia-reportador-desktop.') from exc
    if response.status_code >= 400 or not isinstance(data, dict) or data.get('error'):
        mensaje = data.get('error', 'Operación rechazada') if isinstance(data, dict) else 'Error del servidor'
        if response.status_code in (404, 503):
            mensaje += ' Revisa la migración SQL y la Edge Function del Reportador.'
        raise ErrorReportador(str(mensaje)[:450])
    return data


def solicitar_sesion(usuario: str, contrasena: str, id_usuario: object, rol: object) -> str | None:
    """Se llama UNA vez desde el login normal de AXIA, nunca solicita otro login."""
    if int(rol or 0) not in PERMITIDOS:
        return None
    result = _api({'accion': 'iniciar_sesion', 'usuario': usuario, 'contrasena': contrasena}, timeout=12)
    return str(result['token'])


def establecer_sesion(token: str | None, id_usuario: object) -> None:
    global _TOKEN, _USUARIO_ID
    _TOKEN = token if token and len(token) == 64 else None
    _USUARIO_ID = str(id_usuario) if _TOKEN else None


def cerrar_sesion() -> None:
    establecer_sesion(None, None)


def _accion(accion: str, **datos) -> dict:
    usuario = obtener_usuario_actual()
    if not permite_reportador(usuario):
        raise PermissionError('Reportador disponible únicamente para roles 1, 2, 3 y 4.')
    if not _TOKEN or _USUARIO_ID != str(usuario.get('id_usuario')):
        raise ErrorReportador('El Reportador no tiene una sesión activa. Publica su Edge Function y vuelve a iniciar sesión en AXIA.')
    return _api({'accion': accion, **datos}, token=_TOKEN)


def consultar_acos(buscar: str = '') -> list[dict]:
    """Lista ACOs del catálogo operativo mediante la sesión del Reportador.

    La Edge Function consulta db_acos y las sucursales vinculadas; no expone
    estas tablas directamente desde la app ni requiere otro inicio de sesión.
    """
    return _accion('acos', buscar=buscar[:100]).get('acos', [])


def consultar_aco(numero: str) -> dict:
    """Obtiene los datos actualizados del ACO y sus órdenes vinculadas."""
    return _accion('aco_detalle', numero=numero[:60]).get('aco', {})


def fecha_para_mostrar(valor: object) -> str:
    """El formulario presenta DD-MM-AAAA; Supabase conserva ISO AAAA-MM-DD."""
    texto = str(valor or '').strip()
    if not texto:
        return ''
    try:
        return date.fromisoformat(texto[:10]).strftime('%d-%m-%Y')
    except ValueError:
        return texto


def fecha_para_guardar(valor: object) -> str:
    texto = str(valor or '').strip()
    try:
        return datetime.strptime(texto, '%d-%m-%Y').date().isoformat()
    except ValueError as exc:
        raise ErrorReportador('La fecha debe ser válida en formato DD-MM-AAAA.') from exc


def listar_reportes(buscar: str = '') -> list[dict]:
    return _accion('listar', buscar=buscar[:100]).get('reportes', [])


def obtener_reporte(id_reporte: int) -> dict:
    return _accion('obtener', id=int(id_reporte))


def guardar_reporte(id_reporte: int | None, datos: dict) -> int:
    return int(_accion('guardar', id=id_reporte, datos=datos)['id'])


def definir_cantidad_os(id_reporte: int, cantidad: int) -> None:
    _accion('ordenes_cantidad', id=id_reporte, cantidad=cantidad)


def cambiar_estado(id_reporte: int, accion: str) -> str:
    return str(_accion('estado', id=id_reporte, nuevo=accion)['estado'])


def guardar_autoguardado(clave: str, id_reporte: int | None, datos: dict) -> None:
    _accion('autoguardar', clave=clave, id=id_reporte, datos=datos)


def listar_autoguardados() -> list[dict]:
    return _accion('borradores').get('borradores', [])


def borrar_autoguardado(clave: str) -> None:
    _accion('borrar_autoguardado', clave=clave)


def preparar_jpeg(path: str | Path) -> bytes:
    path = Path(path)
    if path.stat().st_size > 12 * 1024 * 1024:
        raise ErrorReportador('La imagen original excede 12 MB.')
    with Image.open(path) as original:
        if original.format not in ('JPEG', 'PNG', 'WEBP'):
            raise ErrorReportador('Formato no válido: usa JPG, PNG o WEBP.')
        w, h = original.size
        # Mismos límites de archivo de entrada del Reportador PHP original.
        if w < 50 or h < 50 or w * h > 35_000_000:
            raise ErrorReportador('Fotografía demasiado pequeña, grande o incompatible.')
        img = ImageOps.exif_transpose(original).convert('RGB')
        img.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
        for limit, quality in ((1800, 86), (1600, 78), (1300, 68), (1000, 63), (850, 60), (720, 58)):
            copy = img.copy()
            copy.thumbnail((limit, limit), Image.Resampling.LANCZOS)
            output = BytesIO()
            copy.save(output, 'JPEG', quality=quality, optimize=True, progressive=True)
            if output.tell() <= 900_000:
                return output.getvalue()
    raise ErrorReportador('No fue posible reducir el tamaño de la fotografía.')


def subir_imagen(id_reporte: int, ruta: str, numero: int, clave: str | None = None, *, os: bool = False) -> None:
    jpeg = preparar_jpeg(ruta)
    data = {'id': id_reporte, 'numero': numero, 'nombre': Path(ruta).name,
            'base64': base64.b64encode(jpeg).decode('ascii')}
    if not os:
        data['clave'] = clave
    _accion('subir_os' if os else 'subir_foto', **data)


def leer_imagen(id_reporte: int, numero: int, clave: str | None = None, *, os: bool = False) -> bytes:
    args = {'id': id_reporte, 'numero': numero, 'tipo': 'os' if os else 'foto'}
    if not os:
        args['clave'] = clave
    return base64.b64decode(_accion('leer_imagen', **args)['base64'], validate=True)


def quitar_imagen(id_reporte: int, numero: int, clave: str | None = None, *, os: bool = False) -> None:
    args = {'id': id_reporte, 'numero': numero, 'tipo': 'os' if os else 'foto'}
    if not os:
        args['clave'] = clave
    _accion('quitar_imagen', **args)


def nueva_actividad() -> dict:
    return {'clave': str(uuid4()), 'titulo': '', 'descripcion': '',
            'descripcion_habilitada': True, 'cantidad_fotos': 2}


def validar_captura(datos: dict) -> None:
    limits = {'aco': 60, 'cliente': 200, 'sucursal': 200, 'nombre_servicio': 250,
              'tecnico_responsable': 150}
    for campo, limite in limits.items():
        texto = str(datos.get(campo) or '').strip()
        if not texto or len(texto) > limite:
            raise ErrorReportador(f'Completa {campo.replace("_", " ")} (máximo {limite} caracteres).')
    try:
        date.fromisoformat(str(datos['fecha_servicio']))
    except (ValueError, TypeError, KeyError) as exc:
        raise ErrorReportador('La fecha debe ser válida en formato AAAA-MM-DD.') from exc
    if len(str(datos.get('observaciones') or '')) > 5000:
        raise ErrorReportador('Las observaciones exceden el límite de 5,000 caracteres.')
    acts = datos.get('actividades') or []
    if not 1 <= len(acts) <= MAX_ACTIVIDADES:
        raise ErrorReportador(f'Incluye de 1 a {MAX_ACTIVIDADES} actividades.')
    seen = set()
    for index, act in enumerate(acts, 1):
        name = str(act.get('titulo') or '').strip()
        if not name or len(name) > 200:
            raise ErrorReportador(f'Actividad {index}: título obligatorio (máximo 200 caracteres).')
        if len(str(act.get('descripcion') or '')) > 3000:
            raise ErrorReportador(f'Actividad {index}: descripción demasiado larga.')
        if act['clave'] in seen:
            raise ErrorReportador('Identificador repetido en actividades.')
        seen.add(act['clave'])
        if int(act.get('cantidad_fotos') or 0) not in range(1, 6):
            raise ErrorReportador(f'Actividad {index}: selecciona entre 1 y 5 fotografías.')
