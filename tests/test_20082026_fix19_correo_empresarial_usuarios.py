from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _txt(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_formulario_admin_expone_correo_empresarial():
    txt = _txt("views/usuarios_admin_view.py")
    assert '("usu_correo", "Correo electrónico de empresa", False)' in txt
    assert "correo empresarial" in txt


def test_servicio_ya_usa_columna_usu_correo_sin_migracion_nueva():
    txt = _txt("services/usuarios_service.py")
    assert "usu_correo" in txt.split("COLUMNAS_USUARIOS", 1)[1].splitlines()[0]
    assert 'datos_normalizados["usu_correo"]' in txt
    assert '"usu_correo",\n        "usu_depto"' in txt


def test_cotizaciones_siguen_tomando_correo_del_usuario():
    txt = _txt("services/cotizaciones_service.py")
    assert 'vendedor.get("usu_correo")' in txt


def test_mi_usuario_etiqueta_empresarial():
    txt = _txt("views/mi_bitacora_view.py")
    assert '"usu_correo": "✉️ Correo electrónico de empresa"' in txt
