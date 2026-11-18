from __future__ import annotations

from tkinter import ttk
from typing import Any, Callable, Iterable
import unicodedata


def _sort_key(value: Any) -> str:
    text = str(value or "").strip()
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).casefold()


def _sorted_values(values: Iterable[Any] | None) -> tuple[Any, ...]:
    items = list(values or ())
    if len(items) < 2:
        return tuple(items)
    leading = []
    while items and _sort_key(items[0]).startswith(("seleccion", "elige", "--")):
        leading.append(items.pop(0))
    return tuple(leading + sorted(items, key=_sort_key))


def _filter_values(values: Iterable[Any], query: str) -> tuple[Any, ...]:
    needle = _sort_key(query)
    if not needle:
        return tuple(values)
    starts = []
    contains = []
    for value in values:
        key = _sort_key(value)
        if key.startswith(needle):
            starts.append(value)
        elif needle in key:
            contains.append(value)
    return tuple(starts + contains)


def _exact_value(values: Iterable[Any], query: str) -> str | None:
    target = _sort_key(query)
    for value in values:
        if _sort_key(value) == target:
            return str(value)
    return None


def _install_safe_customtkinter_mousewheel() -> None:
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
            if "master" in str(exc):
                return None
            raise

    safe_mouse_wheel_all._axia_safe_mousewheel = True
    safe_mouse_wheel_all._axia_original = original
    CTkScrollableFrame._mouse_wheel_all = safe_mouse_wheel_all


_install_safe_customtkinter_mousewheel()


class NativeComboBox(ttk.Combobox):
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
        predictive: bool = True,
        **kwargs: Any,
    ) -> None:
        self._axia_command = command
        self._axia_dropdown_rows = max(3, int(dropdown_rows or 8))
        self._axia_predictive = bool(predictive)
        self._axia_all_values = _sorted_values(values)
        self._axia_selected = ""
        self._axia_editing = False

        for option in self._IGNORED_OPTIONS:
            kwargs.pop(option, None)

        ttk_kwargs: dict[str, Any] = {
            "textvariable": variable,
            "values": self._axia_all_values,
            "state": self._map_state(state, self._axia_predictive),
            "height": self._axia_dropdown_rows,
        }
        if width is not None:
            ttk_kwargs["width"] = max(8, min(80, int(width / 9)))
        if font is None:
            font = ("Montserrat", 11)
        ttk_kwargs["font"] = font
        ttk_kwargs.update(kwargs)

        super().__init__(master, **ttk_kwargs)
        self._axia_selected = self.get()
        self.bind("<<ComboboxSelected>>", self._on_selected, add="+")
        self.bind("<KeyRelease>", self._on_search, add="+")
        self.bind("<Return>", self._on_return, add="+")
        self.bind("<Escape>", self._on_escape, add="+")
        self.bind("<FocusOut>", self._on_focusout, add="+")
        self.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind("<Button-4>", self._on_mousewheel, add="+")
        self.bind("<Button-5>", self._on_mousewheel, add="+")

    @staticmethod
    def _map_state(state: Any, predictive: bool = True) -> str:
        normalized = str(state or "normal").lower()
        if normalized == "disabled":
            return "disabled"
        if normalized == "readonly" and not predictive:
            return "readonly"
        return "normal" if predictive else "readonly"

    def _restore_options(self) -> None:
        if tuple(super().cget("values")) != self._axia_all_values:
            super().configure(values=self._axia_all_values)

    def _on_selected(self, _event=None) -> None:
        self._axia_selected = self.get()
        self._axia_editing = False
        self._restore_options()
        if callable(self._axia_command):
            self._axia_command(self.get())

    def _on_search(self, event=None):
        if not self._axia_predictive or str(self.cget("state")) == "disabled":
            return None
        key = getattr(event, "keysym", "")
        if key in ("Up", "Down", "Left", "Right", "Return", "Escape", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"):
            return None
        if key and not (len(key) == 1 or key in ("BackSpace", "Delete", "space")):
            return None
        query = self.get()
        self._axia_editing = True
        filtered = _filter_values(self._axia_all_values, query)
        super().configure(values=filtered)
        if filtered:
            try:
                self.tk.call("ttk::combobox::Post", self)
                if self.get() != query:
                    super().set(query)
            except Exception:
                pass
        return None

    def _on_return(self, _event=None):
        if not self._axia_predictive:
            return None
        match = _exact_value(self._axia_all_values, self.get())
        if match is None:
            matches = _filter_values(self._axia_all_values, self.get())
            if len(matches) == 1:
                match = str(matches[0])
        if match is not None:
            self.set(match)
            self._on_selected()
        else:
            self._revert_invalid()
        return "break"

    def _revert_invalid(self) -> None:
        value = _exact_value(self._axia_all_values, self.get())
        if value is None:
            value = self._axia_selected if _exact_value(self._axia_all_values, self._axia_selected) is not None else ""
        self.set(value)
        self._axia_editing = False
        self._restore_options()

    def _on_escape(self, _event=None):
        if self._axia_predictive:
            self.set(self._axia_selected)
            self._axia_editing = False
            self._restore_options()
            return "break"
        return None

    def _on_focusout(self, _event=None):
        if self._axia_predictive and self._axia_editing:
            match = _exact_value(self._axia_all_values, self.get())
            if match is None:
                self._revert_invalid()
            else:
                self.set(match)
                self._on_selected()
        return None

    def _on_mousewheel(self, event=None):
        return "break"

    def set(self, value):
        super().set(value)
        if not getattr(self, "_axia_editing", False):
            self._axia_selected = str(value)

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)

        if "command" in kwargs:
            self._axia_command = kwargs.pop("command")
        if "variable" in kwargs:
            kwargs["textvariable"] = kwargs.pop("variable")
        if "predictive" in kwargs:
            self._axia_predictive = bool(kwargs.pop("predictive"))
        if "state" in kwargs:
            kwargs["state"] = self._map_state(kwargs["state"], self._axia_predictive)
        if "values" in kwargs:
            self._axia_all_values = _sorted_values(kwargs["values"])
            kwargs["values"] = self._axia_all_values
            self._axia_editing = False
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
