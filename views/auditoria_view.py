"""
=========================================================
MÓDULO: views/auditoria_view.py
DESCRIPCIÓN:
Vista administrativa para consultar la auditoría de movimientos.

Incluye filtros por fecha, usuario, módulo, equipo e IP.
=========================================================
"""

import customtkinter as ctk
from tkinter import messagebox

from app_context import obtener_usuario_actual
from security.permissions import es_admin
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY, SECONDARY, BUTTON_HOVER
from ui.fonts import TEXT_MD, TEXT_SM, BUTTON_FONT
from services.movimientos_service import buscar_movimientos
from services.export_service import exportar_registros_dialogo
from ui.detail_popup import mostrar_detalle_registro


CAMPOS_AUDITORIA = [
    ("fecha_hora", "Fecha"),
    ("usuario", "Usuario"),
    ("modulo", "Módulo"),
    ("accion", "Acción"),
    ("descripcion", "Descripción"),
    ("equipo", "Equipo"),
    ("ip_local", "IP"),
]


def mostrar_auditoria(parent, app):
    """
    Renderiza la vista de auditoría para administradores.
    """

    usuario_activo = obtener_usuario_actual()
    if not es_admin(usuario_activo):
        messagebox.showerror("Acceso denegado", "Solo administradores pueden consultar auditoría.")
        app.mostrar_vista_inicio_aco()
        return

    for widget in parent.winfo_children():
        widget.destroy()

    estado = {
        "registros": [],
    }

    contenedor = ctk.CTkFrame(parent, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=28, pady=8)

    barra = ctk.CTkFrame(contenedor, fg_color="transparent")
    barra.pack(fill="x", pady=(0, 10))
    barra.grid_columnconfigure(0, weight=1)

    resumen = ctk.CTkFrame(barra, fg_color=WHITE, corner_radius=16)
    resumen.grid(row=0, column=0, sticky="ew", padx=(0, 10))
    resumen.grid_columnconfigure((0, 1, 2), weight=1)

    metricas = [
        ("Movimientos", "Buscar"),
        ("Usuarios", "Bajo demanda"),
        ("Módulos", "Sin carga inicial"),
    ]

    for columna, (etiqueta, valor) in enumerate(metricas):
        ctk.CTkLabel(
            resumen,
            text=etiqueta,
            font=TEXT_SM,
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=0, column=columna, sticky="w", padx=18, pady=(12, 0))

        ctk.CTkLabel(
            resumen,
            text=str(valor),
            font=TEXT_MD,
            text_color=PRIMARY,
            anchor="w",
        ).grid(row=1, column=columna, sticky="w", padx=18, pady=(0, 12))

    filtros = ctk.CTkFrame(contenedor, fg_color=WHITE, corner_radius=16)
    filtros.pack(fill="x", pady=(0, 10))
    filtros.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="filtros")

    variables = {
        "fecha": ctk.StringVar(),
        "usuario": ctk.StringVar(),
        "modulo": ctk.StringVar(),
        "equipo": ctk.StringVar(),
        "ip": ctk.StringVar(),
    }

    campos_filtro = [
        ("fecha", "📅 Fecha"),
        ("usuario", "👤 Usuario"),
        ("modulo", "🧩 Módulo"),
        ("equipo", "💻 Equipo"),
        ("ip", "🌐 Dirección IP"),
    ]

    for columna, (clave, etiqueta) in enumerate(campos_filtro):
        wrapper = ctk.CTkFrame(filtros, fg_color="transparent")
        wrapper.grid(row=0, column=columna, sticky="ew", padx=10, pady=(10, 8))
        wrapper.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            wrapper,
            text=etiqueta,
            font=TEXT_SM,
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        entry = ctk.CTkEntry(
            wrapper,
            textvariable=variables[clave],
            height=34,
        )
        entry.grid(row=1, column=0, sticky="ew", pady=(3, 0))
        entry.bind("<Return>", lambda _event: aplicar_filtros())

    acciones = ctk.CTkFrame(contenedor, fg_color="transparent")
    acciones.pack(fill="x", pady=(0, 10))

    ctk.CTkButton(
        acciones,
        text="🔎 Buscar",
        width=120,
        height=38,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=lambda: aplicar_filtros(),
    ).pack(side="left", padx=(0, 8))

    ctk.CTkButton(
        acciones,
        text="↻ Limpiar filtros",
        width=150,
        height=38,
        fg_color="#64748B",
        hover_color="#475569",
        font=BUTTON_FONT,
        command=lambda: limpiar_filtros(),
    ).pack(side="left", padx=(0, 8))

    ctk.CTkButton(
        acciones,
        text="⬇ Exportar filtrados",
        width=170,
        height=38,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=lambda: exportar_registros_dialogo(estado.get("filtrados", []), "AXIA_auditoria_filtrada"),
    ).pack(side="left")

    panel = ctk.CTkScrollableFrame(contenedor, fg_color=WHITE, corner_radius=16)
    panel.pack(fill="both", expand=True)

    def coincide_filtros(movimiento):
        fecha = variables["fecha"].get().strip().lower()
        usuario = variables["usuario"].get().strip().lower()
        modulo = variables["modulo"].get().strip().lower()
        equipo = variables["equipo"].get().strip().lower()
        ip = variables["ip"].get().strip().lower()

        condiciones = [
            (fecha, str(movimiento.get("fecha_hora", "") or "").lower()),
            (usuario, str(movimiento.get("usuario", "") or "").lower()),
            (modulo, str(movimiento.get("modulo", "") or "").lower()),
            (equipo, str(movimiento.get("equipo", "") or "").lower()),
            (ip, str(movimiento.get("ip_local", "") or "").lower()),
        ]

        return all(not filtro or filtro in valor for filtro, valor in condiciones)

    def pintar_tabla(registros):
        for widget in panel.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            panel,
            text=f"Movimientos encontrados ({len(registros)})",
            font=("Montserrat", 16, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w", padx=18, pady=(16, 8))

        if not registros:
            ctk.CTkLabel(
                panel,
                text="Ingresa filtros y presiona Buscar para consultar movimientos.",
                font=TEXT_SM,
                text_color=TEXT_SECONDARY,
                anchor="w",
            ).pack(anchor="w", padx=18, pady=8)
            return

        header = ctk.CTkFrame(panel, fg_color="#F4F7FB", corner_radius=10)
        header.pack(fill="x", padx=18, pady=(0, 4))

        for columna, (_campo, etiqueta) in enumerate(CAMPOS_AUDITORIA):
            peso = 2 if _campo == "descripcion" else 1
            header.grid_columnconfigure(columna, weight=peso, uniform="auditoria")
            ctk.CTkLabel(
                header,
                text=etiqueta,
                font=TEXT_SM,
                text_color=TEXT_PRIMARY,
                anchor="w",
                justify="left",
            ).grid(row=0, column=columna, sticky="ew", padx=8, pady=8)

        for movimiento in registros[:100]:
            fila = ctk.CTkFrame(panel, fg_color="transparent")
            fila.pack(fill="x", padx=18, pady=2)

            for columna, (campo, _etiqueta) in enumerate(CAMPOS_AUDITORIA):
                peso = 2 if campo == "descripcion" else 1
                fila.grid_columnconfigure(columna, weight=peso, uniform="auditoria")
                valor = str(movimiento.get(campo, "") or "-")
                ctk.CTkLabel(
                    fila,
                    text=valor,
                    font=TEXT_SM,
                    text_color=TEXT_SECONDARY,
                    anchor="w",
                    justify="left",
                    wraplength=260 if campo == "descripcion" else 150,
                ).grid(row=0, column=columna, sticky="ew", padx=8, pady=5)

            acciones_fila = ctk.CTkFrame(fila, fg_color="transparent")
            acciones_fila.grid(row=0, column=len(CAMPOS_AUDITORIA), sticky="e", padx=8, pady=3)
            ctk.CTkButton(acciones_fila, text="👁", width=34, height=28, fg_color="#64748B", hover_color="#475569", command=lambda r=movimiento: mostrar_detalle_registro(parent, "Movimiento de auditoría", r)).pack(side="left", padx=(0, 4))
            ctk.CTkButton(acciones_fila, text="⬇", width=34, height=28, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=lambda r=movimiento: exportar_registros_dialogo(r, "AXIA_movimiento_auditoria")).pack(side="left")

        if len(registros) > 100:
            ctk.CTkLabel(
                panel,
                text=f"Mostrando los 100 movimientos más recientes de {len(registros)} registros.",
                font=TEXT_SM,
                text_color=TEXT_SECONDARY,
                anchor="e",
            ).pack(anchor="e", padx=18, pady=(8, 16))

    def aplicar_filtros():
        termino = " ".join(
            variable.get().strip()
            for variable in variables.values()
            if variable.get().strip()
        ).strip()

        if not termino:
            messagebox.showwarning("Búsqueda requerida", "Ingresa al menos un filtro para consultar auditoría.")
            pintar_tabla([])
            return

        registros = buscar_movimientos(termino=termino, limite=200) or []
        filtrados = [movimiento for movimiento in registros if coincide_filtros(movimiento)]
        estado["registros"] = registros
        estado["filtrados"] = filtrados
        pintar_tabla(filtrados)

    def limpiar_filtros():
        for variable in variables.values():
            variable.set("")
        estado["registros"] = []
        estado["filtrados"] = []
        pintar_tabla([])

    pintar_tabla([])
