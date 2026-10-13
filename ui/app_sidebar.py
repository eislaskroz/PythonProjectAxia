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
    puede_ver_almacen,
    puede_generar_orden_servicio,
    puede_ver_auditoria,
    puede_ver_reportes,
    puede_ver_direccion_general,
    puede_ver_bitacoras_operativas,
)


# =====================================================
# FONDO TEMÁTICO DE LEVANTAMIENTOS
# =====================================================
_FONDO_SIDEBAR_GENERAL = "fondo_general.png"

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
    "Obra Civil": "fondo_obra_civil.png",
}

def _ruta_recurso_sidebar(nombre):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets" / nombre

def _crear_fondo_sidebar(tipo, size=(230, 900)):
    """Crea un wallpaper que cubre TODO el sidebar sin deformar la imagen.

    Se usa recorte tipo cover y un velo azul oscuro para que textos/botones
    mantengan contraste. La imagen no se limita al área del logotipo.
    """
    # El sidebar siempre tiene fondo. Cuando no hay un levantamiento activo
    # (o el tipo no tiene imagen específica), se usa la imagen GENERAL.
    # Al abrir una especialidad, esa imagen sustituye temporalmente al fondo
    # general; Obra Civil ya cuenta también con su wallpaper dedicado.
    nombre = _FONDOS_SIDEBAR.get(str(tipo or "").strip(), _FONDO_SIDEBAR_GENERAL)
    ruta = _ruta_recurso_sidebar(nombre)
    if not ruta.exists():
        logger.warning("No se encontró fondo de sidebar para %s: %s", tipo, ruta)
        return None
    ancho=max(220, int(size[0] or 260))
    alto=max(600, int(size[1] or 900))
    with Image.open(ruta) as src:
        base = ImageOps.fit(src.convert("RGB"), (ancho, alto), method=Image.Resampling.LANCZOS)
    base = ImageEnhance.Brightness(base).enhance(0.28).convert("RGBA")
    # Velo corporativo para conservar contraste de menú y botones.
    velo = Image.new("RGBA", (ancho, alto), (15, 35, 55, 105))
    base = Image.alpha_composite(base, velo)
    return ImageTk.PhotoImage(base)

def _redibujar_fondo_sidebar(sidebar):
    tipo = getattr(sidebar, "_axia_sidebar_tipo", None)
    label = getattr(sidebar, "_axia_background_label", None)
    if sidebar is None or label is None:
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
    """Muestra el wallpaper de especialidad o restaura el fondo GENERAL."""
    if sidebar is None:
        return
    sidebar._axia_sidebar_tipo = str(tipo_levantamiento or "").strip() or None
    # El logo corporativo permanece como capa superior; el wallpaper cubre
    # desde el borde superior hasta las acciones de sesión. Si tipo es None,
    # se mantiene el fondo GENERAL en lugar de ocultar la imagen.
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
    color_normal = "#183247" if habilitado else "#1e293b"

    fila = ctk.CTkFrame(
        parent,
        width=214,
        height=40,
        corner_radius=10,
        fg_color=color_normal,
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
        font=BUTTON_FONT,
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
            fila.configure(fg_color=color_normal)

        for widget in (fila, lbl_icono, lbl_texto):
            widget.bind("<Button-1>", ejecutar)
            widget.bind("<Enter>", hover)
            widget.bind("<Leave>", leave)
            try:
                widget.configure(cursor="hand2")
            except Exception:
                logger.debug("Excepción recuperable controlada.", exc_info=True)




# =====================================================
# ORGANIZACIÓN VISUAL DEL MENÚ (SIN MODIFICAR PERMISOS)
# =====================================================
def _opciones_menu_por_rol(usuario_activo, callbacks):
    """Agrupa las mismas opciones, permisos y callbacks del menú original.

    La agrupación es solo presentación. El controlador de navegación continúa
    validando los permisos cuando se abre cada módulo.
    """
    puede_consulta = puede_consultar_procesos(usuario_activo)
    tipo_usuario = obtener_tipo_usuario(usuario_activo)
    opciones = {
        "operaciones": [],
        "administracion": [],
        "sistema": [],
    }

    if puede_generar_levantamiento(usuario_activo):
        opciones["operaciones"].append((
            "levantamientos", "📋", "Levantamientos",
            callbacks["admin_levantamientos"] if puede_consulta else callbacks["levantamiento"],
        ))
    if puede_entrar_inicio_aco(usuario_activo):
        opciones["operaciones"].append((
            "aco", "🏠", "ACO", callbacks["inicio_aco"],
        ))
    if puede_consulta:
        opciones["operaciones"].append((
            "ordenes_trabajo", "🛠️", "Órdenes de trabajo",
            callbacks["admin_ordenes_trabajo"],
        ))
    if puede_ver_bitacoras_operativas(usuario_activo):
        callback_bitacoras = (
            callbacks["bitacora_avance"] if tipo_usuario == OPERADOR
            else callbacks["admin_bitacoras"]
        )
        opciones["operaciones"].append((
            "bitacoras", "📊", "Bitácoras operativas", callback_bitacoras,
        ))
    if puede_generar_orden_servicio(usuario_activo):
        callback_os = (
            callbacks["orden_servicio"] if tipo_usuario == OPERADOR
            else callbacks["admin_ordenes_servicio"] if puede_consulta
            else callbacks["orden_servicio"]
        )
        opciones["operaciones"].append((
            "ordenes_servicio", "🧾", "Órdenes de servicio", callback_os,
        ))

    if puede_cotizar_levantamientos(usuario_activo):
        opciones["administracion"].append((
            "cotizaciones", "💲", "Cotizaciones", callbacks["cotizaciones"],
        ))
    if puede_ver_compras(usuario_activo):
        opciones["administracion"].append((
            "compras", "🛒", "Compras", callbacks["compras"],
        ))
    if puede_ver_almacen(usuario_activo):
        opciones["administracion"].append((
            "almacen", "📦", "Almacén", callbacks["almacen"],
        ))

    if puede_ver_reportes(usuario_activo):
        opciones["sistema"].append((
            "reportes", "📈", "Reportes", callbacks["reportes"],
        ))
    if puede_ver_auditoria(usuario_activo):
        opciones["sistema"].append((
            "auditoria", "🛡️", "Auditoría", callbacks["auditoria"],
        ))
    if puede_administrar_usuarios(usuario_activo):
        opciones["sistema"].append((
            "usuarios", "👥", "Usuarios", callbacks["usuarios"],
        ))
    if puede_administrar_clientes(usuario_activo):
        opciones["sistema"].append((
            "clientes", "🏢", "Clientes", callbacks["clientes"],
        ))

    direccion = (
        ("direccion_general", "📊", "Dirección General", callbacks["direccion_general"])
        if puede_ver_direccion_general(usuario_activo) else None
    )
    return opciones, direccion


def _crear_menu_acordeon(sidebar, menu_host, opciones, direccion):
    """Dibuja un acordeón navegable, resaltando el módulo seleccionado."""
    secciones = (
        ("operaciones", "⚒", "Operaciones"),
        ("administracion", "▣", "Administración"),
        ("sistema", "⚙", "Sistema y Control"),
    )
    color_cabecera = "#183247"
    color_cabecera_abierta = "#20506D"
    color_hover = "#286184"
    color_item = "#10293F"
    color_item_hover = "#20506D"
    color_seleccion = "#135C85"
    acento = "#70D7FB"
    paneles = {}
    botones = {}
    estado = {"seccion": None, "opcion": None}

    def _refrescar():
        """Actualiza contraste y visibilidad sin reconstruir los botones."""
        for key, (cabecera, contenido, flecha) in paneles.items():
            abierto = estado["seccion"] == key
            cabecera.configure(fg_color=color_cabecera_abierta if abierto else color_cabecera)
            flecha.configure(text="▾" if abierto else "▸")
            if abierto:
                if not contenido.winfo_manager():
                    contenido.pack(fill="x", padx=0, pady=(1, 3))
            else:
                contenido.pack_forget()
        for key, (fila, icono, etiqueta, marca) in botones.items():
            marcado = estado["opcion"] == key
            fila.configure(fg_color=color_seleccion if marcado else color_item)
            icono.configure(text_color=WHITE if marcado else "#CFECFB")
            etiqueta.configure(text_color=WHITE if marcado else "#DCEAF4")
            marca.configure(fg_color=acento if marcado else "transparent")

    def _abrir_seccion(key):
        estado["seccion"] = None if estado["seccion"] == key else key
        _refrescar()

    def _navegar(seccion, opcion, callback):
        estado["seccion"] = seccion
        estado["opcion"] = opcion
        _refrescar()
        callback()  # Se llama exactamente al callback original (sin parámetros nuevos).

    def _vincular_fila(widgets, click, fondo, hover):
        """Las tres zonas de cada fila responden al clic y al hover."""
        def _hover(_event=None):
            fondo.configure(fg_color=hover)

        def _salir(_event=None):
            _refrescar()

        for widget in widgets:
            widget.bind("<Button-1>", lambda _event, fn=click: fn())
            widget.bind("<Enter>", _hover)
            widget.bind("<Leave>", _salir)
            widget.bind("<Return>", lambda _event, fn=click: fn())
            widget.bind("<space>", lambda _event, fn=click: fn())
            try:
                widget.configure(cursor="hand2")
            except (tk.TclError, ValueError):
                pass

    for clave, simbolo, titulo in secciones:
        items = opciones[clave]
        if not items:
            continue  # No se muestran encabezados vacíos a roles sin permiso.

        bloque = ctk.CTkFrame(menu_host, fg_color="transparent", corner_radius=0)
        bloque.pack(fill="x", padx=(3, 3), pady=(3, 3))
        encabezado = ctk.CTkFrame(
            bloque, height=43, fg_color=color_cabecera, corner_radius=10,
        )
        encabezado.pack(fill="x")
        encabezado.pack_propagate(False)
        encabezado.grid_propagate(False)
        encabezado.grid_columnconfigure(1, weight=1)
        cab_icono = ctk.CTkLabel(
            encabezado, text=simbolo, width=31, font=("Segoe UI Symbol", 17),
            text_color=acento,
        )
        cab_icono.grid(row=0, column=0, padx=(5, 1), sticky="nsew")
        cab_texto = ctk.CTkLabel(
            encabezado, text=titulo, font=BUTTON_FONT,
            text_color=WHITE, anchor="w",
        )
        cab_texto.grid(row=0, column=1, sticky="nsew")
        cab_flecha = ctk.CTkLabel(
            encabezado, text="▸", width=22, font=("Segoe UI Symbol", 17),
            text_color="#D7E8F3",
        )
        cab_flecha.grid(row=0, column=2, padx=(0, 4), sticky="nsew")

        contenedor = ctk.CTkFrame(bloque, fg_color="transparent", corner_radius=0)
        paneles[clave] = (encabezado, contenedor, cab_flecha)
        _vincular_fila(
            (encabezado, cab_icono, cab_texto, cab_flecha),
            lambda k=clave: _abrir_seccion(k), encabezado, color_hover,
        )

        for ident, icono, nombre, callback in items:
            fila = ctk.CTkFrame(
                contenedor, height=37, fg_color=color_item, corner_radius=8,
            )
            fila.pack(fill="x", padx=(15, 1), pady=(2, 1))
            fila.pack_propagate(False)
            fila.grid_propagate(False)
            fila.grid_columnconfigure(2, weight=1)
            marca = ctk.CTkFrame(fila, width=3, height=24, fg_color="transparent", corner_radius=2)
            marca.grid(row=0, column=0, sticky="ns", padx=(0, 4), pady=6)
            boton_icono = ctk.CTkLabel(
                fila, text=icono, width=26, font=("Segoe UI Emoji", 15),
                text_color="#CFECFB",
            )
            boton_icono.grid(row=0, column=1, sticky="nsew")
            boton_texto = ctk.CTkLabel(
                fila, text=nombre, font=("Segoe UI", 12),
                text_color="#DCEAF4", anchor="w",
            )
            boton_texto.grid(row=0, column=2, padx=(3, 2), sticky="nsew")
            botones[ident] = (fila, boton_icono, boton_texto, marca)
            _vincular_fila(
                (fila, boton_icono, boton_texto, marca),
                lambda k=clave, o=ident, fn=callback: _navegar(k, o, fn),
                fila, color_item_hover,
            )

    if direccion is not None:
        ident, icono, nombre, callback = direccion
        separador = ctk.CTkFrame(menu_host, height=1, fg_color="#466177")
        separador.pack(fill="x", padx=11, pady=(9, 6))
        fila = ctk.CTkFrame(menu_host, height=43, fg_color=color_cabecera, corner_radius=10)
        fila.pack(fill="x", padx=3, pady=(0, 4))
        fila.pack_propagate(False)
        fila.grid_propagate(False)
        fila.grid_columnconfigure(2, weight=1)
        marca = ctk.CTkFrame(fila, width=3, height=24, fg_color="transparent", corner_radius=2)
        marca.grid(row=0, column=0, sticky="ns", padx=(1, 4), pady=7)
        boton_icono = ctk.CTkLabel(fila, text=icono, width=31, font=("Segoe UI Emoji", 16), text_color=acento)
        boton_icono.grid(row=0, column=1, sticky="nsew")
        boton_texto = ctk.CTkLabel(fila, text=nombre, font=BUTTON_FONT, text_color=WHITE, anchor="w")
        boton_texto.grid(row=0, column=2, sticky="nsew")
        botones[ident] = (fila, boton_icono, boton_texto, marca)
        _vincular_fila(
            (fila, boton_icono, boton_texto, marca),
            lambda o=ident, fn=callback: _navegar(None, o, fn),
            fila, color_hover,
        )

    # Para el rol Administrador se abre Operaciones; otros roles ven primero
    # la primera sección permitida (Compras, Almacén, etc.).
    estado["seccion"] = next(iter(paneles), None)
    _refrescar()
    sidebar._axia_menu_activar = _navegar
    sidebar._axia_menu_estado = estado


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
        width=230,
        fg_color=PRIMARY_DARK,
        corner_radius=0
    )
    sidebar.grid(
        row=0,
        column=0,
        sticky="ns"
    )
    sidebar.pack_propagate(False)

    # Wallpaper del sidebar: el fondo GENERAL permanece siempre visible y
    # se sustituye temporalmente por el de la especialidad activa.
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
    # NAVEGACIÓN EN SECCIONES DESPLEGABLES
    # =================================================
    usuario_es_admin = es_admin(usuario_activo)
    opciones, direccion = _opciones_menu_por_rol(usuario_activo, callbacks)

    # El menú es desplazable; el logo y los controles de sesión permanecen
    # siempre a la vista aunque la ventana se utilice en tamaño reducido.
    menu_scroll = ctk.CTkScrollableFrame(
        sidebar,
        width=215,
        fg_color="transparent",
        corner_radius=0,
        scrollbar_button_color="#4A6880",
        scrollbar_button_hover_color="#70D7FB",
    )
    menu_scroll.pack(side="top", fill="both", expand=True, padx=(5, 3), pady=(2, 4))
    _crear_menu_acordeon(sidebar, menu_scroll, opciones, direccion)

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
