"""Regenera etiquetas y tickets exclusivamente con movimientos históricos confirmados.

Esta capa no registra movimientos ni realiza escrituras en Supabase.
Los datos deben proceder de la consulta autenticada `comprobante_kardex`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

from services.almacen_comprobantes import generar_etiqueta_entrada, generar_ticket_salida


def generar_comprobante_historico(detalle: Mapping, *, ruta: str | Path | None = None) -> Path:
    """Reutiliza exactamente los generadores de comprobantes de Entrada/Salida.

    `detalle` representa el resultado del servidor para un movimiento real: para
    una entrega por OT incluye solamente las partidas de ESA entrega, no todas
    las que compartan el mismo folio de OT.
    """
    if not isinstance(detalle, Mapping):
        raise ValueError('No se recibió el movimiento histórico del Kárdex.')
    tipo = str(detalle.get('tipo') or '').strip().upper()
    partidas = detalle.get('movimientos')
    if tipo not in ('ENTRADA', 'SALIDA') or not isinstance(partidas, list) or not partidas:
        raise ValueError('El registro no tiene datos suficientes para reimprimir.')
    if len(partidas) > 80:
        raise ValueError('La entrega contiene demasiadas partidas para el ticket.')
    for partida in partidas:
        if not isinstance(partida, Mapping) or not str(partida.get('codigo') or '').strip() \
                or not str(partida.get('cantidad') or '').strip():
            raise ValueError('Hay partidas incompletas en el historial de Almacén.')
    ident = str(detalle.get('identificador') or '').strip()
    fecha = detalle.get('fecha')
    referencia = str(detalle.get('referencia') or '')
    if tipo == 'ENTRADA':
        if len(partidas) != 1:
            raise ValueError('Una etiqueta debe corresponder a un único movimiento de entrada.')
        producto = partidas[0]
        return generar_etiqueta_entrada(
            codigo=str(producto['codigo']), producto=str(producto.get('producto') or ''),
            cantidad=producto['cantidad'], referencia=referencia,
            identificador=ident, fecha=fecha, ruta=ruta,
        )
    return generar_ticket_salida(
        partidas=partidas, destinatario=str(detalle.get('destinatario') or ''),
        motivo=str(detalle.get('motivo') or ''), referencia=referencia,
        responsable=str(detalle.get('responsable') or ''),
        identificador=ident, fecha=fecha, ruta=ruta,
    )
