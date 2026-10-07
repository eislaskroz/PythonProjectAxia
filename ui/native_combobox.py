"""Combobox nativo ligero con API compatible con CTkOptionMenu.

Se usa en formularios con muchos selectores para reducir el costo visual y de
renderizado de CustomTkinter, manteniendo callbacks y estados existentes.
"""
from __future__ import annotations

from tkinter import ttk
from typing import Any, Callable, Iterable
import unicodedata


def _sort_key(value: Any) -> str:
    """Clave alfabetica estable, ignorando acentos y mayusculas."""
    text = str(value or "").strip()
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).casefold()


def _sorted_values(values: Iterable[Any] | None) -> tuple[Any, ...]:
    """Ordena catalogos sin perder placeholders operativos al inicio."""
    items = list(values or ())
    if len(items) < 2:
        return tuple(items)
    # Los textos de seleccion no son elementos del catalogo y deben quedar arriba.
    leading = []
    while items and _sort_key(items[0]).startswith(("seleccion", "elige", "--")):
        leading.append(items.pop(0))
    return tuple(leading + sorted(items, key=_sort_key))


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
        "height", "corner_radius", "fg_color", "button_color",
        "button_hover_color", "dropdown_fg_color", "dropdown_hover_color",
        "dropdown_text_color", "text_color", "anchor", "dynamic_resizing",
    }

    def __init__(
        self,
        master=None,
        *,
        variable=None,
        values: Iterable[Any] | None = None,
        font: Any | None = None,
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
            "values": _sorted_values(values),
            "state": self._map_state(state),
            "height": self._axia_dropdown_rows,
        }
        if width is not None:
            # CTk expresa width en píxeles; ttk lo hace en caracteres.
            ttk_kwargs["width"] = max(8, min(80, int(width / 9)))
        if font is None:
            font = ("Montserrat", 11)
        ttk_kwargs["font"] = font
        ttk_kwargs.update(kwargs)

        super().__init__(master, **ttk_kwargs)
        self.bind("<<ComboboxSelected>>", self._on_selected, add="+")
        self.bind("<KeyPress>", self._on_keypress, add="+")
        self.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind("<Button-4>", self._on_mousewheel, add="+")
        self.bind("<Button-5>", self._on_mousewheel, add="+")

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

    def _on_keypress(self, event=None):
        """Selecciona la primera opcion que inicia con la tecla pulsada."""
        char = str(getattr(event, "char", "") or "").strip()
        if not char or not char.isprintable():
            return None
        needle = _sort_key(char)
        values = list(self.cget("values") or ())
        for index, value in enumerate(values):
            if _sort_key(value).startswith(needle):
                self.current(index)
                self._on_selected()
                return "break"
        return None

    def _on_mousewheel(self, event=None):
        """Impide que la rueda cambie un selector que conserva el foco a distancia."""
        try:
            x, y = self.winfo_pointerxy()
            under_pointer = self.winfo_containing(x, y)
            if under_pointer is self:
                return None
            # Si el puntero esta sobre un hijo real del combobox, tambien se permite.
            current = under_pointer
            while current is not None and hasattr(current, "master"):
                if current is self:
                    return None
                current = current.master
        except Exception:
            pass
        return "break"

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
            kwargs["values"] = _sorted_values(kwargs["values"])
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
