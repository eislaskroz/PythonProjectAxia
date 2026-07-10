
"""Ventana emergente para vista rápida de registros seleccionados."""

import customtkinter as ctk


def mostrar_detalle_registro(parent, titulo, registro):
    ventana = ctk.CTkToplevel(parent)
    ventana.title(titulo)
    ventana.geometry("760x560")
    ventana.grab_set()

    contenedor = ctk.CTkFrame(ventana, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=18, pady=18)

    ctk.CTkLabel(
        contenedor,
        text=titulo,
        font=("Montserrat", 20, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 12))

    scroll = ctk.CTkScrollableFrame(contenedor, corner_radius=14)
    scroll.pack(fill="both", expand=True)
    scroll.grid_columnconfigure(0, weight=0)
    scroll.grid_columnconfigure(1, weight=1)

    for fila, (campo, valor) in enumerate((registro or {}).items()):
        ctk.CTkLabel(
            scroll,
            text=str(campo),
            font=("Montserrat", 12, "bold"),
            anchor="w",
        ).grid(row=fila, column=0, sticky="nw", padx=12, pady=6)
        ctk.CTkLabel(
            scroll,
            text=str(valor or "-"),
            font=("Montserrat", 12),
            anchor="w",
            justify="left",
            wraplength=520,
        ).grid(row=fila, column=1, sticky="ew", padx=12, pady=6)

    ctk.CTkButton(contenedor, text="Cerrar", width=140, command=ventana.destroy).pack(anchor="e", pady=(12, 0))
