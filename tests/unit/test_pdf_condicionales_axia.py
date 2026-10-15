from services.levantamiento_seguridad_pdf import (
    _pdf_has_value, _pdf_filter_pairs, _pdf_filter_table_rows,
    _mapping_rows, _filter_pdf_dependencies,
)
from services.pdf_registro_service import _es_vacio
from services.axia_pdf_profiles import _non_empty


def test_respuestas_negativas_y_vacias():
    for value in ("No", " no ", "No aplica", "N/A", "Sin información", "", None, False):
        assert not _pdf_has_value(value)
        assert _es_vacio(value)
        assert not _non_empty(value)
    for value in ("Sí", "Instalación", "Rack 1", 0, 2):
        assert _pdf_has_value(value)


def test_dependencias_y_filas():
    rows = _mapping_rows({
        "requiere_ups": "No", "tipo_ups": "10 kVA",
        "punto_red": "Rack 1", "sin_dato": "No aplica",
    })
    assert rows == [["Punto de red", "Rack 1", "", ""]]
    assert _pdf_filter_pairs([["A", "No", "B", "Sí"], ["C", None, "D", ""]]) == [["B", "Sí", "", ""]]
    assert _pdf_filter_table_rows([["", ""], ["Cajas", "FS"], ["No", ""]]) == [["Cajas", "FS"]]


def test_dependencias_rack_y_switch():
    assert "tipo_rack" not in _filter_pdf_dependencies({"rack_requerido": "No", "tipo_rack": "12U"})
    assert "tipo_switch" not in _filter_pdf_dependencies({"requiere_switch": "No", "tipo_switch": "PoE"})
