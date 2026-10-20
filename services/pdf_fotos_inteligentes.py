"""Composición adaptable de fotografías para documentos PDF de AXIA.

Las fotografías se renderizan sin recortes ni deformaciones. Dos imágenes
verticales consecutivas comparten fila; el resto se muestra en una columna.
Este módulo es independiente de los formularios y de Supabase para poder
reutilizar la distribución en otros documentos corporativos.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from io import BytesIO
from typing import Sequence

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Image as RLImage, Paragraph, Table, TableStyle


@dataclass(frozen=True)
class FotoPdf:
    contenido: bytes
    nombre: str
    ancho_px: int
    alto_px: int

    @property
    def es_vertical(self) -> bool:
        # Cuadradas y casi cuadradas se muestran como horizontales para evitar
        # dos capturas pequeñas ilegibles en la misma fila.
        return self.alto_px > self.ancho_px * 1.10


def agrupar_fotos(fotos: Sequence[FotoPdf]) -> list[tuple[FotoPdf, ...]]:
    """Respeta el orden original y agrupa solo verticales consecutivas."""
    grupos = []
    i = 0
    while i < len(fotos):
        actual = fotos[i]
        if actual.es_vertical and i + 1 < len(fotos) and fotos[i + 1].es_vertical:
            grupos.append((actual, fotos[i + 1]))
            i += 2
        else:
            grupos.append((actual,))
            i += 1
    return grupos


def dimensiones_ajustadas(foto: FotoPdf, max_ancho: float, max_alto: float) -> tuple[float, float]:
    """Escala manteniendo 100 % la relación de aspecto; nunca amplía el origen."""
    w, h = max(1, foto.ancho_px), max(1, foto.alto_px)
    escala = min(max_ancho / w, max_alto / h, 1.0)
    return w * escala, h * escala


def construir_filas_fotos(
    fotos: Sequence[FotoPdf],
    *,
    estilo_texto: ParagraphStyle,
    color_borde=colors.HexColor('#8FA3B5'),
    color_pie=colors.HexColor('#EAF1F7'),
    ancho_total: float = 6.90 * inch,
) -> list[Table]:
    """Devuelve filas independientes y paginables para insertar en una story.

    Las horizontales usan el ancho de la página; las verticales se presentan
    en parejas cuando son consecutivas o centradas cuando están solas.
    """
    caption_style = ParagraphStyle(
        'AxiaBitFotoCaptionAdaptable', parent=estilo_texto,
        fontSize=7, leading=9, alignment=1,
    )
    filas = []
    for grupo in agrupar_fotos(fotos):
        pareja = len(grupo) == 2
        ancho_tarjeta = (ancho_total - 14) / 2 if pareja else (
            3.55 * inch if grupo[0].es_vertical else ancho_total - 8
        )
        ancho_imagen = ancho_tarjeta - 12
        alto_imagen = (3.55 if pareja else 4.25) * inch
        tarjetas = []
        for foto in grupo:
            ancho, alto = dimensiones_ajustadas(foto, ancho_imagen, alto_imagen)
            imagen = RLImage(BytesIO(foto.contenido), width=ancho, height=alto)
            # Capciones independientes para evitar cortar nombres largos.
            caption = Paragraph(escape(foto.nombre or 'Evidencia'), caption_style)
            tarjeta = Table([[imagen], [caption]], colWidths=[ancho_tarjeta], hAlign='CENTER')
            tarjeta.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 0.4, color_borde),
                ('BACKGROUND', (0, 1), (0, 1), color_pie),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, 0), 5),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                ('TOPPADDING', (0, 1), (-1, 1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, 1), 4),
            ]))
            tarjetas.append(tarjeta)

        if pareja:
            fila = Table([tarjetas], colWidths=[ancho_total / 2] * 2, hAlign='CENTER')
        else:
            fila = Table([[tarjetas[0]]], colWidths=[ancho_total], hAlign='CENTER')
        fila.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        filas.append(fila)
    return filas
