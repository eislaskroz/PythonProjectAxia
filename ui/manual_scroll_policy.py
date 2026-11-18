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
    if getattr(root, "_axia_manual_scroll_only", False):
        return
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

    for widget_class in ("Treeview", "Text", "TCombobox", "Listbox", "Canvas"):
        for event in _WHEEL_EVENTS:
            root.bind_class(widget_class, event, _ignore_wheel)

    root._axia_manual_scroll_only = True
