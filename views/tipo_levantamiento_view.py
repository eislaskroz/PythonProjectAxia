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
from ui.iconos import cargar_icono
from tkinter import messagebox
from pathlib import Path
from PIL import Image

from ui.colors import WHITE, PRIMARY, SECONDARY, TEXT_PRIMARY, TEXT_SECONDARY, BUTTON_HOVER
from ui.fonts import TITLE_MD, TEXT_MD, TEXT_SM, BUTTON_FONT
from services.movimientos_service import registrar_movimiento


TIPOS_LEVANTAMIENTO = [
    {"nombre": "General", "habilitado": True, "icono": "📋"},
    {"nombre": "Seguridad y Monitoreo", "habilitado": True, "icono_archivo": "1.png"},
    {"nombre": "Redes Voz y Datos", "habilitado": True, "icono_archivo": "2.png"},
    {"nombre": "Control de Accesos", "habilitado": True, "icono_archivo": "3.png"},
    {"nombre": "Enlaces Inalámbricos", "habilitado": True, "icono_archivo": "4.png"},
    {"nombre": "Tecnología, Equipos y Periféricos", "habilitado": True, "icono_archivo": "10.png", "icono": "💻"},
    {"nombre": "Electricidad", "habilitado": True, "icono_archivo": "5.png"},
    {"nombre": "Paneles Solares", "habilitado": True, "icono_archivo": "6.png"},
    {"nombre": "Plantas de Energía", "habilitado": True, "icono_archivo": "7.png"},
    {"nombre": "Obra Civil", "habilitado": True, "icono_archivo": "8.png"},
    # Se conserva el módulo ya implementado para no perder funcionalidad.
    {"nombre": "Aires Acondicionados", "habilitado": True, "icono_archivo": "9.png", "icono": "❄️"},
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

    # Seis columnas lógicas: cada tarjeta ocupa dos. Esto permite
    # centrar las dos tarjetas finales conservando exactamente el ancho
    # de las tarjetas de las tres primeras filas.
    for col in range(6):
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

    total_tipos = len(TIPOS_LEVANTAMIENTO)
    for indice, tipo in enumerate(TIPOS_LEVANTAMIENTO):
        fila = indice // 3
        columna = (indice % 3) * 2
        # Si sobran dos tarjetas, distribuirlas simétricamente en el centro.
        # Con 11 opciones ocuparán las columnas 1-2 y 3-4 (sobre seis).
        if total_tipos % 3 == 2 and indice >= total_tipos - 2:
            columna += 1

        item = ctk.CTkFrame(
            grid,
            fg_color="#F8FAFC" if tipo["habilitado"] else "#F1F5F9",
            corner_radius=16,
            border_width=1,
            border_color="#CBD5E1" if tipo["habilitado"] else "#E2E8F0"
        )
        item.grid(row=fila, column=columna, columnspan=2, sticky="nsew", padx=5, pady=5)
        item.grid_columnconfigure(0, weight=1)

        # Separar ícono y nombre en widgets independientes garantiza una
        # separación uniforme también cuando se usa un ícono de respaldo.
        encabezado = ctk.CTkFrame(item, fg_color="transparent")
        encabezado.pack(fill="x", padx=9, pady=(10, 8))
        icono_tipo = cargar_icono(tipo.get("icono_archivo", ""), (24, 24)) if tipo.get("icono_archivo") else None
        if icono_tipo:
            ctk.CTkLabel(encabezado, text="", image=icono_tipo, width=24, height=28).pack(side="left", padx=(0, 9))
        elif tipo.get("icono"):
            ctk.CTkLabel(encabezado, text=tipo["icono"], font=("Segoe UI Emoji", 18), width=24, height=28).pack(side="left", padx=(0, 9))
        ctk.CTkLabel(
            encabezado,
            text=tipo["nombre"],
            font=("Montserrat", 16, "bold"),
            text_color=PRIMARY if tipo["habilitado"] else "#64748B",
            anchor="w",
            height=28,
        ).pack(side="left", fill="x", expand=True)

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

    carpeta_iconos = Path(__file__).resolve().parent.parent / "assets" / "iconos"

    def cargar_icono_barra(nombre):
        with Image.open(carpeta_iconos / nombre) as imagen:
            imagen = imagen.convert("RGBA")
        icono_blanco = Image.new("RGBA", imagen.size, (255, 255, 255, 0))
        icono_blanco.putalpha(imagen.getchannel("A"))
        return ctk.CTkImage(
            light_image=icono_blanco,
            dark_image=icono_blanco,
            size=(18, 18)
        )

    icono_atras = cargar_icono_barra("f2.png")
    icono_inicio = cargar_icono_barra("f1.png")

    ctk.CTkButton(
        barra,
        text="Atrás",
        image=icono_atras,
        compound="left",
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
        text="Regresar a Inicio ACO",
        image=icono_inicio,
        compound="left",
        width=210,
        height=40,
        corner_radius=12,
        fg_color="gray",
        font=BUTTON_FONT,
        command=app.mostrar_vista_inicio_aco
    ).grid(row=0, column=1, padx=4)
