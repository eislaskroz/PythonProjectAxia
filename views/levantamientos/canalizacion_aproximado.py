"""Reglas visuales para el aproximado de canalización y materiales."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


def unidad_forzada_canalizacion(categoria: str, unidad_actual: str = "") -> str:
    """Cada pieza de tubo representa un tramo comercial de tres metros."""
    if str(categoria or "").strip() == "Tubo":
        return "Pieza(s)"
    return str(unidad_actual or "").strip()


def texto_aproximado_canalizacion(categoria: str, cantidad: str, unidad: str) -> str:
    """Construye la leyenda informativa que aparece junto a cada partida."""
    cantidad_texto = str(cantidad or "").strip()
    if not cantidad_texto:
        return "—"

    if str(categoria or "").strip() == "Tubo":
        try:
            metros = Decimal(cantidad_texto.replace(",", ".")) * Decimal("3")
        except InvalidOperation:
            return "—"
        metros_texto = format(metros.normalize(), "f")
        if "." in metros_texto:
            metros_texto = metros_texto.rstrip("0").rstrip(".")
        return f"{metros_texto} metros"

    unidad_texto = str(unidad or "").strip()
    return f"{cantidad_texto} {unidad_texto}".strip()
