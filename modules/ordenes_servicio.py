"""
Módulo de compatibilidad AXIA.

La lógica real fue movida a la capa `services/`.
Este archivo se conserva temporalmente para evitar romper importaciones antiguas.
En código nuevo, importa directamente desde `services.ordenes_servicio_service`.
"""

from services.ordenes_servicio_service import (
    crear_orden_servicio,
    obtener_ordenes_servicio,
    obtener_ordenes_por_aco,
    buscar_orden_por_folio,
    actualizar_orden_servicio,
    obtener_estadisticas_ordenes
)
