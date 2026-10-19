"""Regresiones del editor de croquis etapa 2, sin interfaz Tk."""
import base64
import copy
import io
import json

import pytest
from PIL import Image, ImageDraw
from reportlab.platypus import Image as RLImage

from services.croquis_documento import (
    BASE_KEY, PNG_KEY, WIDTH, HEIGHT, CroquisDocumento,
    hit_test, import_image_bytes, new_image_object, ordered_objects, resize, rotate_90,
)
from services.croquis_simbolos import SYMBOLS, symbol_bitmap


def test_imagen_jpg_se_incrusta_y_permite_edicion_y_roundtrip():
    source = Image.new('RGB', (600, 360), '#efd8ba')
    ImageDraw.Draw(source).rectangle((30, 30, 200, 150), fill='red')
    buffer = io.BytesIO(); source.save(buffer, format='JPEG')
    encoded = import_image_bytes(buffer.getvalue(), '.jpg')
    obj = new_image_object(encoded)
    doc = CroquisDocumento(); doc.add(obj)
    doc.add({'kind': 'arrow', 'coords': [40,40,250,100], 'layer':'trazos',
             'color':'#0369F8','width':6})
    png = base64.b64decode(doc.export_base64())
    assert RLImage(io.BytesIO(png)).imageWidth == WIDTH
    restored = CroquisDocumento(base64.b64encode(png).decode('ascii'))
    assert restored.objects == doc.objects
    assert restored.objects[0]['kind'] == 'image'
    assert len(restored.layers) == 4
    assert len(restored.render().getbands()) == 3
    old = copy.deepcopy(restored.objects[0])
    resize(restored.objects[0], (old['coords'][0], old['coords'][1]),
           (old['coords'][2]+50, old['coords'][3]+20), old)
    assert restored.objects[0]['coords'][2] > old['coords'][2]


def test_png_transparente_conserva_transparencia():
    original = Image.new('RGBA', (220, 100), (0,0,0,0))
    ImageDraw.Draw(original).rectangle((10, 10, 150, 85), fill=(200,20,20,180))
    data = io.BytesIO(); original.save(data,'PNG')
    encoded = import_image_bytes(data.getvalue(), '.png')
    restored = CroquisDocumento()
    restored.add(new_image_object(encoded))
    reopened = CroquisDocumento(restored.export_base64())
    assert reopened.objects[0]['image_b64'] == encoded
    assert reopened.render().getpixel((0,0)) == (255,255,255)


def test_simbolos_todos_se_renderizan_y_se_guardan():
    for kind in SYMBOLS:
        bitmap = symbol_bitmap(kind, '#0369F8', 70, 70)
        assert bitmap.size == (70,70)
        assert bitmap.getbbox() is not None
    doc = CroquisDocumento()
    doc.add({'kind':'symbol','symbol':'camara_bullet','coords':[40,40,100,100],
             'color':'#DC2626','layer':'simbolos'})
    assert doc.render().getpixel((0,0)) == (255,255,255)
    rotate_90(doc.objects[0])
    assert doc.objects[0]['rotation'] == 90
    reopened = CroquisDocumento(doc.export_base64())
    assert reopened.objects[0]['rotation'] == 90
    assert hit_test(reopened.objects, 70,70, layers=reopened.layers) == 0


def test_capas_ocultas_y_bloqueadas_se_respetan_en_lienzo_pdf_y_seleccion():
    doc = CroquisDocumento()
    doc.add({'kind':'rectangle','coords':[10,10,150,150],'color':'#DC2626',
             'width':8,'layer':'trazos'})
    doc.add({'kind':'rectangle','coords':[10,10,150,150],'color':'#16A34A',
             'width':8,'layer':'simbolos'})
    assert doc.render().getpixel((10,80)) == (22,163,74)
    assert hit_test(doc.objects, 70,70, layers=doc.layers) == 1
    doc.configure_layer('simbolos', visible=False)
    assert hit_test(doc.objects, 70,70, layers=doc.layers) == 0
    assert doc.render().getpixel((10,80)) == (220,38,38)
    doc.configure_layer('simbolos', visible=True, locked=True)
    assert doc.render().getpixel((10,80)) == (22,163,74)
    assert hit_test(doc.objects, 70,70, layers=doc.layers) == 0
    doc.configure_layer('simbolos', locked=False)
    assert hit_test(doc.objects, 70,70, layers=doc.layers) == 1
    reopened = CroquisDocumento(doc.export_base64())
    assert reopened.layer('simbolos')['visible']
    assert not reopened.layer('simbolos')['locked']
    assert reopened.render().getpixel((10,80)) == (22,163,74)


def test_reordenacion_capas_personalizadas_undo_redo():
    doc = CroquisDocumento()
    custom = doc.add_layer('Cableado')
    doc.add({'kind':'text','text':'ABC','x':10,'y':10,'layer':custom,'size':20})
    assert doc.layers[-1]['id'] == custom
    assert doc.move_layer(custom, -1)
    assert doc.layers[-2]['id'] == custom
    assert doc.undo() and doc.layers[-1]['id'] == custom
    assert doc.redo() and doc.layers[-2]['id'] == custom
    doc.configure_layer(custom, name='Canalizaciones')
    assert doc.layer(custom)['name'] == 'Canalizaciones'
    assert len(CroquisDocumento(doc.export_base64()).layers) == 5


def test_compatibilidad_png_fase_uno_y_croquis_legado():
    old_doc = CroquisDocumento()
    old_doc.add({'kind':'line','coords':[10,15,80,100],'color':'#172554','width':3})
    current = base64.b64decode(old_doc.export_base64())
    # Simular fase 1: mismo PNG pero sin campo layers.
    from PIL import PngImagePlugin
    with Image.open(io.BytesIO(current)) as img:
        payload = json.loads(img.info[PNG_KEY]); payload.pop('layers')
        info = PngImagePlugin.PngInfo(); info.add_text(PNG_KEY, json.dumps(payload), zip=True)
        raw = io.BytesIO(); img.save(raw, format='PNG', pnginfo=info)
    restored = CroquisDocumento(base64.b64encode(raw.getvalue()).decode('ascii'))
    assert restored.objects == old_doc.objects
    assert restored.render().getpixel((10,15)) != (255,255,255)
    raw_legacy = io.BytesIO(); Image.new('RGB',(WIDTH,HEIGHT),'#eeeedd').save(raw_legacy,'PNG')
    legacy = CroquisDocumento(base64.b64encode(raw_legacy.getvalue()).decode('ascii'))
    assert legacy.legacy_background
    legacy.add({'kind':'symbol','symbol':'rack','coords':[10,10,80,80],'layer':'simbolos'})
    reopened = CroquisDocumento(legacy.export_base64())
    assert reopened.legacy_background
    assert reopened.objects[0]['kind'] == 'symbol'


def test_importa_primera_pagina_pdf():
    fitz = pytest.importorskip('fitz')
    pdf = fitz.open(); page=pdf.new_page(width=400,height=300)
    page.draw_rect(fitz.Rect(20,20,250,200),color=(1,0,0))
    raw = pdf.tobytes(); pdf.close()
    encoded = import_image_bytes(raw,'.pdf')
    doc = CroquisDocumento(); doc.add(new_image_object(encoded))
    assert CroquisDocumento(doc.export_base64()).objects[0]['kind']=='image'


def test_interfaz_contiene_botones_operativos_de_fase_dos():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    view = (root / 'views' / 'croquis_editor_view.py').read_text(encoding='utf-8')
    for fragment in ('import_plan', 'SYMBOLS', 'symbol_bitmap', 'new_image_object',
                     'toggle_layer', 'add_layer', 'reorder_layer', 'move_to_layer',
                     'doc.export_base64()', 'doc.undo()', 'doc.redo()'):
        assert fragment in view
    assert (root/'services'/'croquis_simbolos.py').exists()


def test_imagen_horizontal_rota_90_no_se_recorta():
    source = Image.new('RGB', (400, 180), '#DC2626')
    buff = io.BytesIO(); source.save(buff, 'JPEG')
    obj = new_image_object(import_image_bytes(buff.getvalue(), '.jpg'))
    before = (obj['coords'][2]-obj['coords'][0], obj['coords'][3]-obj['coords'][1])
    rotate_90(obj)
    after = (obj['coords'][2]-obj['coords'][0], obj['coords'][3]-obj['coords'][1])
    assert round(after[0]) == round(before[1])
    assert round(after[1]) == round(before[0])
    doc = CroquisDocumento(); doc.add(obj)
    assert doc.render().getpixel((WIDTH//2, HEIGHT//2))[0] > 150
    assert CroquisDocumento(doc.export_base64()).objects == doc.objects
