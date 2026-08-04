"""
=========================================================
SERVICIO DE ÓRDENES DE TRABAJO - AXIA
=========================================================

Nueva capa de negocio para el formato Orden de Trabajo.
La vista no consulta Supabase directamente; todo pasa por este servicio.
"""

from core.logger import configurar_logger
from core.error_reporting import register_error
from core.date_utils import normalizar_campos_fecha
from core.performance import page_range
from supabase_config import supabase
from services.folios_service import asegurar_folio
from services.query_compat import execute_select_compatible
from services.ordenes_trabajo_schema import (
    TABLE as TABLA_ORDENES_TRABAJO, SELECT_COLUMNS as COLUMNAS_ORDENES_TRABAJO,
    filter_payload, metadata_item, extract_origin,
)

logger = configurar_logger(__name__)
from services.movimientos_service import registrar_movimiento_seguro
from services.search_service import buscar_parcial_supabase


def _detalle_error_supabase(error):
    """Devuelve un mensaje legible sin perder la respuesta real de PostgREST."""
    if isinstance(error, dict):
        return str(error)
    partes = []
    for atributo in ("message", "code", "details", "hint"):
        valor = getattr(error, atributo, None)
        if valor:
            partes.append(f"{atributo}: {valor}")
    return " | ".join(partes) or str(error)


def _columna_inexistente(error):
    """Extrae la columna reportada por PGRST204, cuando sea posible."""
    import re
    texto = _detalle_error_supabase(error)
    patrones = (
        r"Could not find the ['\"]([^'\"]+)['\"] column",
        r"column ['\"]?([a-zA-Z0-9_]+)['\"]? does not exist",
    )
    for patron in patrones:
        coincidencia = re.search(patron, texto, flags=re.IGNORECASE)
        if coincidencia:
            return coincidencia.group(1)
    return ""


def crear_orden_trabajo(datos_orden):
    """Crea una OT, confirma el INSERT y muestra el error real de Supabase.

    El esquema de instalaciones antiguas puede no contener algunas columnas
    opcionales. Si PostgREST reporta PGRST204, se elimina únicamente esa columna
    opcional y se reintenta. Los campos esenciales nunca se descartan.
    """
    datos_orden = asegurar_folio(datos_orden, "ot_folio", "OT")
    datos_orden = normalizar_campos_fecha(filter_payload(datos_orden))
    obligatorias = {"ot_folio", "ot_cliente"}
    omitidas = []

    for _ in range(8):
        try:
            respuesta = (
                supabase.table(TABLA_ORDENES_TRABAJO)
                .insert(datos_orden)
                .execute()
            )
            registros = list(getattr(respuesta, "data", None) or [])

            # Algunas configuraciones de PostgREST ejecutan el INSERT pero no
            # devuelven representación. Confirmamos por folio antes de declarar fallo.
            if not registros:
                confirmacion = (
                    supabase.table(TABLA_ORDENES_TRABAJO)
                    .select(COLUMNAS_ORDENES_TRABAJO)
                    .eq("ot_folio", datos_orden.get("ot_folio"))
                    .limit(1)
                    .execute()
                )
                registros = list(getattr(confirmacion, "data", None) or [])

            if not registros:
                raise RuntimeError(
                    "Supabase ejecutó la solicitud, pero no fue posible confirmar "
                    f"el registro con folio {datos_orden.get('ot_folio')}."
                )

            registrar_movimiento_seguro(
                modulo="ORDENES_TRABAJO",
                accion="CREAR",
                descripcion=("Creación de orden de trabajo" +
                             (f"; columnas opcionales omitidas: {', '.join(omitidas)}" if omitidas else "")),
                registro_afectado=datos_orden.get("ot_folio"),
            )
            return registros

        except Exception as error:
            columna = _columna_inexistente(error)
            if columna and columna in datos_orden and columna not in obligatorias:
                omitidas.append(columna)
                datos_orden.pop(columna, None)
                logger.warning(
                    "La columna opcional %s no existe en db_ordenes_trabajo; se reintenta sin ella.",
                    columna,
                )
                continue

            register_error(error, "Registrar orden de trabajo")
            logger.exception("Error al crear orden de trabajo.")
            detalle = _detalle_error_supabase(error)
            raise RuntimeError(
                "Supabase rechazó la creación de la Orden de Trabajo. "
                f"Detalle técnico: {detalle}"
            ) from error

    raise RuntimeError(
        "No fue posible adaptar el registro al esquema de db_ordenes_trabajo. "
        f"Columnas opcionales omitidas: {', '.join(omitidas) or 'ninguna'}."
    )


def obtener_ordenes_trabajo(page=1, page_size=100):
    """
    Consulta todas las órdenes de trabajo registradas.
    """

    try:
        respuesta = execute_select_compatible(
            supabase,
            TABLA_ORDENES_TRABAJO,
            COLUMNAS_ORDENES_TRABAJO,
            lambda query: query
            .order("fecha_registro", desc=True)
            .range(*page_range(page, page_size))
        )

        registrar_movimiento_seguro(
            modulo="ORDENES_TRABAJO",
            accion="CONSULTAR",
            descripcion="Consulta general de órdenes de trabajo",
            registro_afectado=f"Total: {len(respuesta.data or [])}",
        )
        return respuesta.data

    except Exception:
        logger.exception("Error al consultar órdenes de trabajo.")
        return []


def obtener_ordenes_trabajo_por_aco(aco_numero, page=1, page_size=100):
    """
    Consulta órdenes de trabajo asociadas a un ACO.
    """

    try:
        respuesta = execute_select_compatible(
            supabase,
            TABLA_ORDENES_TRABAJO,
            COLUMNAS_ORDENES_TRABAJO,
            lambda query: query
            .eq("ot_aco_numero", aco_numero)
            .order("fecha_registro", desc=True)
            .range(*page_range(page, page_size))
        )

        registrar_movimiento_seguro(
            modulo="ORDENES_TRABAJO",
            accion="BUSCAR_POR_ACO",
            descripcion=f"Consulta de órdenes de trabajo por ACO: {aco_numero}",
            registro_afectado=aco_numero,
        )
        return respuesta.data

    except Exception:
        logger.exception("Error al consultar órdenes de trabajo por ACO.")
        return []


def buscar_orden_trabajo_por_folio(folio):
    """
    Busca una orden de trabajo por folio.
    """

    try:
        respuesta = execute_select_compatible(
            supabase,
            TABLA_ORDENES_TRABAJO,
            COLUMNAS_ORDENES_TRABAJO,
            lambda query: query
            .eq("ot_folio", str(folio).strip().upper())
        )

        if respuesta.data:
            registrar_movimiento_seguro(
                modulo="ORDENES_TRABAJO",
                accion="BUSCAR",
                descripcion=f"Búsqueda de orden de trabajo por folio: {folio}",
                registro_afectado=folio,
            )
            return respuesta.data[0]

        registrar_movimiento_seguro(
            modulo="ORDENES_TRABAJO",
            accion="BUSCAR_SIN_RESULTADO",
            descripcion=f"Búsqueda de orden de trabajo sin resultado: {folio}",
            registro_afectado=folio,
        )
        return None

    except Exception as error:
        logger.exception("Error al buscar orden de trabajo.")
        raise RuntimeError("No fue posible consultar la orden de trabajo en Supabase.") from error


def obtener_estadisticas_ordenes_trabajo(page=1, page_size=100):
    """
    Estadísticas simples para reportes administrativos.
    """

    try:
        ordenes = obtener_ordenes_trabajo()
        total = len(ordenes)
        pendientes = len([o for o in ordenes if o.get("ot_estatus") == 1])
        proceso = len([o for o in ordenes if o.get("ot_estatus") == 2])
        finalizadas = len([o for o in ordenes if o.get("ot_estatus") == 3])
        return total, pendientes, proceso, finalizadas

    except Exception:
        logger.exception("Error al obtener estadísticas de órdenes de trabajo.")
        return 0, 0, 0, 0


# Búsqueda parcial unificada
def buscar_ordenes_trabajo(termino, limite=100):
    resultados = buscar_parcial_supabase(
        supabase=supabase, tabla=TABLA_ORDENES_TRABAJO, columnas=COLUMNAS_ORDENES_TRABAJO, termino=termino,
        campos=('ot_folio', 'ot_aco_numero', 'ot_cliente', 'ot_sucursal', 'ot_esi', 'ot_supervisor', 'ot_estatus', 'ot_asunto', 'ot_descripcion'), id_campos=('ot_id', 'ot_folio'), orden='fecha_registro', limite=limite,
    )
    registrar_movimiento_seguro(
        modulo='ORDENES_TRABAJO', accion="BUSCAR",
        descripcion=f"Búsqueda parcial: {str(termino).strip().upper()}",
        registro_afectado=f"Coincidencias: {len(resultados)}",
    )
    return resultados


def buscar_orden_trabajo_por_orden_servicio(folio_os):
    """Comprueba si una OS ya fue convertida sin depender de columnas opcionales.

    La relación se conserva como metadato interno dentro de ``ot_partidas_json``;
    así funciona con el esquema real existente sin requerir una migración.
    """
    folio = str(folio_os or "").strip().upper()
    if not folio:
        return None
    try:
        respuesta = execute_select_compatible(
            supabase, TABLA_ORDENES_TRABAJO,
            "ot_id,ot_folio,ot_partidas_json,fecha_registro",
            lambda query: query.order("fecha_registro", desc=True).limit(1000),
        )
        for record in respuesta.data or []:
            if extract_origin(record.get("ot_partidas_json")) == folio:
                return record
        return None
    except Exception as error:
        logger.exception("Error al comprobar conversión previa de OS %s", folio)
        detalle = getattr(error, "message", None) or str(error)
        raise RuntimeError(
            "No fue posible comprobar si la orden de servicio ya tiene una orden de trabajo. "
            f"Detalle técnico: {detalle}"
        ) from error

def convertir_orden_servicio_a_trabajo(orden_original, cambios, usuario_activo=None):
    """Transforma una Orden de Servicio en Orden de Trabajo y conserva trazabilidad."""
    original = dict(orden_original or {})
    editados = dict(cambios or {})
    folio_os = str(original.get("os_folio") or editados.get("os_folio") or "").strip().upper()
    if not folio_os:
        raise ValueError("La orden de servicio seleccionada no tiene folio válido.")
    existente = buscar_orden_trabajo_por_orden_servicio(folio_os)
    if existente:
        raise ValueError(f"La orden {folio_os} ya fue convertida en {existente.get('ot_folio', 'una OT')}.")

    def valor(campo, default=""):
        dato = editados.get(campo, original.get(campo, default))
        return dato if dato not in (None, "") else default

    cliente = str(valor("os_cliente")).strip()
    asunto = str(valor("os_descripcion")).strip()
    if not cliente or not asunto:
        raise ValueError("La Orden de Trabajo requiere cliente y asunto/descripcion.")

    usuario = str((usuario_activo or {}).get("usu_nickname") or (usuario_activo or {}).get("usuario") or "Administrativo")
    partidas = editados.get("ot_partidas_json")
    if not partidas:
        materiales = str(valor("os_materiales")).strip()
        partidas = [{
            "partida": "1", "unidad": "Servicio", "cantidad": "1",
            "modelo": "", "marca": "", "concepto": asunto,
        }]
        if materiales:
            partidas.append({
                "partida": "2", "unidad": "Lote", "cantidad": "1",
                "modelo": "", "marca": "", "concepto": materiales,
            })
    import json
    if isinstance(partidas, str):
        try:
            partidas_lista = json.loads(partidas)
        except Exception as error:
            raise ValueError("Las partidas de la Orden de Trabajo no contienen JSON válido.") from error
    else:
        partidas_lista = list(partidas or [])
    partidas_lista = [item for item in partidas_lista if not (isinstance(item, dict) and "_axia_meta" in item)]
    partidas_lista.append(metadata_item(folio_os))
    partidas = partidas_lista

    payload = {
        "ot_aco_numero": valor("os_aco_numero"),
        "ot_asunto": editados.get("ot_asunto") or asunto,
        "ot_cliente": cliente,
        "ot_contacto": valor("os_contacto") or valor("os_encargado"),
        "ot_descripcion": editados.get("ot_descripcion") or asunto,
        "ot_esi": editados.get("ot_esi") or valor("os_tecnico") or valor("os_tecnicos"),
        "ot_estatus": 1,
        "ot_fecha": editados.get("ot_fecha_programada") or editados.get("ot_fecha") or valor("os_fecha_programada") or valor("os_fecha"),
        "ot_jefe_operacion": editados.get("ot_jefe_operacion") or valor("os_encargado_servicio"),
        "ot_numero_dias": editados.get("ot_numero_dias") or "1",
        "ot_numero_personas": editados.get("ot_numero_personas") or "1",
        "ot_partidas_json": partidas,
        "ot_prioridad": int(valor("os_prioridad", 2) or 2),
        "ot_sucursal": valor("os_sucursal") or valor("os_ubicacion"),
        "ot_supervisor": valor("os_supervisor"),
        "creado_por": usuario,
    }
    payload = filter_payload({k: v for k, v in payload.items() if v not in (None, "")})
    resultado = crear_orden_trabajo(payload)
    if not resultado:
        raise RuntimeError("Supabase no confirmó la creación de la Orden de Trabajo.")

    # La OS queda marcada como convertida/en proceso. El UPDATE es mínimo.
    try:
        supabase.table("db_ordenes_servicio").update({"os_estatus": 2, "actualizado_por": usuario}).eq("os_folio", folio_os).execute()
    except Exception:
        logger.exception("La OT fue creada, pero no se pudo actualizar el estatus de la OS %s", folio_os)

    registrar_movimiento_seguro(
        modulo="ORDENES_TRABAJO", accion="CONVERTIR_ORDEN_SERVICIO",
        descripcion=f"Conversión {folio_os} a orden de trabajo",
        registro_afectado=(resultado[0].get("ot_folio") if resultado else folio_os),
    )
    return resultado
