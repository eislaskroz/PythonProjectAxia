from pathlib import Path

from security.permissions import puede_validar_levantamiento_ventas


VIEW = Path('views/orden_servicio_conversion_view.py')
MAIL = Path('services/mail_service.py')


def test_validacion_ventas_es_exclusiva_del_rol_5():
    assert puede_validar_levantamiento_ventas({'usu_tipo': 5}) is True
    for rol in (1, 2, 3, 4, 6):
        assert puede_validar_levantamiento_ventas({'usu_tipo': rol}) is False


def test_boton_validar_y_destinatario_ventas_estan_integrados():
    src = VIEW.read_text(encoding='utf-8')
    mail = MAIL.read_text(encoding='utf-8')
    assert 'text="✓ Validar Levantamiento"' in src
    assert 'command=validar_levantamiento_ventas' in src
    assert 'puede_validar_levantamiento_ventas(usuario)' in src
    assert 'enviar_levantamiento_validacion_ventas' in src
    assert 'gte.ventas@axiacomunicaciones.mx' in mail
    assert 'to=["gte.ventas@axiacomunicaciones.mx"]' in mail


def test_convertir_a_ot_permanece_visible_pero_deshabilitado():
    src = VIEW.read_text(encoding='utf-8')
    assert 'text="✓ Convertir a OT"' in src
    bloque = src[src.index('btn_convertir = ctk.CTkButton'):]
    assert 'state="disabled"' in bloque.split('btn_convertir.pack', 1)[0]
    assert 'btn_convertir.configure(state="normal")' not in src


def test_etiqueta_fecha_admin_homologada():
    src = VIEW.read_text(encoding='utf-8')
    assert 'campo("Fecha de Levantamiento", "lev_fecha_programada"' in src
