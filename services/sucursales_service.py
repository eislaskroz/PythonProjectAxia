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
from core.performance import page_range
from supabase_config import supabase, TABLA_SUCURSALES, TABLA_CONTACTOS_SUCURSAL
from services.movimientos_service import registrar_movimiento_seguro

logger = configurar_logger(__name__)


COLUMNAS_SUCURSALES = "suc_id,id_cliente,suc_nombre,suc_calle_numero,suc_colonia,suc_municipio,suc_estado,suc_codigo_postal,suc_telefono,suc_correo,suc_domicilio,suc_estatus,fecha_registro"
COLUMNAS_CONTACTOS = "con_id,suc_id,con_nombre,con_puesto,con_correo,con_telefono,con_estatus,fecha_registro"

def _suc_id(sucursal):
    """Devuelve el ID real de sucursal aceptando alias antiguos."""
    sucursal = sucursal or {}
    return sucursal.get("suc_id") or sucursal.get("id_sucursal")


def _con_id(contacto):
    """Devuelve el ID real de contacto aceptando alias antiguos."""
    contacto = contacto or {}
    return contacto.get("con_id") or contacto.get("id_contacto")


@ttl_cache(ttl_seconds=180)
def obtener_sucursales_por_cliente(id_cliente, page=1, page_size=100):
    """Devuelve las sucursales activas ligadas a un cliente."""
    if not id_cliente:
        return []
    try:
        respuesta = (
            supabase
            .table(TABLA_SUCURSALES)
            .select(COLUMNAS_SUCURSALES)
            .eq("id_cliente", id_cliente)
            .eq("suc_estatus", 1)
            .order("suc_nombre")
            .range(*page_range(page, page_size))
            .execute()
        )
        return respuesta.data or []
    except Exception as error:
        # Compatibilidad con esquemas históricos: algunas instalaciones de AXIA
        # tienen variaciones de columnas en db_clientes_sucursales. Un SELECT
        # explícito con una columna inexistente hacía que la vista interpretara
        # erróneamente que el cliente no tenía sucursales. Reintentamos leyendo
        # la fila completa y, como último recurso, sin filtrar suc_estatus.
        logger.warning("Consulta principal de sucursales falló; se intentará fallback: %s", error)
        try:
            respuesta = (
                supabase
                .table(TABLA_SUCURSALES)
                .select("*")
                .eq("id_cliente", id_cliente)
                .order("suc_nombre")
                .range(*page_range(page, page_size))
                .execute()
            )
            filas = respuesta.data or []
            # Si existe suc_estatus, conserva solo registros activos; si no,
            # acepta la fila para compatibilidad con esquemas anteriores.
            return [
                fila for fila in filas
                if "suc_estatus" not in fila or str(fila.get("suc_estatus")) in {"1", "True", "true"}
            ]
        except Exception:
            logger.exception("Error al consultar sucursales del cliente incluso con fallback.")
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
            .select(COLUMNAS_SUCURSALES)
            .eq("suc_id", id_sucursal)
            .limit(1)
            .execute()
        )
        return (respuesta.data or [None])[0]
    except Exception:
        logger.exception("Error al consultar sucursal por ID.")
        return None


@ttl_cache(ttl_seconds=180)
def obtener_contactos_por_sucursal(id_sucursal, page=1, page_size=100):
    """Devuelve contactos ligados a una sucursal usando suc_id.

    Algunas instalaciones históricas de AXIA manejan ``con_estatus`` como
    entero, booleano, texto o incluso no lo tienen. Un filtro rígido
    ``con_estatus = 1`` podía devolver cero filas aunque el contacto existiera.
    Por eso primero intentamos la consulta normal y, si no devuelve resultados
    (o falla por esquema), hacemos una lectura completa por ``suc_id`` y
    filtramos el estatus en Python de forma tolerante.
    """
    if not id_sucursal:
        return []

    def _activo(contacto):
        if "con_estatus" not in contacto:
            return True
        valor = contacto.get("con_estatus")
        if valor is None or valor == "":
            return True
        if isinstance(valor, bool):
            return valor
        texto = str(valor).strip().lower()
        return texto in {"1", "true", "t", "activo", "active", "si", "sí"}

    try:
        respuesta = (
            supabase
            .table(TABLA_CONTACTOS_SUCURSAL)
            .select(COLUMNAS_CONTACTOS)
            .eq("suc_id", id_sucursal)
            .eq("con_estatus", 1)
            .order("con_nombre")
            .range(*page_range(page, page_size))
            .execute()
        )
        filas = respuesta.data or []
        if filas:
            return filas
    except Exception as error:
        logger.warning("Consulta principal de contactos falló; se intentará fallback: %s", error)

    try:
        respuesta = (
            supabase
            .table(TABLA_CONTACTOS_SUCURSAL)
            .select("*")
            .eq("suc_id", id_sucursal)
            .order("con_nombre")
            .range(*page_range(page, page_size))
            .execute()
        )
        return [fila for fila in (respuesta.data or []) if _activo(fila)]
    except Exception:
        logger.exception("Error al consultar contactos de la sucursal incluso con fallback.")
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
            .select(COLUMNAS_CONTACTOS)
            .eq("con_id", id_contacto)
            .limit(1)
            .execute()
        )
        return (respuesta.data or [None])[0]
    except Exception:
        logger.exception("Error al consultar contacto por ID.")
        return None


def construir_domicilio_sucursal(sucursal):
    """Construye una dirección operativa legible con el esquema 2026 de sucursales.

    ``suc_domicilio`` se conserva como fallback para registros históricos, pero
    las nuevas altas usan calle/número, colonia, municipio, estado y C.P.
    """
    sucursal = sucursal or {}
    partes = [
        str(sucursal.get("suc_calle_numero", "") or "").strip(),
        str(sucursal.get("suc_colonia", "") or "").strip(),
        str(sucursal.get("suc_municipio", "") or "").strip(),
        str(sucursal.get("suc_estado", "") or "").strip(),
    ]
    cp = str(sucursal.get("suc_codigo_postal", "") or "").strip()
    if cp:
        partes.append(f"C.P. {cp}")
    domicilio = ", ".join(parte for parte in partes if parte)
    return domicilio or str(sucursal.get("suc_domicilio", "") or "").strip()


def normalizar_sucursal(datos):
    """Limpia los datos de una sucursal antes de enviarlos a Supabase."""
    datos = datos or {}
    calle_numero = str(
        datos.get("suc_calle_numero", "") or datos.get("suc_domicilio", "") or ""
    ).strip()
    colonia = str(datos.get("suc_colonia", "") or "").strip()
    municipio = str(datos.get("suc_municipio", "") or "").strip()
    estado = str(datos.get("suc_estado", "") or "").strip()
    codigo_postal = str(datos.get("suc_codigo_postal", "") or "").strip()

    # Campo legado: se mantiene sincronizado para módulos/versiones anteriores.
    domicilio_legacy = ", ".join(
        parte for parte in (calle_numero, colonia, municipio, estado, f"C.P. {codigo_postal}" if codigo_postal else "")
        if parte
    )

    return {
        "id_cliente": datos.get("id_cliente"),
        "suc_nombre": str(datos.get("suc_nombre", "") or "").strip(),
        "suc_calle_numero": calle_numero,
        "suc_colonia": colonia,
        "suc_municipio": municipio,
        "suc_estado": estado,
        "suc_codigo_postal": codigo_postal,
        "suc_domicilio": domicilio_legacy,
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



def actualizar_sucursal(id_sucursal, datos):
    """Actualiza una sucursal operativa existente."""
    try:
        if not id_sucursal:
            return False, "Selecciona una sucursal válida.", None
        datos_guardar = normalizar_sucursal(datos)
        datos_guardar.pop("id_cliente", None)
        respuesta = (
            supabase.table(TABLA_SUCURSALES)
            .update(datos_guardar)
            .eq("suc_id", id_sucursal)
            .execute()
        )
        registro = (respuesta.data or [None])[0]
        clear_cache("services.sucursales_service")
        registrar_movimiento_seguro(
            modulo="SUCURSALES", accion="ACTUALIZAR",
            descripcion="Actualización de sucursal operativa",
            registro_afectado=id_sucursal,
        )
        return True, "Sucursal actualizada correctamente.", registro
    except Exception as error:
        logger.exception("Error al actualizar sucursal.")
        return False, f"No fue posible actualizar la sucursal.\n\n{error}", None


def actualizar_contacto_sucursal(id_contacto, datos):
    """Actualiza un contacto operativo existente."""
    try:
        if not id_contacto:
            return False, "Selecciona un contacto válido.", None
        datos_guardar = normalizar_contacto(datos)
        datos_guardar.pop("suc_id", None)
        respuesta = (
            supabase.table(TABLA_CONTACTOS_SUCURSAL)
            .update(datos_guardar)
            .eq("con_id", id_contacto)
            .execute()
        )
        registro = (respuesta.data or [None])[0]
        clear_cache("services.sucursales_service")
        registrar_movimiento_seguro(
            modulo="CONTACTOS_SUCURSAL", accion="ACTUALIZAR",
            descripcion="Actualización de contacto operativo",
            registro_afectado=id_contacto,
        )
        return True, "Contacto actualizado correctamente.", registro
    except Exception as error:
        logger.exception("Error al actualizar contacto de sucursal.")
        return False, f"No fue posible actualizar el contacto.\n\n{error}", None
