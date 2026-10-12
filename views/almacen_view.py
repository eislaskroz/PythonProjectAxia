"""Módulo Almacén, etapa inicial: catálogo de referencia, sin movimientos."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from tkinter import messagebox
import customtkinter as ctk

from app_context import obtener_usuario_actual
from security.permissions import puede_ver_almacen
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY
from ui.fonts import TITLE_MD, TEXT_MD
from ui.native_table import NativeTreeTable


def _moneda(valor):
    try:
        return f"${float(valor or 0):,.2f}"
    except (ValueError, TypeError):
        return "—"


def _catalogo():
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    archivo = base / "assets" / "almacen_catalogo_eleventa.json"
    with archivo.open("r", encoding="utf-8") as f:
        return json.load(f)


def mostrar_almacen(parent, app=None):
    if not puede_ver_almacen(obtener_usuario_actual()):
        messagebox.showerror("Acceso denegado", "Se requiere nivel Almacén o Administrador.")
        return
    root = ctk.CTkFrame(parent, fg_color="transparent")
    root.pack(fill="both", expand=True, padx=14, pady=(4, 12))
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(2, weight=1)

    cab = ctk.CTkFrame(root, fg_color=WHITE, corner_radius=14)
    cab.grid(row=0, column=0, sticky="ew", pady=(0, 9))
    cab.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(cab, text="Almacén · Catálogo inicial", font=TITLE_MD,
                 text_color=TEXT_PRIMARY, anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))
    ctk.CTkLabel(cab,
                 text="VISTA DE CONSULTA — Datos de BD.xlsx (ELEVENTA). Las existencias son una fotografía histórica, NO inventario en vivo.",
                 font=TEXT_MD, text_color="#A65E09", anchor="w", wraplength=1000,
                 justify="left").grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

    herramientas = ctk.CTkFrame(root, fg_color=WHITE, corner_radius=12)
    herramientas.grid(row=1, column=0, sticky="ew", pady=(0, 9))
    herramientas.grid_columnconfigure(0, weight=1)
    buscar = ctk.CTkEntry(herramientas, placeholder_text="Buscar por código, producto o departamento...", height=36)
    buscar.grid(row=0, column=0, sticky="ew", padx=12, pady=10)
    contador = ctk.CTkLabel(herramientas, text="", text_color=TEXT_SECONDARY)
    contador.grid(row=0, column=1, padx=(4, 14))

    panel = ctk.CTkFrame(root, fg_color=WHITE, corner_radius=12)
    panel.grid(row=2, column=0, sticky="nsew")
    panel.grid_columnconfigure(0, weight=1)
    panel.grid_rowconfigure(0, weight=1)
    tabla = NativeTreeTable(panel, columns=(
        ("codigo", "Código", 140), ("producto", "Producto", 335),
        ("departamento", "Departamento", 160), ("existencia", "Existencia exportada", 145),
        ("costo", "P. costo", 95), ("venta", "P. venta", 95),
        ("minimo", "Mínimo", 85), ("maximo", "Máximo", 85),
    ), height=19)
    tabla.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    footer = ctk.CTkLabel(root,
        text="Entradas, salidas y ajustes: pendientes de habilitar en Supabase con transacciones, permisos y Kardex. No se modifica ningún dato.",
        text_color=SECONDARY, anchor="w", wraplength=1050)
    footer.grid(row=3, column=0, sticky="ew", pady=(7, 0))

    try:
        registros = _catalogo()
    except (OSError, ValueError) as exc:
        messagebox.showerror("Catálogo no disponible", f"No se pudo abrir el catálogo inicial: {exc}")
        return

    def refrescar(*_):
        filtro = buscar.get().strip().casefold()
        visibles = [r for r in registros if not filtro or any(
            filtro in str(r.get(k, "")).casefold() for k in ("codigo", "producto", "departamento")
        )]
        tabla.set_rows([{**r, "costo": _moneda(r.get("costo")), "venta": _moneda(r.get("venta"))}
                        for r in visibles])
        contador.configure(text=f"{len(visibles):,} / {len(registros):,} productos")

    buscar.bind("<KeyRelease>", refrescar)
    refrescar()
