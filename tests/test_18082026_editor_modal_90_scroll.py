from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONV = (ROOT / "views" / "orden_servicio_conversion_view.py").read_text(encoding="utf-8")
LEV = (ROOT / "views" / "levantamiento_view.py").read_text(encoding="utf-8")


def test_editor_modal_usa_90_por_ciento_de_pantalla():
    assert "int(screen_w * 0.90)" in CONV
    assert "int(screen_h * 0.90)" in CONV
    assert 'ventana.state("zoomed")' not in CONV


def test_editor_modal_queda_centrado():
    assert "(screen_w - modal_w) // 2" in CONV
    assert "(screen_h - modal_h) // 2" in CONV


def test_formulario_sigue_siend_scrollable_y_botonera_fija():
    assert "CTkScrollableFrame" in LEV
    assert 'frame_botones.pack(side="bottom", fill="x"' in LEV
    assert 'text="💾 Guardar Nueva Versión" if registro_editar' in LEV
