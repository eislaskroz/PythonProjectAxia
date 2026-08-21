# =====================================================
# THEME MANAGER AXIA
# =====================================================
"""Administrador visual centralizado para AXIA.

Objetivo:
- Mantener la misma paleta de colores entre Windows 10/11 y equipos distintos.
- Forzar modo claro para evitar variaciones por tema del sistema.
- Usar Montserrat desde ui/fonts.py como fuente base.
- Centralizar colores, radios, escalas y estilos nativos de Tk/ttk.
"""



from __future__ import annotations

from core.logger import configurar_logger

logger = configurar_logger(__name__)

import os
import sys
from pathlib import Path

import customtkinter as ctk

from ui.fonts import FONT_FAMILY


class ThemeManager:
    """Punto único para aplicar la identidad visual de AXIA."""

    APP_NAME = "AXIA"

    # Paleta fija. Usar estos valores evita que Windows cambie colores
    # por modo oscuro, tema de accesibilidad o configuración del sistema.
    PRIMARY = "#000A8B"
    PRIMARY_DARK = "#0F2337"
    SECONDARY = "#0369F8"
    BACKGROUND = "#F4F6F8"
    SURFACE = "#FFFFFF"
    TEXT_PRIMARY = "#111827"
    TEXT_SECONDARY = "#6B7280"
    BORDER = "#B8C4D1"
    INPUT_BACKGROUND = "#EEF2F6"
    TEXTBOX_BACKGROUND = "#EEF2F6"
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
        """Devuelve una ruta compatible con desarrollo y PyInstaller."""
        base_path = getattr(sys, "_MEIPASS", None)
        if base_path:
            return str(Path(base_path) / relative_path)
        return str(Path(__file__).resolve().parent.parent / relative_path)

    @classmethod
    def theme_json_path(cls) -> str:
        return cls.resource_path("ui/axia_theme.json")

    @classmethod
    def apply_global_theme(cls) -> None:
        """Aplica tema global antes de crear ventanas.

        Debe ejecutarse al inicio del programa, antes de abrir Login/App.
        """
        try:
            ctk.set_appearance_mode("Light")
            theme_path = cls.theme_json_path()
            if os.path.exists(theme_path):
                ctk.set_default_color_theme(theme_path)
            else:
                ctk.set_default_color_theme("blue")
            ctk.set_widget_scaling(cls.WIDGET_SCALING)
            ctk.set_window_scaling(cls.WINDOW_SCALING)

            # FIX9: campos de captura visualmente homologados.
            # Algunos formularios aún declaran corner_radius localmente; este
            # parche central obliga a que CTkEntry/CTkTextbox sean cuadrados
            # sin tocar botones, tarjetas ni otros controles.
            cls._aplicar_campos_cuadrados()
        except Exception:
            # Si por alguna razón falla el tema personalizado, la app no debe detenerse.
            try:
                ctk.set_appearance_mode("Light")
                ctk.set_default_color_theme("blue")
            except Exception:
                logger.debug("Excepción recuperable controlada.", exc_info=True)

    @classmethod
    def _aplicar_campos_cuadrados(cls) -> None:
        """Fuerza CTkEntry y CTkTextbox con esquinas cuadradas en toda AXIA."""
        for widget_cls in (ctk.CTkEntry, ctk.CTkTextbox):
            if getattr(widget_cls, "_axia_square_inputs", False):
                continue
            original_init = widget_cls.__init__

            def _init_cuadrado(self, *args, __orig=original_init, **kwargs):
                kwargs["corner_radius"] = 0
                return __orig(self, *args, **kwargs)

            widget_cls.__init__ = _init_cuadrado
            widget_cls._axia_square_inputs = True

    @classmethod
    def apply_native_tk_theme(cls, root=None) -> None:
        """Fuerza fuente y colores en widgets nativos Tk/ttk.

        CustomTkinter toma la mayoría del estilo desde axia_theme.json,
        pero algunos diálogos, menús, Treeview o widgets Tk siguen usando
        configuraciones nativas. Este método reduce esas diferencias.
        """
        try:
            import tkinter as tk
            import tkinter.font as tkfont
            from tkinter import ttk

            # Fuentes nativas Tk.
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

            # Estilo ttk uniforme para tablas/combos nativos.
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
                    rowheight=28,
                    bordercolor=cls.BORDER,
                    lightcolor=cls.BORDER,
                    darkcolor=cls.BORDER,
                )
                style.configure(
                    "Treeview.Heading",
                    font=(cls.FONT_FAMILY, cls.BASE_FONT_SIZE, "bold"),
                    background=cls.PRIMARY_DARK,
                    foreground="#FFFFFF",
                )
                style.map("Treeview", background=[("selected", cls.PRIMARY)], foreground=[("selected", "#FFFFFF")])
                style.configure("TCombobox", fieldbackground=cls.SURFACE, background=cls.SURFACE)
            except Exception:
                logger.debug("Excepción recuperable controlada.", exc_info=True)

            # Fondo base de la ventana raíz.
            if root is not None:
                try:
                    root.configure(bg=cls.BACKGROUND)
                except Exception:
                    logger.debug("Excepción recuperable controlada.", exc_info=True)
        except Exception:
            logger.debug("Excepción recuperable controlada.", exc_info=True)

    @classmethod
    def apply_window_defaults(cls, window, min_width: int | None = None, min_height: int | None = None) -> None:
        """Aplica ajustes comunes a una ventana concreta."""
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
        """Nombre genérico para metadata de PDFs/vistas previas."""
        return "Sistema AXIA"
