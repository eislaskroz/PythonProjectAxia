"""
=========================================================
MÓDULO: ui/app_sidebar.py
DESCRIPCIÓN:
Componente visual del menú lateral principal de AXIA.

OBJETIVO:
Sacar la construcción del sidebar fuera de app.py.

Este archivo se encarga únicamente de UI:
- Logo.
- Datos del usuario activo.
- Botones de navegación.
- Botón salir.

IMPORTANTE:
No debe tener lógica de negocio ni consultas a Supabase.
Recibe callbacks ya preparados desde app.py/controladores.
=========================================================
"""

# =====================================================
# IMPORTACIÓN DE LIBRERÍAS
# =====================================================

import customtkinter as ctk

# =====================================================
# IMPORTACIÓN DE RECURSOS VISUALES
# =====================================================

from ui.assets import cargar_logo_axia

from ui.colors import (
    PRIMARY_DARK,
    SECONDARY,
    WHITE,
    BUTTON_HOVER
)

from ui.fonts import (
    FONT_FAMILY,
    TEXT_SM,
    BUTTON_FONT
)

from security.permissions import es_admin


# =====================================================
# FUNCIÓN: crear_boton_sidebar()
# =====================================================
def crear_boton_sidebar(parent, texto, comando=None, habilitado=True):
    """Crea una opción del menú lateral con icono y texto alineados.

    Los emojis se colocan en una columna fija con fuente Segoe UI Emoji para
    evitar que cada símbolo empuje el texto a posiciones distintas.
    """

    partes = texto.split(" ", 1)
    icono = partes[0] if len(partes) > 1 else ""
    etiqueta = partes[1] if len(partes) > 1 else texto

    fila = ctk.CTkFrame(
        parent,
        width=214,
        height=40,
        corner_radius=10,
        fg_color="transparent" if habilitado else "#1e293b",
    )
    fila.pack(pady=4, padx=18, fill="x")
    fila.pack_propagate(False)
    fila.grid_propagate(False)
    fila.grid_columnconfigure(0, minsize=34, weight=0)
    fila.grid_columnconfigure(1, weight=1)

    color_texto = WHITE if habilitado else "#64748b"

    lbl_icono = ctk.CTkLabel(
        fila,
        text=icono,
        width=34,
        height=40,
        font=("Segoe UI Emoji", 16),
        text_color=color_texto,
        anchor="center",
    )
    lbl_icono.grid(row=0, column=0, sticky="nsew", padx=(4, 2), pady=0)

    lbl_texto = ctk.CTkLabel(
        fila,
        text=etiqueta,
        height=40,
        font=(FONT_FAMILY, 13),
        text_color=color_texto,
        anchor="w",
    )
    lbl_texto.grid(row=0, column=1, sticky="nsew", padx=(6, 8), pady=0)

    if habilitado and comando:
        def ejecutar(_event=None):
            comando()

        def hover(_event=None):
            fila.configure(fg_color=BUTTON_HOVER)

        def leave(_event=None):
            fila.configure(fg_color="transparent")

        for widget in (fila, lbl_icono, lbl_texto):
            widget.bind("<Button-1>", ejecutar)
            widget.bind("<Enter>", hover)
            widget.bind("<Leave>", leave)
            try:
                widget.configure(cursor="hand2")
            except Exception:
                pass



# =====================================================
# FUNCIÓN: crear_app_sidebar()
# =====================================================
def crear_app_sidebar(parent, usuario_activo, callbacks, on_exit, on_logout=None):
    """
    Construye el menú lateral principal.

    Args:
        parent:
            Frame layout donde se colocará el sidebar.
        usuario_activo:
            Diccionario con datos del usuario actual.
        callbacks:
            Diccionario de funciones de navegación.
        on_exit:
            Función para cerrar la aplicación.
        on_logout:
            Función opcional para cerrar sesión y volver al Login.

    Returns:
        CTkFrame:
            Sidebar completamente construido.
    """

    sidebar = ctk.CTkFrame(
        parent,
        width=260,
        fg_color=PRIMARY_DARK,
        corner_radius=0
    )
    sidebar.grid(
        row=0,
        column=0,
        sticky="ns"
    )
    sidebar.pack_propagate(False)

    # =================================================
    # LOGOTIPO
    # =================================================
    logo_axia = cargar_logo_axia(size=(155, 155))

    label_logo = ctk.CTkLabel(
        sidebar,
        image=logo_axia,
        text=""
    )
    label_logo.image = logo_axia
    label_logo.pack(pady=(18, 18))

    # =================================================
    # INFORMACIÓN DEL USUARIO
    # =================================================
    # Se eliminan las etiquetas de usuario/rol para liberar
    # espacio vertical en el menú lateral. La sesión sigue
    # disponible internamente mediante app_context.

    # =================================================
    # BOTONES PRINCIPALES
    # =================================================
    usuario_es_admin = es_admin(usuario_activo)

    crear_boton_sidebar(
        sidebar,
        "🏠 Inicio ACO",
        callbacks["inicio_aco"]
    )

    crear_boton_sidebar(
        sidebar,
        "📋 Levantamientos",
        callbacks["admin_levantamientos"] if usuario_es_admin else callbacks["levantamiento"]
    )

    crear_boton_sidebar(
        sidebar,
        "🧾 Órdenes de servicio",
        callbacks["admin_ordenes_servicio"] if usuario_es_admin else None,
        habilitado=usuario_es_admin
    )

    crear_boton_sidebar(
        sidebar,
        "🛠️ Órdenes de trabajo",
        callbacks["admin_ordenes_trabajo"] if usuario_es_admin else None,
        habilitado=usuario_es_admin
    )

    crear_boton_sidebar(
        sidebar,
        "📊 Bitácoras operativas",
        callbacks["admin_bitacoras"] if usuario_es_admin else None,
        habilitado=usuario_es_admin
    )

    # Obras civiles se retira del menú lateral.
    # El flujo queda integrado desde Inicio ACO / Levantamientos.

    # =================================================
    # OPCIONES ADMINISTRADOR
    # =================================================
    if usuario_es_admin:
        crear_boton_sidebar(
            sidebar,
            "📈 Reportes",
            callbacks["reportes"]
        )

        # Dashboard se retira temporalmente porque todavía no
        # aporta funcionalidad operativa y ocupa espacio vertical.

        crear_boton_sidebar(
            sidebar,
            "🛡️ Auditoría",
            callbacks["auditoria"]
        )

        crear_boton_sidebar(
            sidebar,
            "👥 Usuarios",
            callbacks["usuarios"]
        )

        crear_boton_sidebar(
            sidebar,
            "🏢 Clientes",
            callbacks["clientes"]
        )

    # =================================================
    # ESPACIO FLEXIBLE
    # =================================================
    ctk.CTkLabel(
        sidebar,
        text=""
    ).pack(expand=True)

    # =================================================
    # MI USUARIO Y ACCIONES DE SESIÓN
    # =================================================
    # Administradores no muestran este acceso para conservar
    # espacio en el menú lateral. Ellos ya consultan usuarios
    # desde el módulo administrativo.
    if not usuario_es_admin:
        crear_boton_sidebar(
            sidebar,
            "👤 Mi Usuario",
            callbacks.get("mi_usuario") or callbacks.get("mi_bitacora")
        )

    acciones_sesion = ctk.CTkFrame(
        sidebar,
        fg_color="transparent"
    )
    acciones_sesion.pack(
        pady=(4, 25),
        padx=20,
        fill="x"
    )
    acciones_sesion.grid_columnconfigure(0, weight=1)
    acciones_sesion.grid_columnconfigure(1, weight=1)

    ctk.CTkButton(
        acciones_sesion,
        text="🔒 Cerrar",
        width=98,
        height=38,
        corner_radius=10,
        fg_color="#64748B",
        hover_color="#475569",
        text_color=WHITE,
        font=BUTTON_FONT,
        command=on_logout or on_exit
    ).grid(
        row=0,
        column=0,
        sticky="ew",
        padx=(0, 4)
    )

    ctk.CTkButton(
        acciones_sesion,
        text="⏻ Salir",
        width=98,
        height=38,
        corner_radius=10,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        text_color=WHITE,
        font=BUTTON_FONT,
        command=on_exit
    ).grid(
        row=0,
        column=1,
        sticky="ew",
        padx=(4, 0)
    )

    return sidebar
