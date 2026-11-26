import base64
from io import BytesIO
from unittest.mock import Mock
from PIL import Image, ImageDraw
from pypdf import PdfReader
from services import levantamiento_seguridad_pdf as renderer


def image_bytes(size, color):
    buf = BytesIO()
    image = Image.new('RGB', size, 'white')
    ImageDraw.Draw(image).rectangle((20,20,size[0]-20,size[1]-20), outline=color, width=12)
    image.save(buf, 'PNG')
    return buf.getvalue()


def test_pdf_layout_with_plan_photo_and_signoff(tmp_path, monkeypatch):
    plan = image_bytes((1080,2400),'blue')
    photo = image_bytes((1440,1920),'green')
    annotation = image_bytes((1200,800),'black')
    signature = image_bytes((300,100),'black')
    paths = {'LEV-00145/plan.png':plan,'LEV-00145/foto.png':photo}
    fetch = Mock(side_effect=paths.__getitem__)
    monkeypatch.setattr(renderer,'descargar_evidencia_field',fetch)
    registro = dict(lev_folio='LEV-00145', lev_tipo=11, lev_tipo_levantamiento='General',
        lev_modalidad_operativa='General', lev_cliente='Cliente de prueba', lev_descripcion='Levantamiento de prueba desde Android',
        lev_fecha_programada='2026-11-26', lev_direccion='Calle de prueba, número 123, colonia de prueba, municipio de prueba, estado de prueba',
        lev_direccion_sucursal='Otra calle de prueba, número 456, municipio de prueba, código postal 00000',
        lev_contacto='Contacto de prueba', lev_correo='contacto@example.com', lev_personas_considerar=2, lev_dias_trabajo=50,
        lev_tecnico='Técnico de prueba',lev_observaciones='OK',
        lev_detalle_tecnico_json={'canalizacion_materiales':[{'material':'Tubo','tipo':'Conduit metálico de pared intermedia','medida':'1/2" (13mm)','cantidad':'150','unidad':'Pieza(s)'}], 'vobo_nombre':'Cliente de prueba','vobo_puesto':'Desarrollo'},
        lev_firma_cliente=base64.b64encode(signature).decode(),
        lev_anotacion_plano_json={'imagen_base64':base64.b64encode(annotation).decode()},
        lev_evidencias_json=[{'bucket':'levantamientos-evidencias','storage_path':p,'mime':'image/png','relacion_clave':'attached_plans' if 'plan' in p else 'photo'} for p in paths])
    dest=tmp_path/'layout.pdf'
    renderer.generar_pdf_levantamiento_maestro(registro,ruta_salida=dest)
    reader=PdfReader(dest)
    pages=[(p.extract_text() or '').casefold() for p in reader.pages]
    assert len(pages)<=2, pages
    assert any('vobo del cliente' in p and 'elaborado por:' in p for p in pages)
    for heading in ['anotaciones tipo plano','plano adjunto','evidencia fotográfica']:
        assert any(heading in p for p in pages)
    assert fetch.call_count == 2
    # Ensure both protected images appear as image XObjects.
    sizes={(o.get_object().get('/Width'),o.get_object().get('/Height')) for p in reader.pages for o in p['/Resources'].get('/XObject',{}).get_object().values()}
    assert (1080,2400) in sizes and (1440,1920) in sizes
