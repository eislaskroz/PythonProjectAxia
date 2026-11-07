"""Reglas visuales compartidas de unidad y aproximado de canalización."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


# El tubo comercial es de 3 m y la canaleta de 2 m por pieza.
# El patch cord siempre se cuenta por pieza, independientemente de su longitud.
_UNIDADES_FIJAS_PIEZAS = frozenset({"tubo", "canaleta", "patch cord", "patchcord"})
# Estos cuatro tipos de Tubo se cuantifican directamente por metro, no por tramo.
_TUBOS_POR_METRO = frozenset({
    "helicoidal metálico / flexible zapa",
    "liquidtight /licuatite",
    "liquidtight / licuatite",
    "poliducto corrugado (ligero)",
    "vorrugado no metálico (ent)",
    "corrugado no metálico (ent)",
})
# Aliases históricos para registros cuyo tipo anterior no tenía el nombre actualizado.
_TUBOS_POR_METRO_HISTORICOS = frozenset({"helicoidal metálico", "liquidtight"})
_METROS_POR_PIEZA = {"tubo": Decimal("3"), "canaleta": Decimal("2")}


def _categoria_normalizada(categoria: str) -> str:
    return " ".join(str(categoria or "").strip().casefold().split())


def tubo_por_metro(categoria: str, tipo: str = "") -> bool:
    """Determina qué tipos de tubo se cuantifican en metros directamente."""
    return (_categoria_normalizada(categoria) == "tubo" and
            _categoria_normalizada(tipo) in (_TUBOS_POR_METRO | _TUBOS_POR_METRO_HISTORICOS))


def unidad_fija_canalizacion(categoria: str, tipo: str = "") -> bool:
    """Una unidad fija: metros para 4 tipos de tubo; piezas para otros tramos."""
    return _categoria_normalizada(categoria) in _UNIDADES_FIJAS_PIEZAS


def unidad_forzada_canalizacion(categoria: str, unidad_actual: str = "", tipo: str = "") -> str:
    """Resuelve la unidad a partir de material y tipo, nunca solo del material."""
    if tubo_por_metro(categoria, tipo):
        return "Metro(s)"
    if unidad_fija_canalizacion(categoria, tipo):
        return "Pieza(s)"
    return str(unidad_actual or "").strip()


def texto_aproximado_canalizacion(categoria: str, cantidad: str, unidad: str, tipo: str = "") -> str:
    """Calcula la referencia visual, sin persistirla en el registro ni el PDF."""
    cantidad_texto = str(cantidad or "").strip()
    if not cantidad_texto:
        return "—"

    if tubo_por_metro(categoria, tipo):
        try:
            metros = Decimal(cantidad_texto.replace(",", "."))
        except InvalidOperation:
            return "—"
        return f"{format(metros.normalize(), 'f')} metros"

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
    unidad_texto = unidad_forzada_canalizacion(categoria, unidad, tipo)
    return f"{cantidad_texto} {unidad_texto}".strip()
