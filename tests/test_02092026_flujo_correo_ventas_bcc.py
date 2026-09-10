from services import mail_service


def test_destinatarios_fijos_del_flujo_de_levantamientos():
    src = open(mail_service.__file__, encoding="utf-8").read()
    assert '_AUTORIZACION_LEVANTAMIENTOS = "gte.ventas@axiacomunicaciones.mx"' in src
    assert '_BCC_AUDITORIA = "eislaskroz@gmail.com"' in src
    assert 'mmachuca@axiacomunicaciones.mx' not in src


def test_bcc_no_se_expone_como_header():
    src = open(mail_service.__file__, encoding="utf-8").read()
    assert 'receptores = destinatarios + copias + copias_ocultas' in src
    assert 'msg["Bcc"]' not in src
