from views.levantamientos.form_definitions import (
    FORMULARIOS_DETALLADOS_EXTRA, TIPOS_LEVANTAMIENTO_ESPECIALIZADOS,
)

def test_tipos_especializados_sin_duplicados():
    assert len(TIPOS_LEVANTAMIENTO_ESPECIALIZADOS) == len(set(TIPOS_LEVANTAMIENTO_ESPECIALIZADOS))

def test_definiciones_tienen_estructura_valida():
    assert FORMULARIOS_DETALLADOS_EXTRA
    for nombre, formulario in FORMULARIOS_DETALLADOS_EXTRA.items():
        assert nombre
        assert formulario["titulo"]
        assert formulario["tipo_sistema"]
        assert formulario["secciones"]
        claves=[]
        for titulo, campos in formulario["secciones"]:
            assert titulo and campos
            for campo in campos:
                assert len(campo) == 5
                claves.append(campo[0])
        assert len(claves) == len(set(claves)), f"Campos duplicados en {nombre}"
