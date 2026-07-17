"""Navegación global por teclado para AXIA.

CustomTkinter no incorpora todos sus controles personalizados al recorrido
nativo de TAB. Este módulo crea un recorrido lógico dinámico que incluye
campos de texto, selectores, casillas, interruptores y botones.
"""
from __future__ import annotations

import customtkinter as ctk

_SUPPORTED = tuple(
    cls for cls in (
        getattr(ctk, "CTkEntry", None),
        getattr(ctk, "CTkTextbox", None),
        getattr(ctk, "CTkComboBox", None),
        getattr(ctk, "CTkOptionMenu", None),
        getattr(ctk, "CTkCheckBox", None),
        getattr(ctk, "CTkRadioButton", None),
        getattr(ctk, "CTkSwitch", None),
        getattr(ctk, "CTkButton", None),
    ) if cls is not None
)

_SELECTORS = tuple(
    cls for cls in (
        getattr(ctk, "CTkComboBox", None),
        getattr(ctk, "CTkOptionMenu", None),
    ) if cls is not None
)
_ACTIONS = tuple(
    cls for cls in (
        getattr(ctk, "CTkCheckBox", None),
        getattr(ctk, "CTkRadioButton", None),
        getattr(ctk, "CTkSwitch", None),
        getattr(ctk, "CTkButton", None),
    ) if cls is not None
)


def _enabled(widget) -> bool:
    try:
        return str(widget.cget("state")).lower() != "disabled"
    except Exception:
        return True


def _visible(widget) -> bool:
    try:
        return bool(widget.winfo_exists() and widget.winfo_viewable())
    except Exception:
        return False


def _walk(widget):
    """Recorre en orden de creación, equivalente al flujo visual usual."""
    try:
        children = widget.winfo_children()
    except Exception:
        return
    for child in children:
        if isinstance(child, _SUPPORTED) and _enabled(child) and _visible(child):
            yield child
        yield from _walk(child)


def _contains(parent, child) -> bool:
    current = child
    while current is not None:
        if current == parent:
            return True
        try:
            current = current.master
        except Exception:
            break
    return False


def _scroll_into_view(widget) -> None:
    """Intenta desplazar el CTkScrollableFrame que contiene al control."""
    current = widget
    while current is not None:
        canvas = getattr(current, "_parent_canvas", None)
        if canvas is not None:
            try:
                current.update_idletasks()
                y = max(0, widget.winfo_rooty() - current.winfo_rooty())
                total = max(1, current.winfo_height())
                canvas.yview_moveto(max(0.0, min(1.0, y / total - 0.08)))
            except Exception:
                pass
            return
        current = getattr(current, "master", None)


def _focus(widget) -> None:
    _scroll_into_view(widget)
    try:
        widget.focus_set()
    except Exception:
        pass


def _selector_step(widget, delta: int) -> bool:
    if not isinstance(widget, _SELECTORS):
        return False
    try:
        values = list(widget.cget("values") or [])
        if not values:
            return True
        current = widget.get()
        try:
            index = values.index(current)
        except ValueError:
            index = 0
        value = values[(index + delta) % len(values)]
        widget.set(value)
        command = getattr(widget, "_command", None)
        if callable(command):
            command(value)
        return True
    except Exception:
        return True


def install_keyboard_navigation(root) -> None:
    """Instala una sola vez la navegación global TAB/Shift+TAB."""
    if getattr(root, "_axia_keyboard_navigation", False):
        return
    root._axia_keyboard_navigation = True

    def controls():
        return list(_walk(root))

    def current_wrapper(items):
        focused = root.focus_get()
        if focused is None:
            return None
        for item in items:
            if _contains(item, focused):
                return item
        return None

    def move(event, backwards=False):
        items = controls()
        if not items:
            return "break"
        current = current_wrapper(items)
        if current is None:
            target = items[-1] if backwards else items[0]
        else:
            index = items.index(current)
            target = items[(index - 1 if backwards else index + 1) % len(items)]
        _focus(target)
        return "break"

    def key_action(event):
        items = controls()
        current = current_wrapper(items)
        if current is None:
            return None
        key = event.keysym
        if key in {"Up", "Left"} and _selector_step(current, -1):
            return "break"
        if key in {"Down", "Right"} and _selector_step(current, 1):
            return "break"
        if key in {"Return", "KP_Enter", "space"} and isinstance(current, _ACTIONS):
            try:
                current.invoke()
            except Exception:
                pass
            return "break"
        return None

    root.bind_all("<Tab>", lambda e: move(e, False), add="+")
    root.bind_all("<Shift-Tab>", lambda e: move(e, True), add="+")
    root.bind_all("<ISO_Left_Tab>", lambda e: move(e, True), add="+")
    root.bind_all("<KeyPress>", key_action, add="+")
