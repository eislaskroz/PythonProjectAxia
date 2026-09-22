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
from core.error_reporting import register_error
from core.cache import ttl_cache, clear_cache

logger = configurar_logger(__name__)
from services.movimientos_service import registrar_movimiento_seguro
from services.search_service import buscar_parcial_supabase

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


# Columnas explícitas de db_acos usadas por la aplicación.
# Mantener esta lista sincronizada con migrations/validar_esquema_beta_095.sql.
COLUMNAS_ACOS = ",".join([
    "id_aco",
    "aco_numero",
    "aco_cliente",
    "aco_descripcion",
    "aco_observaciones",
    "aco_responsable",
    "aco_creado_por",
    "aco_fecha_inicio",
    "aco_fecha_compromiso",
    "aco_estatus",
    "id_cliente",
    "id_sucursal",
    "id_contacto",
    "fecha_registro",
])


class AcoServiceError(RuntimeError):
    """Error de comunicación o consulta del servicio de ACOs."""



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
            .select(COLUMNAS_ACOS)
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
        logger.exception("Error al buscar ACO %s.", aco_numero)
        raise AcoServiceError(
            "No fue posible consultar el ACO en Supabase. "
            "Revisa la conexión y la estructura de db_acos."
        ) from error


@ttl_cache(ttl_seconds=90)
def buscar_aco_por_id(id_aco):
    """Busca un ACO por su llave primaria y devuelve el registro enriquecido."""
    if id_aco in (None, ""):
        return None
    try:
        respuesta = (
            supabase.table(TABLA_ACOS)
            .select(COLUMNAS_ACOS)
            .eq("id_aco", id_aco)
            .limit(1)
            .execute()
        )
        return enriquecer_aco_con_sucursal_contacto(respuesta.data[0]) if respuesta.data else None
    except Exception as error:
        logger.exception("Error al buscar ACO por ID %s.", id_aco)
        raise AcoServiceError("No fue posible consultar el ACO por ID en Supabase.") from error


def _marca_levantamiento_aco(folio_levantamiento):
    folio = str(folio_levantamiento or "").strip().upper()
    return f"[AXIA-LEV:{folio}]" if folio else ""


def buscar_aco_generado_por_levantamiento(folio_levantamiento):
    """Recupera el ACO automático de un LEV para evitar duplicados en reintentos."""
    marca = _marca_levantamiento_aco(folio_levantamiento)
    if not marca:
        return None
    try:
        respuesta = (
            supabase.table(TABLA_ACOS)
            .select(COLUMNAS_ACOS)
            .ilike("aco_observaciones", f"%{marca}%")
            .order("fecha_registro", desc=True)
            .limit(1)
            .execute()
        )
        return enriquecer_aco_con_sucursal_contacto(respuesta.data[0]) if respuesta.data else None
    except Exception as error:
        logger.exception("Error buscando ACO generado para %s.", folio_levantamiento)
        raise AcoServiceError("No fue posible comprobar el ACO automático del levantamiento.") from error


def crear_aco_desde_levantamiento(levantamiento, usuario_activo=None):
    """Crea el ACO que nace al autorizar un levantamiento para convertirse en OT."""
    lev = dict(levantamiento or {})
    folio = str(lev.get("lev_folio") or "").strip().upper()
    if not folio:
        raise ValueError("El levantamiento no contiene folio para generar su ACO.")

    existente = buscar_aco_generado_por_levantamiento(folio)
    if existente:
        return existente

    marca = _marca_levantamiento_aco(folio)
    observaciones = str(lev.get("lev_observaciones") or "").strip()
    observaciones = f"{marca}\n{observaciones}".strip()
    usuario = str(
        (usuario_activo or {}).get("usu_nickname")
        or (usuario_activo or {}).get("usuario")
        or "Sistema AXIA"
    ).strip()
    datos = {
        # aco_numero lo asigna el trigger vigente de Supabase.
        "aco_estatus": 1,
        "id_cliente": lev.get("id_cliente"),
        "id_sucursal": lev.get("id_sucursal"),
        "id_contacto": lev.get("id_contacto"),
        "aco_cliente": str(lev.get("lev_cliente") or "").strip(),
        "aco_descripcion": str(lev.get("lev_descripcion") or "").strip(),
        "aco_observaciones": observaciones,
        "aco_responsable": str(lev.get("lev_supervisor") or lev.get("lev_tecnico") or usuario).strip(),
        "aco_creado_por": usuario,
        "aco_fecha_inicio": lev.get("lev_fecha_programada") or lev.get("lev_fecha_realizacion") or None,
        "aco_fecha_compromiso": None,
    }
    datos = {clave: valor for clave, valor in datos.items() if valor is not None}
    resultado = crear_aco(datos)
    if not resultado:
        raise AcoServiceError("Supabase no confirmó la creación automática del ACO.")
    creado = dict(resultado[0])
    clear_cache("services.acos_service")
    return enriquecer_aco_con_sucursal_contacto(creado)


# =====================================================
# FUNCIÓN: obtener_acos()
# =====================================================
@ttl_cache(ttl_seconds=60)
def obtener_acos(page=1, page_size=100):
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
            .select(COLUMNAS_ACOS)
            .order("fecha_registro", desc=True)
            .range(*page_range(page, page_size))
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
        register_error(error, "Registrar ACO")
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

# Búsqueda parcial unificada
def buscar_acos(termino, limite=100):
    resultados = buscar_parcial_supabase(
        supabase=supabase, tabla=TABLA_ACOS, columnas=COLUMNAS_ACOS, termino=termino,
        campos=('aco_numero', 'aco_cliente', 'aco_responsable', 'aco_sucursal', 'aco_estatus'), id_campos=('id_aco', 'aco_numero'), orden='fecha_registro', limite=limite,
    )
    registrar_movimiento_seguro(
        modulo='ACOS', accion="BUSCAR",
        descripcion=f"Búsqueda parcial: {str(termino).strip().upper()}",
        registro_afectado=f"Coincidencias: {len(resultados)}",
    )
    return resultados
