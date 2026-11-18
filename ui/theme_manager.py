# =====================================================
# THEME MANAGER AXIA
# =====================================================
from __future__ import annotations

from core.logger import configurar_logger

logger = configurar_logger(__name__)

import os
import sys
from pathlib import Path

import customtkinter as ctk

from ui.fonts import FONT_FAMILY


class ThemeManager:
    APP_NAME = "AXIA"

    PRIMARY = "#000A8B"
    PRIMARY_DARK = "#0F2337"
    SECONDARY = "#0369F8"
    BACKGROUND = "#F4F6F8"
    SURFACE = "#FFFFFF"
    SURFACE_SOFT = "#F8FAFC"
    SURFACE_MUTED = "#F1F5F9"
    PRIMARY_50 = "#EEF2FF"
    PRIMARY_100 = "#E0E7FF"
    PRIMARY_700 = "#1E3A8A"
    TEXT_PRIMARY = "#111827"
    TEXT_SECONDARY = "#6B7280"
    TEXT_MUTED = "#94A3B8"
    DIVIDER = "#E2E8F0"
    BORDER = "#CBD5E1"
    INPUT_BACKGROUND = "#FFFFFF"
    TEXTBOX_BACKGROUND = "#FFFFFF"
    BUTTON_HOVER = "#1D4ED8"
    SUCCESS = "#16A34A"
    WARNING = "#F59E0B"
    DANGER = "#DC2626"

    FONT_FAMILY = FONT_FAMILY
    BASE_FONT_SIZE = 12
    WIDGET_SCALING = 1.0
    WINDOW_SCALING = 1.0

    @classmethod
    def resource_path(cls, relative_path: str) -> str:
        base_path = getattr(sys, "_MEIPASS", None)
        if base_path:
            return str(Path(base_path) / relative_path)
        return str(Path(__file__).resolve().parent.parent / relative_path)

    @classmethod
    def theme_json_path(cls) -> str:
        return cls.resource_path("ui/axia_theme.json")

    @classmethod
    def apply_global_theme(cls) -> None:
        try:
            ctk.set_appearance_mode("Light")
            theme_path = cls.theme_json_path()
            if os.path.exists(theme_path):
                ctk.set_default_color_theme(theme_path)
            else:
                ctk.set_default_color_theme("blue")
            ctk.set_widget_scaling(cls.WIDGET_SCALING)
            ctk.set_window_scaling(cls.WINDOW_SCALING)
        except Exception:
            try:
                ctk.set_appearance_mode("Light")
                ctk.set_default_color_theme("blue")
            except Exception:
                logger.debug("Excepción recuperable controlada.", exc_info=True)

    @classmethod
    def apply_native_tk_theme(cls, root=None) -> None:
        try:
            import tkinter as tk
            import tkinter.font as tkfont
            from tkinter import ttk

            for name in (
                "TkDefaultFont",
                "TkTextFont",
                "TkFixedFont",
                "TkMenuFont",
                "TkHeadingFont",
                "TkCaptionFont",
                "TkSmallCaptionFont",
                "TkIconFont",
                "TkTooltipFont",
            ):
                try:
                    font = tkfont.nametofont(name)
                    font.configure(family=cls.FONT_FAMILY, size=cls.BASE_FONT_SIZE)
                except Exception:
                    logger.debug("Excepción recuperable controlada.", exc_info=True)

            try:
                style = ttk.Style(root)
                style.theme_use("clam")
                style.configure(
                    ".",
                    font=(cls.FONT_FAMILY, cls.BASE_FONT_SIZE),
                    background=cls.BACKGROUND,
                    foreground=cls.TEXT_PRIMARY,
                    fieldbackground=cls.SURFACE,
                )
                style.configure(
                    "Treeview",
                    background=cls.SURFACE,
                    fieldbackground=cls.SURFACE,
                    foreground=cls.TEXT_PRIMARY,
                    rowheight=32,
                    bordercolor=cls.DIVIDER,
                    lightcolor=cls.DIVIDER,
                    darkcolor=cls.DIVIDER,
                    borderwidth=0,
                )
                style.configure(
                    "Treeview.Heading",
                    font=(cls.FONT_FAMILY, cls.BASE_FONT_SIZE),
                    background=cls.PRIMARY_DARK,
                    foreground="#FFFFFF",
                    padding=(10, 8),
                    bordercolor=cls.PRIMARY_700,
                    lightcolor=cls.PRIMARY_700,
                    darkcolor=cls.PRIMARY_700,
                    borderwidth=0,
                )
                style.map("Treeview", background=[("selected", cls.PRIMARY)], foreground=[("selected", "#FFFFFF")])
                style.map("Treeview.Heading", background=[("active", cls.PRIMARY_700)])
                try:
                    root.option_add("*TCombobox*Listbox*Background", cls.SURFACE)
                    root.option_add("*TCombobox*Listbox*Foreground", cls.TEXT_PRIMARY)
                    root.option_add("*TCombobox*Listbox*Font", (cls.FONT_FAMILY, cls.BASE_FONT_SIZE))
                    root.option_add("*TCombobox*Listbox*selectBackground", cls.PRIMARY)
                    root.option_add("*TCombobox*Listbox*selectForeground", "#FFFFFF")
                except Exception:
                    pass

                style.configure(
                    "TCombobox", fieldbackground="#E1E0DD",
                    background="#E1E0DD", padding=4,
                    bordercolor="#B9C5D2", lightcolor="#B9C5D2",
                    darkcolor="#B9C5D2", borderwidth=1,
                )
                style.map(
                    "TCombobox",
                    fieldbackground=[("disabled", "#F2F4F7"), ("readonly", "#E1E0DD")],
                    foreground=[("disabled", "#8391A2"), ("readonly", cls.TEXT_PRIMARY)],
                )
            except Exception:
                logger.debug("Excepción recuperable controlada.", exc_info=True)

            if root is not None:
                try:
                    root.configure(bg=cls.BACKGROUND)
                except Exception:
                    logger.debug("Excepción recuperable controlada.", exc_info=True)
        except Exception:
            logger.debug("Excepción recuperable controlada.", exc_info=True)

    @classmethod
    def apply_window_defaults(cls, window, min_width: int | None = None, min_height: int | None = None) -> None:
        cls.apply_native_tk_theme(window)
        try:
            window.configure(fg_color=cls.BACKGROUND)
        except Exception:
            logger.debug("Excepción recuperable controlada.", exc_info=True)
        if min_width and min_height:
            try:
                window.minsize(min_width, min_height)
            except Exception:
                logger.debug("Excepción recuperable controlada.", exc_info=True)

    @classmethod
    def style_preview_metadata_name(cls) -> str:
        return "Sistema AXIA"