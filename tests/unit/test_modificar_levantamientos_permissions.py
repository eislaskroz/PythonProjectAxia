from security.permissions import (
    puede_convertir_levantamiento_a_orden,
    puede_modificar_levantamientos,
    puede_validar_levantamiento_ventas,
)


def test_roles_autorizados_para_modificar_levantamientos():
    for tipo in (1, 2, 3, 5):
        assert puede_modificar_levantamientos({"usu_tipo": tipo})


def test_modificar_no_hereda_conversion_ni_validacion():
    for tipo in (2, 3):
        usuario = {"usu_tipo": tipo}
        assert puede_modificar_levantamientos(usuario)
        assert not puede_convertir_levantamiento_a_orden(usuario)
        assert not puede_validar_levantamiento_ventas(usuario)


def test_roles_no_autorizados_para_modificar_levantamientos():
    for tipo in (4, 6, 7, 8, 99):
        assert not puede_modificar_levantamientos({"usu_tipo": tipo})
