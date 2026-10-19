"""Pruebas sin entorno gráfico: compatibilidad Base64, edición y PDF."""
import base64
import io
import json

from PIL import Image, ImageDraw
from reportlab.platypus import Image as RLImage

from services.croquis_documento import (
    CroquisDocumento, WIDTH, HEIGHT, PNG_KEY, bounds, hit_test, translate, resize, rotate_90,
)


def png_legacy():
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    ImageDraw.Draw(img).line((25, 30, 250, 70), fill="black", width=5)
    buff = io.BytesIO(); img.save(buff, "PNG")
    return base64.b64encode(buff.getvalue()).decode("ascii")


def test_png_nuevo_persiste_objetos_reeditables_y_pdf_reportlab():
    doc = CroquisDocumento()
    doc.add({"kind":"line", "coords":[10,10,100,80], "color":"#0369F8", "width":3})
    doc.add({"kind":"arrow", "coords":[130,40,280,90], "color":"#16A34A", "width":4})
    doc.add({"kind":"rectangle", "coords":[15,100,180,180], "color":"#DC2626", "width":5})
    doc.add({"kind":"ellipse", "coords":[270,120,390,230], "color":"#F59E0B", "width":2})
    doc.add({"kind":"text", "x":300, "y":50, "size":20, "text":"Rack 01", "color":"#111827"})
    doc.add({"kind":"stroke", "points":[[20,200],[80,210],[170,200]], "color":"#172554", "width":3})
    base64_png = doc.export_base64()
    raw = base64.b64decode(base64_png)
    with Image.open(io.BytesIO(raw)) as img:
        assert img.size == (WIDTH, HEIGHT)
        assert img.format == "PNG"
        assert json.loads(img.info[PNG_KEY])["version"] == 1
    assert RLImage(io.BytesIO(raw)).imageWidth == WIDTH
    reopened = CroquisDocumento(base64_png)
    assert reopened.objects == doc.objects
    assert not reopened.legacy_background
    reopened.modify(4, text="Rack 02")
    assert CroquisDocumento(reopened.export_base64()).objects[4]["text"] == "Rack 02"


def test_legado_se_mantiene_como_capa_de_fondo_y_se_edita_encima():
    doc = CroquisDocumento(png_legacy())
    assert doc.legacy_background
    assert not doc.objects
    assert doc.background.getpixel((80, 40)) != (255, 255, 255)
    doc.add({"kind":"text", "x":5, "y":5, "text":"Nuevo", "size":20, "color":"#172554"})
    reopened = CroquisDocumento(doc.export_base64())
    assert reopened.legacy_background
    assert reopened.objects[0]["text"] == "Nuevo"
    assert reopened.background.getpixel((80,40)) == doc.background.getpixel((80,40))


def test_desplazamiento_redimensionado_y_seleccion_de_objeto():
    obj = {"kind":"rectangle", "coords":[20,30,120,130], "color":"#172554", "width":2}
    assert hit_test([obj], 20, 70) == 0
    assert hit_test([obj], 70, 70) == 0
    translate(obj, 15, 10)
    assert bounds(obj) == (35,40,135,140)
    start = json.loads(json.dumps(obj))
    resize(obj, (35,40), (235,240), start)
    assert bounds(obj) == (35,40,235,240)


def test_undo_redo_guardado_y_no_modificar_original_sin_guardar():
    doc = CroquisDocumento()
    doc.add({"kind":"line", "coords":[0,0,100,100], "color":"#172554", "width":3})
    doc.duplicate(0)
    assert len(doc.objects) == 2
    assert doc.objects[1]["coords"] == [18,18,118,118]
    assert doc.undo() and len(doc.objects) == 1
    assert doc.redo() and len(doc.objects) == 2
    doc.delete(0)
    assert len(doc.objects) == 1
    doc.clear()
    assert not doc.objects
    assert doc.undo() and len(doc.objects) == 1


def test_colores_y_trazos_el_png_resultante_conserva_color():
    doc = CroquisDocumento()
    doc.add({"kind":"rectangle", "coords":[30,30,90,90], "color":"#DC2626", "width":4})
    with Image.open(io.BytesIO(base64.b64decode(doc.export_base64()))) as image:
        assert image.getpixel((30,60)) == (220,38,38)
    doc.modify(0, color="#16A34A")
    with Image.open(io.BytesIO(base64.b64decode(doc.export_base64()))) as image:
        assert image.getpixel((30,60)) == (22,163,74)


def test_opciones_editor_etapa_uno_estan_conectadas():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    common = (root/'views'/'formato_helpers.py').read_text(encoding='utf-8')
    editor = (root/'views'/'croquis_editor_view.py').read_text(encoding='utf-8')
    assert 'from views.croquis_editor_view import anotacion_plano_popup' in common
    for required in ('select', 'stroke', 'erase', 'line', 'arrow', 'rectangle', 'ellipse', 'text'):
        assert f'"{required}"' in editor
    assert 'doc.export_base64()' in editor
    assert 'doc.undo()' in editor and 'doc.redo()' in editor
    assert 'state["grid"]' in editor


def test_giro_90_linea_y_texto_vuelven_a_abrir():
    doc = CroquisDocumento()
    line = {"kind":"line", "coords":[100,100,200,100], "color":"#0369F8", "width":3}
    rotate_90(line)
    assert line["coords"] == [150,50,150,150]
    doc.add(line)
    label = {"kind":"text", "x":300, "y":45, "text":"Cámara A", "size":22, "color":"#DC2626"}
    rotate_90(label)
    assert label["rotation"] == 90
    doc.add(label)
    result = CroquisDocumento(doc.export_base64())
    assert result.objects == doc.objects
    assert result.render().getbbox() == (0, 0, WIDTH, HEIGHT)
