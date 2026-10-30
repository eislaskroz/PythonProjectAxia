"""Regresión visual estática: conceptos largos de Obra Civil sin truncar."""
from pathlib import Path

FUENTE = (Path(__file__).resolve().parents[2] / "views" / "obra_civil_view.py").read_text(encoding="utf-8")


def test_catalogo_conserva_selector_y_lectura_multilinea():
    assert 'NativeComboBox(cont_concepto, variable=vconcepto' in FUENTE
    assert 'concepto_vista = AxiaTextbox(cont_concepto, height=66, wrap="word", state="disabled")' in FUENTE
    assert 'concepto_vista.insert("1.0", texto)' in FUENTE
    assert 'concepto_vista.grid(row=1, column=0, sticky="ew")' in FUENTE


def test_otros_tiene_texto_libre_tres_renglones_y_sincroniza_variable():
    assert 'econcepto = AxiaTextbox(cont_concepto, height=99, wrap="word")' in FUENTE
    assert 'vconcepto.set(texto)' in FUENTE
    assert 'econcepto.bind("<KeyRelease>", _capturar_concepto_manual)' in FUENTE
    assert 'econcepto.bind("<FocusOut>", _capturar_concepto_manual)' in FUENTE
    assert 'item_concepto["concepto_label"].get().strip()' in FUENTE or 'item["concepto_label"].get().strip()' in FUENTE


def test_alternar_tipo_no_superpone_cajas_y_recupera_borrador():
    assert 'concepto_vista.grid_remove()' in FUENTE
    assert 'oconcepto.grid_remove()' in FUENTE
    assert 'econcepto.grid_remove()' in FUENTE
    assert 'item["concepto_label"].set(str(fila.get("concepto") or ""))' in FUENTE
