from security.permissions import puede_convertir_levantamiento_a_orden


def test_solo_administrativo_convierte_levantamientos():
    for tipo in range(1, 7):
        assert puede_convertir_levantamiento_a_orden({"usu_tipo": tipo}) is (tipo == 5)
