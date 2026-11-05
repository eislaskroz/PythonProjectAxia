"""Presentación de canalización por familia en los PDF de AXIA.

Sólo transforma filas para su impresión: no modifica el JSON de captura,
la base, los identificadores de materiales ni las cantidades originales.
Soporta registros históricos donde ``categoria`` era el material.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Any, Mapping, Sequence
import unicodedata

from views.levantamientos.catalogos_materiales_jerarquicos import (
    FAMILIA_POR_MATERIAL, familias_materiales,
    normalizar_material,
)

TITULO_CANALIZACION = "Canalización, cableado y materiales"
ENCABEZADOS_CANALIZACION = ("Material", "Tipo", "Tamaño / calibre", "Cantidad", "Unidad")


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
        # Compatibilidad con PDF anterior: «Familia / Material» en una celda.
        candidata, resto = categoria.split(" / ", 1)
        if _identidad(candidata) in nombres_familias:
            familia, material = nombres_familias[_identidad(candidata)], resto
    if not familia and _identidad(categoria) in nombres_familias:
        familia = nombres_familias[_identidad(categoria)]
    if not material and categoria and _identidad(categoria) not in nombres_familias:
        material = categoria
    material = normalizar_material(material or "Por definir")
    # Para históricos con material sin familia, se deduce únicamente cuando
    # existe una correspondencia explícita en el catálogo, no por suposición.
    if not familia:
        familia = FAMILIA_POR_MATERIAL.get(material, "Otros materiales")
    else:
        familia = nombres_familias.get(_identidad(familia), familia)
    return familia, material


def agrupar_partidas_canalizacion(partidas: Sequence[Mapping] | None) -> list[tuple[str, list[dict[str, str]]]]:
    """Agrupa filas preservando su cantidad, unidad, tipo y especificación.

    No fusiona filas ni suma cantidades: dos partidas iguales siguen siendo
    dos renglones, para no perder referencias del registro original.
    """
    grupos: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
    for item in partidas or ():
        if not isinstance(item, Mapping):
            continue
        # Los borradores pueden contener una fila de captura todavía vacía.
        # No generar renglones ficticios en un PDF a partir de esa fila.
        if not any(_texto(v) for v in item.values()):
            continue
        familia, material = _resolver_familia_material(item)
        cantidad = _valor(item, "cantidad", "Cantidad")
        unidad = _valor(item, "unidad", "Unidad")
        # "Aproximado" es sólo una ayuda visual en la captura, nunca
        # forma parte de las tablas del PDF, incluso en registros antiguos.
        grupos.setdefault(familia, []).append({
            "Material": material,
            "Tipo": _valor(item, "tipo", "Tipo") or "Por definir",
            "Tamaño / calibre": _valor(item, "tamano_calibre_especificacion", "tamano", "calibre", "Especificación", "Tamaño/Calibre", "Tamaño / calibre") or "Por definir",
            "Cantidad": cantidad or "-",
            "Unidad": unidad or "-",
        })
    # El orden sigue las siete familias oficiales; secciones heredadas no
    # reconocidas quedan al final conservando el orden en que aparecieron.
    orden = {nombre: indice for indice, nombre in enumerate(familias_materiales())}
    return sorted(grupos.items(), key=lambda x: orden.get(x[0], len(orden)))


def desglosar_secciones_pdf(secciones: Sequence[tuple] | None) -> list[tuple]:
    """Cambia sólo la sección de canalización; las demás pasan intactas.

    Una cabecera general sin filas precede a una cabecera por categoría con su
    propia tabla de componentes. ``columnas=None`` identifica un título solo.
    """
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
