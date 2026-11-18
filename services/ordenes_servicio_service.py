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
    "ot_id,os_folio_ot,os_folio_bitacora,"
    "os_solicitante,os_celular,os_hora_llegada,os_hora_salida,"
    "os_tipos_servicio_json,os_tipo_servicio,os_encargado_servicio,"
    "os_tecnicos,os_equipos_json,os_eval_trato,os_eval_habilidades,"
    "os_eval_velocidad,os_eval_otro,os_firma_cliente,os_fotos,id_sucursal,id_contacto,"
    "os_firmante_nombre,os_firmante_puesto,os_porcentaje_avance"
)


# =====================================================
# FUNCIÓN: crear_orden_servicio()
# =====================================================
def crear_orden_servicio(datos_orden):
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
        campos=('os_folio', 'os_folio_ot', 'os_folio_bitacora', 'os_aco_numero', 'os_cliente', 'os_sucursal', 'os_tecnico', 'os_supervisor', 'os_estatus', 'os_tipo_servicio', 'os_descripcion'), id_campos=('id_orden', 'os_folio'), orden='fecha_registro', limite=limite,
    )
    registrar_movimiento_seguro(
        modulo='ORDENES_SERVICIO', accion="BUSCAR",
        descripcion=f"Búsqueda parcial: {str(termino).strip().upper()}",
        registro_afectado=f"Coincidencias: {len(resultados)}",
    )
    return resultados




def obtener_contextos_aco_disponibles_cierre(limite=1000):
    try:
        ots_resp = execute_select_compatible(
            supabase, "db_ordenes_trabajo",
            "ot_id,ot_folio,ot_folio_levantamiento,ot_aco_numero,ot_estatus,ot_cliente,ot_contacto,ot_sucursal,ot_supervisor,ot_esi,ot_asunto,ot_descripcion,fecha_registro",
            lambda q: q.order("fecha_registro", desc=True).limit(limite),
        )
        os_resp = execute_select_compatible(
            supabase, TABLA_ORDENES, COLUMNAS_ORDENES,
            lambda q: q.order("fecha_registro", desc=True).limit(max(limite * 2, 1000)),
        )
        os_por_ot = {}
        for os in os_resp.data or []:
            key = str(os.get("os_folio_ot") or "").strip().upper()
            if key and key not in os_por_ot:
                os_por_ot[key] = os

        salida, vistos = [], set()
        for ot in ots_resp.data or []:
            aco = str(ot.get("ot_aco_numero") or "").strip().upper()
            folio_ot = str(ot.get("ot_folio") or "").strip().upper()
            if not aco or not folio_ot or aco in vistos:
                continue
            try:
                estatus_ot = int(ot.get("ot_estatus") or 0)
            except (TypeError, ValueError):
                estatus_ot = 0
            if estatus_ot == 3:
                continue
            os_existente = os_por_ot.get(folio_ot) or {}
            try:
                estatus_os = int(os_existente.get("os_estatus") or 0)
            except (TypeError, ValueError):
                estatus_os = 0
            if estatus_os == 3:
                continue
            vistos.add(aco)
            salida.append({
                "aco_numero": aco, "ot_id": ot.get("ot_id"), "ot_folio": folio_ot,
                "ot_folio_levantamiento": str(ot.get("ot_folio_levantamiento") or "").strip().upper(),
                "cliente": ot.get("ot_cliente") or "", "ot": ot, "os": os_existente,
            })
        salida.sort(key=lambda x: x["aco_numero"])
        return salida
    except Exception:
        logger.exception("Error al obtener ACOs disponibles para cierre de Orden de Servicio.")
        return []


def buscar_orden_por_levantamiento(folio_levantamiento=None, id_levantamiento=None):
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

        registro = consultar_por(campo, valor)
        if registro and int(registro.get("lev_estatus") or 0) == int(datos.get("lev_estatus") or 0):
            return [registro]

    raise RuntimeError(
        "Supabase no actualizó ningún levantamiento con el ID o folio seleccionado. "
        "Verifica que el registro exista y que la política RLS permita UPDATE en db_levantamientos."
    )

def _resolver_contacto_conversion(levantamiento, correo_actual, telefono_actual):
    correo = str(correo_actual or "").strip()
    telefono = str(telefono_actual or "").strip()
    recuperado = False
    fuentes = []

    if correo and telefono:
        return correo, telefono, False, "LEV"

    aco = None
    try:
        from services.acos_service import buscar_aco_por_numero, buscar_aco_por_id

        aco_numero = str(
            levantamiento.get("lev_aco_numero")
            or levantamiento.get("aco_numero")
            or ""
        ).strip()
        id_aco = levantamiento.get("id_aco")

        if aco_numero:
            aco = buscar_aco_por_numero(aco_numero)
        if not aco and id_aco not in (None, ""):
            aco = buscar_aco_por_id(id_aco)

        if aco:
            if not correo:
                correo_aco = str(aco.get("aco_correo") or "").strip()
                if correo_aco:
                    correo = correo_aco
                    recuperado = True
                    fuentes.append("ACO")
            if not telefono:
                telefono_aco = str(aco.get("aco_telefono") or "").strip()
                if telefono_aco:
                    telefono = telefono_aco
                    recuperado = True
                    fuentes.append("ACO")
    except Exception:
        logger.exception(
            "No fue posible recuperar datos de contacto del ACO al convertir el LEV %s.",
            levantamiento.get("lev_folio"),
        )

    if not correo or not telefono:
        id_cliente = levantamiento.get("id_cliente") or (aco or {}).get("id_cliente")
        if id_cliente not in (None, ""):
            try:
                respuesta_cliente = (
                    supabase.table("db_clientes")
                    .select("cli_correo,cli_telefono")
                    .eq("id_cliente", id_cliente)
                    .limit(1)
                    .execute()
                )
                cliente = (getattr(respuesta_cliente, "data", None) or [None])[0] or {}
                if not correo:
                    correo_cliente = str(cliente.get("cli_correo") or "").strip()
                    if correo_cliente:
                        correo = correo_cliente
                        recuperado = True
                        fuentes.append("CLIENTE")
                if not telefono:
                    telefono_cliente = str(cliente.get("cli_telefono") or "").strip()
                    if telefono_cliente:
                        telefono = telefono_cliente
                        recuperado = True
                        fuentes.append("CLIENTE")
            except Exception:
                logger.exception(
                    "No fue posible recuperar datos de contacto del cliente %s para el LEV %s.",
                    id_cliente,
                    levantamiento.get("lev_folio"),
                )

    if not fuentes:
        fuente = "LEV" if (correo or telefono) else "SIN_DATOS"
    else:
        fuente = " + ".join(dict.fromkeys(fuentes))
    return correo, telefono, recuperado, fuente


def convertir_levantamiento_a_orden(levantamiento_original, cambios, usuario_activo=None):
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

    correo_levantamiento = str(valor("lev_correo", default="")).strip()
    telefono_levantamiento = str(valor("lev_telefono", default="")).strip()
    correo_resuelto, telefono_resuelto, contacto_recuperado, fuente_contacto = _resolver_contacto_conversion(
        original, correo_levantamiento, telefono_levantamiento
    )
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
        "os_telefono": telefono_resuelto,
        "os_correo": correo_resuelto,
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
        "os_domicilio": valor("lev_direccion"),
        "os_encargado": valor("lev_contacto"),
        "os_solicitante": usuario,
        "os_celular": telefono_resuelto,
        "os_tipos_servicio_json": _texto_json([tipo_compuesto]),
        "os_tipo_servicio": tipo_compuesto,
        "os_encargado_servicio": valor("lev_contacto"),
        "os_tecnicos": valor("lev_tecnico"),
        "os_equipos_json": _texto_json(equipos) if equipos else None,
    }
    datos_os = {k: v for k, v in datos_os.items() if v not in (None, "")}

    resultado_os = _crear_orden_estricta(datos_os)
    orden_creada = resultado_os[0]

    campos_lev = filtrar_payload_levantamiento(
        editados,
        campos_permitidos=CAMPOS_CONVERSION_EDITABLES,
    )

    if contacto_recuperado:
        if not correo_levantamiento and correo_resuelto:
            campos_lev["lev_correo"] = correo_resuelto
        if not telefono_levantamiento and telefono_resuelto:
            campos_lev["lev_telefono"] = telefono_resuelto
        logger.info(
            "Datos de contacto recuperados para %s desde %s: correo=%s teléfono=%s",
            folio_lev,
            fuente_contacto,
            bool(correo_resuelto),
            bool(telefono_resuelto),
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



# =====================================================
# FLUJO VIGENTE: ORDEN DE TRABAJO -> ORDEN DE SERVICIO
# =====================================================
def buscar_orden_servicio_por_ot(folio_ot=None, ot_id=None):
    folio = str(folio_ot or "").strip().upper()
    try:
        if ot_id not in (None, ""):
            resp = execute_select_compatible(
                supabase, TABLA_ORDENES, COLUMNAS_ORDENES,
                lambda q: q.eq("ot_id", ot_id).limit(1),
            )
            if resp.data:
                return resp.data[0]
        if folio:
            resp = execute_select_compatible(
                supabase, TABLA_ORDENES, COLUMNAS_ORDENES,
                lambda q: q.eq("os_folio_ot", folio).limit(1),
            )
            if resp.data:
                return resp.data[0]
        return None
    except Exception as error:
        logger.exception("No fue posible comprobar OS previa de la OT %s", folio)
        raise RuntimeError("No fue posible comprobar si la Orden de Trabajo ya tiene una Orden de Servicio.") from error


def _numero_porcentaje(valor, nombre="Porcentaje"):
    from decimal import Decimal, InvalidOperation
    try:
        num = Decimal(str(valor).strip())
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{nombre}: ingresa un número válido entre 0 y 100.")
    if not num.is_finite() or num < 0 or num > 100 or num.as_tuple().exponent < -2:
        raise ValueError(f"{nombre}: debe estar entre 0 y 100 con máximo dos decimales.")
    return num


def avance_comprobado_para_cierre_os(orden_servicio):
    from decimal import Decimal
    os = dict(orden_servicio or {})
    ot_id = os.get("ot_id")
    folio_ot = str(os.get("os_folio_ot") or "").strip().upper()
    if ot_id in (None, "") and not folio_ot:
        raise ValueError("Selecciona la Orden de Trabajo correspondiente.")
    if ot_id not in (None, ""):
        respuesta_ot = supabase.table("db_ordenes_trabajo").select("ot_id,ot_folio,ot_estatus").eq("ot_id", ot_id).limit(1).execute()
    else:
        respuesta_ot = supabase.table("db_ordenes_trabajo").select("ot_id,ot_folio,ot_estatus").eq("ot_folio", folio_ot).limit(1).execute()
    ots = list(getattr(respuesta_ot, "data", None) or [])
    if not ots:
        raise ValueError("No se encontró la OT asociada.")
    ot = ots[0]
    folio_real = str(ot.get("ot_folio") or "").strip().upper()
    if not folio_real or (folio_ot and folio_real != folio_ot):
        raise ValueError("El folio de la OT no coincide con el servicio.")
    if int(ot.get("ot_estatus") or 0) == 3:
        raise ValueError("Esta OT ya está finalizada; no se puede crear otra OS.")
    # Se consultan todas las bitácoras vinculadas; no limitar a 100 filas.
    consulta = supabase.table("db_bitacoras").select("id_bitacora,bit_porcentaje_avance").eq("bit_ot_folio", folio_real).execute()
    total = Decimal("0")
    for bit in (getattr(consulta, "data", None) or []):
        total += _numero_porcentaje(bit.get("bit_porcentaje_avance"), "Avance de bitácora")
    if total > 100:
        raise ValueError(f"Las bitácoras de {folio_real} ya superan 100% ({total}%). Corrige el historial antes del cierre.")
    return total


def exigir_avance_cien_para_cierre_os(orden_servicio):
    from decimal import Decimal
    os = dict(orden_servicio or {})
    nombre = str(os.get("os_firmante_nombre") or "").strip()
    puesto = str(os.get("os_firmante_puesto") or "").strip()
    firma = str(os.get("os_firma_cliente") or "").strip()
    if not nombre or not puesto or not firma:
        raise ValueError("La Orden de Servicio requiere Nombre, Puesto y firma del cliente para finalizar.")
    os_pct = _numero_porcentaje(os.get("os_porcentaje_avance"), "Avance final de OS")
    try:
        bit_pct = avance_comprobado_para_cierre_os(os)
    except ValueError:
        raise
    except Exception as exc:
        logger.exception("No se pudo comprobar el avance de la OT.")
        raise ValueError("No se pudo verificar el avance en Supabase. No se generará la Orden de Servicio.") from exc
    total = bit_pct + os_pct
    if total != Decimal("100"):
        raise ValueError(
            f"No se puede generar la OS: bitácoras {bit_pct:g}% + avance final {os_pct:g}% "
            f"= {total:g}%. Se requiere exactamente 100%."
        )
    return total


def _cerrar_ot_por_os_completa(orden_servicio, usuario_activo=None):
    os = dict(orden_servicio or {})
    folio_ot = str(os.get("os_folio_ot") or "").strip().upper()
    ot_id = os.get("ot_id")
    if ot_id in (None, "") and not folio_ot:
        return False
    try:
        exigir_avance_cien_para_cierre_os(os)
    except ValueError as error:
        logger.warning("Cierre automático de OT bloqueado: %s", error)
        return False
    usuario = str((usuario_activo or {}).get("usu_nickname") or (usuario_activo or {}).get("usuario") or "Administrativo")
    try:
        from services.ordenes_trabajo_service import actualizar_orden_trabajo
        resultado = None
        if ot_id not in (None, ""):
            resultado = actualizar_orden_trabajo(ot_id, {"ot_estatus": 3})
        if not resultado and folio_ot:
            resp = supabase.table("db_ordenes_trabajo").update({"ot_estatus": 3}).eq("ot_folio", folio_ot).execute()
            resultado = list(getattr(resp, "data", None) or [])
        if resultado:
            registrar_movimiento_seguro(
                modulo="ORDENES_TRABAJO", accion="CIERRE_AUTOMATICO_OS",
                descripcion=f"OT {folio_ot or ot_id} cerrada automáticamente al completar la Orden de Servicio {os.get('os_folio') or ''}.",
                registro_afectado=folio_ot or ot_id,
            )
            return True
    except Exception:
        logger.exception("No fue posible cerrar automáticamente la OT %s al completar la OS.", folio_ot or ot_id)
    return False


def convertir_orden_trabajo_a_servicio(orden_trabajo, usuario_activo=None):
    raise ValueError(
        "La Orden de Servicio es el cierre definitivo, no un documento en proceso. "
        "Abre el formulario de OS, captura el avance restante y obtén la firma del cliente."
    )


def guardar_os_definitiva(datos, usuario_activo=None, id_orden=None):
    os = dict(datos or {})
    exigir_avance_cien_para_cierre_os(os)
    existente = buscar_orden_servicio_por_ot(os.get("os_folio_ot"), os.get("ot_id"))
    if existente and str(existente.get("id_orden")) != str(id_orden):
        raise ValueError(f"La OT ya tiene una Orden de Servicio ({existente.get('os_folio')}).")
    if id_orden and not existente:
        raise ValueError("No se encontró la OS existente. No se guardarán cambios.")
    os["os_estatus"] = 3
    os["os_porcentaje_avance"] = float(_numero_porcentaje(os.get("os_porcentaje_avance"), "Avance final de OS"))
    if id_orden:
        if int(existente.get("os_estatus") or 0) == 3:
            raise ValueError("La Orden de Servicio ya está finalizada y no se puede modificar desde captura.")
        respuesta = actualizar_orden_servicio(id_orden, os)
    else:
        respuesta = crear_orden_servicio(os)
    if not respuesta:
        raise RuntimeError("Supabase no confirmó el guardado de la Orden de Servicio.")
    registro = respuesta[0] if isinstance(respuesta, list) and respuesta else {}
    nuevo_id = id_orden or registro.get("id_orden")
    try:
        exigir_avance_cien_para_cierre_os(os)
        cerrado = _cerrar_ot_por_os_completa(os, usuario_activo)
        if not cerrado:
            raise RuntimeError("No se pudo confirmar el cierre de la Orden de Trabajo.")
    except Exception as exc:
        if not id_orden and nuevo_id:
            try:
                supabase.table(TABLA_ORDENES).delete().eq("id_orden", nuevo_id).execute()
            except Exception:
                logger.exception("URGENTE: No se pudo compensar la OS %s después del fallo de cierre.", nuevo_id)
        elif id_orden:
            try:
                supabase.table(TABLA_ORDENES).update({"os_estatus": 2}).eq("id_orden", id_orden).execute()
            except Exception:
                logger.exception("URGENTE: No se pudo restaurar la OS previa al fallar el cierre.")
        raise RuntimeError("No se completó el cierre; verifica la OT y la OS antes de reintentar.") from exc
    return respuesta


def finalizar_servicio_desde_os(orden_servicio, usuario_activo=None):
    os = dict(orden_servicio or {})
    folio_os = str(os.get("os_folio") or "").strip().upper()
    folio_ot = str(os.get("os_folio_ot") or "").strip().upper()
    ot_id = os.get("ot_id")
    exigir_avance_cien_para_cierre_os(os)
    usuario = str((usuario_activo or {}).get("usu_nickname") or (usuario_activo or {}).get("usuario") or "Administrativo")
    resultado_ot = None
    if folio_ot or ot_id not in (None, ""):
        from services.ordenes_trabajo_service import actualizar_orden_trabajo
        resultado_ot = actualizar_orden_trabajo(ot_id, {"ot_estatus": 3}) if ot_id not in (None, "") else None
        if not resultado_ot and folio_ot:
            try:
                resp = supabase.table("db_ordenes_trabajo").update({"ot_estatus": 3}).eq("ot_folio", folio_ot).execute()
                resultado_ot = list(getattr(resp, "data", None) or [])
            except Exception as error:
                raise RuntimeError(f"No fue posible finalizar la Orden de Trabajo {folio_ot}.") from error
    else:
        raise ValueError("No se permite cerrar una OS sin una OT de origen verificada.")

    if not resultado_ot:
        raise RuntimeError("Supabase no confirmó el cierre de la OT.")
    payload_os = {"os_estatus": 3, "actualizado_por": usuario}
    try:
        respuesta = supabase.table(TABLA_ORDENES).update(payload_os).eq("id_orden", os.get("id_orden")).execute()
        filas = list(getattr(respuesta, "data", None) or [])
    except Exception as error:
        raise RuntimeError(f"La OT se finalizó, pero no fue posible cerrar la Orden de Servicio {folio_os}.") from error

    registrar_movimiento_seguro(
        modulo="ORDENES_SERVICIO", accion="FINALIZAR_SERVICIO",
        descripcion=f"Finalización de {folio_ot} desde {folio_os}", registro_afectado=folio_os,
    )
    return filas or [dict(os, **payload_os)]