from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_contactos_se_consultan_cuando_existe_sucursal():
    text = (ROOT / "views" / "levantamiento_view.py").read_text(encoding="utf-8")
    inicio = text.index("def cargar_contactos_sucursal")
    fin = text.index("def cargar_encargado_sucursal", inicio)
    bloque = text[inicio:fin]
    assert "if sucursal:" in bloque
    assert "for contacto in obtener_contactos_por_sucursal(_id_sucursal(sucursal)) or []:" in bloque
    pos_if = bloque.index("if sucursal:")
    pos_for = bloque.index("for contacto in obtener_contactos_por_sucursal")
    pos_else = bloque.index("else:", pos_if)
    assert pos_if < pos_for < pos_else


def test_contactos_alimentan_combo_y_datos_contacto():
    text = (ROOT / "views" / "levantamiento_view.py").read_text(encoding="utf-8")
    assert 'combo_encargado["widget"].configure(values=opciones)' in text
    assert 'var_telefono.set(str(contacto.get("con_telefono") or "").strip())' in text
    assert 'var_correo.set(str(contacto.get("con_correo") or "").strip())' in text
