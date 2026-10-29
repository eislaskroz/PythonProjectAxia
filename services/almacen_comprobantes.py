"""Comprobantes imprimibles del Almacén AXIA.

Generación posterior a una transacción confirmada: este módulo no conecta con
Supabase, no consulta ni modifica existencias y nunca repite un movimiento.
Las etiquetas usan Code 128 auténtico y los tickets tienen ancho de 80 mm.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Mapping, Sequence
from xml.sax.saxutils import escape
import os
import re
import subprocess
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.graphics.barcode import code128
from reportlab.pdfgen import canvas
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from services.almacen_fechas import ZONA_MEXICO, fecha_kardex_mexico

AZUL = colors.HexColor('#123C58')
CIAN = colors.HexColor('#0FA5C6')
GRIS = colors.HexColor('#53677C')


def _texto(valor: object, max_len: int = 500) -> str:
    return str(valor if valor is not None else '').strip()[:max_len]


def _n(valor: object) -> str:
    try:
        return f'{Decimal(str(valor)).normalize():f}'
    except Exception:
        return _texto(valor, 32)


def _fecha(valor=None) -> str:
    if valor:
        return fecha_kardex_mexico(valor)
    return datetime.now(ZONA_MEXICO).strftime('%d/%m/%Y %H:%M:%S')


def _carpeta() -> Path:
    """Preferir Documentos en Windows; no almacenar comprobantes en el ZIP."""
    candidates = [Path.home() / 'Documents' / 'AXIA' / 'Almacen' / 'Comprobantes']
    local = os.getenv('LOCALAPPDATA')
    if local:
        candidates.append(Path(local) / 'AXIA' / 'comprobantes_almacen')
    else:
        candidates.append(Path.home() / '.axia' / 'comprobantes_almacen')
    for target in candidates:
        try:
            target.mkdir(parents=True, exist_ok=True)
            return target
        except OSError:
            continue
    raise OSError('No fue posible crear la carpeta local de comprobantes.')


def _ruta(tipo: str, codigo: str, identificador: str | None) -> Path:
    safe = re.sub(r'[^A-Za-z0-9_-]', '_', _texto(codigo, 60)) or 'SIN_CODIGO'
    ident = re.sub(r'[^A-Za-z0-9_-]', '', _texto(identificador, 100))[:45]
    if not ident:
        ident = datetime.now(ZONA_MEXICO).strftime('%Y%m%d_%H%M%S_%f')
    return _carpeta() / f'{tipo}_{safe}_{ident}.pdf'


def abrir_comprobante(ruta: str | Path) -> None:
    """Abre en el visor del SO; el usuario elige impresora y número de copias."""
    ruta = Path(ruta).resolve()
    if sys.platform == 'win32':
        os.startfile(str(ruta))  # type: ignore[attr-defined]
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', str(ruta)])
    else:
        subprocess.Popen(['xdg-open', str(ruta)])


def generar_etiqueta_entrada(*, codigo: str, producto: str, cantidad,
                            referencia: str = '', identificador: str | None = None,
                            fecha=None, ruta: str | Path | None = None) -> Path:
    """Etiqueta autoadhesiva 100 x 60 mm con código Code128 del identificador AXIA."""
    codigo = _texto(codigo, 120)
    if not codigo or not all(32 <= ord(c) < 127 for c in codigo):
        raise ValueError('El código AXIA no puede convertirse a un Code 128 válido.')
    ruta = Path(ruta) if ruta else _ruta('ETIQUETA_ENTRADA', codigo, identificador)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    w, h = 100 * mm, 60 * mm
    c = canvas.Canvas(str(ruta), pagesize=(w, h))
    c.setTitle(f'Etiqueta AXIA - {codigo}')
    c.setStrokeColor(colors.HexColor('#C6D4DF'))
    c.setLineWidth(.7)
    c.roundRect(2 * mm, 2 * mm, w - 4 * mm, h - 4 * mm, 3 * mm, stroke=1, fill=0)
    c.setFillColor(AZUL)
    c.roundRect(2 * mm, h - 14 * mm, w - 4 * mm, 12 * mm, 3 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(6 * mm, h - 10.2 * mm, 'AXIA  /  ALMACEN')
    c.setFont('Helvetica', 7.2)
    c.drawRightString(w - 6 * mm, h - 10 * mm, 'ETIQUETA DE ENTRADA')
    # Nombre completo en hasta 2 líneas: si es muy largo, truncar con elipsis
    # únicamente en la etiqueta (la ficha del catálogo conserva el nombre).
    def wrap_label(texto, max_w, font='Helvetica-Bold', size=9.0, max_lines=2):
        words = _texto(texto, 500).split()
        lines, line = [], ''
        for word in words:
            test = f'{line} {word}'.strip()
            if pdfmetrics.stringWidth(test, font, size) <= max_w:
                line = test
            else:
                if line:
                    lines.append(line)
                    line = word
                else:
                    # Una palabra sin espacios puede ser extensa: abreviar.
                    while pdfmetrics.stringWidth(word, font, size) > max_w and len(word) > 1:
                        word = word[:-1]
                    lines.append(word)
                    line = ''
                if len(lines) == max_lines:
                    break
        if len(lines) < max_lines and line:
            lines.append(line)
        if len(lines) == max_lines and ' '.join(lines) != ' '.join(words):
            last = lines[-1]
            while pdfmetrics.stringWidth(last + '...', font, size) > max_w and last:
                last = last[:-1]
            lines[-1] = last + '...'
        return lines

    c.setFillColor(AZUL)
    c.setFont('Helvetica-Bold', 9)
    for i, line in enumerate(wrap_label(producto, w - 12 * mm)):
        c.drawString(6 * mm, h - 19.2 * mm - i * 4 * mm, line)
    barcode = code128.Code128(codigo, barHeight=13 * mm, barWidth=.32 * mm, humanReadable=False)
    available = w - 16 * mm
    scale = min(1, available / barcode.width)
    x = (w - barcode.width * scale) / 2
    c.saveState()
    c.translate(x, 18 * mm)
    c.scale(scale, 1)
    barcode.drawOn(c, 0, 0)
    c.restoreState()
    c.setFont('Helvetica-Bold', 10)
    c.drawCentredString(w / 2, 15 * mm, codigo)
    c.setFont('Helvetica-Bold', 8)
    c.drawString(6 * mm, 9.4 * mm, f'CANTIDAD: {_n(cantidad)}')
    c.setFont('Helvetica', 7)
    c.setFillColor(GRIS)
    c.drawRightString(w - 6 * mm, 9.4 * mm, _fecha(fecha))
    if referencia:
        ref = _texto(referencia, 40)
        while pdfmetrics.stringWidth(ref, 'Helvetica', 7) > w - 12 * mm:
            ref = ref[:-1]
        c.drawString(6 * mm, 5 * mm, f'Ref: {ref}')
    c.showPage()
    c.save()
    return ruta


def generar_ticket_salida(*, partidas: Sequence[Mapping], destinatario: str,
                          motivo: str, referencia: str = '', responsable: str = '',
                          identificador: str | None = None, fecha=None,
                          ruta: str | Path | None = None) -> Path:
    """Ticket térmico de 80 mm. No contiene precios internos de AXIA."""
    if not partidas:
        raise ValueError('El ticket necesita al menos una partida confirmada.')
    referencia = _texto(referencia, 120)
    ident = _texto(identificador, 100)
    ruta = Path(ruta) if ruta else _ruta('TICKET_SALIDA', referencia or 'INDIVIDUAL', ident)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    usable = 70 * mm
    normal = ParagraphStyle('axia-ticket-texto', fontName='Helvetica', fontSize=8, leading=11,
                            textColor=colors.HexColor('#202733'), spaceAfter=0)
    small = ParagraphStyle('axia-ticket-small', parent=normal, fontSize=7, leading=9)
    bold = ParagraphStyle('axia-ticket-bold', parent=normal, fontName='Helvetica-Bold')
    header = ParagraphStyle('axia-ticket-title', parent=bold, fontSize=14, leading=17, alignment=TA_CENTER,
                            textColor=AZUL)
    subhead = ParagraphStyle('axia-ticket-subtitle', parent=small, alignment=TA_CENTER, textColor=GRIS)
    def p(text, style=normal):
        return Paragraph(escape(_texto(text, 1000)).replace('\n','<br/>'), style)

    story = [p('AXIA COMUNICACIONES', header), p('COMPROBANTE DE SALIDA DE ALMACEN', subhead),
             Spacer(1, 3 * mm), HRFlowable(width='100%', thickness=1.5, color=AZUL), Spacer(1, 3 * mm)]
    for title, val in [('Emitido (México)',_fecha(fecha)), ('Movimiento',ident or 'CONFIRMADO'),
                       ('OT / Referencia',referencia or 'Salida individual'),
                       ('Recibe',destinatario), ('Entrega',responsable), ('Motivo',motivo)]:
        if val:
            story.append(p(f'{title}: {val}', small))
            story.append(Spacer(1, 1.2 * mm))
    story.extend((Spacer(1,2*mm), HRFlowable(width='100%', thickness=.5,color=GRIS),Spacer(1,2*mm)))
    for i, r in enumerate(partidas, start=1):
        codigo = _texto(r.get('codigo'), 120)
        producto = _texto(r.get('producto'), 500) or 'Producto sin descripción'
        cantidad = _n(r.get('cantidad'))
        item = [p(f'{i}. {codigo}', bold), p(producto, small),
                p(f'Cantidad entregada: {cantidad}', bold), Spacer(1, 2 * mm),
                HRFlowable(width='100%', thickness=.35, color=colors.HexColor('#D6DBDF')),
                Spacer(1, 2 * mm)]
        story.append(KeepTogether(item))
    story.append(Spacer(1, 5 * mm))
    story.append(p(f'ARTICULOS: {len(partidas)}', bold))
    story.append(Spacer(1, 9 * mm))
    story.extend([HRFlowable(width='90%', thickness=.5, color=GRIS),
                  p('RECIBE / FIRMA',subhead), Spacer(1,3*mm),
                  p('Documento interno - No es comprobante fiscal',subhead)])
    # Página de largo variable para impresora térmica: evita una hoja de 280 mm
    # con espacios vacíos. Se mide cada flowable antes de construir el PDF.
    def alto(elemento):
        if isinstance(elemento, KeepTogether):
            return sum(alto(parte) for parte in elemento._content)
        return elemento.wrap(usable, 10_000 * mm)[1]
    altura = max(75 * mm, sum(alto(e) for e in story) + 22 * mm)
    doc = SimpleDocTemplate(str(ruta), pagesize=(80 * mm, altura),
                            leftMargin=5 * mm, rightMargin=5 * mm,
                            topMargin=7 * mm, bottomMargin=7 * mm,
                            title='Ticket AXIA - Salida de Almacén',
                            author='AXIA Comunicaciones')
    doc.build(story)
    return ruta
