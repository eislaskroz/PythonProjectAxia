from __future__ import annotations

import tkinter as tk
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
        self._axia_popup = None
        self._axia_listbox = None
        self._axia_matches = ()
        self._axia_pending_hide = None

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
        self.bind("<Down>", self._on_down, add="+")
        self.bind("<Up>", self._on_up, add="+")
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

    def _hide_suggestions(self) -> None:
        popup = self._axia_popup
        self._axia_popup = None
        self._axia_listbox = None
        self._axia_matches = ()
        if popup is not None:
            try:
                popup.destroy()
            except tk.TclError:
                pass

    def _show_suggestions(self, matches: tuple[Any, ...]) -> None:
        self._hide_suggestions()
        if not matches or not self.winfo_viewable():
            return
        try:
            top = tk.Toplevel(self)
            top.withdraw()
            top.overrideredirect(True)
            top.transient(self.winfo_toplevel())
            box = tk.Listbox(
                top,
                exportselection=False,
                activestyle="none",
                font=self.cget("font"),
                selectmode=tk.SINGLE,
                relief="solid",
                borderwidth=1,
            )
            box.pack(fill="both", expand=True)
            shown = tuple(matches[:100])
            for item in shown:
                box.insert(tk.END, str(item))
            count = min(len(shown), self._axia_dropdown_rows)
            height = max(26, count * 24 + 3)
            width = max(self.winfo_width(), 180)
            x = self.winfo_rootx()
            y = self.winfo_rooty() + self.winfo_height()
            screen_height = self.winfo_screenheight()
            if y + height > screen_height and self.winfo_rooty() > height:
                y = self.winfo_rooty() - height
            top.geometry(f"{width}x{height}+{x}+{y}")
            self._axia_popup = top
            self._axia_listbox = box
            self._axia_matches = shown
            box.bind("<ButtonRelease-1>", self._on_popup_click)
            box.bind("<Return>", self._on_popup_return)
            box.bind("<Escape>", self._on_escape)
            top.deiconify()
            top.lift()
        except tk.TclError:
            self._hide_suggestions()

    def _on_popup_click(self, _event=None):
        box = self._axia_listbox
        if box is None:
            return "break"
        index = box.curselection()
        if index:
            self._select_match(index[0])
        return "break"

    def _on_popup_return(self, _event=None):
        box = self._axia_listbox
        if box is not None and box.curselection():
            self._select_match(box.curselection()[0])
        return "break"

    def _select_match(self, index: int):
        if not 0 <= index < len(self._axia_matches):
            return
        value = str(self._axia_matches[index])
        self._axia_editing = False
        self._hide_suggestions()
        self.set(value)
        self._axia_selected = value
        if callable(self._axia_command):
            self._axia_command(value)
        try:
            self.focus_set()
            self.icursor(tk.END)
        except tk.TclError:
            pass

    def _on_selected(self, _event=None) -> None:
        self._hide_suggestions()
        self._axia_selected = self.get()
        self._axia_editing = False
        if callable(self._axia_command):
            self._axia_command(self.get())

    def _on_search(self, event=None):
        if not self._axia_predictive or str(self.cget("state")) == "disabled":
            return None
        key = getattr(event, "keysym", "")
        ignored = {"Up", "Down", "Left", "Right", "Return", "KP_Enter", "Escape", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"}
        if key in ignored:
            return None
        if key and not (len(key) == 1 or key in ("BackSpace", "Delete", "space") or getattr(event, "state", 0) & 4):
            return None
        query = self.get()
        self._axia_editing = True
        self._show_suggestions(_filter_values(self._axia_all_values, query))
        return None

    def _on_down(self, _event=None):
        if self._axia_listbox is not None:
            box = self._axia_listbox
            current = box.curselection()
            index = min((current[0] + 1) if current else 0, box.size() - 1)
            box.selection_clear(0, tk.END)
            box.selection_set(index)
            box.see(index)
            return "break"
        return None

    def _on_up(self, _event=None):
        if self._axia_listbox is not None:
            box = self._axia_listbox
            current = box.curselection()
            index = max((current[0] - 1) if current else 0, 0)
            box.selection_clear(0, tk.END)
            box.selection_set(index)
            box.see(index)
            return "break"
        return None

    def _on_return(self, _event=None):
        if not self._axia_predictive:
            return None
        box = self._axia_listbox
        if box is not None and box.curselection():
            self._select_match(box.curselection()[0])
            return "break"
        match = _exact_value(self._axia_all_values, self.get())
        if match is None:
            matches = _filter_values(self._axia_all_values, self.get())
            if len(matches) == 1:
                match = str(matches[0])
        if match is not None:
            self._axia_editing = False
            self._hide_suggestions()
            self.set(match)
            self._axia_selected = match
            if callable(self._axia_command):
                self._axia_command(match)
        else:
            self._revert_invalid()
        return "break"

    def _revert_invalid(self) -> None:
        value = _exact_value(self._axia_all_values, self.get())
        if value is None:
            value = self._axia_selected if _exact_value(self._axia_all_values, self._axia_selected) is not None else ""
        self._axia_editing = False
        self._hide_suggestions()
        self.set(value)

    def _on_escape(self, _event=None):
        if self._axia_predictive:
            self._axia_editing = False
            self._hide_suggestions()
            self.set(self._axia_selected)
            return "break"
        return None

    def _on_focusout(self, _event=None):
        if not self._axia_predictive:
            return None
        try:
            self.after(120, self._finish_focusout)
        except tk.TclError:
            pass
        return None

    def _finish_focusout(self):
        if not self.winfo_exists():
            return
        current_focus = self.focus_get()
        if current_focus is self or (self._axia_listbox is not None and current_focus is self._axia_listbox):
            return
        if self._axia_editing:
            match = _exact_value(self._axia_all_values, self.get())
            if match is not None:
                self._axia_editing = False
                self._hide_suggestions()
                self.set(match)
                self._axia_selected = match
                if callable(self._axia_command):
                    self._axia_command(match)
            else:
                self._revert_invalid()
        else:
            self._hide_suggestions()

    def _on_mousewheel(self, event=None):
        if self._axia_listbox is not None:
            return None
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
            self._hide_suggestions()
        if "state" in kwargs:
            kwargs["state"] = self._map_state(kwargs["state"], self._axia_predictive)
            if kwargs["state"] == "disabled":
                self._hide_suggestions()
        if "values" in kwargs:
            self._axia_all_values = _sorted_values(kwargs["values"])
            kwargs["values"] = self._axia_all_values
            self._axia_editing = False
            self._hide_suggestions()
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
