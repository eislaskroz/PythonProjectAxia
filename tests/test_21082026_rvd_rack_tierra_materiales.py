from pathlib import Path

VIEW = Path('views/levantamiento_view.py').read_text(encoding='utf-8')
PDF = Path('services/pdf_registro_service.py').read_text(encoding='utf-8')


def test_rack_permite_kit_o_accesorios_separados():
    assert '"Kit completo", "Rack solo + accesorios"' in VIEW
    for campo in ('rack_organizadores', 'rack_charolas', 'rack_pdu', 'rack_panel_parcheo'):
        assert campo in VIEW
    assert 'if var_rvd_modalidad_rack.get() == "Rack solo + accesorios"' in VIEW


def test_tierra_fisica_captura_materiales_requeridos():
    assert '¿Se requiere sistema de tierra física?' in VIEW
    for campo in (
        'tierra_barra_cobre', 'tierra_aisladores_cobre', 'tierra_varilla_cobre',
        'tierra_abrazaderas_cobre', 'tierra_cable_cobre', 'tierra_quimico',
        'tierra_tuberia', 'tierra_bote',
    ):
        assert campo in VIEW
        assert f'"{campo}"' in PDF


def test_compatibilidad_tierra_fisica_legacy():
    assert 'if "requiere_tierra_fisica" not in hojas and "tierra_fisica" in hojas' in VIEW
