from security.permissions import (
    puede_convertir_levantamiento_a_orden,
    puede_modificar_levantamientos,
    puede_validar_levantamiento_ventas,
)


def test_roles_autorizados_para_modificar_levantamientos():
    for tipo in (1, 2, 3, 5):
        assert puede_modificar_levantamientos({"usu_tipo": tipo})


def test_jefe_operaciones_convierte_y_supervisor_solo_modifica():
    jefe = {"usu_tipo": 2}
    supervisor = {"usu_tipo": 3}
    assert puede_modificar_levantamientos(jefe)
    assert puede_convertir_levantamiento_a_orden(jefe)
    assert not puede_validar_levantamiento_ventas(jefe)
    assert puede_modificar_levantamientos(supervisor)
    assert not puede_convertir_levantamiento_a_orden(supervisor)
    assert not puede_validar_levantamiento_ventas(supervisor)


def test_roles_no_autorizados_para_modificar_levantamientos():
    for tipo in (4, 6, 7, 8, 99):
        assert not puede_modificar_levantamientos({"usu_tipo": tipo})
