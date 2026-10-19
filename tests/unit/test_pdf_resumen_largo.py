"""Regresión: un resumen técnico muy extenso no debe impedir exportar PDF."""
from pathlib import Path

from services.levantamiento_seguridad_pdf import (
    _fragmentos_resumen_pdf,
    generar_pdf_levantamiento_maestro,
)


def test_fragmentar_parrafo_extenso_sin_perder_contenido():
    texto = " ".join(f"Elemento{i}" for i in range(900))
    partes = _fragmentos_resumen_pdf(texto)
    assert len(partes) > 1
    assert all(len(parte) <= 480 for parte in partes)
    assert " ".join(partes) == texto


def test_fragmentar_texto_sin_espacios():
    texto = "A" * 8000
    partes = _fragmentos_resumen_pdf(texto)
    assert "".join(partes) == texto
    assert all(len(parte) <= 480 for parte in partes)


def test_pdf_general_con_descripcion_de_varias_paginas(tmp_path: Path):
    frase = (
        "Se revisa la instalación, canalización y características del servicio "
        "para documentar correctamente los trabajos solicitados. "
    )
    descripcion = frase * 200
    registro = {
        "lev_folio": "LEV-PRUEBA-LARGA",
        "lev_detalle_tecnico_json": {
            "tipo_levantamiento": "General",
            "resumen_servicio": descripcion,
            "observaciones": "Observación adicional extensa. " * 100,
        },
    }
    salida = tmp_path / "levantamiento_general.pdf"
    generar_pdf_levantamiento_maestro(registro, ruta_salida=salida)
    assert salida.read_bytes().startswith(b"%PDF-")
    assert salida.stat().st_size > 1000


def test_pdf_corto_inalterado(tmp_path: Path):
    salida = tmp_path / "levantamiento_corto.pdf"
    generar_pdf_levantamiento_maestro({
        "lev_folio": "LEV-PRUEBA-CORTA",
        "lev_detalle_tecnico_json": {
            "tipo_levantamiento": "General", "resumen_servicio": "Instalar equipos de red."
        },
    }, ruta_salida=salida)
    assert salida.read_bytes().startswith(b"%PDF-")
