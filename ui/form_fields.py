import customtkinter as ctk

CAMPO_HABILITADO = "#E1E0DD"
BORDE_HABILITADO = "#B9C5D2"
CAMPO_SOLO_LECTURA = "#EDF0F4"
BORDE_SOLO_LECTURA = "#D6DEE8"
CAMPO_DESHABILITADO = "#F2F4F7"
BORDE_DESHABILITADO = "#E0E5ED"


def colores_para_estado(state):
    estado = str(state or "normal").strip().lower()
    if estado == "disabled":
        return CAMPO_DESHABILITADO, BORDE_DESHABILITADO
    if estado == "readonly":
        return CAMPO_SOLO_LECTURA, BORDE_SOLO_LECTURA
    return CAMPO_HABILITADO, BORDE_HABILITADO


class _EstiloCampo:

    def __init__(self, *args, **kwargs):
        fondo, borde = colores_para_estado(kwargs.get("state", "normal"))
        kwargs["fg_color"] = fondo
        kwargs["border_color"] = borde
        kwargs["corner_radius"] = 0
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


class AxiaTextbox(_EstiloCampo, ctk.CTkTextbox):