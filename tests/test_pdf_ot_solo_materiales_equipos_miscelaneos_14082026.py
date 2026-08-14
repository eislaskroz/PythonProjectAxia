from services.ordenes_trabajo_schema import partidas_desde_detalle_levantamiento


def test_ot_solo_extrae_materiales_equipos_y_miscelaneos():
    detalle = {
        "solicitud_alcance": {"descripcion": "NO DEBE SALIR", "partidas": [{"descripcion":"NO"}]},
        "revision_diagnostico": {"partidas": [{"descripcion":"DIAGNOSTICO NO"}]},
        "canalizacion_cableado_materiales": {"partidas": [
            {"categoria":"Cable", "tipo":"UTP Cat6", "cantidad":100, "unidad":"Metro(s)"}
        ]},
        "equipos_principales": [
            {"familia":"Switch", "subfamilia":"Administrable", "cantidad":1, "marca":"Ubiquiti", "modelo":"X"}
        ],
        "materiales_miscelaneos": [
            {"material":"Taquetes", "cantidad":50, "unidad":"Pieza(s)"}
        ],
        "conceptos_obra": [{"concepto":"NO DEBE SALIR", "cantidad":1, "unidad":"Servicio"}],
    }
    rows = partidas_desde_detalle_levantamiento(detalle)
    conceptos = " | ".join(r["concepto"] for r in rows)
    assert len(rows) == 3
    assert "UTP Cat6" in conceptos
    assert "Switch" in conceptos
    assert "Taquetes" in conceptos
    assert "NO DEBE SALIR" not in conceptos
    assert "DIAGNOSTICO" not in conceptos
