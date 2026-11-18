from security.permissions import puede_ver_direccion_general


def test_administradores_entran_independientemente_del_id():
    for uid in (2, 8, 999):
        assert puede_ver_direccion_general({"id_usuario": uid, "usu_tipo": 1})


def test_cuentas_de_direccion_con_tipo_nueve_entran():
    for uid in (39, 42, 43):
        assert puede_ver_direccion_general({"id_usuario": uid, "usu_tipo": 9})
        assert puede_ver_direccion_general({"id_usuario": str(uid), "usu_tipo": "9"})


def test_otras_cuentas_de_tipo_nueve_no_entran():
    assert not puede_ver_direccion_general({"id_usuario": 44, "usu_tipo": 9})


def test_id_sin_rol_correcto_no_concede_acceso():
    for uid in (39, 42, 43):
        assert not puede_ver_direccion_general({"id_usuario": uid, "usu_tipo": 2})
        assert not puede_ver_direccion_general({"id_usuario": uid, "usu_tipo": 4})


def test_entradas_invalidas_no_tienen_acceso():
    for user in (None, {}, {"usu_tipo": 9}, {"id_usuario": "n/a", "usu_tipo": 9}):
        assert not puede_ver_direccion_general(user)