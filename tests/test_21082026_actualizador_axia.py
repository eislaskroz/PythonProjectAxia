from pathlib import Path

from core.version import APP_VERSION, es_version_mas_nueva


def test_version_central_actualizada():
    assert APP_VERSION == "2.02.0"
    assert es_version_mas_nueva("2.02.1") is True
    assert es_version_mas_nueva("2.03.0") is True
    assert es_version_mas_nueva("2.02.0") is False
    assert es_version_mas_nueva("2.01.99") is False


def test_login_usa_version_centralizada():
    texto = Path("login.py").read_text(encoding="utf-8")
    assert "from core.version import APP_VERSION" in texto
    assert 'text=f"Sistema AXIA · v{APP_VERSION}"' in texto


def test_app_comprueba_actualizaciones_en_segundo_plano():
    texto = Path("app.py").read_text(encoding="utf-8")
    assert "self.after(1800, self._comprobar_actualizacion_axia)" in texto
    assert "Actualizar ahora" in texto
    assert "Más tarde" in texto
    assert "Salir de AXIA" in texto
    assert "descargar_actualizacion" in texto
    assert "programar_instalacion" in texto


def test_servicio_verifica_integridad_y_actualiza_con_instalador():
    texto = Path("services/update_service.py").read_text(encoding="utf-8")
    assert 'TABLA_ACTUALIZACIONES = "db_actualizaciones"' in texto
    assert "hashlib.sha256" in texto
    assert "/VERYSILENT" in texto
    assert "/CLOSEAPPLICATIONS" in texto
    assert "AXIA_Update" not in texto  # no depende de un exe que pueda quedar bloqueado


def test_migracion_actualizaciones_es_lectura_para_cliente():
    texto = Path("migrations/20260821_actualizaciones_axia.sql").read_text(encoding="utf-8")
    assert "create table if not exists public.db_actualizaciones" in texto.lower()
    assert "enable row level security" in texto.lower()
    assert "for select" in texto.lower()
    assert "to anon, authenticated" in texto.lower()


def test_instalador_conserva_appid_y_version_nueva():
    texto = Path("installer/AXIA.iss").read_text(encoding="utf-8")
    assert '#define MyAppVersion "2.02.0"' in texto
    assert "AppId={{9B5A9E1C-BDC2-4E75-A842-5B1189702F37}" in texto
    assert "UsePreviousAppDir=yes" in texto
