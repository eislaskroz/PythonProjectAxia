from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_pdf_no_duplica_folio_en_subtitulo_y_ordena_datos_como_referencia():
    s = text("services/cotizacion_pdf.py")
    assert 'f"Folio: <b>' not in s
    assert 'p("FECHA DE COTIZACIÓN"' in s
    assert 'p("NO. COTIZACIÓN"' in s
    assert 'p("NO. LEVANTAMIENTO"' in s
    assert s.index('p("FECHA DE COTIZACIÓN"') < s.index('p("NO. COTIZACIÓN"') < s.index('p("NO. LEVANTAMIENTO"')
    assert 'p("PLAN DE PAGOS"' in s
    assert 'p("VIGENCIA DE COTIZACIÓN"' in s


def test_tab_scroll_usa_scrollregion_real_del_canvas():
    s = text("ui/keyboard_navigation.py")
    assert 'canvas.bbox("all")' in s
    assert 'canvas.yview()' in s
    assert 'viewport_height' in s
    assert 'widget_bottom_view' in s
    assert 'canvas.yview_moveto(target_top / content_height)' in s
