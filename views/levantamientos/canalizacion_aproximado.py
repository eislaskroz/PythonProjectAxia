"""Reglas visuales compartidas de unidad y aproximado de canalización."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


# El tubo comercial es de 3 m y la canaleta de 2 m por pieza.
# El patch cord siempre se cuenta por pieza, independientemente de su longitud.
_UNIDADES_FIJAS_PIEZAS = frozenset({"tubo", "canaleta", "patch cord", "patchcord"})
_METROS_POR_PIEZA = {"tubo": Decimal("3"), "canaleta": Decimal("2")}


def _categoria_normalizada(categoria: str) -> str:
    return " ".join(str(categoria or "").strip().casefold().split())


def unidad_fija_canalizacion(categoria: str) -> bool:
    """Determina si la unidad de una partida debe bloquearse en piezas."""
    return _categoria_normalizada(categoria) in _UNIDADES_FIJAS_PIEZAS


def unidad_forzada_canalizacion(categoria: str, unidad_actual: str = "") -> str:
    """Tubo, canaleta y patch cord se capturan exclusivamente por pieza."""
    if unidad_fija_canalizacion(categoria):
        return "Pieza(s)"
    return str(unidad_actual or "").strip()


def texto_aproximado_canalizacion(categoria: str, cantidad: str, unidad: str) -> str:
    """Muestra equivalencias métricas sin alterar la cantidad de piezas guardada."""
    cantidad_texto = str(cantidad or "").strip()
    if not cantidad_texto:
        return "—"

    metros_por_pieza = _METROS_POR_PIEZA.get(_categoria_normalizada(categoria))
    if metros_por_pieza is not None:
        try:
            metros = Decimal(cantidad_texto.replace(",", ".")) * metros_por_pieza
        except InvalidOperation:
            return "—"
        metros_texto = format(metros.normalize(), "f")
        if "." in metros_texto:
            metros_texto = metros_texto.rstrip("0").rstrip(".")
        return f"{metros_texto} metros"

    # Para categorías sin conversión se informa la cantidad/unidad capturada.
    unidad_texto = unidad_forzada_canalizacion(categoria, unidad)
    return f"{cantidad_texto} {unidad_texto}".strip()
