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

from core.logger import configurar_logger

logger = configurar_logger(__name__)

# =====================================================
# IMPORTACIÓN DE LIBRERÍAS
# =====================================================

import customtkinter as ctk
import tkinter as tk
import sys
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps, ImageTk

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

from security.permissions import (
    OPERADOR,
    obtener_tipo_usuario,
    es_admin,
    puede_administrar_clientes,
    puede_administrar_usuarios,
    puede_consultar_procesos,
    puede_entrar_inicio_aco,
    puede_generar_levantamiento,
    puede_cotizar_levantamientos,
    puede_ver_compras,
    puede_generar_orden_servicio,
    puede_ver_auditoria,
    puede_ver_reportes,
    puede_ver_bitacoras_operativas,
)


# =====================================================
# FONDO TEMÁTICO DE LEVANTAMIENTOS
# =====================================================
_FONDOS_SIDEBAR = {
    "Seguridad y Monitoreo": "fondo_seguridad_monitoreo.png",
    "Redes Voz y Datos": "fondo_redes_voz_datos.png",
    "Control de Accesos": "fondo_control_accesos.png",
    "Enlaces Inalámbricos": "fondo_enlaces_inalambricos.png",
    "Tecnología, Equipos y Periféricos": "fondo_tecnologia.png",
    "Electricidad": "fondo_electricidad.png",
    "Paneles Solares": "fondo_paneles_solares.png",
    "Plantas de Energía": "fondo_plantas_energia.png",
    "Aires Acondicionados": "fondo_aires_acondicionados.png",
}

def _ruta_recurso_sidebar(nombre):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets" / nombre

def _crear_fondo_sidebar(tipo, size=(260, 900)):
    """Crea un wallpaper que cubre TODO el sidebar sin deformar la imagen.

    Se usa recorte tipo cover y un velo azul oscuro para que textos/botones
    mantengan contraste. La imagen no se limita al área del logotipo.
    """
    nombre = _FONDOS_SIDEBAR.get(str(tipo or "").strip())
    if not nombre:
        return None
    ruta = _ruta_recurso_sidebar(nombre)
    if not ruta.exists():
        logger.warning("No se encontró fondo de sidebar para %s: %s", tipo, ruta)
        return None
    ancho=max(220, int(size[0] or 260))
    alto=max(600, int(size[1] or 900))
    with Image.open(ruta) as src:
        base = ImageOps.fit(src.convert("RGB"), (ancho, alto), method=Image.Resampling.LANCZOS)
    base = ImageEnhance.Brightness(base).enhance(0.34).convert("RGBA")
    # Velo corporativo para conservar contraste de menú y botones.
    velo = Image.new("RGBA", (ancho, alto), (15, 35, 55, 105))
    base = Image.alpha_composite(base, velo)
    return ImageTk.PhotoImage(base)

def _redibujar_fondo_sidebar(sidebar):
    tipo = getattr(sidebar, "_axia_sidebar_tipo", None)
    label = getattr(sidebar, "_axia_background_label", None)
    if sidebar is None or label is None:
        return
    if not tipo:
        try:
            label.place_forget()
        except Exception:
            pass
        return
    try:
        sidebar.update_idletasks()
        ancho = max(220, sidebar.winfo_width())
        alto = max(600, sidebar.winfo_height())
        imagen = _crear_fondo_sidebar(tipo, (ancho, alto))
        if imagen is None:
            label.place_forget()
            return
        label.configure(image=imagen, text="", bd=0, highlightthickness=0)
        label.image = imagen
        sidebar._axia_background_image = imagen
        label.place(x=0, y=0, relwidth=1, relheight=1)
        # IMPORTANTE: no bajar el label sin referencia. En CustomTkinter
        # eso puede mandar la imagen por debajo del canvas/fondo interno del
        # CTkFrame y volverla invisible. La dejamos por encima del fondo del
        # sidebar, pero justo por debajo del primer control real; los demás
        # controles fueron creados después y permanecen encima.
        hijos = [w for w in sidebar.winfo_children() if w is not label]
        if hijos:
            try:
                label.lower(hijos[0])
            except Exception:
                pass
    except Exception:
        logger.debug("No se pudo redibujar fondo temático del sidebar.", exc_info=True)

def actualizar_sidebar_especialidad(sidebar, tipo_levantamiento=None):
    """Activa/desactiva el wallpaper de especialidad en todo el sidebar."""
    if sidebar is None:
        return
    sidebar._axia_sidebar_tipo = str(tipo_levantamiento or "").strip() or None
    # El logo corporativo permanece como capa superior; el wallpaper cubre
    # desde el borde superior hasta las acciones de sesión.
    _redibujar_fondo_sidebar(sidebar)

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
    fila.pack(pady=2, padx=9, fill="x")
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
    lbl_icono.grid(row=0, column=0, sticky="nsew", padx=(2, 1), pady=0)

    lbl_texto = ctk.CTkLabel(
        fila,
        text=etiqueta,
        height=40,
        font=(FONT_FAMILY, 13),
        text_color=color_texto,
        anchor="w",
    )
    lbl_texto.grid(row=0, column=1, sticky="nsew", padx=(3, 4), pady=0)

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
                logger.debug("Excepción recuperable controlada.", exc_info=True)



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

    # Wallpaper temático: ocupa toda la superficie del sidebar y se activa
    # únicamente al abrir un levantamiento especializado.
    background_label = tk.Label(sidebar, text="", bd=0, highlightthickness=0, bg=PRIMARY_DARK)
    sidebar._axia_background_label = background_label
    sidebar._axia_background_image = None
    sidebar._axia_sidebar_tipo = None

    def _on_sidebar_configure(_event=None):
        # Redibujo diferido para no recalcular la imagen en cada pixel del resize.
        after_id = getattr(sidebar, "_axia_bg_after", None)
        if after_id:
            try:
                sidebar.after_cancel(after_id)
            except Exception:
                pass
        sidebar._axia_bg_after = sidebar.after(120, lambda: _redibujar_fondo_sidebar(sidebar))

    sidebar.bind("<Configure>", _on_sidebar_configure, add="+")

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
    label_logo.pack(pady=(9, 9))
    # Referencia estable para sustituir únicamente la cabecera visual cuando
    # se abra uno de los nueve levantamientos temáticos.
    sidebar._axia_header_label = label_logo
    sidebar._axia_header_image = logo_axia

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
    puede_inicio = puede_entrar_inicio_aco(usuario_activo)
    puede_consulta = puede_consultar_procesos(usuario_activo)

    # Orden visual homologado al flujo operativo vigente:
    # LEVANTAMIENTO -> ACO -> ORDEN DE TRABAJO -> BITÁCORA -> ORDEN DE SERVICIO.
    if puede_generar_levantamiento(usuario_activo):
        crear_boton_sidebar(
            sidebar,
            "📋 Levantamientos",
            callbacks["admin_levantamientos"] if puede_consulta else callbacks["levantamiento"]
        )

    # Etapa comercial: después de la preautorización del levantamiento y antes de ACO.
    if puede_cotizar_levantamientos(usuario_activo):
        crear_boton_sidebar(
            sidebar,
            "💲 Cotizaciones",
            callbacks["cotizaciones"]
        )

    if puede_ver_compras(usuario_activo):
        crear_boton_sidebar(
            sidebar,
            "🛒 Compras",
            callbacks["compras"]
        )

    if puede_inicio:
        crear_boton_sidebar(
            sidebar,
            "🏠 ACO",
            callbacks["inicio_aco"]
        )

    if puede_consulta:
        crear_boton_sidebar(
            sidebar,
            "🛠️ Órdenes de trabajo",
            callbacks["admin_ordenes_trabajo"]
        )

    # Las Bitácoras Operativas forman parte del trabajo del Operador (usu_tipo=4).
    # Para ese rol el menú abre directamente el FORMULARIO OPERATIVO de captura;
    # los perfiles con permiso de consulta administrativa conservan la vista de
    # búsqueda/edición de bitácoras registradas.
    if puede_ver_bitacoras_operativas(usuario_activo):
        tipo_usuario = obtener_tipo_usuario(usuario_activo)
        callback_bitacoras = (
            callbacks["bitacora_avance"]
            if tipo_usuario == OPERADOR
            else callbacks["admin_bitacoras"]
        )
        crear_boton_sidebar(
            sidebar,
            "📊 Bitácoras operativas",
            callback_bitacoras
        )

    # La captura operativa de Orden de Servicio también está disponible para
    # Operador (usu_tipo=4). Los roles de gestión conservan la vista administrativa.
    if puede_generar_orden_servicio(usuario_activo):
        tipo_usuario = obtener_tipo_usuario(usuario_activo)
        callback_os = (
            callbacks["orden_servicio"]
            if tipo_usuario == OPERADOR
            else callbacks["admin_ordenes_servicio"]
            if puede_consulta
            else callbacks["orden_servicio"]
        )
        crear_boton_sidebar(
            sidebar,
            "🧾 Órdenes de servicio",
            callback_os
        )

    if puede_ver_reportes(usuario_activo):
        crear_boton_sidebar(
            sidebar,
            "📈 Reportes",
            callbacks["reportes"]
        )

    if puede_ver_auditoria(usuario_activo):
        crear_boton_sidebar(
            sidebar,
            "🛡️ Auditoría",
            callbacks["auditoria"]
        )

    if puede_administrar_usuarios(usuario_activo):
        crear_boton_sidebar(
            sidebar,
            "👥 Usuarios",
            callbacks["usuarios"]
        )

    if puede_administrar_clientes(usuario_activo):
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
        pady=(2, 12),
        padx=10,
        fill="x"
    )
    acciones_sesion.grid_columnconfigure(0, weight=1)
    acciones_sesion.grid_columnconfigure(1, weight=1)

    ctk.CTkButton(
        acciones_sesion,
        text="⏻ Cerrar AXIA",
        width=98,
        height=38,
        corner_radius=10,
        fg_color="#64748B",
        hover_color="#475569",
        text_color=WHITE,
        font=BUTTON_FONT,
        command=on_exit
    ).grid(
        row=0,
        column=0,
        sticky="ew",
        padx=(0, 2)
    )

    ctk.CTkButton(
        acciones_sesion,
        text="🔒 Salir",
        width=98,
        height=38,
        corner_radius=10,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        text_color=WHITE,
        font=BUTTON_FONT,
        command=on_logout or on_exit
    ).grid(
        row=0,
        column=1,
        sticky="ew",
        padx=(2, 0)
    )

    # Garantiza una jerarquía estable al terminar de construir el sidebar:
    # fondo temático > fondo sólido interno de CTkFrame, y controles > fondo.
    # La primera activación temática redimensionará la imagen al tamaño real.
    try:
        sidebar.after_idle(lambda: _redibujar_fondo_sidebar(sidebar))
    except Exception:
        pass

    return sidebar
