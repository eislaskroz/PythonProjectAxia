"""
=========================================================
MÓDULO: reportes_view.py
DESCRIPCIÓN:
Vista administrativa para consultar reportes actuales del sistema AXIA.

Esta vista es de solo lectura y está pensada para administradores.
Incluye búsquedas rápidas por ACO, levantamiento, orden de servicio,
orden de trabajo y bitácora operativa.
=========================================================
"""

import customtkinter as ctk
from tkinter import messagebox

from app_context import obtener_usuario_actual
from security.permissions import es_admin

from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY, SECONDARY, BUTTON_HOVER
from ui.fonts import TEXT_MD, TEXT_SM, BUTTON_FONT

from services.acos_service import obtener_acos, buscar_aco_por_numero
from services.levantamientos_service import obtener_levantamientos, buscar_levantamiento_por_folio
from services.ordenes_servicio_service import obtener_ordenes_servicio, buscar_orden_por_folio
from services.ordenes_trabajo_service import obtener_ordenes_trabajo, buscar_orden_trabajo_por_folio
from services.bitacoras_service import obtener_bitacoras, buscar_bitacora_por_folio
from services.obras_civiles_service import obtener_obras_civiles, buscar_obra_civil_por_folio
from services.export_service import exportar_registros_dialogo
from ui.detail_popup import mostrar_detalle_registro


REPORTES = [
    {
        "titulo": "ACOs registrados",
        "icono": "📁",
        "placeholder": "Buscar por número de ACO...",
        "obtener": obtener_acos,
        "buscar": buscar_aco_por_numero,
        "campos": ["aco_numero", "aco_cliente", "aco_responsable", "aco_fecha_inicio", "aco_fecha_compromiso"],
    },
    {
        "titulo": "Levantamientos",
        "icono": "📋",
        "placeholder": "Buscar por folio LEV-0001...",
        "obtener": obtener_levantamientos,
        "buscar": buscar_levantamiento_por_folio,
        "campos": ["lev_folio", "lev_aco_numero", "lev_cliente", "lev_tecnico", "lev_fecha_programada"],
    },
    {
        "titulo": "Órdenes de servicio",
        "icono": "🧾",
        "placeholder": "Buscar por folio OS-0001...",
        "obtener": obtener_ordenes_servicio,
        "buscar": buscar_orden_por_folio,
        "campos": ["os_folio", "os_aco_numero", "os_cliente", "os_tecnico", "os_fecha_programada"],
    },
    {
        "titulo": "Órdenes de trabajo",
        "icono": "🛠️",
        "placeholder": "Buscar por folio OT-0001...",
        "obtener": obtener_ordenes_trabajo,
        "buscar": buscar_orden_trabajo_por_folio,
        "campos": ["ot_folio", "ot_aco_numero", "ot_cliente", "ot_tecnico", "ot_fecha_programada"],
    },
    {
        "titulo": "Bitácoras operativas",
        "icono": "📊",
        "placeholder": "Buscar por folio BIT-0001...",
        "obtener": obtener_bitacoras,
        "buscar": buscar_bitacora_por_folio,
        "campos": ["bit_folio", "bit_aco_numero", "bit_cliente", "bit_tecnico", "bit_avance"],
    },
    {
        "titulo": "Obras civiles",
        "icono": "🏗️",
        "placeholder": "Buscar por folio OBC-0001...",
        "obtener": obtener_obras_civiles,
        "buscar": buscar_obra_civil_por_folio,
        "campos": ["obc_folio", "obc_aco_numero", "obc_cliente", "obc_nombre_proyecto", "obc_fecha"],
    },
]


def mostrar_reportes(parent, app):
    """
    Muestra reportes administrativos con botones/filtros de búsqueda.
    """

    usuario_activo = obtener_usuario_actual()

    if not es_admin(usuario_activo):
        messagebox.showerror(
            "Acceso denegado",
            "Solo administradores pueden consultar reportes."
        )
        app.mostrar_vista_inicio_aco()
        return

    for widget in parent.winfo_children():
        widget.destroy()

    contenedor = ctk.CTkFrame(parent, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=28, pady=8)

    scroll = ctk.CTkScrollableFrame(
        contenedor,
        fg_color="transparent",
        corner_radius=0
    )
    scroll.pack(fill="both", expand=True)

    for reporte in REPORTES:
        crear_bloque_reporte(scroll, reporte)


def crear_bloque_reporte(parent, reporte):
    """
    Crea una tarjeta visual para un reporte con búsqueda individual.
    """

    estado = {
        "registros": [],
    }

    card = ctk.CTkFrame(
        parent,
        fg_color=WHITE,
        corner_radius=18
    )
    card.pack(fill="x", pady=(0, 16), padx=4)

    header = ctk.CTkFrame(card, fg_color="transparent")
    header.pack(fill="x", padx=22, pady=(16, 8))
    header.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        header,
        text=f"{reporte['icono']} {reporte['titulo']}",
        font=TEXT_MD,
        text_color=TEXT_PRIMARY,
        anchor="w",
    ).grid(row=0, column=0, sticky="w")

    total_label = ctk.CTkLabel(
        header,
        text="Resultados: 0",
        font=TEXT_SM,
        text_color=PRIMARY
    )
    total_label.grid(row=0, column=1, sticky="e")

    barra = ctk.CTkFrame(card, fg_color="transparent")
    barra.pack(fill="x", padx=22, pady=(0, 10))
    barra.grid_columnconfigure(0, weight=1)

    var_busqueda = ctk.StringVar()
    entry_busqueda = ctk.CTkEntry(
        barra,
        textvariable=var_busqueda,
        placeholder_text=reporte["placeholder"],
        height=36,
    )
    entry_busqueda.grid(row=0, column=0, sticky="ew", padx=(0, 8))

    ctk.CTkButton(
        barra,
        text="🔎 Buscar",
        width=110,
        height=36,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=lambda: buscar(),
    ).grid(row=0, column=1, padx=(0, 8))

    ctk.CTkButton(
        barra,
        text="↻ Limpiar",
        width=120,
        height=36,
        fg_color="#64748B",
        hover_color="#475569",
        font=BUTTON_FONT,
        command=lambda: limpiar(),
    ).grid(row=0, column=2)

    panel_tabla = ctk.CTkFrame(card, fg_color="transparent")
    panel_tabla.pack(fill="x", padx=0, pady=(0, 8))

    def pintar(registros):
        for widget in panel_tabla.winfo_children():
            widget.destroy()

        total_label.configure(text=f"Resultados: {len(registros)}")

        if not registros:
            ctk.CTkLabel(
                panel_tabla,
                text="Sin registros para mostrar. Ingresa un criterio de búsqueda.",
                font=TEXT_SM,
                text_color=TEXT_SECONDARY,
                anchor="w",
            ).pack(anchor="w", padx=24, pady=(0, 14))
            return

        fila_header = ctk.CTkFrame(panel_tabla, fg_color="#F4F7FB", corner_radius=10)
        fila_header.pack(fill="x", padx=22, pady=(4, 4))

        for columna, campo in enumerate(reporte["campos"]):
            fila_header.grid_columnconfigure(columna, weight=1, uniform="cols")
            ctk.CTkLabel(
                fila_header,
                text=campo,
                font=TEXT_SM,
                text_color=TEXT_PRIMARY,
                anchor="w"
            ).grid(row=0, column=columna, sticky="ew", padx=8, pady=8)

        for registro in registros[:10]:
            fila = ctk.CTkFrame(panel_tabla, fg_color="transparent")
            fila.pack(fill="x", padx=22, pady=2)

            for columna, campo in enumerate(reporte["campos"]):
                fila.grid_columnconfigure(columna, weight=1, uniform="cols")
                valor = registro.get(campo, "")
                ctk.CTkLabel(
                    fila,
                    text=str(valor or "-"),
                    font=TEXT_SM,
                    text_color=TEXT_SECONDARY,
                    anchor="w",
                    justify="left",
                    wraplength=180
                ).grid(row=0, column=columna, sticky="ew", padx=8, pady=5)

            acciones_fila = ctk.CTkFrame(fila, fg_color="transparent")
            acciones_fila.grid(row=0, column=len(reporte["campos"]), sticky="e", padx=8, pady=3)
            ctk.CTkButton(
                acciones_fila,
                text="👁",
                width=36,
                height=28,
                fg_color="#64748B",
                hover_color="#475569",
                command=lambda r=registro: mostrar_detalle_registro(parent, "Vista rápida", r)
            ).pack(side="left", padx=(0, 4))
            ctk.CTkButton(
                acciones_fila,
                text="⬇",
                width=36,
                height=28,
                fg_color=SECONDARY,
                hover_color=BUTTON_HOVER,
                command=lambda r=registro: exportar_registros_dialogo(r, "AXIA_reporte_seleccionado")
            ).pack(side="left")

        if len(registros) > 10:
            ctk.CTkLabel(
                panel_tabla,
                text=f"Mostrando 10 de {len(registros)} registros.",
                font=TEXT_SM,
                text_color=TEXT_SECONDARY
            ).pack(anchor="e", padx=24, pady=(4, 10))

    def cargar_todos():
        try:
            estado["registros"] = reporte["obtener"]() or []
        except Exception:
            estado["registros"] = []
        pintar(estado["registros"])

    def buscar():
        termino = var_busqueda.get().strip()

        if not termino:
            messagebox.showwarning("Búsqueda requerida", "Ingresa un dato para consultar este reporte.")
            limpiar()
            return

        try:
            encontrado = reporte["buscar"](termino)
            estado["registros"] = [encontrado] if encontrado else []
        except Exception:
            estado["registros"] = []

        pintar(estado["registros"])

    def limpiar():
        var_busqueda.set("")
        estado["registros"] = []
        pintar([])

    entry_busqueda.bind("<Return>", lambda _event: buscar())
    limpiar()
