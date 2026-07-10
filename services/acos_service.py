"""
=========================================================
SERVICIO DE ACOS - AXIA
=========================================================

Este archivo pertenece a la capa de servicios de AXIA.

Responsabilidad principal:
- Contener lógica de negocio.
- Consultar y modificar datos en Supabase.
- Devolver resultados limpios a las vistas.

Regla de arquitectura:
Las vistas en `views/` no deben hablar directamente con Supabase.
Deben llamar funciones de esta capa `services/`.
"""

from datetime import datetime

from core.logger import configurar_logger
from core.cache import ttl_cache, clear_cache

logger = configurar_logger(__name__)
from services.movimientos_service import registrar_movimiento_seguro

# =====================================================
# NORMALIZACIÓN DE FECHAS
# =====================================================
def normalizar_fecha_supabase(valor):
    """
    Convierte una fecha capturada por el usuario al formato ISO
    que PostgreSQL/Supabase acepta de forma segura: YYYY-MM-DD.

    Formatos aceptados:
    - 28082026
    - 28/08/2026
    - 28-08-2026
    - 2026-08-28

    Si el campo viene vacío, retorna None para guardar NULL.
    Si el formato no es válido, lanza ValueError para evitar
    enviar una fecha incorrecta a Supabase.
    """

    if valor is None:
        return None

    valor = str(valor).strip()

    if not valor:
        return None

    formatos_permitidos = [
        "%d%m%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
    ]

    for formato in formatos_permitidos:
        try:
            return datetime.strptime(valor, formato).date().isoformat()
        except ValueError:
            continue

    raise ValueError(
        f"Formato de fecha inválido: {valor}. "
        "Usa DD/MM/AAAA o AAAA-MM-DD."
    )


def normalizar_fechas_aco(datos_aco):
    """
    Normaliza todas las fechas conocidas del diccionario de ACO
    antes de insertar o actualizar en Supabase.

    Esta función trabaja sobre una copia para no modificar el
    diccionario original recibido desde la vista.
    """

    datos_normalizados = dict(datos_aco or {})

    campos_fecha = [
        "aco_fecha_inicio",
        "aco_fecha_compromiso",
        "aco_fecha_creacion",
        "fecha_inicio",
        "fecha_compromiso",
        "fecha_creacion",
        "fecha_registro",
    ]

    for campo in campos_fecha:
        if campo in datos_normalizados:
            datos_normalizados[campo] = normalizar_fecha_supabase(
                datos_normalizados.get(campo)
            )

    return datos_normalizados


# =====================================================
# IMPORTACIÓN DE SUPABASE
# =====================================================

from supabase_config import supabase, TABLA_ACOS


def enriquecer_aco_con_sucursal_contacto(aco):
    """Completa un ACO con datos operativos de sucursal/contacto si tiene IDs ligados."""
    if not aco:
        return aco
    aco = dict(aco)
    try:
        from services.sucursales_service import (
            obtener_sucursal_por_id,
            obtener_contacto_por_id,
            construir_domicilio_sucursal,
        )

        sucursal = obtener_sucursal_por_id(aco.get("id_sucursal"))
        contacto = obtener_contacto_por_id(aco.get("id_contacto"))

        if sucursal:
            aco.setdefault("aco_sucursal", sucursal.get("suc_nombre", ""))
            aco.setdefault("aco_direccion", construir_domicilio_sucursal(sucursal))
            aco.setdefault("aco_telefono", sucursal.get("suc_telefono", ""))
            aco.setdefault("aco_correo", sucursal.get("suc_correo", ""))

        if contacto:
            # El contacto operativo tiene prioridad sobre el contacto fiscal del cliente.
            aco["aco_contacto"] = contacto.get("con_nombre", "") or aco.get("aco_contacto", "")
            aco["aco_telefono"] = contacto.get("con_telefono", "") or aco.get("aco_telefono", "")
            aco["aco_correo"] = contacto.get("con_correo", "") or aco.get("aco_correo", "")

    except Exception:
        logger.exception("No fue posible enriquecer el ACO con sucursal/contacto.")
    return aco


# =====================================================
# FUNCIÓN: buscar_aco_por_numero()
# =====================================================
@ttl_cache(ttl_seconds=90)
def buscar_aco_por_numero(aco_numero):
    """
    Busca un ACO por su número interno.

    RETORNA:
        dict | None:
            Diccionario con la información del ACO
            si existe, o None si no se encuentra.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_ACOS)
            .select("*")
            .eq("aco_numero", aco_numero)
            .execute()
        )

        if respuesta.data:
            registrar_movimiento_seguro(
                modulo="ACOS",
                accion="BUSCAR",
                descripcion=f"Consulta de ACO por número: {aco_numero}",
                registro_afectado=aco_numero,
            )
            return enriquecer_aco_con_sucursal_contacto(respuesta.data[0])

        registrar_movimiento_seguro(
            modulo="ACOS",
            accion="BUSCAR_SIN_RESULTADO",
            descripcion=f"Búsqueda de ACO sin resultado: {aco_numero}",
            registro_afectado=aco_numero,
        )
        return None

    except Exception as error:
        logger.exception("Error al buscar ACO.")
        return None


# =====================================================
# FUNCIÓN: obtener_acos()
# =====================================================
@ttl_cache(ttl_seconds=60)
def obtener_acos():
    """
    Consulta todos los ACOs registrados.

    RETORNA:
        list:
            Lista de ACOs ordenados del más reciente al más antiguo.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_ACOS)
            .select("*")
            .order("fecha_registro", desc=True)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="ACOS",
            accion="CONSULTAR",
            descripcion="Consulta general de ACOs",
            registro_afectado=f"Total: {len(respuesta.data or [])}",
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al consultar ACOs.")
        return []


# =====================================================
# FUNCIÓN: crear_aco()
# =====================================================
def crear_aco(datos_aco):
    """
    Crea un nuevo ACO en Supabase.

    PARÁMETROS:
        datos_aco:
            Diccionario con los campos de db_acos.

    RETORNA:
        list | None:
            Respuesta de Supabase si el registro fue exitoso.
    """

    try:
        # PostgreSQL requiere fechas en formato seguro ISO: YYYY-MM-DD.
        # La vista puede recibir DD/MM/AAAA, DD-MM-AAAA o DDMMAAAA,
        # por eso normalizamos aquí antes del insert.
        datos_aco = normalizar_fechas_aco(datos_aco)

        respuesta = (
            supabase
            .table(TABLA_ACOS)
            .insert(datos_aco)
            .execute()
        )

        clear_cache("services.acos_service")

        registrar_movimiento_seguro(
            modulo="ACOS",
            accion="CREAR",
            descripcion="Creación de ACO",
            registro_afectado=datos_aco.get("aco_numero") or datos_aco.get("aco_folio") or respuesta.data,
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al crear ACO.")
        return None


# =====================================================
# FUNCIÓN: actualizar_aco()
# =====================================================
def actualizar_aco(id_aco, datos_aco):
    """
    Actualiza la información de un ACO existente.

    PARÁMETROS:
        id_aco:
            Identificador principal del ACO.

        datos_aco:
            Diccionario con los campos a actualizar.

    RETORNA:
        list | None:
            Respuesta de Supabase si la actualización fue exitosa.
    """

    try:
        # También normalizamos fechas en actualizaciones para mantener
        # consistencia si después editamos fechas de un ACO existente.
        datos_aco = normalizar_fechas_aco(datos_aco)

        respuesta = (
            supabase
            .table(TABLA_ACOS)
            .update(datos_aco)
            .eq("id_aco", id_aco)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="ACOS",
            accion="ACTUALIZAR",
            descripcion=f"Actualización de ACO ID: {id_aco}",
            registro_afectado=id_aco,
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al actualizar ACO.")
        return None


# =====================================================
# FUNCIÓN: validar_aco_existente()
# =====================================================
def validar_aco_existente(aco_numero):
    """
    Valida si un ACO existe dentro de la base de datos.

    RETORNA:
        bool:
            True si existe.
            False si no existe.
    """

    return buscar_aco_por_numero(aco_numero) is not None