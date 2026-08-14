from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEV = (ROOT / 'views' / 'levantamiento_view.py').read_text(encoding='utf-8')
MAIL = (ROOT / 'services' / 'mail_service.py').read_text(encoding='utf-8')


def test_edicion_crea_nuevo_registro_y_no_actualiza_original():
    bloque = LEV[LEV.index('folio_origen_revision = ""'):LEV.index('if resultado:', LEV.index('folio_origen_revision = ""'))]
    assert 'datos["lev_folio"] = ""' in bloque
    assert 'resultado = crear_levantamiento(datos)' in bloque
    assert 'actualizar_levantamiento(id_levantamiento_edicion, datos)' not in bloque


def test_interfaz_explica_que_se_guarda_nueva_version():
    assert 'text="💾 Guardar Nueva Versión" if registro_editar' in LEV
    assert 'Se conservó {folio_origen_revision} y se creó la nueva versión {folio}.' in LEV


def test_correo_identifica_revision_y_folio_origen():
    assert 'folio_origen: str = ""' in MAIL
    assert 'Nueva versión de levantamiento' in MAIL
    assert 'Versión generada a partir de: {folio_origen}' in MAIL
