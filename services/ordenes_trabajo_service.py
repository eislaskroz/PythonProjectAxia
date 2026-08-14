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
    filter_payload, metadata_item, extract_origin, partidas_desde_detalle_levantamiento,
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


def actualizar_orden_trabajo(ot_id, datos_orden):
    """Actualiza una Orden de Trabajo existente usando el contrato central."""
    try:
        payload = normalizar_campos_fecha(filter_payload(datos_orden))
        respuesta = (
            supabase.table(TABLA_ORDENES_TRABAJO)
            .update(payload)
            .eq("ot_id", ot_id)
            .execute()
        )
        registrar_movimiento_seguro(
            modulo="ORDENES_TRABAJO", accion="ACTUALIZAR",
            descripcion=f"Actualización de orden de trabajo ID: {ot_id}",
            registro_afectado=ot_id,
        )
        return list(getattr(respuesta, "data", None) or [])
    except Exception as error:
        register_error(error, "Actualizar orden de trabajo")
        logger.exception("Error al actualizar orden de trabajo.")
        return None


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
        campos=('ot_folio', 'ot_folio_levantamiento', 'ot_aco_numero', 'ot_cliente', 'ot_sucursal', 'ot_esi', 'ot_supervisor', 'ot_estatus', 'ot_asunto', 'ot_descripcion'), id_campos=('ot_id', 'ot_folio'), orden='fecha_registro', limite=limite,
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


# =====================================================
# FLUJO VIGENTE: LEVANTAMIENTO -> ORDEN DE TRABAJO
# =====================================================
def buscar_orden_trabajo_por_levantamiento(folio_levantamiento=None, id_levantamiento=None):
    """Devuelve la OT vinculada al levantamiento, si ya existe."""
    folio = str(folio_levantamiento or "").strip().upper()
    try:
        if id_levantamiento not in (None, ""):
            respuesta = execute_select_compatible(
                supabase, TABLA_ORDENES_TRABAJO, COLUMNAS_ORDENES_TRABAJO,
                lambda q: q.eq("id_levantamiento", id_levantamiento).limit(1),
            )
            if respuesta.data:
                return respuesta.data[0]
        if folio:
            respuesta = execute_select_compatible(
                supabase, TABLA_ORDENES_TRABAJO, COLUMNAS_ORDENES_TRABAJO,
                lambda q: q.eq("ot_folio_levantamiento", folio).limit(1),
            )
            if respuesta.data:
                return respuesta.data[0]
            # Compatibilidad con OTs creadas antes de agregar las columnas de relación.
            respuesta = execute_select_compatible(
                supabase, TABLA_ORDENES_TRABAJO, "ot_id,ot_folio,ot_partidas_json,fecha_registro",
                lambda q: q.order("fecha_registro", desc=True).limit(1000),
            )
            for record in respuesta.data or []:
                if extract_origin(record.get("ot_partidas_json"), "lev") == folio:
                    return record
        return None
    except Exception as error:
        logger.exception("Error al comprobar OT previa del levantamiento %s", folio)
        raise RuntimeError("No fue posible comprobar si el levantamiento ya tiene una Orden de Trabajo.") from error


def convertir_levantamiento_a_trabajo(levantamiento_original, cambios, usuario_activo=None):
    """Convierte un levantamiento autorizado en OT y garantiza su ACO.

    Flujo operativo vigente:
        LEVANTAMIENTO -> ACO (automático si falta) -> ORDEN DE TRABAJO

    El ACO nace exactamente al confirmar esta conversión, porque ese clic
    representa la autorización del cliente. Si el levantamiento ya estaba
    ligado a un ACO, se reutiliza y nunca se crea un duplicado.
    """
    original = dict(levantamiento_original or {})
    editados = dict(cambios or {})
    folio_lev = str(original.get("lev_folio") or editados.get("lev_folio") or "").strip().upper()
    id_lev = original.get("id_levantamiento")
    if not folio_lev:
        raise ValueError("El levantamiento seleccionado no tiene folio válido.")
    existente = buscar_orden_trabajo_por_levantamiento(folio_lev, id_lev)
    if existente:
        raise ValueError(f"El levantamiento {folio_lev} ya fue convertido en {existente.get('ot_folio', 'una OT')}.")

    def valor(campo, *alternos, default=""):
        for clave in (campo, *alternos):
            dato = editados.get(clave, original.get(clave))
            if dato not in (None, ""):
                return dato
        return default

    cliente = str(valor("lev_cliente")).strip()
    descripcion = str(valor("lev_descripcion")).strip()
    if not cliente or not descripcion:
        raise ValueError("La Orden de Trabajo requiere cliente y descripción del levantamiento.")

    # -------------------------------------------------
    # 1) GARANTIZAR ACO EN EL MOMENTO DE AUTORIZACIÓN
    # -------------------------------------------------
    from services.acos_service import (
        buscar_aco_por_numero, buscar_aco_por_id, buscar_aco_generado_por_levantamiento,
        crear_aco_desde_levantamiento,
    )

    aco = None
    aco_generado = False
    numero_aco_actual = str(valor("lev_aco_numero") or "").strip().upper()
    id_aco_actual = original.get("id_aco")

    if numero_aco_actual:
        aco = buscar_aco_por_numero(numero_aco_actual)
        if not aco:
            raise ValueError(
                f"El levantamiento indica el ACO {numero_aco_actual}, pero no existe en Supabase. "
                "Corrige la relación antes de convertirlo."
            )
    elif id_aco_actual not in (None, ""):
        aco = buscar_aco_por_id(id_aco_actual)

    if not aco:
        # Defensa ante reintentos después de una falla parcial: si el ACO ya
        # alcanzó a generarse para este LEV, lo recuperamos antes de crear otro.
        aco = buscar_aco_generado_por_levantamiento(folio_lev)

    if not aco:
        datos_para_aco = dict(original)
        datos_para_aco.update(editados)
        aco = crear_aco_desde_levantamiento(datos_para_aco, usuario_activo)
        aco_generado = True

    id_aco = aco.get("id_aco")
    numero_aco = str(aco.get("aco_numero") or "").strip().upper()
    if not id_aco or not numero_aco:
        raise RuntimeError("El ACO asociado no contiene ID y folio válidos.")

    # Persistimos la relación en el LEV antes de crear la OT. Si la OT fallara,
    # el reintento reutiliza este mismo ACO y no genera duplicados.
    from services.levantamientos_service import actualizar_levantamiento
    relacion = actualizar_levantamiento(
        id_lev,
        {"id_aco": id_aco, "lev_aco_numero": numero_aco},
    )
    if not relacion:
        raise RuntimeError(
            f"Se obtuvo el ACO {numero_aco}, pero no fue posible vincularlo al levantamiento {folio_lev}. "
            "La Orden de Trabajo no se creó para evitar perder trazabilidad."
        )

    original["id_aco"] = id_aco
    original["lev_aco_numero"] = numero_aco
    editados["lev_aco_numero"] = numero_aco

    usuario = str((usuario_activo or {}).get("usu_nickname") or (usuario_activo or {}).get("usuario") or "Administrativo")
    requerimientos = str(valor("lev_requerimientos")).strip()
    detalle = valor("lev_detalle_tecnico_json", default={})
    if isinstance(detalle, str):
        try:
            import json
            detalle = json.loads(detalle) if detalle else {}
        except Exception:
            detalle = {}
    # La OT conserva las partidas operativas reales del levantamiento para que
    # su PDF pueda mostrar materiales, equipos y misceláneos en tabla. El texto
    # descriptivo del LEV permanece en ot_asunto/ot_descripcion y no se duplica
    # como una fila gigantesca dentro de la tabla.
    partidas = partidas_desde_detalle_levantamiento(detalle)
    if not partidas:
        partidas = [{
            "partida": "1", "unidad": "Servicio", "cantidad": "1",
            "modelo": "", "marca": "", "concepto": descripcion,
        }]
    partidas.append(metadata_item(folio_lev, "lev"))

    payload = {
        "id_aco": id_aco,
        "id_levantamiento": id_lev,
        "ot_folio_levantamiento": folio_lev,
        "ot_aco_numero": numero_aco,
        "ot_cliente": cliente,
        "ot_contacto": valor("lev_contacto"),
        "ot_sucursal": valor("lev_ubicacion", "lev_direccion"),
        "ot_supervisor": valor("lev_supervisor"),
        "ot_esi": valor("lev_tecnico"),
        "ot_fecha": valor("lev_fecha_programada", "lev_fecha_realizacion", "fecha_registro"),
        "ot_numero_dias": str(valor("lev_dias_trabajo", default="1") or "1"),
        "ot_numero_personas": str(valor("lev_personas_considerar", default="1") or "1"),
        "ot_asunto": descripcion,
        "ot_descripcion": descripcion,
        "ot_partidas_json": partidas,
        "ot_estatus": 1,
        "ot_prioridad": int(valor("lev_prioridad", default=2) or 2),
        "creado_por": usuario,
    }
    payload = filter_payload({k: v for k, v in payload.items() if v not in (None, "")})
    resultado = crear_orden_trabajo(payload)
    if not resultado:
        raise RuntimeError("Supabase no confirmó la creación de la Orden de Trabajo.")

    # El levantamiento pasa a En proceso/conversión completada.
    try:
        actualizar_levantamiento(id_lev, {"lev_estatus": 2})
    except Exception:
        logger.exception("La OT fue creada, pero no se pudo actualizar el levantamiento %s", folio_lev)

    # Metadatos locales para que la UI informe si el ACO nació en esta acción.
    if isinstance(resultado, list) and resultado and isinstance(resultado[0], dict):
        resultado[0]["_axia_aco_numero"] = numero_aco
        resultado[0]["_axia_aco_generado"] = aco_generado

    registrar_movimiento_seguro(
        modulo="ORDENES_TRABAJO", accion="CONVERTIR_LEVANTAMIENTO",
        descripcion=f"Conversión {folio_lev} -> {numero_aco} -> Orden de Trabajo",
        registro_afectado=(resultado[0].get("ot_folio") if resultado else folio_lev),
    )

    # Conserva automáticamente la Orden de Trabajo en su carpeta dedicada:
    # Documents/AXIA/ordenes_trabajo.
    try:
        from services.operational_document_pdf import guardar_pdf_orden_trabajo
        registro_ot = dict(payload)
        if isinstance(resultado, list) and resultado and isinstance(resultado[0], dict):
            registro_ot.update(resultado[0])
        guardar_pdf_orden_trabajo(registro_ot)
    except Exception:
        # El registro en Supabase ya fue confirmado; una incidencia local de PDF
        # no debe revertir ni duplicar la conversión. Queda registrada en log.
        logger.exception("La OT fue creada, pero no se pudo guardar automáticamente su PDF local.")

    return resultado


def buscar_ordenes_trabajo_por_aco(aco_numero):
    """Obtiene OTs de un ACO, priorizando las que siguen abiertas."""
    numero = str(aco_numero or "").strip()
    if not numero:
        return []
    respuesta = execute_select_compatible(
        supabase, TABLA_ORDENES_TRABAJO, COLUMNAS_ORDENES_TRABAJO,
        lambda q: q.eq("ot_aco_numero", numero).order("fecha_registro", desc=True).limit(100),
    )
    return list(respuesta.data or [])
