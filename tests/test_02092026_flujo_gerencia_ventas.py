from pathlib import Path

MAIL = Path("services/mail_service.py").read_text(encoding="utf-8")
VIEW = Path("views/orden_servicio_conversion_view.py").read_text(encoding="utf-8")
COT = Path("services/cotizaciones_service.py").read_text(encoding="utf-8")
SCHEMA = Path("services/levantamientos_schema.py").read_text(encoding="utf-8")
MIG = Path("migrations/02092026_asignacion_cotizaciones_ventas.sql").read_text(encoding="utf-8")


def test_levantamiento_nuevo_va_directo_a_gerencia_con_bcc():
    bloque = MAIL[MAIL.index("def enviar_levantamiento_pdf"):MAIL.index("def enviar_levantamiento_validacion_ventas")]
    assert 'to=["gte.ventas@axiacomunicaciones.mx"]' in bloque
    assert 'bcc=["eislaskroz@gmail.com"]' in bloque
    assert "mmachuca@axiacomunicaciones.mx" not in MAIL


def test_bcc_no_se_publica_como_encabezado():
    assert 'msg["Bcc"]' not in MAIL
    assert "receptores = destinatarios + copias + copias_ocultas" in MAIL


def test_gerencia_asigna_obligatoriamente_a_usuario_tipo_6():
    assert "obtener_usuarios_por_tipos([6])" in VIEW
    assert '"lev_asignado_ventas_id": id_vendedor' in VIEW
    assert '"lev_validado_ventas": True' in VIEW
    assert 'text="✓ Autorizar y asignar"' in VIEW


def test_ventas_solo_consulta_asignaciones_propias():
    assert 'if tipo_usuario == 6:' in COT
    assert 'lev_asignado_ventas_id' in COT


def test_schema_y_migracion_incluyen_asignacion():
    for campo in ("lev_asignado_ventas_id", "lev_asignado_ventas_nombre", "lev_asignado_ventas_correo", "lev_fecha_asignacion"):
        assert campo in SCHEMA
        assert campo in MIG
