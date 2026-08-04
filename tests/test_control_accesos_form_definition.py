from views.levantamientos.form_definitions import FORMULARIOS_DETALLADOS_EXTRA


def _fields():
    sections = FORMULARIOS_DETALLADOS_EXTRA["Control de Accesos"]["secciones"]
    return {key for _title, fields in sections for key, *_rest in fields}


def test_control_accesos_removes_execution_only_fields():
    fields = _fields()
    assert not {"software_config", "prueba_apertura", "prueba_eventos", "capacitacion"} & fields


def test_control_accesos_includes_conditional_infrastructure_fields():
    fields = _fields()
    expected = {
        "requiere_infraestructura",
        "tipo_cable", "cantidad_cable",
        "tipo_canalizacion", "cantidad_canalizacion",
        "tipo_tubos", "cantidad_tubos",
        "tipo_coples", "cantidad_coples",
        "tipo_registros", "cantidad_registros",
        "tipo_conectores", "cantidad_conectores",
        "tipo_abrazaderas", "cantidad_abrazaderas",
        "dias_trabajo", "personas_trabajo",
    }
    assert expected <= fields
