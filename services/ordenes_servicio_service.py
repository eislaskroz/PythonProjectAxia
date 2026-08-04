"""
=========================================================
SERVICIO DE ÓRDENES DE SERVICIO - AXIA
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

from core.logger import configurar_logger
from core.error_reporting import register_error
from core.date_utils import normalizar_campos_fecha
from core.performance import page_range

logger = configurar_logger(__name__)
from services.movimientos_service import registrar_movimiento_seguro
from services.search_service import buscar_parcial_supabase

# =====================================================
# IMPORTACIÓN DE SUPABASE
# =====================================================

from supabase_config import supabase
from services.folios_service import asegurar_folio
from services.query_compat import execute_select_compatible
from services.levantamientos_schema import (
    TABLA_LEVANTAMIENTOS,
    CAMPOS_CONVERSION_EDITABLES,
    filtrar_payload_levantamiento,
)


# =====================================================
# CONSTANTE DE TABLA
# =====================================================

TABLA_ORDENES = "db_ordenes_servicio"
COLUMNAS_ORDENES = (
    "id_orden,id_aco,os_aco_numero,id_levantamiento,os_folio_levantamiento,"
    "id_cliente,os_cliente,os_folio,os_tipo,os_estatus,os_prioridad,"
    "os_contacto,os_telefono,os_correo,os_direccion,os_ubicacion,"
    "os_descripcion,os_actividades,os_materiales,os_observaciones,"
    "os_tecnico,os_supervisor,os_fecha_programada,os_fecha_inicio,"
    "os_fecha_cierre,creado_por,actualizado_por,fecha_registro,"
    "fecha_actualizacion,os_fecha,os_sucursal,os_domicilio,os_encargado,"
    "os_solicitante,os_celular,os_hora_llegada,os_hora_salida,"
    "os_tipos_servicio_json,os_tipo_servicio,os_encargado_servicio,"
    "os_tecnicos,os_equipos_json,os_eval_trato,os_eval_habilidades,"
    "os_eval_velocidad,os_eval_otro,os_firma_cliente,id_sucursal,id_contacto"
)


# =====================================================
# FUNCIÓN: crear_orden_servicio()
# =====================================================
def crear_orden_servicio(datos_orden):
    """
    Crea una nueva orden de servicio.

    PARÁMETROS:
        datos_orden:
            Diccionario con los datos de la orden.

    RETORNA:
        list | None:
            Datos insertados si el registro fue exitoso.
    """

    try:
        datos_orden = asegurar_folio(datos_orden, "os_folio", "OS")
        datos_orden = normalizar_campos_fecha(datos_orden)

        respuesta = (
            supabase
            .table(TABLA_ORDENES)
            .insert(datos_orden)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="ORDENES_SERVICIO",
            accion="CREAR",
            descripcion="Creación de orden de servicio",
            registro_afectado=datos_orden.get("os_folio") or datos_orden.get("folio_orden") or respuesta.data,
        )
        return respuesta.data

    except Exception as error:
        register_error(error, "Registrar orden de servicio")
        logger.exception("Error al crear orden de servicio.")
        return None


# =====================================================
# FUNCIÓN: obtener_ordenes_servicio()
# =====================================================
def obtener_ordenes_servicio(page=1, page_size=100):
    """
    Consulta todas las órdenes de servicio.

    RETORNA:
        list:
            Lista de órdenes registradas.
    """

    try:
        respuesta = execute_select_compatible(
            supabase,
            TABLA_ORDENES,
            COLUMNAS_ORDENES,
            lambda query: query
            .order("fecha_registro", desc=True)
            .range(*page_range(page, page_size))
        )

        registrar_movimiento_seguro(
            modulo="ORDENES_SERVICIO",
            accion="CONSULTAR",
            descripcion="Consulta general de órdenes de servicio",
            registro_afectado=f"Total: {len(respuesta.data or [])}",
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al consultar órdenes.")
        return []


# =====================================================
# FUNCIÓN: obtener_ordenes_por_aco()
# =====================================================
def obtener_ordenes_por_aco(aco_numero, page=1, page_size=100):
    """
    Consulta órdenes relacionadas con un ACO.

    PARÁMETROS:
        aco_numero:
            Número de ACO.

    RETORNA:
        list:
            Lista de órdenes relacionadas.
    """

    try:
        respuesta = execute_select_compatible(
            supabase,
            TABLA_ORDENES,
            COLUMNAS_ORDENES,
            lambda query: query
            .eq("os_aco_numero", aco_numero)
            .order("fecha_registro", desc=True)
            .range(*page_range(page, page_size))
        )

        registrar_movimiento_seguro(
            modulo="ORDENES_SERVICIO",
            accion="BUSCAR_POR_ACO",
            descripcion=f"Consulta de órdenes de servicio por ACO: {aco_numero}",
            registro_afectado=aco_numero,
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al consultar órdenes por ACO.")
        return []


# =====================================================
# FUNCIÓN: buscar_orden_por_folio()
# =====================================================
def buscar_orden_por_folio(folio):
    """
    Busca una orden por folio.

    PARÁMETROS:
        folio:
            Folio único de la orden.

    RETORNA:
        dict | None:
            Datos de la orden si existe.
    """

    try:
        respuesta = execute_select_compatible(
            supabase,
            TABLA_ORDENES,
            COLUMNAS_ORDENES,
            lambda query: query
            .eq("os_folio", str(folio).strip().upper())
        )

        if respuesta.data:
            registrar_movimiento_seguro(
                modulo="ORDENES_SERVICIO",
                accion="BUSCAR",
                descripcion=f"Búsqueda de orden de servicio por folio: {folio}",
                registro_afectado=folio,
            )
            return respuesta.data[0]

        registrar_movimiento_seguro(
            modulo="ORDENES_SERVICIO",
            accion="BUSCAR_SIN_RESULTADO",
            descripcion=f"Búsqueda de orden de servicio sin resultado: {folio}",
            registro_afectado=folio,
        )
        return None

    except Exception as error:
        logger.exception("Error al buscar orden de servicio.")
        raise RuntimeError("No fue posible consultar la orden de servicio en Supabase.") from error


# =====================================================
# FUNCIÓN: actualizar_orden_servicio()
# =====================================================
def actualizar_orden_servicio(id_orden, datos_orden):
    """
    Actualiza una orden existente.

    PARÁMETROS:
        id_orden:
            ID principal de la orden.

        datos_orden:
            Campos a actualizar.

    RETORNA:
        list | None:
            Datos actualizados.
    """

    try:
        datos_orden = normalizar_campos_fecha(datos_orden)

        respuesta = (
            supabase
            .table(TABLA_ORDENES)
            .update(datos_orden)
            .eq("id_orden", id_orden)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="ORDENES_SERVICIO",
            accion="ACTUALIZAR",
            descripcion=f"Actualización de orden de servicio ID: {id_orden}",
            registro_afectado=id_orden,
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al actualizar orden.")
        return None


# =====================================================
# FUNCIÓN: obtener_estadisticas_ordenes()
# =====================================================
def obtener_estadisticas_ordenes(page=1, page_size=100):
    """
    Obtiene estadísticas generales de órdenes.

    RETORNA:
        tuple:
            Total, pendientes, proceso y finalizadas.
    """

    try:
        ordenes = obtener_ordenes_servicio()

        total = len(ordenes)
        pendientes = len([o for o in ordenes if o.get("os_estatus") == 1])
        proceso = len([o for o in ordenes if o.get("os_estatus") == 2])
        finalizadas = len([o for o in ordenes if o.get("os_estatus") == 3])

        return total, pendientes, proceso, finalizadas

    except Exception as error:
        logger.exception("Error al obtener estadísticas de movimientos.")
        return 0, 0, 0, 0

# Búsqueda parcial unificada
def buscar_ordenes_servicio(termino, limite=100):
    resultados = buscar_parcial_supabase(
        supabase=supabase, tabla=TABLA_ORDENES, columnas=COLUMNAS_ORDENES, termino=termino,
        campos=('os_folio', 'os_aco_numero', 'os_cliente', 'os_sucursal', 'os_tecnico', 'os_supervisor', 'os_estatus', 'os_tipo_servicio', 'os_descripcion'), id_campos=('id_orden', 'os_folio'), orden='fecha_registro', limite=limite,
    )
    registrar_movimiento_seguro(
        modulo='ORDENES_SERVICIO', accion="BUSCAR",
        descripcion=f"Búsqueda parcial: {str(termino).strip().upper()}",
        registro_afectado=f"Coincidencias: {len(resultados)}",
    )
    return resultados


def buscar_orden_por_levantamiento(folio_levantamiento=None, id_levantamiento=None):
    """Devuelve la OS vinculada a un levantamiento, si ya existe.

    La relación oficial usa ``id_levantamiento`` y ``os_folio_levantamiento``.
    Se conserva compatibilidad con órdenes antiguas buscando primero por ID y
    después por folio.
    """
    folio = str(folio_levantamiento or "").strip().upper()
    try:
        if id_levantamiento not in (None, ""):
            respuesta = execute_select_compatible(
                supabase,
                TABLA_ORDENES,
                COLUMNAS_ORDENES,
                lambda query: query.eq("id_levantamiento", id_levantamiento),
            )
            if respuesta.data:
                return respuesta.data[0]

        if folio:
            respuesta = execute_select_compatible(
                supabase,
                TABLA_ORDENES,
                COLUMNAS_ORDENES,
                lambda query: query.eq("os_folio_levantamiento", folio),
            )
            if respuesta.data:
                return respuesta.data[0]
        return None
    except Exception as error:
        logger.exception("Error al comprobar conversión previa del levantamiento %s", folio)
        raise RuntimeError(
            "No fue posible comprobar si el levantamiento ya cuenta con una orden de servicio."
        ) from error


def _texto_json(valor):
    """Serializa estructuras para columnas TEXT sin perder acentos."""
    if valor in (None, ""):
        return ""
    if isinstance(valor, str):
        return valor.strip()
    import json
    return json.dumps(valor, ensure_ascii=False)


def _extraer_usuario(usuario_activo):
    usuario_activo = usuario_activo or {}
    return str(
        usuario_activo.get("usu_nickname")
        or usuario_activo.get("usuario")
        or usuario_activo.get("usu_nombre")
        or "Administrativo"
    ).strip()


def _crear_orden_estricta(datos_orden):
    """Inserta una OS y conserva el error técnico real de Supabase."""
    datos = asegurar_folio(datos_orden, "os_folio", "OS")
    datos = normalizar_campos_fecha(datos)
    try:
        respuesta = supabase.table(TABLA_ORDENES).insert(datos).execute()
    except Exception as error:
        register_error(error, "Convertir levantamiento a orden de servicio")
        logger.exception("Supabase rechazó la creación de la orden de servicio. Payload=%s", datos)
        detalle = str(error).strip()
        raise RuntimeError(
            "Supabase rechazó la creación de la orden de servicio. "
            f"Detalle técnico: {detalle or type(error).__name__}"
        ) from error

    filas = getattr(respuesta, "data", None) or []
    if not filas:
        raise RuntimeError(
            "Supabase procesó la solicitud, pero no devolvió el registro creado. "
            "Revisa la configuración de retorno del INSERT y los logs de Supabase."
        )
    return filas


def _eliminar_orden_compensacion(id_orden):
    """Revierte la OS si falla el segundo paso de la conversión."""
    if id_orden in (None, ""):
        return False
    try:
        respuesta = (
            supabase.table(TABLA_ORDENES)
            .delete()
            .eq("id_orden", id_orden)
            .execute()
        )
        return bool(getattr(respuesta, "data", None))
    except Exception:
        logger.exception("No fue posible revertir la OS %s después de fallar la conversión.", id_orden)
        return False



def _actualizar_levantamiento_conversion(id_levantamiento, folio_levantamiento, campos):
    """Actualiza y verifica el levantamiento durante la conversión.

    Supabase/PostgREST puede ejecutar correctamente un UPDATE y devolver una lista
    vacía cuando la preferencia de retorno es ``minimal``. Por eso no se usa
    ``bool(response.data)`` como única confirmación: después del UPDATE se consulta
    el registro y se comprueba el estatus. También se intenta por folio si el ID
    recibido no localiza una fila.
    """
    datos = filtrar_payload_levantamiento(campos, campos_permitidos=CAMPOS_CONVERSION_EDITABLES | {"lev_estatus", "actualizado_por"})
    datos = normalizar_campos_fecha(datos)
    # Una fecha vacía debe almacenarse como NULL, no como cadena vacía.
    for clave in tuple(datos):
        if "fecha" in clave.lower() and datos[clave] == "":
            datos[clave] = None

    def ejecutar_por(campo, valor):
        try:
            return (
                supabase.table(TABLA_LEVANTAMIENTOS)
                .update(datos)
                .eq(campo, valor)
                .execute()
            )
        except Exception as error:
            register_error(error, "Actualizar levantamiento durante conversión a OS")
            logger.exception(
                "Supabase rechazó la actualización del levantamiento. filtro=%s:%s payload=%s",
                campo, valor, datos,
            )
            detalle = str(error).strip()
            raise RuntimeError(
                "Supabase rechazó la actualización del levantamiento. "
                f"Detalle técnico: {detalle or type(error).__name__}"
            ) from error

    def consultar_por(campo, valor):
        try:
            respuesta = (
                supabase.table(TABLA_LEVANTAMIENTOS)
                .select("id_levantamiento,lev_folio,lev_estatus")
                .eq(campo, valor)
                .limit(1)
                .execute()
            )
            filas = getattr(respuesta, "data", None) or []
            return filas[0] if filas else None
        except Exception as error:
            logger.exception("No fue posible verificar el levantamiento actualizado.")
            detalle = str(error).strip()
            raise RuntimeError(
                "Supabase no permitió verificar el levantamiento después de actualizarlo. "
                f"Detalle técnico: {detalle or type(error).__name__}"
            ) from error

    filtros = []
    if id_levantamiento not in (None, ""):
        filtros.append(("id_levantamiento", id_levantamiento))
    folio = str(folio_levantamiento or "").strip().upper()
    if folio:
        filtros.append(("lev_folio", folio))

    for campo, valor in filtros:
        respuesta = ejecutar_por(campo, valor)
        filas = getattr(respuesta, "data", None) or []
        if filas:
            return filas

        # UPDATE correcto con retorno minimal: verificar el estado persistido.
        registro = consultar_por(campo, valor)
        if registro and int(registro.get("lev_estatus") or 0) == int(datos.get("lev_estatus") or 0):
            return [registro]

    raise RuntimeError(
        "Supabase no actualizó ningún levantamiento con el ID o folio seleccionado. "
        "Verifica que el registro exista y que la política RLS permita UPDATE en db_levantamientos."
    )

def convertir_levantamiento_a_orden(levantamiento_original, cambios, usuario_activo=None):
    """Transforma un levantamiento en una OS vinculada y evita duplicados.

    Orden de operaciones:
    1. Valida duplicidad por ``id_levantamiento``/folio.
    2. Crea la OS usando únicamente columnas reales de Supabase.
    3. Actualiza el levantamiento a estatus 2.
    4. Si el paso 3 falla, elimina la OS recién creada como compensación.
    """
    original = dict(levantamiento_original or {})
    editados = dict(cambios or {})
    folio_lev = str(original.get("lev_folio") or editados.get("lev_folio") or "").strip().upper()
    id_lev = original.get("id_levantamiento")
    if not folio_lev or id_lev in (None, ""):
        raise ValueError("El levantamiento seleccionado no contiene ID o folio válido.")

    existente = buscar_orden_por_levantamiento(folio_lev, id_lev)
    if existente:
        raise ValueError(
            f"El levantamiento {folio_lev} ya fue convertido en "
            f"{existente.get('os_folio', 'una orden de servicio')}."
        )

    def valor(campo, *alternos, default=None):
        for clave in (campo, *alternos):
            dato = editados.get(clave, original.get(clave))
            if dato not in (None, ""):
                return dato
        return default

    cliente = str(valor("lev_cliente", default="")).strip()
    descripcion = str(valor("lev_descripcion", default="")).strip()
    if not cliente or not descripcion:
        raise ValueError("La orden requiere cliente y descripción antes de realizar la conversión.")

    tipo_servicio = str(valor("lev_tipo", default="Servicio")).strip()
    modalidad = str(valor("lev_modalidad_operativa", default="")).strip()
    tipo_compuesto = " / ".join(x for x in (tipo_servicio, modalidad) if x)
    usuario = _extraer_usuario(usuario_activo)

    detalle = valor("lev_detalle_tecnico_json", default={})
    requerimientos = str(valor("lev_requerimientos", default="")).strip()
    equipos = original.get("lev_equipos_danados_json") or {}

    actividades = "\n\n".join(filter(None, [
        requerimientos,
        f"Detalle técnico JSON: {_texto_json(detalle)}" if detalle else "",
    ]))
    observaciones = "\n\n".join(filter(None, [
        f"Orden generada desde el levantamiento {folio_lev} por {usuario}.",
        str(valor("lev_observaciones", default="")).strip(),
    ]))

    datos_os = {
        "id_aco": original.get("id_aco"),
        "os_aco_numero": valor("lev_aco_numero"),
        "id_levantamiento": id_lev,
        "os_folio_levantamiento": folio_lev,
        "id_cliente": original.get("id_cliente"),
        "os_cliente": cliente,
        "os_tipo": 1,
        "os_estatus": 1,
        "os_prioridad": int(valor("lev_prioridad", default=2) or 2),
        "os_contacto": valor("lev_contacto"),
        "os_telefono": valor("lev_telefono"),
        "os_correo": valor("lev_correo"),
        "os_direccion": valor("lev_direccion"),
        "os_ubicacion": valor("lev_ubicacion"),
        "os_descripcion": descripcion,
        "os_actividades": actividades,
        "os_materiales": requerimientos,
        "os_observaciones": observaciones,
        "os_tecnico": valor("lev_tecnico"),
        "os_supervisor": valor("lev_supervisor"),
        "os_fecha": valor("lev_fecha_realizacion", "fecha_registro"),
        "os_fecha_programada": valor("lev_fecha_programada"),
        "creado_por": usuario,
        "actualizado_por": usuario,
        # Compatibilidad con la pantalla histórica de órdenes:
        "os_domicilio": valor("lev_direccion"),
        "os_encargado": valor("lev_contacto"),
        "os_solicitante": usuario,
        "os_celular": valor("lev_telefono"),
        "os_tipos_servicio_json": _texto_json([tipo_compuesto]),
        "os_tipo_servicio": tipo_compuesto,
        "os_encargado_servicio": valor("lev_contacto"),
        "os_tecnicos": valor("lev_tecnico"),
        "os_equipos_json": _texto_json(equipos) if equipos else None,
    }
    datos_os = {k: v for k, v in datos_os.items() if v not in (None, "")}

    resultado_os = _crear_orden_estricta(datos_os)
    orden_creada = resultado_os[0]

    # Persiste únicamente columnas reales y editables del levantamiento.
    # La relación con la OS vive en db_ordenes_servicio; aquí solo se guardan
    # las correcciones administrativas y el cambio de estatus.
    campos_lev = filtrar_payload_levantamiento(
        editados,
        campos_permitidos=CAMPOS_CONVERSION_EDITABLES,
    )
    campos_lev["lev_estatus"] = 2
    campos_lev["actualizado_por"] = usuario

    try:
        actualizado = _actualizar_levantamiento_conversion(id_lev, folio_lev, campos_lev)
    except Exception as error:
        revertida = _eliminar_orden_compensacion(orden_creada.get("id_orden"))
        if revertida:
            raise RuntimeError(
                f"{error} La orden creada se revirtió automáticamente; "
                "puedes corregir el problema e intentarlo de nuevo."
            ) from error
        raise RuntimeError(
            f"{error} La orden fue creada, pero no fue posible revertirla. "
            "No repitas el proceso; revisa Supabase y los logs."
        ) from error

    registrar_movimiento_seguro(
        modulo="ORDENES_SERVICIO",
        accion="CONVERTIR_LEVANTAMIENTO",
        descripcion=f"Conversión {folio_lev} a orden de servicio",
        registro_afectado=orden_creada.get("os_folio") or folio_lev,
    )
    return resultado_os

