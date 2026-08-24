from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_actualizador_ya_no_depende_de_powershell():
    txt=(ROOT/'services/update_service.py').read_text(encoding='utf-8')
    assert 'ShellExecuteW' in txt
    assert '"runas"' in txt
    assert 'powershell.exe' not in txt
    assert '/SILENT' in txt

def test_inno_reabre_axia_en_modo_silencioso():
    txt=(ROOT/'installer/AXIA.iss').read_text(encoding='utf-8')
    assert 'Check: WizardSilent' in txt
    assert 'skipifsilent' in txt

def test_build_update_exige_instalador_completo():
    txt=(ROOT/'scripts/build_update.ps1').read_text(encoding='utf-8')
    assert 'AXIA_Setup_$Version.exe' in txt
    assert 'NO publiques dist' in txt and 'AXIA.exe' in txt

def test_dialogos_principales_usan_centrado_comun():
    app=(ROOT/'app.py').read_text(encoding='utf-8')
    helpers=(ROOT/'views/formato_helpers.py').read_text(encoding='utf-8')
    detail=(ROOT/'ui/detail_popup.py').read_text(encoding='utf-8')
    assert app.count('centrar_ventana(dialogo') >= 2
    assert 'centrar_ventana(win' in helpers
    assert 'centrar_ventana(ventana, 760, 560' in detail
