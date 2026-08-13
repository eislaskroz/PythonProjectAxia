from pathlib import Path

SRC = Path('views/inicio_aco_view.py').read_text(encoding='utf-8')


def test_aco_importa_altas_y_actualizaciones_cliente():
    assert 'crear_cliente,' in SRC
    assert 'actualizar_cliente,' in SRC


def test_aco_tiene_botones_cliente_nuevo_y_modificar():
    assert 'text="+ Cliente nuevo"' in SRC
    assert 'text="Modificar cliente"' in SRC
    assert 'abrir_editor_cliente("nuevo")' in SRC
    assert 'abrir_editor_cliente("editar")' in SRC


def test_editor_refresca_catalogo_y_selecciona_cliente_guardado():
    assert 'def refrescar_clientes(' in SRC
    assert 'selector.configure(values=nombres)' in SRC
    assert 'refrescar_clientes(nombre_guardado)' in SRC


def test_editor_modifica_el_cliente_actual_no_el_aco():
    assert 'actualizar_cliente(' in SRC
    assert 'cliente_actual.get("id_cliente")' in SRC


def test_cliente_nuevo_no_precarga_cliente_seleccionado():
    assert 'if modo == "editar" and cliente_actual:' in SRC
    assert 'if cliente_actual:\n                for nombre_campo' not in SRC


def test_aco_usa_solo_observaciones_en_captura_visible():
    assert 'crear_label("Descripción")' not in SRC
    assert 'txt_descripcion = ctk.CTkTextbox' not in SRC
    assert 'crear_label("Observaciones")' in SRC
    assert '"aco_descripcion": ""' in SRC
    assert '"aco_observaciones": observaciones' in SRC
