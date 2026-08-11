from services.levantamiento_seguridad_pdf import _visible_declarative_sections


def _sections(accion):
    return {
        'tipo_de_solicitud_y_alcance': {'accion_ti': accion},
        'identificación_y_características_generales': {'marca_actual': 'AXIA'},
        'revisión_y_diagnóstico': {'enciende_equipo': 'No aplica'},
        'mantenimiento_o_reparación': {'tipo_intervencion': 'No aplica'},
        'requerimientos_para_suministro': {'especificaciones_minimas': 'Core i7'},
        'instalación_configuración_pruebas_y_entrega': {'instalacion_fisica': 'Sí'},
    }


def keys(accion):
    return [k for k, _ in _visible_declarative_sections('Tecnología, Equipos y Periféricos', _sections(accion))]


def test_tecnologia_suministro_instalacion_no_imprime_diagnostico_ni_reparacion():
    result = keys('Suministro e instalación')
    assert 'revisión_y_diagnóstico' not in result
    assert 'mantenimiento_o_reparación' not in result
    assert 'requerimientos_para_suministro' in result
    assert 'instalación_configuración_pruebas_y_entrega' in result


def test_tecnologia_reparacion_si_imprime_diagnostico_y_reparacion():
    result = keys('Reparación')
    assert 'revisión_y_diagnóstico' in result
    assert 'mantenimiento_o_reparación' in result
    assert 'requerimientos_para_suministro' not in result


def test_tecnologia_revision_no_imprime_mantenimiento_reparacion():
    result = keys('Revisión')
    assert 'revisión_y_diagnóstico' in result
    assert 'mantenimiento_o_reparación' not in result
