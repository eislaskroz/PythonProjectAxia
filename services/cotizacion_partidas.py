"""Reglas comunes para identificar y valorizar el lote de mano de obra.

Se preservan las claves JSON antiguas para no exigir migraciones en Supabase.
"""
from __future__ import annotations


def es_lote_servicio(item: dict, indice: int, total: int) -> bool:
    """El servicio que AXIA agrega al final del levantamiento, no cualquier insumo."""
    if indice != total - 1 or not isinstance(item, dict):
        return False
    unidad = str(item.get("unidad_tipo") or "").strip().casefold()
    concepto = str(item.get("concepto") or "").strip().casefold()
    return unidad == "servicio" or concepto.startswith("servicio de ")


def importes_servicio(item: dict) -> tuple[float, float]:
    """Importe manual del servicio y precio unitario implícito según cantidad."""
    def numero(valor):
        try:
            return float(str(valor or "0").replace("$", "").replace(",", "").strip() or 0)
        except (ValueError, TypeError):
            return 0.0

    importe = round(numero(item.get("importe")), 2)
    cantidad = numero(item.get("cantidad")) or 1.0
    return importe, round(importe / cantidad, 2)
