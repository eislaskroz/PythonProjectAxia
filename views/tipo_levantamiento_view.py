"""
=========================================================
MÓDULO: tipo_levantamiento_view.py
DESCRIPCIÓN:
Selector inicial para definir el tipo de levantamiento.

Regla operativa:
Antes de mostrar el formulario de levantamiento, el técnico
primero debe indicar qué tipo de levantamiento realizará.
Esto permite que AXIA cargue formularios dedicados por área.
=========================================================
"""

import customtkinter as ctk
from tkinter import messagebox

from ui.colors import WHITE, PRIMARY, SECONDARY, TEXT_PRIMARY, TEXT_SECONDARY, BUTTON_HOVER
from ui.fonts import TITLE_MD, TEXT_MD, TEXT_SM, BUTTON_FONT
from services.movimientos_service import registrar_movimiento


TIPOS_LEVANTAMIENTO = [
    {"nombre": "Seguridad y Monitoreo", "habilitado": True, "icono": "📹"},
    {"nombre": "Redes Voz y Datos", "habilitado": True, "icono": "🌐"},
    {"nombre": "Control de Accesos", "habilitado": True, "icono": "🚪"},
    {"nombre": "Enlaces Inalámbricos", "habilitado": True, "icono": "📡"},
    {"nombre": "Tecnología, Equipos y Periféricos", "habilitado": True, "icono": "💻"},
    {"nombre": "Electricidad", "habilitado": True, "icono": "🔌"},
    {"nombre": "Paneles Solares", "habilitado": True, "icono": "☀️"},
    {"nombre": "Plantas de Energía", "habilitado": True, "icono": "⚡"},
    {"nombre": "Obra Civil", "habilitado": True, "icono": "🏗️"},
    # Se conserva el módulo ya implementado para no perder funcionalidad.
    {"nombre": "Aires Acondicionados", "habilitado": True, "icono": "❄️"},
]


def mostrar_selector_tipo_levantamiento(parent, app, aco=None):
    """
    Muestra una pantalla previa al formulario de levantamiento.

    Args:
        parent:
            Contenedor dinámico principal.
        app:
            Instancia principal de AXIA.
        aco:
            ACO opcional previamente validado desde Inicio ACO.
    """

    for widget in parent.winfo_children():
        widget.destroy()

    contenedor = ctk.CTkFrame(parent, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=12, pady=5)

    card = ctk.CTkFrame(
        contenedor,
        fg_color=WHITE,
        corner_radius=22
    )
    card.pack(fill="both", expand=True, padx=4, pady=4)

    ctk.CTkLabel(
        card,
        text="¿Qué tipo de levantamiento deseas realizar?",
        font=TITLE_MD,
        text_color=TEXT_PRIMARY
    ).pack(pady=(14, 3))

    ctk.CTkLabel(
        card,
        text="Selecciona el proceso operativo que necesitas capturar.",
        font=TEXT_MD,
        text_color=TEXT_SECONDARY
    ).pack(pady=(0, 11))

    grid = ctk.CTkFrame(card, fg_color="transparent")
    grid.pack(fill="both", expand=True, padx=18, pady=(0, 10))

    for col in range(3):
        grid.grid_columnconfigure(col, weight=1, uniform="tipos_lev")

    def seleccionar_tipo(tipo):
        if not tipo.get("habilitado"):
            messagebox.showinfo(
                "Formulario en preparación",
                f"El levantamiento de {tipo['nombre']} se agregará en una siguiente etapa."
            )
            return

        registrar_movimiento(
            modulo="Levantamientos",
            accion="SELECCIONAR_TIPO",
            descripcion=f"El usuario seleccionó levantamiento tipo {tipo['nombre']}",
            registro_afectado=tipo["nombre"]
        )
        if tipo["nombre"] == "Obra Civil":
            app.mostrar_vista_obra_civil(aco=aco)
        else:
            app.mostrar_vista_levantamiento(aco=aco, tipo_levantamiento=tipo["nombre"])

    for indice, tipo in enumerate(TIPOS_LEVANTAMIENTO):
        fila = indice // 3
        columna = indice % 3

        item = ctk.CTkFrame(
            grid,
            fg_color="#F8FAFC" if tipo["habilitado"] else "#F1F5F9",
            corner_radius=16,
            border_width=1,
            border_color="#CBD5E1" if tipo["habilitado"] else "#E2E8F0"
        )
        item.grid(row=fila, column=columna, sticky="nsew", padx=5, pady=5)
        item.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            item,
            text=f"{tipo['icono']} {tipo['nombre']}",
            font=("Montserrat", 16, "bold"),
            text_color=PRIMARY if tipo["habilitado"] else "#64748B"
        ).pack(anchor="w", padx=9, pady=(10, 8))

        ctk.CTkButton(
            item,
            text="Iniciar" if tipo["habilitado"] else "Próximamente",
            height=36,
            corner_radius=10,
            fg_color=SECONDARY if tipo["habilitado"] else "#94A3B8",
            hover_color=BUTTON_HOVER if tipo["habilitado"] else "#94A3B8",
            font=BUTTON_FONT,
            state="normal" if tipo["habilitado"] else "disabled",
            command=lambda t=tipo: seleccionar_tipo(t)
        ).pack(fill="x", padx=9, pady=(0, 10))

    barra = ctk.CTkFrame(card, fg_color="transparent")
    barra.pack(pady=(0, 12))
    ctk.CTkButton(
        barra,
        text="⬅ Atrás",
        width=120,
        height=40,
        corner_radius=12,
        fg_color="#64748B",
        hover_color="#475569",
        font=BUTTON_FONT,
        command=app.volver_atras
    ).grid(row=0, column=0, padx=4)
    ctk.CTkButton(
        barra,
        text="↩ Regresar a Inicio ACO",
        width=210,
        height=40,
        corner_radius=12,
        fg_color="gray",
        font=BUTTON_FONT,
        command=app.mostrar_vista_inicio_aco
    ).grid(row=0, column=1, padx=4)
