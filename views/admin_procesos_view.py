"""
=========================================================
MÓDULO: views/admin_procesos_view.py
DESCRIPCIÓN:
Vistas administrativas/consulta para procesos operativos.

Regla de negocio:
- El sidebar administrativo NO debe abrir formularios de generación.
- La generación de procesos debe iniciar desde Inicio ACO.
- Estas vistas sirven para buscar, consultar y revisar registros existentes.
=========================================================
"""

import customtkinter as ctk
from tkinter import messagebox

from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY, BUTTON_HOVER
from ui.fonts import TITLE_MD, TEXT_MD, TEXT_SM, BUTTON_FONT
from services.export_service import exportar_registros_dialogo
from ui.detail_popup import mostrar_detalle_registro
from core.background_tasks import run_async


def _valor(registro, campos, default="No registrado"):
    """
    Obtiene el primer valor disponible dentro de una lista de posibles campos.
    Esto permite tolerar pequeñas diferencias entre tablas sin romper la vista.
    """

    for campo in campos:
        valor = registro.get(campo)
        if valor not in (None, ""):
            return str(valor)
    return default


def _crear_card_resultado(parent, registro, configuracion):
    """
    Renderiza una tarjeta simple con la información principal del registro.
    """

    card = ctk.CTkFrame(
        parent,
        fg_color="#f8fafc",
        corner_radius=14,
        border_width=1,
        border_color="#e2e8f0"
    )
    card.pack(fill="x", padx=18, pady=8)

    folio = _valor(registro, [configuracion["campo_folio"]])
    aco = _valor(registro, configuracion["campos_aco"])
    cliente = _valor(registro, configuracion["campos_cliente"])
    estatus = _valor(registro, configuracion["campos_estatus"])
    fecha = _valor(registro, configuracion["campos_fecha"])
    descripcion = _valor(registro, configuracion["campos_descripcion"])

    ctk.CTkLabel(
        card,
        text=f"📄 {folio}",
        font=("Montserrat", 15, "bold"),
        text_color=TEXT_PRIMARY,
        anchor="w"
    ).pack(fill="x", padx=16, pady=(12, 4))

    info = (
        f"ACO: {aco}\n"
        f"Cliente: {cliente}\n"
        f"Estatus: {estatus}    Fecha: {fecha}\n"
        f"Descripción: {descripcion}"
    )

    ctk.CTkLabel(
        card,
        text=info,
        font=TEXT_SM,
        text_color=TEXT_SECONDARY,
        anchor="w",
        justify="left",
        wraplength=980
    ).pack(fill="x", padx=16, pady=(0, 8))

    acciones = ctk.CTkFrame(card, fg_color="transparent")
    acciones.pack(fill="x", padx=16, pady=(0, 12))

    ctk.CTkButton(
        acciones,
        text="👁 Vista rápida",
        width=130,
        height=32,
        fg_color="#64748B",
        hover_color="#475569",
        font=TEXT_SM,
        command=lambda r=registro: mostrar_detalle_registro(parent, f"Vista rápida - {folio}", r)
    ).pack(side="left", padx=(0, 8))

    ctk.CTkButton(
        acciones,
        text="⬇ Exportar seleccionado",
        width=180,
        height=32,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=TEXT_SM,
        command=lambda r=registro, f=folio: exportar_registros_dialogo(r, f"AXIA_{f}")
    ).pack(side="left")


def mostrar_admin_procesos(parent, app, configuracion):
    """
    Construye una vista administrativa genérica para procesos.

    Args:
        parent: Contenedor principal.
        app: Instancia de la aplicación.
        configuracion: Diccionario con nombre de proceso, funciones y campos.
    """

    contenedor = ctk.CTkFrame(parent, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=30, pady=(5, 24))
    contenedor.grid_columnconfigure(0, weight=1)
    contenedor.grid_rowconfigure(1, weight=1)

    barra_busqueda = ctk.CTkFrame(
        contenedor,
        fg_color=WHITE,
        corner_radius=18
    )
    barra_busqueda.grid(row=0, column=0, sticky="ew", pady=(0, 16))
    barra_busqueda.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        barra_busqueda,
        text=f"Administración de {configuracion['titulo']}",
        font=TITLE_MD,
        text_color=TEXT_PRIMARY,
        anchor="w"
    ).grid(row=0, column=0, columnspan=3, sticky="ew", padx=22, pady=(18, 4))

    ctk.CTkLabel(
        barra_busqueda,
        text="Ingresa un folio para consultar. No se cargan registros automáticamente para mejorar rendimiento.",
        font=TEXT_MD,
        text_color=TEXT_SECONDARY,
        anchor="w"
    ).grid(row=1, column=0, columnspan=3, sticky="ew", padx=22, pady=(0, 14))

    var_folio = ctk.StringVar()

    entrada = ctk.CTkEntry(
        barra_busqueda,
        textvariable=var_folio,
        height=42,
        corner_radius=12,
        placeholder_text=f"Ejemplo: {configuracion['prefijo']}-0001"
    )
    entrada.grid(row=2, column=0, sticky="ew", padx=(22, 10), pady=(0, 18))

    resultados = ctk.CTkScrollableFrame(
        contenedor,
        fg_color=WHITE,
        corner_radius=18
    )
    resultados.grid(row=1, column=0, sticky="nsew")

    def limpiar_resultados():
        for widget in resultados.winfo_children():
            widget.destroy()

    def renderizar_lista(registros):
        limpiar_resultados()

        if not registros:
            ctk.CTkLabel(
                resultados,
                text="No se encontraron registros.",
                font=TEXT_MD,
                text_color=TEXT_SECONDARY
            ).pack(pady=80)
            return

        ctk.CTkLabel(
            resultados,
            text=f"Resultados ({len(registros)})",
            font=TITLE_MD,
            text_color=TEXT_PRIMARY,
            anchor="w"
        ).pack(fill="x", padx=18, pady=(18, 8))

        for registro in registros:
            _crear_card_resultado(resultados, registro, configuracion)

    def mostrar_cargando(mensaje="Consultando información..."):
        limpiar_resultados()
        ctk.CTkLabel(
            resultados,
            text=mensaje,
            font=TEXT_MD,
            text_color=TEXT_SECONDARY
        ).pack(pady=80)

    def buscar_por_folio():
        folio = var_folio.get().strip()

        if not folio:
            messagebox.showwarning(
                "Campo requerido",
                "Captura un folio para realizar la búsqueda."
            )
            return

        mostrar_cargando("Buscando folio...")

        run_async(
            root=parent.winfo_toplevel(),
            task=lambda: configuracion["buscar_por_folio"](folio),
            on_success=lambda registro: renderizar_lista([registro] if registro else []),
            on_error=lambda error: messagebox.showerror("Error", f"No fue posible consultar el folio.\n\n{error}")
        )

    def cargar_recientes():
        mostrar_cargando("Cargando registros recientes...")

        run_async(
            root=parent.winfo_toplevel(),
            task=lambda: configuracion["obtener_todos"](),
            on_success=lambda registros: renderizar_lista((registros or [])[:50]),
            on_error=lambda error: messagebox.showerror("Error", f"No fue posible cargar los registros.\n\n{error}")
        )

    ctk.CTkButton(
        barra_busqueda,
        text="🔎 Buscar",
        width=150,
        height=42,
        corner_radius=12,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=buscar_por_folio
    ).grid(row=2, column=1, padx=(0, 10), pady=(0, 18))

    def limpiar_busqueda():
        var_folio.set("")
        limpiar_resultados()
        ctk.CTkLabel(
            resultados,
            text="Ingresa un folio para consultar registros.",
            font=TEXT_MD,
            text_color=TEXT_SECONDARY
        ).pack(pady=80)

    ctk.CTkButton(
        barra_busqueda,
        text="↻ Limpiar",
        width=160,
        height=42,
        corner_radius=12,
        fg_color="#334155",
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=limpiar_busqueda
    ).grid(row=2, column=2, padx=(0, 22), pady=(0, 18))

    entrada.bind("<Return>", lambda _event: buscar_por_folio())
    limpiar_busqueda()
