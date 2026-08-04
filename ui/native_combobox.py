"""Combobox nativo ligero con API compatible con CTkOptionMenu.

Se usa en formularios con muchos selectores para reducir el costo visual y de
renderizado de CustomTkinter, manteniendo callbacks y estados existentes.
"""
from __future__ import annotations

from tkinter import ttk
from typing import Any, Callable, Iterable


def _install_safe_customtkinter_mousewheel() -> None:
    """Evita fallos de CTkScrollableFrame sobre popups nativos de ttk.

    El desplegable de ``ttk.Combobox`` se crea internamente como una ventana
    Tcl que Tkinter no siempre puede convertir a un objeto Widget. En ese caso
    ``event.widget`` llega como una cadena (por ejemplo ``.!popdown.f.l``).
    CustomTkinter 5.2.2 intenta recorrer ``event.widget.master`` desde su
    manejador global de rueda y provoca ``AttributeError``.

    La protección se instala antes de crear los formularios y únicamente omite
    el desplazamiento del frame cuando el evento pertenece a un popup Tcl. El
    scroll nativo de la lista desplegada continúa funcionando normalmente.
    """
    try:
        from customtkinter.windows.widgets.ctk_scrollable_frame import CTkScrollableFrame
    except Exception:
        try:
            import customtkinter as ctk
            CTkScrollableFrame = ctk.CTkScrollableFrame
        except Exception:
            return

    current = getattr(CTkScrollableFrame, "_mouse_wheel_all", None)
    if not callable(current) or getattr(current, "_axia_safe_mousewheel", False):
        return

    original = current

    def safe_mouse_wheel_all(self, event):
        event_widget = getattr(event, "widget", None)
        if isinstance(event_widget, str) or event_widget is None:
            return None
        if not hasattr(event_widget, "master"):
            return None
        try:
            return original(self, event)
        except AttributeError as exc:
            # Protección específica para widgets Tcl no materializados por Tkinter.
            if "master" in str(exc):
                return None
            raise

    safe_mouse_wheel_all._axia_safe_mousewheel = True
    safe_mouse_wheel_all._axia_original = original
    CTkScrollableFrame._mouse_wheel_all = safe_mouse_wheel_all


_install_safe_customtkinter_mousewheel()


class NativeComboBox(ttk.Combobox):
    """Selector ttk de solo lectura compatible con el uso actual de AXIA.

    Parámetros visuales propios de CustomTkinter (height, corner_radius, font,
    fg_color, button_color, etc.) se aceptan y se ignoran intencionalmente.
    El menú muestra hasta ocho opciones y agrega scroll automáticamente.
    """

    _IGNORED_OPTIONS = {
        "height", "corner_radius", "font", "fg_color", "button_color",
        "button_hover_color", "dropdown_fg_color", "dropdown_hover_color",
        "dropdown_text_color", "text_color", "anchor", "dynamic_resizing",
    }

    def __init__(
        self,
        master=None,
        *,
        variable=None,
        values: Iterable[Any] | None = None,
        command: Callable[[str], Any] | None = None,
        state: str = "normal",
        width: int | None = None,
        dropdown_rows: int = 8,
        **kwargs: Any,
    ) -> None:
        self._axia_command = command
        self._axia_dropdown_rows = max(3, int(dropdown_rows or 8))

        for option in self._IGNORED_OPTIONS:
            kwargs.pop(option, None)

        ttk_kwargs: dict[str, Any] = {
            "textvariable": variable,
            "values": tuple(values or ()),
            "state": self._map_state(state),
            "height": self._axia_dropdown_rows,
        }
        if width is not None:
            # CTk expresa width en píxeles; ttk lo hace en caracteres.
            ttk_kwargs["width"] = max(8, min(80, int(width / 9)))
        ttk_kwargs.update(kwargs)

        super().__init__(master, **ttk_kwargs)
        self.bind("<<ComboboxSelected>>", self._on_selected, add="+")

    @staticmethod
    def _map_state(state: Any) -> str:
        normalized = str(state or "normal").lower()
        if normalized == "disabled":
            return "disabled"
        if normalized == "readonly":
            return "readonly"
        return "readonly"

    def _on_selected(self, _event=None) -> None:
        if callable(self._axia_command):
            self._axia_command(self.get())

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)

        if "command" in kwargs:
            self._axia_command = kwargs.pop("command")
        if "variable" in kwargs:
            kwargs["textvariable"] = kwargs.pop("variable")
        if "state" in kwargs:
            kwargs["state"] = self._map_state(kwargs["state"])
        if "values" in kwargs:
            kwargs["values"] = tuple(kwargs["values"] or ())
        if "width" in kwargs:
            raw_width = kwargs.pop("width")
            if raw_width is not None:
                kwargs["width"] = max(8, min(45, int(raw_width / 9)))
        if "dropdown_rows" in kwargs:
            rows = max(3, int(kwargs.pop("dropdown_rows") or 8))
            self._axia_dropdown_rows = rows
            kwargs["height"] = rows

        for option in self._IGNORED_OPTIONS:
            kwargs.pop(option, None)

        return super().configure(**kwargs)

    config = configure
