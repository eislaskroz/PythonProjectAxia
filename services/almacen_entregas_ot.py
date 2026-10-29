"""Preparación y validación de una entrega de almacén vinculada a OT.

Ninguna partida de la OT se convierte en descuento hasta confirmar un código
exacto del catálogo y su cantidad. Las entregas múltiples son indivisibles.
"""
from __future__ import annotations

import json
from decimal import Decimal

from services.almacen_service import cantidad_valida, formatear_cantidad


def validar_entrega_ot(folio, partidas, destinatario, motivo):
    folio = str(folio or '').strip().upper()
    destinatario = str(destinatario or '').strip()
    motivo = str(motivo or '').strip()
    if not folio or len(folio) > 120:
        raise ValueError('Indica un folio de Orden de Trabajo válido.')
    if not destinatario or len(destinatario) > 120:
        raise ValueError('Indica quién recibe la entrega de la OT.')
    if not motivo or len(motivo) > 250:
        raise ValueError('Indica el motivo de la entrega (máximo 250 caracteres).')
    if not isinstance(partidas, list) or not 1 <= len(partidas) <= 80:
        raise ValueError('La entrega debe contener de 1 a 80 artículos.')
    agrupadas: dict[str, Decimal] = {}
    for item in partidas:
        if not isinstance(item, dict):
            raise ValueError('Partida de OT inválida.')
        codigo = str(item.get('codigo') or '').strip()
        if not codigo or len(codigo) > 120:
            raise ValueError('Indica un código de producto válido en cada partida.')
        agrupadas[codigo] = agrupadas.get(codigo, Decimal('0')) + cantidad_valida(item.get('cantidad'))
        if agrupadas[codigo] > Decimal('1000000'):
            raise ValueError(f'La cantidad total de {codigo} excede 1,000,000.')
    return {'folio': folio, 'destinatario': destinatario, 'motivo': motivo,
            'partidas': [{'codigo': k, 'cantidad':formatear_cantidad(v)}
                         for k,v in sorted(agrupadas.items())]}


def preparar_sugerencias_ot(datos, catalogo):
    """Empareja SOLO códigos/SKU exactos; nunca deduce stock por similitud de nombre."""
    raw = (datos or {}).get('partidas') or (datos or {}).get('ot_partidas_json') or []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            raw = []
    activos = {str(p.get('codigo') or '').strip().casefold():p for p in catalogo
               if p.get('activo', True)}
    sugeridas, pendientes = [], []
    for item in raw if isinstance(raw,list) else []:
        if not isinstance(item, dict) or '_axia_meta' in item:
            continue
        concepto = str(item.get('concepto') or item.get('descripcion') or '').strip()
        # Las partidas 'Servicio' o mano de obra no son artículos del inventario.
        if str(item.get('unidad') or item.get('unidad_tipo') or '').strip().casefold() == 'servicio':
            continue
        codigo = str(item.get('codigo') or item.get('sku') or '').strip()
        p = activos.get(codigo.casefold()) if codigo else None
        try:
            qty = cantidad_valida(item.get('cantidad'))
        except (ValueError, TypeError):
            qty = None
        if p and qty:
            sugeridas.append({'codigo':str(p['codigo']),'cantidad':formatear_cantidad(qty),
                              'concepto':concepto or str(p.get('producto') or '')})
        else:
            pendientes.append({'concepto': concepto or codigo or 'Partida sin descripción',
                               'cantidad':str(item.get('cantidad') or ''),
                               'codigo': codigo})
    return sugeridas, pendientes
