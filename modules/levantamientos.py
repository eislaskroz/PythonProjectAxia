"""
Módulo de compatibilidad AXIA.

La lógica real fue movida a la capa `services/`.
Este archivo se conserva temporalmente para evitar romper importaciones antiguas.
En código nuevo, importa directamente desde `services.levantamientos_service`.
"""

from services.levantamientos_service import (
    crear_levantamiento,
    obtener_levantamientos,
    obtener_levantamientos_por_aco,
    buscar_levantamiento_por_folio,
    actualizar_levantamiento,
    obtener_estadisticas_levantamientos
)
