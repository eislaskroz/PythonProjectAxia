from pathlib import Path

SERVICE = Path('services/update_service.py').read_text(encoding='utf-8')
APP = Path('app.py').read_text(encoding='utf-8')


def test_descarga_valida_ejecutable_windows():
    assert 'firma_mz != b"MZ"' in SERVICE
    assert 'no es un instalador válido de Windows' in SERVICE


def test_instalador_se_ejecuta_elevado_sin_powershell():
    assert 'ShellExecuteW' in SERVICE
    assert '"runas"' in SERVICE
    assert 'powershell.exe' not in SERVICE
    assert '/SILENT' in SERVICE


def test_actualizador_conserva_lectura_de_estado_legacy():
    # Se conserva para poder avisar si quedó un fallo registrado por FIX13 o anterior.
    assert 'def consumir_estado_actualizacion' in SERVICE
    assert 'self.after(1200, self._mostrar_estado_actualizacion_anterior)' in APP
