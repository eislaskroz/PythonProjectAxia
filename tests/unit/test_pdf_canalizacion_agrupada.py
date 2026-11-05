"""Agrupación de PDF: LEV ordinarios, especiales y Obra Civil."""
from pathlib import Path

from services.pdf_canalizacion_agrupada import (
    agrupar_partidas_canalizacion, desglosar_secciones_pdf,
    ENCABEZADOS_CANALIZACION,
)


def _ejemplo():
    return [
        {"familia": "Conductores y Canalización", "material": "Tubo", "tipo": "EMT", "tamano_calibre_especificacion": '1/2"', "color_modelo": "Gris / ZP-10", "cantidad": "2", "unidad": "Pieza(s)"},
        {"familia": "Fijación y Soporte", "material": "Abrazadera", "tipo": "Para Viga", "tamano_calibre_especificacion": '3/4"', "cantidad": "5", "unidad": "Pieza(s)"},
        {"familia": "Conductores y Canalización", "material": "Cable", "tipo": "UTP Cat6", "tamano_calibre_especificacion": "23 AWG", "cantidad": "25", "unidad": "Metro(s)"},
    ]


def test_categorias_unicas_y_partidas_conservadas():
    groups = agrupar_partidas_canalizacion(_ejemplo())
    assert [category for category, _ in groups] == ["Conductores y Canalización", "Fijación y Soporte"]
    assert [row["Material"] for row in groups[0][1]] == ["Tubo", "Cable"]
    assert groups[0][1][0]["Cantidad"] == "2"
    assert groups[0][1][0]["Color/Modelo/Otros"] == "Gris / ZP-10"
    assert list(groups[0][1][0]) == list(ENCABEZADOS_CANALIZACION)
    assert "Aproximado" not in groups[0][1][0]
    assert groups[1][1][0]["Tipo"] == "Para Viga"


def test_legacy_no_pierde_materiales_ni_familias():
    rows = [{"categoria": "Tubo", "tipo": "PVC", "cantidad": "3", "unidad": "Pieza(s)"},
            {"Categoría": "Cajas y Registros / Cajas", "Tipo": "FS", "Cantidad": 25, "Unidad": "Pieza(s)"},
            {"Categoría": "Conexiones y Uniones", "Material": "Codos", "Tipo": "45°", "Cantidad": 7}]
    groups = dict(agrupar_partidas_canalizacion(rows))
    assert groups["Conductores y Canalización"][0]["Material"] == "Tubo"
    assert groups["Cajas y Registros"][0]["Material"] == "Cajas"
    assert groups["Conexiones y Uniones"][0]["Material"] == "Codos"


def test_desglose_solo_modifica_canalizacion():
    sections = [("Conceptos de obra", ["Tipo"], [{"Tipo": "Civil"}]),
                ("Canalización, cableado y materiales", ["Categoría", "Tipo"], _ejemplo())]
    expanded = desglosar_secciones_pdf(sections)
    assert expanded[0] == sections[0]
    assert expanded[1] == ("Canalización, cableado y materiales", None, None)
    assert expanded[2][0] == "Conductores y Canalización"
    assert expanded[2][1] == list(ENCABEZADOS_CANALIZACION)
    assert expanded[3][0] == "Fijación y Soporte"


def test_no_inventa_partidas():
    assert agrupar_partidas_canalizacion([{}, "invalid", None]) == []
    assert desglosar_secciones_pdf([("Canalización, cableado y materiales", ["A"], [])]) == [("Canalización, cableado y materiales", ["A"], [])]


def test_pdf_levantamiento_grupos(tmp_path: Path):
    from services.levantamiento_seguridad_pdf import generar_pdf_levantamiento_maestro
    registro = {"lev_folio": "LEV-DEMO", "lev_detalle_tecnico_json": {
        "tipo_levantamiento": "General",
        "resumen_servicio": "Revisión de canalización.",
        "canalizacion_materiales": _ejemplo(),
    }}
    archivo = tmp_path / "demo-lev.pdf"
    generar_pdf_levantamiento_maestro(registro, ruta_salida=archivo, abrir=False)
    assert archivo.read_bytes().startswith(b"%PDF-")
    import fitz
    texto = "\n".join(page.get_text() for page in fitz.open(archivo))
    assert "CONDUCTORES Y CANALIZACIÓN" in texto.upper()
    assert "FIJACIÓN Y SOPORTE" in texto.upper()
    assert "Para Viga" in texto
    assert "Gris / ZP-10" in texto
    assert "Aproximado" not in texto
    assert "6 metros" not in texto


def test_pdf_obra_civil_grupos(tmp_path: Path):
    import pytest
    pytest.importorskip("customtkinter", reason="Validación gráfica requiere dependencias de Windows")
    from views.formato_helpers import generar_pdf_preview
    archivo = tmp_path / "demo-obc.pdf"
    filas = [{"Categoría": p["familia"], "Material": p["material"], "Tipo": p["tipo"],
              "Especificación": p["tamano_calibre_especificacion"],
              "Color/Modelo/Otros": p.get("color_modelo", ""),
              "Cantidad": p["cantidad"], "Unidad": p["unidad"]} for p in _ejemplo()]
    generado = generar_pdf_preview(
        "Obra Civil", {"Folio OBC": "OBC-DEMO", "Cliente": "Prueba"},
        [("Canalización, cableado y materiales", ["Categoría", "Material", "Tipo", "Especificación", "Cantidad", "Unidad"], filas)],
        ruta_salida=archivo, abrir=False,
    )
    assert generado and archivo.exists()
    import fitz
    texto = "\n".join(page.get_text() for page in fitz.open(archivo))
    assert "CONDUCTORES Y CANALIZACIÓN" in texto.upper()
    assert "FIJACIÓN Y SOPORTE" in texto.upper()
    assert "Para Viga" in texto


def test_pdf_no_imprime_aproximado_historico():
    filas = [
        {"familia": "Conductores y Canalización", "material": "Tubo", "tipo": "EMT",
         "cantidad": "2", "unidad": "Pieza(s)", "aproximado": "6 metros"},
        {"Categoría": "Cajas y Registros / Cajas", "Tipo": "FS",
         "Cantidad": "5", "Unidad": "Pieza(s)", "Aproximado": "15 metros"},
    ]
    grupos = agrupar_partidas_canalizacion(filas)
    assert len(grupos) == 2
    assert list(ENCABEZADOS_CANALIZACION) == ["Material", "Tipo", "Tamaño / calibre", "Color/Modelo/Otros", "Cantidad", "Unidad"]
    for _, partidas in grupos:
        for partida in partidas:
            assert "Aproximado" not in partida
    desglosadas = desglosar_secciones_pdf([
        ("Canalización, cableado y materiales", ["Categoría", "Tipo", "Cantidad"], filas),
    ])
    for _, columnas, _ in desglosadas:
        if columnas is not None:
            assert "Aproximado" not in columnas
