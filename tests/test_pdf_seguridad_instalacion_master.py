from services.levantamiento_seguridad_pdf import es_seguridad_instalacion


def test_detector_seguridad_instalacion():
    assert es_seguridad_instalacion({
        "lev_tipo_levantamiento": "Seguridad y Monitoreo",
        "lev_modalidad_operativa": "Instalación",
    })
    assert not es_seguridad_instalacion({
        "lev_tipo_levantamiento": "Seguridad y Monitoreo",
        "lev_modalidad_operativa": "Reparación",
    })


def test_detector_desde_json_tecnico():
    import json
    assert es_seguridad_instalacion({
        "lev_detalle_tecnico_json": json.dumps({
            "tipo_levantamiento": "Seguridad y Monitoreo",
            "modalidad_operativa": "Instalacion",
        })
    })
