"""Servicios del módulo comercial de cotizaciones de levantamientos."""
from __future__ import annotations

from datetime import datetime, timezone
import json

from core.logger import configurar_logger
from services.movimientos_service import registrar_movimiento_seguro
from services.ordenes_trabajo_schema import partidas_desde_detalle_levantamiento
from services.levantamientos_schema import TABLA_LEVANTAMIENTOS, COLUMNAS_LEVANTAMIENTOS
from services.cotizaciones_schema import TABLA_COTIZACIONES, COLUMNAS_COTIZACIONES
from services.query_compat import execute_select_compatible
from services.folios_service import solicitar_folio_cotizacion
from services.sucursales_service import obtener_sucursal_por_id
from services.usuarios_service import obtener_usuario_por_id
from supabase_config import supabase

logger = configurar_logger(__name__)

ESTATUS_BORRADOR = "BORRADOR"
ESTATUS_EN_COMPRA = "EN COMPRA X COTIZACIÓN"



def _esta_preautorizado_ventas(registro: dict) -> bool:
    if bool((registro or {}).get("lev_validado_ventas")):
        return True
    return bool(
        str((registro or {}).get("lev_validado_por") or "").strip()
        or str((registro or {}).get("lev_fecha_validacion") or "").strip()
    )


def obtener_levantamientos_para_cotizar(limite: int = 200) -> list[dict]:
    """Devuelve levantamientos preautorizados por Operaciones."""
    limite = max(1, int(limite))
    try:
        respuesta = execute_select_compatible(
            supabase,
            TABLA_LEVANTAMIENTOS,
            COLUMNAS_LEVANTAMIENTOS,
            lambda q: q.eq("lev_validado_ventas", True)
                       .order("lev_fecha_validacion", desc=True)
                       .limit(limite),
        )
        filas = list(respuesta.data or [])
        if filas:
            return filas
        respaldo = execute_select_compatible(
            supabase,
            TABLA_LEVANTAMIENTOS,
            COLUMNAS_LEVANTAMIENTOS,
            lambda q: q.order("fecha_registro", desc=True).limit(max(limite * 3, 300)),
        )
        recuperados = [r for r in list(respaldo.data or []) if _esta_preautorizado_ventas(r)]
        recuperados.sort(
            key=lambda r: str(r.get("lev_fecha_validacion") or r.get("fecha_registro") or ""),
            reverse=True,
        )
        return recuperados[:limite]
    except Exception:
        logger.exception("No fue posible consultar levantamientos preautorizados para cotización.")
        raise


def partidas_cotizables(registro: dict) -> list[dict]:
    """Normaliza materiales/equipos/consumibles del LEV para Ventas."""
    detalle = (registro or {}).get("lev_detalle_tecnico_json")
    rows = partidas_desde_detalle_levantamiento(detalle)
    resultado = []
    for i, item in enumerate(rows, 1):
        row = dict(item)
        row["partida"] = str(item.get("partida") or i)
        row["grupo"] = str(item.get("_grupo") or "Materiales")
        row.pop("_grupo", None)
        resultado.append(row)
    return resultado


def _json_dict(valor) -> dict:
    if isinstance(valor, dict):
        return dict(valor)
    if isinstance(valor, str) and valor.strip():
        try:
            obj = json.loads(valor)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
    return {}


def cargar_cotizacion_legacy(registro: dict) -> dict:
    """Lee el JSON de FIX10-FIX17 para utilizarlo como semilla de captura."""
    return _json_dict((registro or {}).get("lev_cotizacion_json"))


def cargar_cotizacion(registro: dict) -> dict:
    """Carga la cotización formal más reciente de un levantamiento."""
    id_levantamiento = (registro or {}).get("id_levantamiento")
    lev_folio = str((registro or {}).get("lev_folio") or "").strip()
    if not id_levantamiento and not lev_folio:
        return {}
    try:
        query = supabase.table(TABLA_COTIZACIONES).select(COLUMNAS_COTIZACIONES)
        if id_levantamiento:
            query = query.eq("id_levantamiento", id_levantamiento)
        else:
            query = query.eq("lev_folio", lev_folio)
        resp = query.order("fecha_actualizacion", desc=True).limit(1).execute()
        return dict((resp.data or [])[0]) if resp.data else {}
    except Exception as exc:
        # La tabla nueva aún puede no existir antes de ejecutar la migración.
        logger.info("Cotización formal aún no disponible: %s", exc)
        return {}


def datos_generales_cotizacion(registro: dict, usuario_actual: dict | None = None) -> dict:
    """Compone datos generales ya disponibles en AXIA sin recapturarlos."""
    registro = registro or {}
    detalle = _json_dict(registro.get("lev_detalle_tecnico_json"))
    generales = detalle.get("datos_generales_axia") if isinstance(detalle.get("datos_generales_axia"), dict) else {}
    recursos = detalle.get("recursos_proyectados") if isinstance(detalle.get("recursos_proyectados"), dict) else {}

    sucursal = obtener_sucursal_por_id(registro.get("id_sucursal")) or {}
    sucursal_nombre = str(sucursal.get("suc_nombre") or registro.get("lev_ubicacion") or "").strip()

    usuario_actual = usuario_actual or {}
    vendedor = obtener_usuario_por_id(usuario_actual.get("id_usuario")) or {}
    nombre_vendedor = " ".join(filter(None, [
        str(vendedor.get("usu_nombre") or usuario_actual.get("nombre") or "").strip(),
        str(vendedor.get("usu_apellido") or usuario_actual.get("apellido") or "").strip(),
    ])).strip() or str(usuario_actual.get("usuario") or "").strip()

    especialidad = str(detalle.get("tipo_levantamiento") or "").strip()
    tipo = especialidad or str(registro.get("lev_tipo") or "").strip()
    modalidad = str(registro.get("lev_modalidad_operativa") or "").strip()
    asunto = " / ".join(filter(None, [tipo, modalidad]))

    return {
        "cot_folio": "SE ASIGNA AL GUARDAR",
        "cot_fecha": datetime.now().strftime("%d/%m/%Y"),
        "lev_folio": str(registro.get("lev_folio") or "").strip(),
        "id_levantamiento": registro.get("id_levantamiento"),
        "id_cliente": registro.get("id_cliente"),
        "cot_cliente": str(registro.get("lev_cliente") or "").strip(),
        "id_sucursal": registro.get("id_sucursal"),
        "cot_sucursal": sucursal_nombre,
        "cot_contacto": str(registro.get("lev_contacto") or "").strip(),
        "cot_asunto": asunto,
        "cot_esi": nombre_vendedor,
        "cot_esi_correo": str(vendedor.get("usu_correo") or "").strip(),
        "cot_esi_telefono": str(vendedor.get("usu_telefono") or "").strip(),
        "cot_jefe_operaciones": str(generales.get("encargado_proyecto") or "").strip(),
        "cot_supervisor": str(registro.get("lev_supervisor") or generales.get("supervisor") or "").strip(),
        "cot_dias": str(registro.get("lev_dias_trabajo") or recursos.get("dias_trabajo") or "").strip(),
        "cot_personas": str(registro.get("lev_personas_considerar") or recursos.get("personas_considerar") or "").strip(),
        "cot_plan_pagos": "",
        "cot_vigencia": "",
        "cot_descuento_pct": 0,
        "cot_iva_pct": 16,
    }


def construir_partidas_comerciales(registro: dict, cotizacion: dict | None = None) -> list[dict]:
    """Genera partidas editables a partir del levantamiento y conserva valores ya guardados."""
    base = partidas_cotizables(registro)
    cotizacion = cotizacion or {}
    guardadas = cotizacion.get("cot_partidas_json") or []
    if isinstance(guardadas, str):
        try:
            guardadas = json.loads(guardadas)
        except Exception:
            guardadas = []
    if isinstance(guardadas, list) and guardadas:
        return [dict(x) for x in guardadas if isinstance(x, dict)]

    legacy = cargar_cotizacion_legacy(registro)
    leg_parts = legacy.get("partidas") if isinstance(legacy.get("partidas"), list) else []
    legacy_map = {
        (str(x.get("partida") or ""), str(x.get("concepto") or "").strip().casefold()): x
        for x in leg_parts if isinstance(x, dict)
    }

    result = []
    for i, item in enumerate(base, 1):
        previa = legacy_map.get((str(item.get("partida") or i), str(item.get("concepto") or "").strip().casefold()), {})
        cantidad = str(item.get("cantidad") or "1").strip() or "1"
        unidad = str(item.get("unidad") or item.get("grupo") or "Pieza(s)").strip()
        result.append({
            "lote": str(i),
            "unidad_tipo": unidad,
            "cantidad": cantidad,
            "proveedor": "",
            "modelo": str(item.get("modelo") or "").strip(),
            "sku": "",
            "marca": str(item.get("marca") or "").strip(),
            "concepto": str(item.get("concepto") or "").strip(),
            "precio_lista": 0,
            "costo": 0,
            "utilidad_pct": 0,
            "precio_venta": 0,
            "precio_unitario": float(previa.get("precio_unitario") or 0) if isinstance(previa, dict) else 0,
            "importe": float(previa.get("costo_total") or 0) if isinstance(previa, dict) else 0,
            "observaciones": "",
        })

    servicio = legacy.get("servicio") if isinstance(legacy.get("servicio"), dict) else {}
    concepto_servicio = str(servicio.get("concepto") or "").strip()
    if not concepto_servicio:
        detalle = _json_dict(registro.get("lev_detalle_tecnico_json"))
        base_serv = str(detalle.get("tipo_levantamiento") or registro.get("lev_tipo") or "levantamiento").strip()
        concepto_servicio = f"Servicio de {base_serv}"
    result.append({
        "lote": str(len(result) + 1), "unidad_tipo": "Servicio", "cantidad": "1",
        "proveedor": "AXIA", "modelo": "", "sku": "", "marca": "AXIA",
        "concepto": concepto_servicio, "precio_lista": 0,
        "costo": float(servicio.get("costo_total") or 0) if servicio else 0,
        "utilidad_pct": 0, "precio_venta": 0,
        "precio_unitario": float(servicio.get("costo_total") or 0) if servicio else 0,
        "importe": float(servicio.get("costo_total") or 0) if servicio else 0,
        "observaciones": "",
    })
    return result


def _numero(value, campo: str, *, minimo: float = 0.0) -> float:
    try:
        n = round(float(str(value).replace(",", "").strip() or 0), 2)
    except (TypeError, ValueError):
        raise ValueError(f"{campo} debe ser numérico.")
    if n < minimo:
        raise ValueError(f"{campo} no puede ser menor a {minimo}.")
    return n


def guardar_cotizacion_comercial(datos: dict, partidas: list[dict], usuario: str) -> dict:
    """Inserta o actualiza una cotización formal en ``db_cotizaciones``."""
    datos = dict(datos or {})
    if not datos.get("id_levantamiento") or not str(datos.get("lev_folio") or "").strip():
        raise ValueError("La cotización debe estar ligada a un levantamiento.")

    requeridos = {
        "cot_cliente": "Cliente", "cot_contacto": "Contacto", "cot_sucursal": "Sucursal",
        "cot_asunto": "Asunto", "cot_esi": "ESI / Ejecutiva de Ventas",
        "cot_esi_correo": "Correo ESI", "cot_esi_telefono": "Teléfono ESI",
        "cot_jefe_operaciones": "Jefe de Operaciones", "cot_supervisor": "Supervisor",
        "cot_dias": "Días", "cot_personas": "Personas", "cot_plan_pagos": "Plan de Pagos",
        "cot_vigencia": "Vigencia de Cotización",
    }
    for key, etiqueta in requeridos.items():
        valor = str(datos.get(key) or "").strip()
        if not valor or valor in {"*", "-"}:
            raise ValueError(f"Falta completar correctamente: {etiqueta}.")
    correo = str(datos.get("cot_esi_correo") or "").strip()
    if "@" not in correo or "." not in correo.rsplit("@", 1)[-1]:
        raise ValueError("El Correo ESI no tiene un formato válido.")
    if not partidas:
        raise ValueError("La cotización no contiene partidas comerciales.")

    limpias = []
    subtotal = 0.0
    for i, item in enumerate(partidas or [], 1):
        for key, etiqueta in (("unidad_tipo", "Unidad / Tipo"), ("concepto", "Concepto"),
                              ("proveedor", "Proveedor"), ("modelo", "Modelo"),
                              ("sku", "SKU"), ("marca", "Marca")):
            if not str(item.get(key) or "").strip():
                raise ValueError(f"Lote {i}: falta {etiqueta}. Usa N/A cuando no aplique.")
        cantidad_txt = str(item.get("cantidad") or "").strip()
        try:
            cantidad_num = float(cantidad_txt.replace(",", ""))
        except ValueError:
            raise ValueError(f"Cantidad, lote {i}, debe ser numérica.")
        if cantidad_num <= 0:
            raise ValueError(f"Cantidad, lote {i}, debe ser mayor que cero.")
        precio_lista = _numero(item.get("precio_lista"), f"Precio de lista, lote {i}", minimo=0.01)
        utilidad = _numero(item.get("utilidad_pct"), f"Utilidad, lote {i}")

        # FIX25: los importes derivados se recalculan también en servicio para no
        # confiar en valores manipulados desde la interfaz o integraciones futuras.
        costo = round(precio_lista * utilidad / 100.0, 2)
        precio_venta = round(precio_lista + costo, 2)
        precio_unitario = precio_venta
        importe = round(precio_unitario * max(cantidad_num, 0.0), 2)
        subtotal += importe
        limpias.append({
            "lote": str(item.get("lote") or i),
            "unidad_tipo": str(item.get("unidad_tipo") or "").strip(),
            "cantidad": cantidad_txt,
            "proveedor": str(item.get("proveedor") or "").strip(),
            "modelo": str(item.get("modelo") or "").strip(),
            "sku": str(item.get("sku") or "").strip(),
            "marca": str(item.get("marca") or "").strip(),
            "concepto": str(item.get("concepto") or "").strip(),
            "precio_lista": precio_lista,
            "costo": costo,
            "utilidad_pct": utilidad,
            "precio_venta": precio_venta,
            "precio_unitario": precio_unitario,
            "importe": importe,
            "observaciones": str(item.get("observaciones") or "").strip(),
        })

    descuento_pct = _numero(datos.get("cot_descuento_pct"), "Descuento")
    iva_pct = _numero(datos.get("cot_iva_pct"), "IVA")
    descuento = round(subtotal * descuento_pct / 100.0, 2)
    subtotal_desc = round(subtotal - descuento, 2)
    iva = round(subtotal_desc * iva_pct / 100.0, 2)
    total = round(subtotal_desc + iva, 2)

    cot_id = datos.get("id_cotizacion")
    folio = str(datos.get("cot_folio") or "").strip().upper()
    if not cot_id and (not folio or folio == "SE ASIGNA AL GUARDAR"):
        folio = solicitar_folio_cotizacion()

    fecha_ui = str(datos.get("cot_fecha") or "").strip()
    if "/" in fecha_ui:
        try:
            fecha_db = datetime.strptime(fecha_ui, "%d/%m/%Y").date().isoformat()
        except ValueError:
            raise ValueError("Fecha de cotización inválida. Usa DD/MM/AAAA.")
    else:
        fecha_db = fecha_ui or datetime.now().date().isoformat()

    payload = {
        "cot_folio": folio,
        "id_levantamiento": datos.get("id_levantamiento"),
        "lev_folio": str(datos.get("lev_folio") or "").strip(),
        "id_cliente": datos.get("id_cliente"),
        "cot_cliente": str(datos.get("cot_cliente") or "").strip(),
        "id_sucursal": datos.get("id_sucursal"),
        "cot_sucursal": str(datos.get("cot_sucursal") or "").strip(),
        "cot_contacto": str(datos.get("cot_contacto") or "").strip(),
        "cot_asunto": str(datos.get("cot_asunto") or "").strip(),
        "cot_fecha": fecha_db,
        "cot_esi": str(datos.get("cot_esi") or "").strip(),
        "cot_esi_correo": str(datos.get("cot_esi_correo") or "").strip(),
        "cot_esi_telefono": str(datos.get("cot_esi_telefono") or "").strip(),
        "cot_jefe_operaciones": str(datos.get("cot_jefe_operaciones") or "").strip(),
        "cot_supervisor": str(datos.get("cot_supervisor") or "").strip(),
        "cot_dias": str(datos.get("cot_dias") or "").strip(),
        "cot_personas": str(datos.get("cot_personas") or "").strip(),
        "cot_plan_pagos": str(datos.get("cot_plan_pagos") or "").strip(),
        "cot_vigencia": str(datos.get("cot_vigencia") or "").strip(),
        "cot_descuento_pct": descuento_pct,
        "cot_iva_pct": iva_pct,
        "cot_partidas_json": limpias,
        "cot_subtotal": round(subtotal, 2),
        "cot_descuento": descuento,
        "cot_subtotal_descuento": subtotal_desc,
        "cot_iva": iva,
        "cot_total": total,
        "cot_estatus": str(datos.get("cot_estatus") or "BORRADOR").strip().upper(),
        "actualizado_por": str(usuario or "").strip(),
        "fecha_actualizacion": datetime.now(timezone.utc).isoformat(),
    }

    if cot_id:
        resp = supabase.table(TABLA_COTIZACIONES).update(payload).eq("id_cotizacion", cot_id).execute()
        accion = "ACTUALIZAR_COTIZACION"
    else:
        payload["creado_por"] = str(usuario or "").strip()
        resp = supabase.table(TABLA_COTIZACIONES).insert(payload).execute()
        accion = "CREAR_COTIZACION"
    guardada = dict((resp.data or [payload])[0])
    registrar_movimiento_seguro(
        modulo="COTIZACIONES",
        accion=accion,
        descripcion=f"Cotización {folio} ligada a {payload['lev_folio']} por ${total:,.2f} MXN.",
        registro_afectado=folio,
    )
    return guardada


def obtener_cotizaciones_en_compra(limite: int = 200) -> list[dict]:
    """Bandeja preparada para el futuro módulo de Compras.

    No genera una Orden de Trabajo: únicamente devuelve cotizaciones que
    Ventas ya finalizó y entregó al siguiente tramo comercial.
    """
    limite = max(1, int(limite))
    resp = (
        supabase.table(TABLA_COTIZACIONES)
        .select(COLUMNAS_COTIZACIONES)
        .eq("cot_estatus", ESTATUS_EN_COMPRA)
        .order("cot_fecha_finalizacion", desc=True)
        .limit(limite)
        .execute()
    )
    return [dict(x) for x in (resp.data or [])]


def finalizar_cotizacion_para_compras(cotizacion: dict, usuario: str) -> dict:
    """Finaliza una COT y la deja disponible para Compras, sin crear OT."""
    cotizacion = dict(cotizacion or {})
    cot_id = cotizacion.get("id_cotizacion")
    folio = str(cotizacion.get("cot_folio") or "").strip().upper()
    if not cot_id or not folio:
        raise ValueError("Primero debes guardar la cotización antes de finalizarla.")

    estatus_actual = str(cotizacion.get("cot_estatus") or ESTATUS_BORRADOR).strip().upper()
    if estatus_actual == ESTATUS_EN_COMPRA:
        return cotizacion
    if estatus_actual != ESTATUS_BORRADOR:
        raise ValueError(f"La cotización {folio} no puede finalizarse desde el estado {estatus_actual}.")

    ahora = datetime.now(timezone.utc).isoformat()
    payload = {
        "cot_estatus": ESTATUS_EN_COMPRA,
        "cot_finalizado_por": str(usuario or "").strip(),
        "cot_fecha_finalizacion": ahora,
        "actualizado_por": str(usuario or "").strip(),
        "fecha_actualizacion": ahora,
    }
    resp = (
        supabase.table(TABLA_COTIZACIONES)
        .update(payload)
        .eq("id_cotizacion", cot_id)
        .eq("cot_folio", folio)
        .execute()
    )
    guardada = dict((resp.data or [dict(cotizacion, **payload)])[0])
    registrar_movimiento_seguro(
        modulo="COTIZACIONES",
        accion="FINALIZAR_COTIZACION_COMPRAS",
        descripcion=(
            f"Cotización {folio} finalizada por Ventas y enviada a Compras. "
            "No se generó Orden de Trabajo."
        ),
        registro_afectado=folio,
    )
    return guardada


# Compatibilidad temporal con llamadas de FIX10-FIX17.
def guardar_cotizacion_levantamiento(registro: dict, partidas: list[dict], usuario: str, servicio: dict | None = None) -> dict:
    datos = datos_generales_cotizacion(registro, {})
    comerciales = []
    for item in partidas or []:
        comerciales.append({
            "lote": item.get("partida"), "unidad_tipo": item.get("unidad"), "cantidad": item.get("cantidad"),
            "proveedor": "", "modelo": item.get("modelo"), "sku": "", "marca": item.get("marca"),
            "concepto": item.get("concepto"), "precio_lista": 0, "costo": item.get("costo_total") or 0,
            "utilidad_pct": 0, "precio_venta": item.get("precio_unitario") or 0,
            "precio_unitario": item.get("precio_unitario") or 0, "importe": item.get("costo_total") or 0,
            "observaciones": "",
        })
    if servicio:
        comerciales.append({
            "lote": len(comerciales)+1, "unidad_tipo": "Servicio", "cantidad": 1, "proveedor": "AXIA",
            "modelo": "", "sku": "", "marca": "AXIA", "concepto": servicio.get("concepto"),
            "precio_lista": 0, "costo": servicio.get("costo_total") or 0, "utilidad_pct": 0,
            "precio_venta": servicio.get("costo_total") or 0, "precio_unitario": servicio.get("costo_total") or 0,
            "importe": servicio.get("costo_total") or 0, "observaciones": "",
        })
    return guardar_cotizacion_comercial(datos, comerciales, usuario)
