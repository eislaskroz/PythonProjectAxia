from pathlib import Path

LEV = Path('views/levantamiento_view.py').read_text(encoding='utf-8')
OBRA = Path('views/obra_civil_view.py').read_text(encoding='utf-8')
SERVICE = Path('services/obras_civiles_service.py').read_text(encoding='utf-8')


def test_nuevos_levantamientos_comparten_canalizacion_dinamica():
    bloque = LEV.split('tipos_con_canalizacion = {', 1)[1].split('}', 1)[0]
    for nombre in ('Paneles Solares', 'Plantas de Energía', 'Aires Acondicionados'):
        assert f'"{nombre}"' in bloque


def test_si_requiere_canalizacion_exige_partida_y_cantidad_positiva():
    assert 'if not filas:' in LEV
    assert 'if float(cantidad) <= 0:' in LEV
    assert 'return canalizacion_materiales_completa()' in LEV
    assert 'Aires Acondicionados' in LEV and 'and canalizacion_materiales_completa()' in LEV


def test_obra_civil_incluye_repetidor_y_valida_si_no():
    assert 'seccion("Canalización, cableado y materiales"' in OBRA
    assert 'var_requiere_canalizacion = ctk.StringVar(value="Sí")' in OBRA
    assert 'def canalizacion_obra_completa()' in OBRA
    assert 'if var_requiere_canalizacion.get() == "No":' in OBRA
    assert 'if not filas:' in OBRA
    assert 'if not canalizacion_obra_completa():' in OBRA


def test_obra_civil_persiste_en_json_existente_sin_columna_nueva():
    assert '"_canalizacion_materiales": {' in OBRA
    assert '"partidas": obtener_canalizacion_materiales_obra()' in OBRA
    assert 'obc_ejecucion_json' in SERVICE
    assert 'obc_canalizacion' not in SERVICE


def test_obra_civil_pdf_incluye_partidas_canalizacion():
    assert 'def seccion_canalizacion_pdf()' in OBRA
    assert OBRA.count('("Canalización, cableado y materiales", ["Categoría", "Tipo", "Especificación", "Cantidad", "Unidad"], seccion_canalizacion_pdf())') == 2
