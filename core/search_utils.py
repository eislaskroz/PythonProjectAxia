"""Utilidades compartidas para búsquedas consistentes en AXIA."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Mapping


def normalizar_termino_busqueda(valor: object) -> str:
    """Convierte una entrada a texto limpio y en mayúsculas."""
    return " ".join(str(valor or "").strip().upper().split())


def texto_comparable(valor: object) -> str:
    """Normaliza texto para comparar sin distinguir acentos ni mayúsculas."""
    texto = normalizar_termino_busqueda(valor)
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caracter)
    )


def coincide_en_campos(registro: Mapping[str, object], termino: object, campos: Iterable[str]) -> bool:
    """Indica si el término aparece parcialmente en cualquiera de los campos."""
    buscado = texto_comparable(termino)
    if not buscado:
        return False
    return any(buscado in texto_comparable(registro.get(campo)) for campo in campos)


def puntaje_coincidencia(registro: Mapping[str, object], termino: object, campos: Iterable[str]) -> tuple[int, str]:
    """Genera un puntaje estable para ordenar primero las coincidencias más cercanas."""
    buscado = texto_comparable(termino)
    mejor = 10_000
    etiqueta = ""

    for indice, campo in enumerate(campos):
        valor = texto_comparable(registro.get(campo))
        if not valor:
            continue
        if valor == buscado:
            nivel = 0
        elif valor.startswith(buscado):
            nivel = 1
        elif buscado in valor:
            nivel = 2
        else:
            continue
        mejor = min(mejor, nivel * 100 + indice)
        if not etiqueta:
            etiqueta = valor

    return mejor, etiqueta
