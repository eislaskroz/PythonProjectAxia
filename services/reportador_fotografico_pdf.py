"""AXIA Reportador fotográfico: réplica nativa del esquema PDF de pdf_service.php.

Referencia: módulo PHP original (noviembre 2026). Carta vertical 612x792 pt,
coordenadas de texto, barras, actividades, fotografías por orientación y páginas
individuales de OS. No necesita PHP ni un navegador.

De forma predeterminada utiliza el mismo fondo vertical corporativo que los
PDF de levantamientos, OS y bitácoras: assets/FormatoFondo.png.
Si se incorpora el fondo exacto del Reportador PHP en
assets/reportador/reporte_base.png, este tiene prioridad. La tipografía
Montserrat se utiliza cuando están disponibles los tres archivos TTF
originales; en su ausencia usa Helvetica, como los otros PDF de Desktop.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys

from PIL import Image as PILImage, ImageOps
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from services import reportador_fotografico_service as service

W, H = 612.0, 792.0
CONTENT_BOTTOM = 728.0
BLUE = colors.HexColor('#124675')
DARK = colors.HexColor('#1C3045')
CYAN = colors.HexColor('#0DABCC')
TEAL = colors.HexColor('#0A6187')
PALE = colors.HexColor('#F0F7FA')
GRAY = colors.HexColor('#526E80')


def _font_names() -> dict[str, str]:
    """No incluimos archivos de tipografía de terceros en el ZIP del usuario."""
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
    candidates = (
        base / 'assets' / 'reportador' / 'fonts',
        Path.home() / 'AppData' / 'Local' / 'Microsoft' / 'Windows' / 'Fonts',
        Path('C:/Windows/Fonts'),
    )
    files = ('Montserrat-Regular.ttf', 'Montserrat-SemiBold.ttf', 'Montserrat-Bold.ttf')
    for folder in candidates:
        if all((folder / name).is_file() for name in files):
            try:
                names = ('RF-Montserrat', 'RF-Montserrat-SemiBold', 'RF-Montserrat-Bold')
                for alias, file in zip(names, files):
                    if alias not in pdfmetrics.getRegisteredFontNames():
                        pdfmetrics.registerFont(TTFont(alias, str(folder / file)))
                return dict(zip(('regular', 'semi', 'bold'), names))
            except Exception:
                continue
    return {'regular': 'Helvetica', 'semi': 'Helvetica-Bold', 'bold': 'Helvetica-Bold'}


def _wrap(value: object, font: str, size: float, max_width: float) -> list[str]:
    """Separar a tamaño real por ancho, sin truncar nombres y descripciones."""
    text = str(value or '')
    result = []
    for paragraph in text.splitlines() or ['']:
        if not paragraph.strip():
            result.append('')
            continue
        line = ''
        for word in paragraph.split():
            proposal = f'{line} {word}'.strip()
            if pdfmetrics.stringWidth(proposal, font, size) <= max_width:
                line = proposal
                continue
            if line:
                result.append(line)
                line = ''
            # Cortar palabras muy largas, correos y enlaces antes que desbordar.
            while word and pdfmetrics.stringWidth(word, font, size) > max_width:
                take = 1
                while take < len(word) and pdfmetrics.stringWidth(word[:take+1], font, size) <= max_width:
                    take += 1
                result.append(word[:take])
                word = word[take:]
            line = word
        result.append(line)
    return result or ['']


def _validate_and_plan(detail: dict) -> tuple[dict, list, list, str]:
    """Emula rf_pdf_valid() + rf_validate_for_finalization() del PHP."""
    report = detail['reporte']
    activities = detail.get('actividades') or []
    if not activities:
        raise service.ErrorReportador('Agrega al menos una actividad antes de generar el PDF.')
    for field in ('aco','cliente','sucursal','nombre_servicio','tecnico_responsable','fecha_servicio'):
        if not str(report.get(field) or '').strip():
            raise service.ErrorReportador('Faltan datos generales del reporte.')
    indexed = {(str(f['clave_actividad']), int(f['numero'])) for f in detail.get('fotos') or []}
    if not 1 <= len(activities) <= service.MAX_ACTIVIDADES:
        raise service.ErrorReportador('Cantidad de actividades incorrecta.')
    for idx, act in enumerate(activities, 1):
        if not str(act.get('titulo') or '').strip():
            raise service.ErrorReportador(f'La actividad {idx} no tiene título.')
        count = int(act.get('cantidad_fotos') or 0)
        if not 1 <= count <= 5:
            raise service.ErrorReportador('Cantidad de fotografías inválida (1 a 5).')
        key = str(act['clave'])
        if any((key, n) not in indexed for n in range(1, count + 1)):
            raise service.ErrorReportador(f'Actividad {idx}: faltan fotografías requeridas ({count}).')
        if any((key, n) in indexed for n in range(count + 1, 6)):
            raise service.ErrorReportador(f'Actividad {idx}: hay fotografías fuera del rango seleccionado.')
    count_os = int(report.get('cantidad_os') or 0)
    if not 1 <= count_os <= 4:
        raise service.ErrorReportador('Selecciona entre 1 y 4 Órdenes de Servicio.')
    order_nums = {int(order['numero']) for order in detail.get('ordenes') or []}
    if order_nums != set(range(1, count_os + 1)):
        raise service.ErrorReportador(f'Faltan Órdenes de Servicio: se necesitan las {count_os} seleccionadas.')
    author = str(report.get('autor_nombre') or '').strip()
    if not author:
        raise service.ErrorReportador('No se encontró el autor original del reporte.')
    return report, activities, list(range(1, count_os + 1)), author


class _OriginalStylePDF:
    def __init__(self, output: BytesIO, report: dict, *, logo_path: str | None = None,
                 background_path: str | None = None):
        self.canvas = Canvas(output, pagesize=(W, H), pageCompression=1,
                             invariant=1)  # salida determinista para pruebas
        self.canvas.setTitle('AXIA ' + str(report.get('aco') or 'REPORTE'))
        self.canvas.setAuthor('AXIA Comunicaciones')
        self.report = report
        self.fonts = _font_names()
        base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
        # Unificar la papelería con el resto de documentos corporativos.
        # Se mantiene la prioridad del fondo original PHP si se facilita después.
        original = base / 'assets' / 'reportador' / 'reporte_base.png'
        corporativo = base / 'assets' / 'FormatoFondo.png'
        provided = Path(background_path) if background_path else None
        self.background = (
            provided if provided and provided.is_file() else
            original if original.is_file() else corporativo
        )
        self.using_corporate_background = self.background == corporativo
        self.logo = Path(logo_path) if logo_path else None
        self.y = 82.0
        self.page()

    def rect(self, x, top, w, h, color):
        self.canvas.setFillColor(color)
        self.canvas.rect(x, H - top - h, w, h, stroke=0, fill=1)

    def text(self, x, top, text, size=10, weight='regular', color=DARK):
        self.canvas.setFillColor(color)
        self.canvas.setFont(self.fonts[weight], size)
        self.canvas.drawString(x, H - top - size, str(text))

    def lines(self, text, size, max_width, leading, weight='regular', x=48, color=DARK):
        for line in _wrap(text, self.fonts[weight], size, max_width):
            self.text(x, self.y, line, size, weight, color)
            self.y += leading

    def page(self, *, new=False):
        if new:
            self.canvas.showPage()
        self.y = 82.0
        if self.background.is_file():
            self.canvas.drawImage(ImageReader(str(self.background)), 0, 0, W, H,
                                  preserveAspectRatio=False, mask='auto')
        else:
            # El PDF PHP cae a hoja blanca si no existe reporte_base.png.
            self.rect(0, 0, W, H, colors.white)

    def image_fit(self, raw: bytes, x: float, top: float, box_width: float,
                  box_height: float, paint_box=True) -> None:
        if paint_box:
            self.rect(x, top, box_width, box_height, PALE)
        try:
            with PILImage.open(BytesIO(raw)) as image:
                normalized = ImageOps.exif_transpose(image).convert('RGB')
                image_width, image_height = normalized.size
                if not image_width or not image_height:
                    raise ValueError('Dimensiones inválidas')
                factor = min(box_width / image_width, box_height / image_height)
                dw, dh = image_width * factor, image_height * factor
                self.canvas.drawImage(ImageReader(normalized),
                                      x + (box_width - dw) / 2,
                                      H - top - (box_height + dh) / 2,
                                      width=dw, height=dh)
        except Exception as exc:
            raise service.ErrorReportador('No se pudo leer una fotografía del reporte.') from exc

    def draw_fields(self):
        r = self.report
        self.text(48, 82, 'REPORTE FOTOGRÁFICO', 18, 'bold', BLUE)
        self.text(48, 112, 'ACO: ' + str(r['aco']), 13, 'bold')
        # Evitar que fechas especialmente largas superen el ancho del papel.
        # FormatoFondo tiene el logotipo en la esquina superior derecha:
        # evitar colocar la fecha encima de él.
        fecha_x = 340 if self.using_corporate_background else 438
        self.text(fecha_x, 114, 'Fecha: ' + service.fecha_para_mostrar(r['fecha_servicio']), 10)
        self.y = 140
        for label, field in [('Cliente', 'cliente'), ('Sucursal / sitio', 'sucursal'),
                             ('Servicio', 'nombre_servicio'), ('Tecnico responsable', 'tecnico_responsable')]:
            self.text(48, self.y, label + ':', 10, 'semi', TEAL)
            start = self.y
            self.lines(r.get(field), 10, 330, 14, x=195)
            self.y = start + max(20, (self.y - start) + 4)
        obs = str(r.get('observaciones') or '').strip()
        if obs:
            self.y += 4
            if self.y + 50 > CONTENT_BOTTOM:
                self.page(new=True)
            self.text(48, self.y, 'Observaciones:', 10, 'bold', TEAL)
            self.y += 16
            for paragraph in _wrap(obs, self.fonts['regular'], 9, 500):
                if self.y + 20 > CONTENT_BOTTOM:
                    self.page(new=True)
                self.text(48, self.y, paragraph, 9)
                self.y += 12
            self.y += 8
        self.y += 8

    def draw_activities(self, acts: list, fetch, report_id: int, author: str):
        for idx, activity in enumerate(acts, 1):
            count = int(activity['cantidad_fotos'])
            pictures = []
            for slot in range(1, count + 1):
                try:
                    data = fetch(report_id, slot, str(activity['clave']))
                    with PILImage.open(BytesIO(data)) as pic:
                        w, h = pic.size
                        aspect = w / h
                except Exception as exc:
                    raise service.ErrorReportador(f'No se pudo cargar la foto {slot} de la actividad {idx}.') from exc
                pictures.append({'data': data, 'aspect': aspect, 'landscape': aspect > 1.12})
            title_lines = _wrap(activity.get('titulo'), self.fonts['bold'], 10, 520)
            description = str(activity.get('descripcion') or '') if activity.get('descripcion_habilitada', True) else ''
            desc_lines = _wrap(description, self.fonts['regular'], 9, 525) if description.strip() else []
            head_need = 12 + 20 + len(title_lines)*15 + 2 + (len(desc_lines)*12 + 10 if desc_lines else 0)
            if head_need + 90 > CONTENT_BOTTOM - 82:
                raise service.ErrorReportador('Descripción demasiado extensa para incluir evidencias.')
            if self.y + head_need + 90 > CONTENT_BOTTOM:
                self.page(new=True)
            self.rect(48, self.y, 520, 2.5, CYAN)
            self.y += 12
            self.text(48, self.y, f'ACTIVIDAD {idx}', 10, 'bold', TEAL)
            self.y += 20
            self.lines(activity.get('titulo'), 10, 520, 15, 'bold', x=48)
            self.y += 2
            if desc_lines:
                for line in desc_lines:
                    self.text(48, self.y, line, 9)
                    self.y += 12
                self.y += 10
            rows = []
            pos = 0
            while pos < len(pictures):
                pic = pictures[pos]
                if pic['landscape']:
                    rows.append(([pic], True))
                    pos += 1
                else:
                    members = [pic]
                    pos += 1
                    if pos < len(pictures) and not pictures[pos]['landscape']:
                        members.append(pictures[pos])
                        pos += 1
                    rows.append((members, False))
            for row_index, (photos, wide) in enumerate(rows):
                row_width = 520.0 if wide else 254.0
                row_cap = 310.0 if wide else 360.0
                target_height = max(90, min(row_cap, max(row_width / p['aspect'] for p in photos)))
                room = CONTENT_BOTTOM - self.y - 14
                if idx == len(acts) and row_index == len(rows)-1:
                    credit_lines = len(_wrap(author, self.fonts['semi'], 10, 500))
                    credit_reserve = 18 + credit_lines*15 + 14 + 18
                    if room - credit_reserve >= 90:
                        room -= credit_reserve
                if room < 90:
                    self.page(new=True)
                    self.text(48, self.y, f'ACTIVIDAD {idx} · EVIDENCIAS (CONT.)', 10, 'bold', TEAL)
                    self.y += 24
                    room = CONTENT_BOTTOM - self.y - 14
                draw_height = min(target_height, room)
                if draw_height < 90:
                    raise service.ErrorReportador('No se pudo reservar espacio para evidencias.')
                for col, pic in enumerate(photos):
                    x = 48.0 if wide else ((W-254.0)/2 if len(photos)==1 else 48.0+col*266.0)
                    self.image_fit(pic['data'], x, self.y, row_width, draw_height)
                self.y += draw_height
                if row_index < len(rows)-1:
                    self.y += 12
            self.y += 18
        # Autoría original: nunca usar el nombre del usuario que descarga.
        credit_lines = _wrap(author, self.fonts['semi'], 10, 500)
        if self.y + 18 + 15*len(credit_lines) + 14 > CONTENT_BOTTOM:
            self.page(new=True)
            self.y = 92
        self.rect(48, self.y, 520, 1, colors.HexColor('#CFDFE8'))
        self.y += 11
        label = 'Reporte elaborado por:'
        x = (W - pdfmetrics.stringWidth(label, self.fonts['regular'], 9))/2
        self.text(x, self.y, label, 9, color=GRAY)
        self.y += 17
        for line in credit_lines:
            x = max(48, (W - pdfmetrics.stringWidth(line, self.fonts['semi'], 10))/2)
            self.text(x, self.y, line, 10, 'semi', BLUE)
            self.y += 15

    def draw_orders(self, order_nums: list, fetch, report_id: int):
        for num in order_nums:
            self.page(new=True)
            self.text(48, 82, 'ORDEN DE SERVICIO ' + str(num), 18, 'bold', BLUE)
            try:
                self.image_fit(fetch(report_id, num, os=True), 48, 116, 516, 590, paint_box=False)
            except Exception as exc:
                raise service.ErrorReportador(f'No se pudo cargar la Orden de Servicio {num}.') from exc

    def build(self) -> bytes:
        self.canvas.save()
        return self.canvas._filename.getvalue()


def generar_pdf_bytes(detalle: dict, obtener_imagen=None, logo_path: str | None = None,
                      background_path: str | None = None) -> bytes:
    """Generar según las proporciones originales. Requiere evidencias completas."""
    report, activities, orders, author = _validate_and_plan(detalle)
    fetch = obtener_imagen or service.leer_imagen
    output = BytesIO()
    pdf = _OriginalStylePDF(output, report, logo_path=logo_path, background_path=background_path)
    pdf.draw_fields()
    pdf.draw_activities(activities, fetch, int(report['id_reporte']), author)
    pdf.draw_orders(orders, fetch, int(report['id_reporte']))
    return pdf.build()


def generar_pdf_reporte(id_reporte: int, ruta_pdf: str) -> None:
    detalle = service.obtener_reporte(id_reporte)
    Path(ruta_pdf).write_bytes(generar_pdf_bytes(detalle))
