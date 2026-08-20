from pathlib import Path


def test_preview_pdf_no_exige_guardar_pero_exige_captura_completa():
    texto = Path('views/cotizaciones_view.py').read_text(encoding='utf-8')
    assert 'text="👁 PDF Cotización (Preview)"' in texto
    assert 'COT-BORRADOR' in texto
    assert 'def validar_captura_completa' in texto
    assert 'btn_pdf.configure(state="normal" if valida else "disabled")' in texto
    assert 'guardar_cotizacion_comercial' not in texto[texto.index('def pdf():'):texto.index('def cargar_seleccion():')]
