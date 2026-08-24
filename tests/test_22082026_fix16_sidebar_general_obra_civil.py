from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sidebar_tiene_fondo_general_y_obra_civil():
    txt = (ROOT / 'ui' / 'app_sidebar.py').read_text(encoding='utf-8')
    assert '_FONDO_SIDEBAR_GENERAL = "fondo_general.png"' in txt
    assert '"Obra Civil": "fondo_obra_civil.png"' in txt
    assert (ROOT / 'assets' / 'fondo_general.png').exists()
    assert (ROOT / 'assets' / 'fondo_obra_civil.png').exists()


def test_sidebar_no_oculta_fondo_cuando_tipo_es_none():
    txt = (ROOT / 'ui' / 'app_sidebar.py').read_text(encoding='utf-8')
    # La implementación anterior ocultaba el label cuando no había tipo.
    assert 'if not tipo:\n        try:\n            label.place_forget()' not in txt
    assert '_FONDOS_SIDEBAR.get(str(tipo or "").strip(), _FONDO_SIDEBAR_GENERAL)' in txt


def test_version_fix16_sincronizada():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    iss = (ROOT / 'installer' / 'AXIA.iss').read_text(encoding='utf-8')
    import re
    app_ver = re.search(r'APP_VERSION = "([^"]+)"', version).group(1)
    iss_ver = re.search(r'#define MyAppVersion "([^"]+)"', iss).group(1)
    assert app_ver == iss_ver
