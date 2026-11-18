from __future__ import annotations

from collections import OrderedDict
from typing import Any, Mapping, Sequence
import unicodedata

from views.levantamientos.catalogos_materiales_jerarquicos import (
    FAMILIA_POR_MATERIAL, familias_materiales,
    normalizar_material,
)

TITULO_CANALIZACION = "Canalización, cableado y materiales"
ENCABEZADOS_CANALIZACION = ("Material", "Tipo", "Tamaño / calibre", "Color/Modelo/Otros", "Cantidad", "Unidad")


def _texto(valor: Any) -> str:
    return str(valor).strip() if valor is not None else ""


def _identidad(valor: Any) -> str:
    normalized = unicodedata.normalize("NFKD", _texto(valor)).casefold()
    return " ".join("".join(x for x in normalized if not unicodedata.combining(x)).split())


def es_seccion_canalizacion(titulo: Any) -> bool:
    return _identidad(titulo) == _identidad(TITULO_CANALIZACION)


def _valor(item: Mapping, *claves: str) -> str:
    for clave in claves:
        valor = _texto(item.get(clave))
        if valor:
            return valor
    return ""


def _resolver_familia_material(partida: Mapping) -> tuple[str, str]:
    familia = _valor(partida, "familia", "Familia")
    categoria = _valor(partida, "categoria", "Categoría")
    material = _valor(partida, "material", "Material")
    nombres_familias = {_identidad(x): x for x in familias_materiales()}
    if not material and " / " in categoria:
        candidata, resto = categoria.split(" / ", 1)
        if _identidad(candidata) in nombres_familias:
            familia, material = nombres_familias[_identidad(candidata)], resto
    if not familia and _identidad(categoria) in nombres_familias:
        familia = nombres_familias[_identidad(categoria)]
    if not material and categoria and _identidad(categoria) not in nombres_familias:
        material = categoria
    material = normalizar_material(material or "Por definir")
    if not familia:
        familia = FAMILIA_POR_MATERIAL.get(material, "Otros materiales")
    else:
        familia = nombres_familias.get(_identidad(familia), familia)
    return familia, material


def agrupar_partidas_canalizacion(partidas: Sequence[Mapping] | None) -> list[tuple[str, list[dict[str, str]]]]:
    grupos: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
    for item in partidas or ():
        if not isinstance(item, Mapping):
            continue
        if not any(_texto(v) for v in item.values()):
            continue
        familia, material = _resolver_familia_material(item)
        cantidad = _valor(item, "cantidad", "Cantidad")
        unidad = _valor(item, "unidad", "Unidad")
        grupos.setdefault(familia, []).append({
            "Material": material,
            "Tipo": _valor(item, "tipo", "Tipo") or "Por definir",
            "Tamaño / calibre": _valor(item, "tamano_calibre_especificacion", "tamano", "calibre", "Especificación", "Tamaño/Calibre", "Tamaño / calibre") or "Por definir",
            "Color/Modelo/Otros": _valor(item, "color_modelo", "Color/Modelo/Otros", "color", "modelo"),
            "Cantidad": cantidad or "-",
            "Unidad": unidad or "-",
        })

    orden = {nombre: indice for indice, nombre in enumerate(familias_materiales())}
    return sorted(grupos.items(), key=lambda x: orden.get(x[0], len(orden)))


def desglosar_secciones_pdf(secciones: Sequence[tuple] | None) -> list[tuple]:
    nuevas = []
    for nombre, columnas, filas in secciones or ():
        if not es_seccion_canalizacion(nombre) or not filas:
            nuevas.append((nombre, columnas, filas))
            continue
        grupos = agrupar_partidas_canalizacion(filas)
        if not grupos:
            continue
        nuevas.append((nombre, None, None))
        for familia, partidas in grupos:
            nuevas.append((familia, list(ENCABEZADOS_CANALIZACION), partidas))
    return nuevas