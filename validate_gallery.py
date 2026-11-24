from pathlib import Path
import fitz
from PIL import Image,ImageOps
from io import BytesIO
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from services.pdf_fotos_inteligentes import FotoPdf,construir_filas_fotos
from core.pdf.base_pdf import BasePdfGenerator

p=Path('/mnt/data/axia_bitacoras_fotos_alineadas')
fotos=[]
for name in ('BIT-00018.pdf','BIT-00012.pdf','BIT-00001.pdf','BIT-00006.pdf'):
    doc=fitz.open('/mnt/data/'+name)
    for page in doc:
        for item in page.get_images(full=True):
            if item[2]==834 and item[3]==1067:
                continue
            raw=doc.extract_image(item[0])['image']
            with Image.open(BytesIO(raw)) as img:
                img=ImageOps.exif_transpose(img)
                img.thumbnail((1800,1800))
                buff=BytesIO()
                img.convert('RGB').save(buff,'PNG')
                fotos.append(FotoPdf(buff.getvalue(),f'{name}',img.width,img.height))

for align in ('CENTER','LEFT'):
    title=ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=8,leading=10,textColor=colors.white)
    w=6.55*inch
    h=Table([[Paragraph('EVIDENCIA FOTOGRÁFICA',title)]],colWidths=[w],hAlign='LEFT')
    h.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#1F4E79')),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    filas=construir_filas_fotos(fotos,estilo_texto=title,ancho_total=w,alineacion=align)
    out=p/f'galeria_{align.lower()}.pdf'
    story=[KeepTogether([h,Spacer(1,5),filas[0]]),*filas[1:]]
    doc=SimpleDocTemplate(str(out),pagesize=letter,leftMargin=34,rightMargin=34,topMargin=96,bottomMargin=78)
    doc.build(story,onFirstPage=lambda c,d:BasePdfGenerator.draw_page(c,d,title='Bitácora de Avance'),onLaterPages=lambda c,d:BasePdfGenerator.draw_page(c,d,title='Bitácora de Avance'))
    d=fitz.open(out)
    print(align,'fotos',len(fotos),'paginas',len(d))
    for i in range(min(2,len(d))):
        pix=d[i].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
        pix.save(str(p/f'galeria_{align.lower()}_pagina{i+1}.png'))
