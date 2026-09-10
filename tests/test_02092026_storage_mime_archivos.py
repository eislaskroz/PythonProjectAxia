from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'services' / 'bitacora_evidencias_service.py').read_text(encoding='utf-8')
SQL = (ROOT / 'supabase' / 'sql' / '02092026_storage_archivos_tecnicos.sql').read_text(encoding='utf-8')


def test_pdf_usa_mime_explicito():
    assert '".pdf": "application/pdf"' in SRC
    assert '_MIME_ARCHIVOS_TECNICOS.get(ext)' in SRC


def test_bucket_habilita_pdf_y_planos():
    assert "'application/pdf'" in SQL
    assert "where id = 'bitacoras-evidencias'" in SQL
