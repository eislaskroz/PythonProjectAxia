from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEV = (ROOT / "views" / "levantamiento_view.py").read_text(encoding="utf-8")
CONV = (ROOT / "views" / "orden_servicio_conversion_view.py").read_text(encoding="utf-8")

def test_editor_reabre_formulario_original_en_popup():
    assert "def abrir_editor_origen" in CONV
    assert "CTkToplevel" in CONV
    assert "registro_editar=original" in CONV
    assert "modal=True" in CONV
    assert "command=abrir_editor_origen" in CONV

def test_formulario_levantamiento_soporta_modo_edicion():
    assert "registro_editar=None" in LEV
    assert "def _cargar_registro_edicion" in LEV
    assert 'datos["lev_folio"] = ""' in LEV
    assert "resultado = crear_levantamiento(datos)" in LEV
    assert 'text="💾 Guardar Nueva Versión" if registro_editar' in LEV

def test_edicion_preserva_relaciones_y_evidencias():
    assert 'for campo_id in ("id_aco", "id_cliente", "id_sucursal", "id_contacto")' in LEV
    assert 'datos["lev_evidencias_json"] = registro_editar.get("lev_evidencias_json") or "[]"' in LEV
    assert 'evidencias_previas = _json_list' in LEV

def test_precarga_detalle_y_listas_dinamicas():
    assert 'detalle = _json_dict(registro.get("lev_detalle_tecnico_json"))' in LEV
    assert 'agregar_partida_canalizacion' in LEV
    assert 'agregar_equipo_catalogo()' in LEV
    assert 'agregar_material_miscelaneo' in LEV

def test_precarga_no_usa_stringvar_como_llave_de_diccionario():
    assert "comunes = [" in LEV
    assert "for variable, valor in comunes:" in LEV
    assert "comunes[var_encargado_proyecto]" not in LEV
