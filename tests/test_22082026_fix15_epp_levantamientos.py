from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEV = (ROOT / 'views' / 'levantamiento_view.py').read_text(encoding='utf-8')
OBC = (ROOT / 'views' / 'obra_civil_view.py').read_text(encoding='utf-8')
PDF = (ROOT / 'services' / 'levantamiento_seguridad_pdf.py').read_text(encoding='utf-8')
VER = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
ISS = (ROOT / 'installer' / 'AXIA.iss').read_text(encoding='utf-8')


def test_epp_comun_en_levantamientos():
    assert '¿Se requiere Equipo de Protección Personal?' in LEV
    assert 'CATALOGO_EPP' in LEV
    assert 'def obtener_epp_json()' in LEV
    assert 'detalle["epp"]' in LEV
    assert 'var_requiere_epp.get() == "Sí"' in LEV


def test_epp_se_restaura_en_edicion():
    assert 'epp_guardado = detalle.get("epp")' in LEV
    assert 'agregar_epp(fila)' in LEV


def test_pdf_muestra_epp():
    assert 'def _epp_rows' in PDF
    assert 'Equipo de Protección Personal (EPP)' in PDF
    assert '"epp"' in PDF


def test_obra_civil_incluye_epp_sin_nueva_columna():
    assert '¿Se requiere EPP?' in OBC
    assert 'def obtener_epp_obra()' in OBC
    assert '"_epp": {"requiere": var_requiere_epp.get(), "partidas": obtener_epp_obra()}' in OBC
    assert 'Equipo de Protección Personal' in OBC


def test_version_sincronizada():
    import re
    app_ver = re.search(r'APP_VERSION = "([^"]+)"', VER).group(1)
    iss_ver = re.search(r'#define MyAppVersion "([^"]+)"', ISS).group(1)
    assert app_ver == iss_ver
