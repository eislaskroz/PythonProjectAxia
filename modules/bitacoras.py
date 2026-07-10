"""
Módulo de compatibilidad AXIA.

La lógica real fue movida a la capa `services/`.
Este archivo se conserva temporalmente para evitar romper importaciones antiguas.
En código nuevo, importa directamente desde `services.bitacoras_service`.
"""

from services.bitacoras_service import (
    crear_bitacora,
    obtener_bitacoras,
    obtener_bitacoras_por_aco,
    buscar_bitacora_por_folio,
    actualizar_bitacora,
    obtener_estadisticas_bitacoras
)
