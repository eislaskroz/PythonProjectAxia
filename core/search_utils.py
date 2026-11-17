from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Mapping


def normalizar_termino_busqueda(valor: object) -> str:
    return " ".join(str(valor or "").strip().upper().split())


def texto_comparable(valor: object) -> str:
    texto = normalizar_termino_busqueda(valor)
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caracter)
    )


def coincide_en_campos(registro: Mapping[str, object], termino: object, campos: Iterable[str]) -> bool:
    buscado = texto_comparable(termino)
    if not buscado:
        return False
    return any(buscado in texto_comparable(registro.get(campo)) for campo in campos)


def puntaje_coincidencia(registro: Mapping[str, object], termino: object, campos: Iterable[str]) -> tuple[int, str]:
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