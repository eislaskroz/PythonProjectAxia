"""Política visual AXIA: desplazamiento mediante barras, no rueda del mouse.

No modifica ``yview`` / ``xview`` ni la conexión de los scrollbars: los usuarios
pueden arrastrar las barras verticales y horizontales normalmente. Tampoco
cambia el teclado, los controles de paginación o el desplazamiento de un
selector por flechas.

Se instala una sola vez en la raíz Tk ANTES de crear los formularios, para que
los CTkScrollableFrame creados posteriormente hereden la política.
"""
from __future__ import annotations


_WHEEL_EVENTS = (
    "<MouseWheel>",
    "<Shift-MouseWheel>",
    "<Button-4>",
    "<Button-5>",
    "<Shift-Button-4>",
    "<Shift-Button-5>",
)


def _ignore_wheel(_event=None):
    return "break"


def install_manual_scroll_only(root) -> None:
    """Deshabilita la rueda sin quitar los scrollbars de los controles AXIA."""
    if getattr(root, "_axia_manual_scroll_only", False):
        return

    # CTkScrollableFrame utiliza bind_all en cada instancia, por lo que un
    # bind_all instalado al principio se puede sobrescribir al crear vistas.
    # Neutralizamos el callback compartido en la clase en vez de ocultar la
    # scrollbar o cambiar los tamaños de los formularios.
    try:
        from customtkinter.windows.widgets.ctk_scrollable_frame import CTkScrollableFrame
    except ImportError:
        import customtkinter as ctk
        CTkScrollableFrame = ctk.CTkScrollableFrame

    original = getattr(CTkScrollableFrame, "_mouse_wheel_all", None)
    if callable(original) and not getattr(original, "_axia_manual_scroll_only", False):
        def wheel_disabled(self, event):
            return None
        wheel_disabled._axia_manual_scroll_only = True
        wheel_disabled._axia_original = original
        CTkScrollableFrame._mouse_wheel_all = wheel_disabled

    # El desplazamiento en Treeview, Text y Combobox viene de los bindings de
    # clase de Tk, que se ejecutan antes de ``bind_all``. Bloquearlos a nivel
    # de clase cubre tanto formularios actuales como ventanas futuras.
    for widget_class in ("Treeview", "Text", "TCombobox", "Listbox", "Canvas"):
        for event in _WHEEL_EVENTS:
            root.bind_class(widget_class, event, _ignore_wheel)

    root._axia_manual_scroll_only = True
