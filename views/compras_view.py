"""Bandeja inicial del módulo de Compras AXIA."""
from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

from app_context import obtener_usuario_actual
from core.background_tasks import run_async
from core.logger import configurar_logger
from security.permissions import puede_ver_compras
from services.cotizaciones_service import obtener_cotizaciones_en_compra
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY, BUTTON_HOVER
from ui.fonts import TITLE_MD, TEXT_MD, BUTTON_FONT
from ui.native_table import NativeTreeTable

logger = configurar_logger(__name__)


def _txt(reg, key):
    return str((reg or {}).get(key) or "").strip()


def _money(value):
    try:
        return f"${float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def mostrar_compras(parent, app=None):
    usuario = obtener_usuario_actual()
    if not puede_ver_compras(usuario):
        messagebox.showerror("Acceso denegado", "Este módulo está disponible para Compras (id=7) y Administrador.")
        return

    for widget in parent.winfo_children():
        widget.destroy()

    root = ctk.CTkFrame(parent, fg_color="transparent")
    root.pack(fill="both", expand=True, padx=14, pady=(4, 12))
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)

    cabecera = ctk.CTkFrame(root, fg_color=WHITE, corner_radius=16)
    cabecera.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    cabecera.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(cabecera, text="Compras", font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w").grid(
        row=0, column=0, sticky="ew", padx=14, pady=(10, 2)
    )
    ctk.CTkLabel(
        cabecera,
        text="Cotizaciones finalizadas por Ventas y pendientes de iniciar el proceso de compra. En esta etapa todavía no se genera una Orden de Trabajo.",
        font=TEXT_MD, text_color=TEXT_SECONDARY, anchor="w", wraplength=1050,
    ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

    panel = ctk.CTkFrame(root, fg_color=WHITE, corner_radius=16)
    panel.grid(row=1, column=0, sticky="nsew")
    panel.grid_columnconfigure(0, weight=1)
    panel.grid_rowconfigure(1, weight=1)

    lbl = ctk.CTkLabel(panel, text="Pendientes de compra (0)", font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w")
    lbl.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 5))

    tabla = NativeTreeTable(
        panel,
        columns=(
            ("cot", "Cotización", 130),
            ("lev", "Levantamiento", 130),
            ("cliente", "Cliente", 250),
            ("asunto", "Asunto", 260),
            ("total", "Total MXN", 135),
            ("fecha", "Finalizada", 155),
        ),
        height=22,
    )
    tabla.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))

    pie = ctk.CTkFrame(panel, fg_color="transparent")
    pie.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
    pie.grid_columnconfigure(0, weight=1)
    lbl_estado = ctk.CTkLabel(pie, text="", text_color=TEXT_SECONDARY, anchor="w")
    lbl_estado.grid(row=0, column=0, sticky="ew")

    def cargar():
        lbl_estado.configure(text="Consultando cotizaciones pendientes...")
        def ok(registros):
            registros = list(registros or [])
            lbl.configure(text=f"Pendientes de compra ({len(registros)})")
            tabla.set_rows(
                registros,
                value_factory=lambda r: (
                    _txt(r, "cot_folio"),
                    _txt(r, "lev_folio"),
                    _txt(r, "cot_cliente"),
                    _txt(r, "cot_asunto"),
                    _money(r.get("cot_total")),
                    _txt(r, "cot_fecha_finalizacion")[:19].replace("T", " "),
                ),
            )
            lbl_estado.configure(
                text="Sin cotizaciones pendientes." if not registros else "Selecciona una cotización cuando el siguiente flujo de Compras sea habilitado."
            )
        run_async(
            parent.winfo_toplevel(),
            obtener_cotizaciones_en_compra,
            ok,
            lambda e: (logger.exception("Error cargando Compras"), messagebox.showerror("Compras", str(e))),
        )

    ctk.CTkButton(
        pie, text="↻ Actualizar", width=145, height=38, fg_color=SECONDARY,
        hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=cargar,
    ).grid(row=0, column=1, padx=(8, 0))

    cargar()
