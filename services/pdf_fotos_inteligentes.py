"""Composición inteligente, ligera y sin recortes de evidencias de bitácora.

Mantiene el orden original, calcula filas de 1 a 3 imágenes por programación
 dinámica (O(n)); no requiere IA ni nuevas dependencias. No incorpora marcos
ni pies de foto. Cada fila puede paginarse por separado en ReportLab.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Sequence

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Image as RLImage, Table, TableStyle


@dataclass(frozen=True)
class FotoPdf:
    contenido: bytes
    nombre: str
    ancho_px: int
    alto_px: int

    @property
    def es_vertical(self) -> bool:
        return self.alto_px > self.ancho_px * 1.10


# Área útil de letter: ~498 pt de ancho y ~618 de alto en el formato AXIA.
_ALTO_MIN = 124.0
_ALTO_MAX = 298.0
_ALTO_OBJETIVO = 215.0
_SEPARACION = 6.0


def _geometria(grupo: Sequence[FotoPdf], ancho_total: float) -> tuple[float, list[float]]:
    """Tamaños proporcionales sin recortar ni ampliar píxeles fuente."""
    aspectos = [max(1, f.ancho_px) / max(1, f.alto_px) for f in grupo]
    disponible = max(1.0, ancho_total - _SEPARACION * (len(grupo) - 1))
    alto = min(_ALTO_MAX, disponible / sum(aspectos))
    # Evitar que una captura de poca resolución se amplíe artificialmente.
    alto = min(alto, *(max(1, f.alto_px) for f in grupo))
    return alto, [alto * a for a in aspectos]


def agrupar_fotos(fotos: Sequence[FotoPdf], ancho_total: float = 6.90 * inch) -> list[tuple[FotoPdf, ...]]:
    """Busca una secuencia de filas equilibradas, sin alterar las evidencias.

    Considera hasta tres fotos consecutivas por fila, con coste lineal
    respecto de la cantidad de fotos. No manipula bytes de imágenes.
    """
    n = len(fotos)
    if not n:
        return []
    costos = [float('inf')] * (n + 1)
    pasos = [1] * n
    costos[n] = 0.0
    for i in range(n - 1, -1, -1):
        for cantidad in range(1, min(3, n - i) + 1):
            grupo = fotos[i:i + cantidad]
            alto, anchos = _geometria(grupo, ancho_total)
            ancho_utilizado = sum(anchos) + _SEPARACION * (cantidad - 1)
            # Área desperdiciada bajo la altura máxima y legibilidad mínima.
            desperdicio = max(0.0, (ancho_total - ancho_utilizado) / ancho_total)
            legibilidad = max(0.0, (_ALTO_MIN - alto) / _ALTO_MIN)
            # Preferir imágenes suficientemente grandes, pero aprovechar la hoja.
            coste = 0.22 * abs(alto - _ALTO_OBJETIVO) / _ALTO_OBJETIVO
            coste += 0.95 * desperdicio + 2.5 * legibilidad
            coste += 0.17  # penalización por cada fila adicional
            if cantidad == 1 and grupo[0].es_vertical:
                coste += 0.26  # no aislar capturas verticales si caben acompañadas
            if cantidad == 3 and alto < 155:
                coste += 0.35  # evitar ilegibilidad para forzar 3 columnas
            coste += costos[i + cantidad]
            if coste < costos[i] - 1e-9:
                costos[i], pasos[i] = coste, cantidad
    grupos = []
    i = 0
    while i < n:
        k = pasos[i]
        grupos.append(tuple(fotos[i:i + k]))
        i += k
    return grupos


def dimensiones_ajustadas(foto: FotoPdf, max_ancho: float, max_alto: float) -> tuple[float, float]:
    """Escala conservando proporciones y sin aumentar tamaño original."""
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
    """Crea filas paginables, sin bordes, leyendas ni fondos decorativos.

    Los parámetros de estilo sin uso permanecen por compatibilidad con AXIA.
    """
    filas = []
    for grupo in agrupar_fotos(fotos, ancho_total):
        alto, anchos = _geometria(grupo, ancho_total)
        imagenes = [RLImage(BytesIO(f.contenido), width=w, height=alto)
                    for f, w in zip(grupo, anchos)]
        # Una única celda contiene todas las fotos, con espacios fijos.
        # Así no se desperdicia ancho por columnas idénticas al mezclar formatos.
        celdas = []
        anchuras = []
        for j, imagen in enumerate(imagenes):
            if j:
                celdas.append('')
                anchuras.append(_SEPARACION)
            celdas.append(imagen)
            anchuras.append(anchos[j])
        fila = Table([celdas], colWidths=anchuras, hAlign='CENTER')
        fila.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        filas.append(fila)
    return filas
