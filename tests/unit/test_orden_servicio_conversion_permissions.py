from security.permissions import puede_convertir_levantamiento_a_orden


def test_administrador_y_administrativo_convierten_levantamientos():
    for tipo in range(1, 7):
        assert puede_convertir_levantamiento_a_orden({"usu_tipo": tipo}) is (tipo in {1, 5})
