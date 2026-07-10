"""
=========================================================
SERVICIO: sucursales_service.py
DESCRIPCIÓN:
Catálogo operativo de sucursales y contactos por cliente.

Estructura real usada en Supabase:
- db_clientes_sucursales.suc_id
- db_clientes_sucursal_contactos.con_id
=========================================================
"""

from core.logger import configurar_logger
from core.cache import ttl_cache, clear_cache
from supabase_config import supabase, TABLA_SUCURSALES, TABLA_CONTACTOS_SUCURSAL
from services.movimientos_service import registrar_movimiento_seguro

logger = configurar_logger(__name__)


def _suc_id(sucursal):
    """Devuelve el ID real de sucursal aceptando alias antiguos."""
    sucursal = sucursal or {}
    return sucursal.get("suc_id") or sucursal.get("id_sucursal")


def _con_id(contacto):
    """Devuelve el ID real de contacto aceptando alias antiguos."""
    contacto = contacto or {}
    return contacto.get("con_id") or contacto.get("id_contacto")


@ttl_cache(ttl_seconds=180)
def obtener_sucursales_por_cliente(id_cliente):
    """Devuelve las sucursales activas ligadas a un cliente."""
    if not id_cliente:
        return []
    try:
        respuesta = (
            supabase
            .table(TABLA_SUCURSALES)
            .select("*")
            .eq("id_cliente", id_cliente)
            .eq("suc_estatus", 1)
            .order("suc_nombre")
            .execute()
        )
        return respuesta.data or []
    except Exception:
        logger.exception("Error al consultar sucursales del cliente.")
        return []


@ttl_cache(ttl_seconds=180)
def obtener_sucursal_por_id(id_sucursal):
    """Devuelve una sucursal por su ID real: suc_id."""
    if not id_sucursal:
        return None
    try:
        respuesta = (
            supabase
            .table(TABLA_SUCURSALES)
            .select("*")
            .eq("suc_id", id_sucursal)
            .limit(1)
            .execute()
        )
        return (respuesta.data or [None])[0]
    except Exception:
        logger.exception("Error al consultar sucursal por ID.")
        return None


@ttl_cache(ttl_seconds=180)
def obtener_contactos_por_sucursal(id_sucursal):
    """Devuelve contactos activos ligados a una sucursal usando suc_id."""
    if not id_sucursal:
        return []
    try:
        respuesta = (
            supabase
            .table(TABLA_CONTACTOS_SUCURSAL)
            .select("*")
            .eq("suc_id", id_sucursal)
            .eq("con_estatus", 1)
            .order("con_nombre")
            .execute()
        )
        return respuesta.data or []
    except Exception:
        logger.exception("Error al consultar contactos de la sucursal.")
        return []


@ttl_cache(ttl_seconds=180)
def obtener_contacto_por_id(id_contacto):
    """Devuelve un contacto por su ID real: con_id."""
    if not id_contacto:
        return None
    try:
        respuesta = (
            supabase
            .table(TABLA_CONTACTOS_SUCURSAL)
            .select("*")
            .eq("con_id", id_contacto)
            .limit(1)
            .execute()
        )
        return (respuesta.data or [None])[0]
    except Exception:
        logger.exception("Error al consultar contacto por ID.")
        return None


def construir_domicilio_sucursal(sucursal):
    """Construye una dirección operativa legible desde db_clientes_sucursales."""
    sucursal = sucursal or {}
    return str(sucursal.get("suc_domicilio", "") or "").strip()


def normalizar_sucursal(datos):
    """Limpia los datos de una sucursal antes de enviarlos a Supabase."""
    datos = datos or {}
    return {
        "id_cliente": datos.get("id_cliente"),
        "suc_nombre": str(datos.get("suc_nombre", "") or "").strip(),
        "suc_domicilio": str(datos.get("suc_domicilio", "") or "").strip(),
        "suc_telefono": str(datos.get("suc_telefono", "") or "").strip(),
        "suc_correo": str(datos.get("suc_correo", "") or "").strip(),
        "suc_estatus": int(datos.get("suc_estatus") or 1),
    }


def normalizar_contacto(datos):
    """Limpia los datos de un contacto operativo antes de enviarlos a Supabase."""
    datos = datos or {}
    return {
        "suc_id": datos.get("suc_id") or datos.get("id_sucursal"),
        "con_nombre": str(datos.get("con_nombre", "") or "").strip(),
        "con_puesto": str(datos.get("con_puesto", "") or "").strip(),
        "con_correo": str(datos.get("con_correo", "") or "").strip(),
        "con_telefono": str(datos.get("con_telefono", "") or datos.get("con_celular", "") or "").strip(),
        "con_estatus": int(datos.get("con_estatus") or 1),
    }


def crear_sucursal(datos):
    """Crea una sucursal operativa ligada a un cliente."""
    try:
        datos_guardar = normalizar_sucursal(datos)
        if not datos_guardar.get("id_cliente"):
            return False, "Selecciona un cliente antes de registrar la sucursal.", None
        if not datos_guardar.get("suc_nombre"):
            return False, "El nombre de la sucursal es obligatorio.", None
        respuesta = supabase.table(TABLA_SUCURSALES).insert(datos_guardar).execute()
        registro = (respuesta.data or [None])[0]
        if registro:
            clear_cache("services.sucursales_service")
            registrar_movimiento_seguro(
                modulo="SUCURSALES",
                accion="CREAR",
                descripcion="Alta de sucursal operativa",
                registro_afectado=_suc_id(registro) or registro.get("suc_nombre"),
            )
            return True, "Sucursal registrada correctamente.", registro
        return False, "No fue posible registrar la sucursal.", None
    except Exception as error:
        logger.exception("Error al crear sucursal.")
        return False, f"No fue posible registrar la sucursal.\n\n{error}", None


def crear_contacto_sucursal(datos):
    """Crea un contacto operativo ligado a una sucursal."""
    try:
        datos_guardar = normalizar_contacto(datos)
        if not datos_guardar.get("suc_id"):
            return False, "Selecciona una sucursal antes de registrar el contacto.", None
        if not datos_guardar.get("con_nombre"):
            return False, "El nombre del contacto es obligatorio.", None
        respuesta = supabase.table(TABLA_CONTACTOS_SUCURSAL).insert(datos_guardar).execute()
        registro = (respuesta.data or [None])[0]
        if registro:
            clear_cache("services.sucursales_service")
            registrar_movimiento_seguro(
                modulo="CONTACTOS_SUCURSAL",
                accion="CREAR",
                descripcion="Alta de contacto operativo",
                registro_afectado=_con_id(registro) or registro.get("con_nombre"),
            )
            return True, "Contacto registrado correctamente.", registro
        return False, "No fue posible registrar el contacto.", None
    except Exception as error:
        logger.exception("Error al crear contacto de sucursal.")
        return False, f"No fue posible registrar el contacto.\n\n{error}", None
