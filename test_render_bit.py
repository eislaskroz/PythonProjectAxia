import ast, sys, tempfile, json, os, io
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageOps
from tkinter import messagebox
sys.path.insert(0, str(Path(__file__).parent))
from core.pdf.base_pdf import BasePdfGenerator
source=(Path(__file__).parent/'views/formato_helpers.py').read_text('utf8')
node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='_generar_pdf_bitacora_avance_axia')
g={'Path':Path,'tempfile':tempfile,'datetime':datetime,'BasePdfGenerator':BasePdfGenerator,'json':json,'io':io,'os':os,'Image':Image,'ImageOps':ImageOps,'messagebox':messagebox}
exec(compile(ast.Module(body=[node],type_ignores=[]),'<pdf-extract>','exec'),g)
fn=g['_generar_pdf_bitacora_avance_axia']
image_file=Path(__file__).parent/'test_picture.png'
Image.new('RGB',(640,480), '#cedfea').save(image_file)
data={'Folio Bitácora':'BIT-00048','Fecha':'2026-11-24','No. ACO':'NOV-359','Levantamiento':'LEV-00131','OT':'OT-00008','Cliente':'AREZ','Dirección de Servicio':'PRINCIPAL / DATOS DEL CLIENTE','Nombre del Encargado':'ALFONSO SERVÍN','Técnico(s)':'MANUEL FLORES','Hora de Llegada':'08:00','Hora de Salida':'17:00','Descripción del Servicio':'Revisión de Impresoras\n'+'Mantenimiento preventivo y correctivo. '*4,'Porcentaje de Avance':'75%','Fotos':[str(image_file)]*3}
file=Path(__file__).parent/'bitacora_test_1.pdf'
print(fn(data,ruta_salida=file,abrir=False))
data['Descripción del Servicio']='\n'.join([f'Actividad {i:02d}: '+'Inspección, limpieza, ajuste y revisión del equipo. '*4 for i in range(1,100)])
file2=Path(__file__).parent/'bitacora_test_larga.pdf'
print(fn(data,ruta_salida=file2,abrir=False))
from pypdf import PdfReader
for f in (file,file2):
    reader=PdfReader(str(f))
    print(f.name, len(reader.pages), f.stat().st_size)
