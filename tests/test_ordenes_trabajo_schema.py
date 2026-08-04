import json
from services.ordenes_trabajo_schema import filter_payload, metadata_item, extract_origin, visible_partidas


def test_payload_elimina_columnas_inexistentes():
    data = filter_payload({"ot_folio": "OT-0001", "ot_actividad": "x", "ot_tecnico": "T", "ot_id": 9})
    assert data == {"ot_folio": "OT-0001"}


def test_metadata_origen_no_aparece_como_partida():
    value = [{"partida": "1", "concepto": "Servicio"}, metadata_item("os-0001")]
    assert extract_origin(json.dumps(value)) == "OS-0001"
    assert visible_partidas(value) == [{"partida": "1", "concepto": "Servicio"}]
