"""Puerta HTTPS hacia el módulo administrativo protegido de AXIA.

No se envían service_role keys a Windows; únicamente la contraseña del
administrador, de forma efímera, a la Edge Function por HTTPS.
"""
from __future__ import annotations
import os
import requests
from supabase_config import SUPABASE_URL, SUPABASE_KEY
from security.permissions import es_admin
from app_context import obtener_usuario_actual

TIPOS = {
    "ACOs": ("db_acos", "id_aco", "aco_numero", "aco_cliente", "aco_estatus", "fecha_registro"),
    "Levantamientos": ("db_levantamientos", "id_levantamiento", "lev_folio", "lev_cliente", "lev_estatus", "fecha_registro"),
    "Órdenes de Trabajo": ("db_ordenes_trabajo", "ot_id", "ot_folio", "ot_cliente", "ot_estatus", "fecha_registro"),
    "Órdenes de Servicio": ("db_ordenes_servicio", "id_orden", "os_folio", "os_cliente", "os_estatus", "fecha_registro"),
    "Bitácoras": ("db_bitacoras", "id_bitacora", "bit_folio", "bit_cliente", "bit_estatus", "fecha_registro"),
}
# La lista no incluye folios, IDs, firmas, evidencias, anexos, relaciones ni
# aprobaciones, para prevenir incoherencias en operaciones encadenadas.
EDITABLES = {
    "db_acos": "aco_cliente aco_descripcion aco_observaciones aco_responsable aco_fecha_inicio aco_fecha_compromiso aco_estatus",
    "db_levantamientos": "lev_cliente lev_tipo lev_estatus lev_prioridad lev_contacto lev_telefono lev_correo lev_direccion lev_direccion_sucursal lev_ubicacion lev_descripcion lev_requerimientos lev_observaciones lev_tecnico lev_supervisor lev_duracion_proyecto lev_horas_estimadas lev_dias_trabajo lev_personas_considerar lev_notas lev_fecha_programada lev_fecha_realizacion lev_modalidad_operativa lev_descripcion_fallas lev_detalle_tecnico_json lev_equipos_danados_json",
    "db_ordenes_trabajo": "ot_cliente ot_contacto ot_sucursal ot_jefe_operacion ot_supervisor ot_esi ot_numero_dias ot_numero_personas ot_asunto ot_descripcion ot_estatus ot_prioridad ot_fecha ot_partidas_json",
    "db_ordenes_servicio": "os_cliente os_tipo os_estatus os_prioridad os_contacto os_telefono os_correo os_direccion os_ubicacion os_descripcion os_actividades os_materiales os_observaciones os_tecnico os_supervisor os_fecha_programada os_fecha_inicio os_fecha_cierre os_sucursal os_encargado os_hora_llegada os_hora_salida",
    "db_bitacoras": "bit_cliente bit_descripcion bit_direccion_sucursal bit_encargado_proyecto_axia bit_estatus bit_fecha bit_hora_llegada bit_hora_salida bit_observaciones bit_porcentaje_avance bit_tecnico bit_tecnico_sitio",
}
EDITABLES = {k: tuple(v.split()) for k,v in EDITABLES.items()}

class AdministracionError(RuntimeError):
    pass


def _mensaje_error_servidor(resultado, status):
    """Convierte errores JSON de Edge/PostgREST a un mensaje útil y seguro.

    Compatible con el despliegue anterior, que entregaba «[object Object]»,
    y con el nuevo, que devuelve {error: texto, codigo: codigo_pg}.
    """
    if not isinstance(resultado, dict):
        return f"El servidor devolvió HTTP {status} sin información de error legible."
    detalle = resultado.get("error") or resultado.get("message")
    codigo = resultado.get("codigo")
    if isinstance(detalle, dict):
        codigo = codigo or detalle.get("code") or detalle.get("codigo")
        detalle = detalle.get("message") or detalle.get("error")
    if isinstance(detalle, list):
        detalle = "; ".join(str(parte) for parte in detalle[:3])
    if not isinstance(detalle, str) or not detalle.strip() or detalle.strip() == "[object Object]":
        detalle = ("Supabase devolvió un error sin su causa. Actualiza la Edge "
                   "Function axia-admin-registros y vuelve a consultar el registro.")
    detalle = detalle.strip()[:380]
    if isinstance(codigo, str) and codigo.isalnum() and len(codigo) <= 12:
        return f"{detalle} (código {codigo})"
    return detalle


def ejecutar(tabla: str, accion: str, contrasena: str, **argumentos):
    usuario = obtener_usuario_actual()
    if not es_admin(usuario):
        raise PermissionError("Solo el Administrador (rol 1) puede usar este módulo.")
    if tabla not in EDITABLES:
        raise AdministracionError("Tipo de registro no permitido")
    if not contrasena:
        raise AdministracionError("Ingresa la contraseña del Administrador")
    if not str(SUPABASE_URL).lower().startswith('https://'):
        raise AdministracionError("La consola requiere HTTPS")
    url = SUPABASE_URL.rstrip('/') + '/functions/v1/axia-admin-registros'
    payload = {"tabla":tabla,"accion":accion,"usuario":usuario.get("usuario"),
               "contrasena":contrasena,**argumentos}
    try:
        response=requests.post(url,headers={"apikey":SUPABASE_KEY,
            "Authorization":f"Bearer {SUPABASE_KEY}", "content-type":"application/json"},
            json=payload,timeout=(8,40),allow_redirects=False)
    except requests.RequestException as exc:
        raise AdministracionError("No fue posible conectar con la función administrativa") from exc
    try:
        resultado=response.json()
    except ValueError as exc:
        raise AdministracionError("Respuesta inválida del servidor. ¿Se desplegó la Edge Function?") from exc
    if not response.ok or not isinstance(resultado,dict) or resultado.get('error'):
        raise AdministracionError(_mensaje_error_servidor(resultado, response.status_code))
    return resultado
