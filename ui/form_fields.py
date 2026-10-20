"""Controles de captura AXIA con estado visual consistente.

El relleno indica si el campo está disponible para captura; su estado real
sigue controlado exclusivamente por CustomTkinter y la lógica del formulario.
No modifica variables, validaciones, permisos ni datos guardados.
"""

import customtkinter as ctk

# Inspirado en el tono gris de los selectores nativos del proyecto.
CAMPO_HABILITADO = "#E1E0DD"
BORDE_HABILITADO = "#B9C5D2"
CAMPO_SOLO_LECTURA = "#EDF0F4"
BORDE_SOLO_LECTURA = "#D6DEE8"
CAMPO_DESHABILITADO = "#F2F4F7"
BORDE_DESHABILITADO = "#E0E5ED"


def colores_para_estado(state):
    """Retorna fondo y borde sin alterar el comportamiento de edición."""
    estado = str(state or "normal").strip().lower()
    if estado == "disabled":
        return CAMPO_DESHABILITADO, BORDE_DESHABILITADO
    if estado == "readonly":
        return CAMPO_SOLO_LECTURA, BORDE_SOLO_LECTURA
    return CAMPO_HABILITADO, BORDE_HABILITADO


class _EstiloCampo:
    """Mixin: actualiza el sombreado al cambiar el estado del control."""

    def __init__(self, *args, **kwargs):
        fondo, borde = colores_para_estado(kwargs.get("state", "normal"))
        # Estos controles representan capturas. Se respeta el resto de sus
        # parámetros: fuente, altura, esquinas, variable y estado funcional.
        kwargs["fg_color"] = fondo
        kwargs["border_color"] = borde
        if isinstance(self, ctk.CTkEntry):
            kwargs.setdefault("placeholder_text_color", "#64748B")
        super().__init__(*args, **kwargs)

    def configure(self, *args, **kwargs):
        if "state" in kwargs:
            fondo, borde = colores_para_estado(kwargs["state"])
            kwargs["fg_color"] = fondo
            kwargs["border_color"] = borde
        return super().configure(*args, **kwargs)

    config = configure


class AxiaEntry(_EstiloCampo, ctk.CTkEntry):
    """Entrada de una línea con sombreado según estado de captura."""


class AxiaTextbox(_EstiloCampo, ctk.CTkTextbox):
    """Entrada multilínea con sombreado según estado de captura."""
