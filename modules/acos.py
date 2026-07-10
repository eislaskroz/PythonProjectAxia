"""
Módulo de compatibilidad AXIA.

La lógica real fue movida a la capa `services/`.
Este archivo se conserva temporalmente para evitar romper importaciones antiguas.
En código nuevo, importa directamente desde `services.acos_service`.
"""

from services.acos_service import (
    buscar_aco_por_numero,
    obtener_acos,
    crear_aco,
    actualizar_aco,
    validar_aco_existente
)
