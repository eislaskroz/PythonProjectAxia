"""Verifica concordancia exacta del catálogo activo con la fuente de noviembre."""
from pathlib import Path
import json

from views.levantamientos.catalogos_materiales_jerarquicos import (
    CATALOGO_XLSX, tipos_de_material, materiales_de_familia,
    familias_materiales,
)


def test_catalogo_coincide_con_las_261_filas_de_la_fuente():
    archivo = Path(__file__).resolve().parents[2] / "docs" / "catalogo_materiales_noviembre_2026_fuente.json"
    filas = json.loads(archivo.read_text(encoding="utf8"))
    triples = [(x["familia"], x["material"], x["tipo"]) for x in filas]
    assert len(triples) == 261 == len(CATALOGO_XLSX)
    assert sorted(triples) == sorted(CATALOGO_XLSX)
    assert set(familias_materiales()) == {f for f, _, _ in triples}
    for familia, material, tipo in triples:
        assert material in materiales_de_familia(familia)
        assert tipo in tipos_de_material(material)


def test_nuevas_capturas_no_reactivan_elementos_eliminados():
    assert "Plugs RJ45 / RJ11" not in materiales_de_familia("Conexiones y Uniones")
    assert "Conector de ZAPA" not in tipos_de_material("Conectores")
    assert "Liquidtight /Licuatite" not in tipos_de_material("Tubo")
