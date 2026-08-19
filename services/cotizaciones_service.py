"""Servicios del módulo comercial de cotizaciones de levantamientos."""
from __future__ import annotations

from datetime import datetime, timezone
import json

from core.logger import configurar_logger
from services.movimientos_service import registrar_movimiento_seguro
from services.ordenes_trabajo_schema import partidas_desde_detalle_levantamiento
from services.levantamientos_schema import TABLA_LEVANTAMIENTOS, COLUMNAS_LEVANTAMIENTOS
from services.query_compat import execute_select_compatible
from supabase_config import supabase

logger = configurar_logger(__name__)


def _esta_preautorizado_ventas(registro: dict) -> bool:
    """Reconoce la preautorización incluso si una escritura anterior quedó parcial."""
    if bool((registro or {}).get("lev_validado_ventas")):
        return True
    return bool(
        str((registro or {}).get("lev_validado_por") or "").strip()
        or str((registro or {}).get("lev_fecha_validacion") or "").strip()
    )


def obtener_levantamientos_para_cotizar(limite: int = 200) -> list[dict]:
    """Devuelve únicamente levantamientos preautorizados por Operaciones.

    Primero usa la bandera oficial ``lev_validado_ventas``. Si no devuelve filas,
    hace una lectura de compatibilidad para recuperar registros cuya validación
    haya quedado parcialmente persistida (usuario/fecha presentes).
    """
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

        # Compatibilidad: una validación puede haber alcanzado a guardar usuario
        # o fecha aunque la bandera booleana no quedara registrada. No se incluyen
        # levantamientos sin ninguna evidencia de preautorización.
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
    """Normaliza materiales/equipos/consumibles del LEV para la pantalla de Ventas."""
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


def cargar_cotizacion(registro: dict) -> dict:
    valor = (registro or {}).get("lev_cotizacion_json")
    if isinstance(valor, dict):
        return dict(valor)
    if isinstance(valor, str) and valor.strip():
        try:
            obj = json.loads(valor)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
    return {}


def guardar_cotizacion_levantamiento(
    registro: dict,
    partidas: list[dict],
    usuario: str,
    servicio: dict | None = None,
) -> dict:
    """Guarda costos de partidas y del servicio en el JSONB de la cotización.

    El costo del servicio se conserva dentro de ``lev_cotizacion_json`` para no
    agregar columnas rígidas por cada concepto comercial y mantener compatibilidad
    con la migración de FIX10.
    """
    id_levantamiento = (registro or {}).get("id_levantamiento")
    folio = str((registro or {}).get("lev_folio") or "").strip().upper()
    if not id_levantamiento:
        raise ValueError("El levantamiento no contiene id_levantamiento.")

    servicio = servicio if isinstance(servicio, dict) else {}
    concepto_servicio = str(servicio.get("concepto") or "").strip()
    if not concepto_servicio:
        raise ValueError("La cotización requiere un concepto de servicio.")
    try:
        costo_servicio = round(float(servicio.get("costo_total")), 2)
    except (TypeError, ValueError):
        raise ValueError("El costo del servicio es inválido.")
    if costo_servicio < 0:
        raise ValueError("El costo del servicio no puede ser negativo.")

    total_partidas = 0.0
    limpias = []
    for item in (partidas or []):
        costo = item.get("costo_total")
        precio_unitario = item.get("precio_unitario")
        try:
            precio_unitario_num = round(float(precio_unitario), 2)
            costo_num = round(float(costo), 2)
        except (TypeError, ValueError):
            raise ValueError(
                f"La partida {item.get('partida') or '?'} tiene un precio unitario o costo inválido."
            )
        if precio_unitario_num < 0 or costo_num < 0:
            raise ValueError("Los precios y costos no pueden ser negativos.")
        total_partidas += costo_num
        limpia = {
            "partida": str(item.get("partida") or ""),
            "grupo": str(item.get("grupo") or ""),
            "unidad": str(item.get("unidad") or ""),
            "cantidad": str(item.get("cantidad") or ""),
            "marca": str(item.get("marca") or ""),
            "modelo": str(item.get("modelo") or ""),
            "concepto": str(item.get("concepto") or ""),
            "precio_unitario": precio_unitario_num,
            "costo_total": costo_num,
        }
        limpias.append(limpia)

    total_general = round(total_partidas + costo_servicio, 2)
    ahora = datetime.now(timezone.utc).isoformat()
    cotizacion = {
        "version": 3,
        "moneda": "MXN",
        "partidas": limpias,
        "servicio": {
            "concepto": concepto_servicio,
            "costo_total": costo_servicio,
        },
        "total_partidas": round(total_partidas, 2),
        "total_general": total_general,
        "cotizado_por": str(usuario or "").strip(),
        "fecha_cotizacion": ahora,
    }
    (
        supabase.table(TABLA_LEVANTAMIENTOS)
        .update({"lev_cotizacion_json": cotizacion})
        .eq("id_levantamiento", id_levantamiento)
        .execute()
    )
    registrar_movimiento_seguro(
        modulo="COTIZACIONES",
        accion="GUARDAR_COSTOS",
        descripcion=(
            f"Ventas capturó costos para {len(limpias)} partidas y servicio. "
            f"Total MXN {total_general:.2f}"
        ),
        registro_afectado=folio or str(id_levantamiento),
    )
    return cotizacion

