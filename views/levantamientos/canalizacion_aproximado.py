from __future__ import annotations

from decimal import Decimal, InvalidOperation

_UNIDADES_FIJAS_PIEZAS = frozenset({"tubo", "canaleta", "patch cord", "patchcord"})

_TUBOS_POR_METRO = frozenset({
    "helicoidal metálico / flexible zapa",
    "liquidtight /licuatite",
    "liquidtight / licuatite",
    "poliducto corrugado (ligero)",
    "vorrugado no metálico (ent)",
    "corrugado no metálico (ent)",
})

_TUBOS_POR_METRO_HISTORICOS = frozenset({"helicoidal metálico", "liquidtight"})
_METROS_POR_PIEZA = {"tubo": Decimal("3"), "canaleta": Decimal("2")}


def _categoria_normalizada(categoria: str) -> str:
    return " ".join(str(categoria or "").strip().casefold().split())


def tubo_por_metro(categoria: str, tipo: str = "") -> bool:
    return (_categoria_normalizada(categoria) == "tubo" and
            _categoria_normalizada(tipo) in (_TUBOS_POR_METRO | _TUBOS_POR_METRO_HISTORICOS))


def unidad_fija_canalizacion(categoria: str, tipo: str = "") -> bool:
    return _categoria_normalizada(categoria) in _UNIDADES_FIJAS_PIEZAS


def unidad_forzada_canalizacion(categoria: str, unidad_actual: str = "", tipo: str = "") -> str:
    if tubo_por_metro(categoria, tipo):
        return "Metro(s)"
    if unidad_fija_canalizacion(categoria, tipo):
        return "Pieza(s)"
    return str(unidad_actual or "").strip()


def texto_aproximado_canalizacion(categoria: str, cantidad: str, unidad: str, tipo: str = "") -> str:
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


    unidad_texto = unidad_forzada_canalizacion(categoria, unidad, tipo)
    return f"{cantidad_texto} {unidad_texto}".strip()