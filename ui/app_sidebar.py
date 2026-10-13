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
from PIL import Image, ImageEnhance, ImageOps, ImageTk, ImageDraw

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

def _imagen_fondo_sidebar(tipo, size=(230, 900)):
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
    return base


def _crear_fondo_sidebar(tipo, size=(230, 900)):
    fondo = _imagen_fondo_sidebar(tipo, size)
    return ImageTk.PhotoImage(fondo) if fondo is not None else None


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
        # El menú usa la misma imagen; actualizarlo al cambiar especialidad.
        refrescar_menu = getattr(sidebar, "_axia_menu_redibujar", None)
        if callable(refrescar_menu):
            refrescar_menu()
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
    """Acordeón sobre lienzo ilustrado.

    Tk/CustomTkinter no ofrece transparencia alfa real en CTkScrollableFrame:
    "transparent" puede heredar un blanco del contenedor superior. Este menú
    dibuja el wallpaper directamente sobre un Canvas y superpone pastillas RGBA,
    sin crear frames opacos entre el usuario y la imagen corporativa.
    """
    secciones = (
        ("operaciones", "", "Operaciones"),
        ("administracion", "", "Administración"),
        ("sistema", "", "Sistema y Control"),
    )
    blanco = "#F3FAFF"
    secundario = "#C9E1F0"
    acento = "#70D7FB"
    estado = {"seccion": None, "opcion": None}
    cache_pastillas = {}
    referencias_imagen = []
    canvas = menu_host

    def _pastilla(ancho, alto, estilo):
        clave = (ancho, alto, estilo)
        if clave not in cache_pastillas:
            colores = {
                "cabecera": (23, 56, 77, 220),
                "cabecera_abierta": (31, 78, 103, 224),
                "cabecera_hover": (38, 96, 125, 238),
                "opcion": (13, 39, 59, 125),
                "opcion_hover": (33, 76, 99, 208),
                "opcion_activa": (24, 85, 115, 235),
            }
            img = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle(
                (0, 0, ancho - 1, alto - 1), radius=9 if estilo.startswith("cabecera") else 7,
                fill=colores[estilo],
            )
            cache_pastillas[clave] = ImageTk.PhotoImage(img, master=canvas)
        return cache_pastillas[clave]

    def _fondo_menu(ancho, alto):
        # Mostrar la misma imagen del sidebar, alineada a su posición vertical.
        try:
            lateral_ancho = max(220, sidebar.winfo_width())
            lateral_alto = max(600, sidebar.winfo_height())
            fondo = _imagen_fondo_sidebar(
                getattr(sidebar, "_axia_sidebar_tipo", None),
                (lateral_ancho, lateral_alto),
            )
            if fondo is None:
                raise ValueError("Wallpaper no disponible")
            origen_x = max(0, canvas.winfo_rootx() - sidebar.winfo_rootx())
            origen_y = max(0, canvas.winfo_rooty() - sidebar.winfo_rooty())
            lienzo = Image.new("RGB", (ancho, alto), "#0E2539")
            # Repetir la imagen si el contenido supera la altura del sidebar.
            y = 0
            while y < alto:
                inicio = (origen_y + y) % lateral_alto
                tramo = min(alto - y, lateral_alto - inicio)
                recorte = fondo.crop((origen_x, inicio, origen_x + ancho, inicio + tramo))
                lienzo.paste(recorte.convert("RGB"), (0, y))
                y += tramo
            # Sombra tenue, sin un panel sólido que tape la ilustración.
            velo = Image.new("RGBA", (ancho, alto), (5, 18, 32, 35))
            lienzo = Image.alpha_composite(lienzo.convert("RGBA"), velo)
            return ImageTk.PhotoImage(lienzo, master=canvas)
        except Exception:
            logger.debug("Fondo del menú no disponible.", exc_info=True)
            return None

    def _navegar(seccion, opcion, callback):
        estado["seccion"] = seccion
        estado["opcion"] = opcion
        _redibujar()
        callback()  # Callback original, sin modificar firma ni permisos.

    def _abrir_seccion(clave):
        estado["seccion"] = None if estado["seccion"] == clave else clave
        _redibujar()

    def _redibujar():
        if not canvas.winfo_exists():
            return
        fraccion = canvas.yview()[0] if canvas.find_all() else 0.0
        canvas.delete("all")
        referencias_imagen.clear()
        ancho = max(185, canvas.winfo_width())
        margen = 6
        fila_ancho = ancho - 2 * margen - 3
        y = 7
        filas = []
        for clave, simbolo, titulo in secciones:
            items = opciones[clave]
            if not items:
                continue
            abierta = estado["seccion"] == clave
            filas.append(("cabecera", clave, simbolo, titulo, None, margen, y, fila_ancho, 44,
                          "cabecera_abierta" if abierta else "cabecera"))
            y += 51
            if abierta:
                for identificador, icono, nombre, callback in items:
                    seleccionada = estado["opcion"] == identificador
                    filas.append(("opcion", identificador, icono, nombre,
                                  (clave, identificador, callback), margen + 12, y, fila_ancho - 12, 36,
                                  "opcion_activa" if seleccionada else "opcion"))
                    y += 40
                y += 7
            else:
                y += 2
        if direccion is not None:
            identificador, icono, nombre, callback = direccion
            y += 11
            filas.append(("separador", None, None, None, None, margen + 8, y, fila_ancho - 16, 1, None))
            y += 15
            seleccionada = estado["opcion"] == identificador
            filas.append(("opcion", identificador, icono, nombre,
                          (None, identificador, callback), margen, y, fila_ancho, 44,
                          "opcion_activa" if seleccionada else "cabecera"))
            y += 54
        alto = max(y + 12, canvas.winfo_height())
        imagen_fondo = _fondo_menu(ancho, alto)
        if imagen_fondo is not None:
            referencias_imagen.append(imagen_fondo)
            canvas.create_image(0, 0, image=imagen_fondo, anchor="nw")
        else:
            canvas.create_rectangle(0, 0, ancho, alto, fill="#0E2539", outline="")
        for indice, (tipo, ident, simbolo, titulo, accion, x, top, w, h, estilo) in enumerate(filas):
            if tipo == "separador":
                canvas.create_line(x, top, x + w, top, fill="#375A70", width=1)
                continue
            etiqueta = f"accion_{indice}"
            fondo_normal = _pastilla(w, h, estilo)
            sprite = canvas.create_image(x, top, image=fondo_normal, anchor="nw", tags=(etiqueta,))
            canvas.create_text(x + 17, top + h // 2, text=simbolo,
                               fill=blanco if tipo == "cabecera" else secundario,
                               font=("Segoe UI Symbol", 15), anchor="w", tags=(etiqueta,))
            activo = estado["opcion"] == ident and tipo == "opcion"
            canvas.create_text(x + 47, top + h // 2, text=titulo, anchor="w",
                               font=("Segoe UI", 11, "bold" if tipo == "cabecera" or activo else "normal"),
                               fill=blanco if tipo == "cabecera" or activo else secundario,
                               tags=(etiqueta,))
            if tipo == "cabecera":
                canvas.create_text(x + w - 17, top + h // 2,
                                   text="▾" if estado["seccion"] == ident else "▸",
                                   font=("Segoe UI", 13), fill=secundario,
                                   anchor="center", tags=(etiqueta,))
            if activo:
                canvas.create_rectangle(x + 3, top + 7, x + 6, top + h - 7,
                                        fill=acento, outline="", tags=(etiqueta,))
            if tipo == "cabecera":
                funcion = lambda _event, k=ident: _abrir_seccion(k)
            else:
                seccion, opcion, callback = accion
                funcion = lambda _event, k=seccion, o=opcion, fn=callback: _navegar(k, o, fn)
            canvas.tag_bind(etiqueta, "<Button-1>", funcion)
            canvas.tag_bind(etiqueta, "<Enter>", lambda _event, item=sprite, ww=w, hh=h, t=tipo, sel=activo:
                            (canvas.itemconfigure(item, image=_pastilla(ww, hh,
                                "cabecera_hover" if t == "cabecera" else
                                "opcion_activa" if sel else "opcion_hover")),
                             canvas.configure(cursor="hand2")))
            canvas.tag_bind(etiqueta, "<Leave>", lambda _event, item=sprite, normal=fondo_normal:
                            (canvas.itemconfigure(item, image=normal), canvas.configure(cursor="")))
        canvas.configure(scrollregion=(0, 0, ancho, alto))
        canvas.yview_moveto(fraccion)

    def _wheel(event):
        paso = int(-event.delta / 120) if event.delta else 0
        if paso:
            canvas.yview_scroll(paso, "units")
        return "break"

    canvas.bind("<MouseWheel>", _wheel, add="+")
    canvas.bind("<Button-4>", lambda _e: (canvas.yview_scroll(-1, "units"), "break")[-1], add="+")
    canvas.bind("<Button-5>", lambda _e: (canvas.yview_scroll(1, "units"), "break")[-1], add="+")
    canvas.bind("<Configure>", lambda _event: _redibujar(), add="+")
    estado["seccion"] = next((k for k, _, _ in secciones if opciones[k]), None)
    sidebar._axia_menu_activar = _navegar
    sidebar._axia_menu_estado = estado
    sidebar._axia_menu_redibujar = _redibujar
    _redibujar()


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
    # Canvas con imagen de fondo + scrollbar: evita que CTkScrollableFrame
    # herede el color claro del panel, lo que ocurría en la V3.
    menu_marco = ctk.CTkFrame(sidebar, fg_color="#10283D", corner_radius=0, border_width=0)
    menu_marco.pack(side="top", fill="both", expand=True, padx=(5, 3), pady=(2, 4))
    menu_scroll = tk.Canvas(
        menu_marco, background="#0E2539", borderwidth=0,
        highlightthickness=0, relief="flat", takefocus=True,
    )
    barra_scroll = ctk.CTkScrollbar(
        menu_marco, orientation="vertical", width=9,
        command=menu_scroll.yview,
        fg_color="#10283D", button_color="#36556C",
        button_hover_color="#70D7FB",
    )
    menu_scroll.configure(yscrollcommand=barra_scroll.set)
    barra_scroll.pack(side="right", fill="y", padx=(1, 0))
    menu_scroll.pack(side="left", fill="both", expand=True)
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
