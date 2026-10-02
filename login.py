import customtkinter as ctk
from tkinter import messagebox

from ui.theme import aplicar_estilo_ventana
from ui.assets import cargar_logo_axia, configurar_icono_app
from app_context import establecer_usuario_actual
from core.background_tasks import run_async
from utils import centrar_ventana
from ui.colors import (
    PRIMARY,
    PRIMARY_50,
    PRIMARY_100,
    PRIMARY_500,
    PRIMARY_600,
    PRIMARY_700,
    SECONDARY,
    WHITE,
    CONTENT_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    BUTTON_HOVER,
    SURFACE,
    DIVIDER,
    RING,
    CARD_BORDER,
)
from ui.fonts import (
    TITLE_XL,
    TITLE_LG,
    TITLE_MD,
    TITLE_SM,
    SECTION_FONT,
    LABEL_BOLD,
    TEXT_MD,
    TEXT_SM,
    TEXT_XS,
    BUTTON_FONT,
    CAPTION,
)
from core.version import APP_VERSION



# Servicios de autenticación cargados bajo demanda. Esto permite mostrar el
# Login antes de inicializar Supabase, Pydantic y el cliente HTTP.
_AUTH_SERVICES = None

def _cargar_servicios_auth():
    global _AUTH_SERVICES
    if _AUTH_SERVICES is None:
        from services.auth_service import (
            obtener_contexto_login,
            validar_login,
            registrar_bitacora_login,
        )
        from services.movimientos_service import registrar_movimiento
        _AUTH_SERVICES = {
            "obtener_contexto_login": obtener_contexto_login,
            "validar_login": validar_login,
            "registrar_bitacora_login": registrar_bitacora_login,
            "registrar_movimiento": registrar_movimiento,
        }
    return _AUTH_SERVICES

LOGIN_WIDTH = 520
LOGIN_HEIGHT = 600
CARD_WIDTH = 440


def _crear_logo(parent, size=(110, 110), pady=(10, 4)):
    """Crea el logotipo corporativo y conserva su referencia visual."""
    logo = cargar_logo_axia(size=size)
    label = ctk.CTkLabel(parent, image=logo, text="")
    label.pack(pady=pady)
    label.logo_axia = logo
    return label


def abrir_login():
    """Abre una pantalla de acceso compacta y consistente con el tema AXIA."""
    app = ctk.CTk()
    aplicar_estilo_ventana(app)
    configurar_icono_app(app)
    app.title("Login - Sistema AXIA")
    centrar_ventana(app, LOGIN_WIDTH, LOGIN_HEIGHT)
    app.resizable(False, False)

    login_resultado = {"autenticado": False}

    def cerrar_login_sin_acceso():
        login_resultado["autenticado"] = False
        try:
            app.destroy()
        except Exception:
            app.quit()

    app.protocol("WM_DELETE_WINDOW", cerrar_login_sin_acceso)

    # Precalienta dependencias de red después de mostrar la ventana.
    # Si el usuario empieza a escribir, la carga ocurre en paralelo y el clic
    # de INGRESAR no paga todo el costo de importación.
    app.after(250, lambda: run_async(root=app, task=_cargar_servicios_auth))

    # Fondo principal: gradiente simulado con frame base + acentos
    root = ctk.CTkFrame(app, fg_color=WHITE, corner_radius=0)
    root.pack(fill="both", expand=True)

    # =================================================
    # CONTENEDOR PRINCIPAL DEL LOGIN
    # =================================================
    # Sin tarjeta exterior, sin franja azul/lila y sin
    # borde alrededor de todo el formulario.

    outer_card = ctk.CTkFrame(
        root,
        fg_color="transparent",
        corner_radius=0,
        border_width=0,
    )
    outer_card.pack(
        expand=True,
        padx=0,
        pady=0,
        fill="both"
    )

    card = ctk.CTkFrame(
        outer_card,
        fg_color=WHITE,
        corner_radius=0,
        border_width=0,
    )
    card.pack(
        expand=True,
        padx=0,
        pady=0,
        fill="both"
    )

    # =================================================
    # FRanja decorativa superior (acento azul)
    # =================================================
    accent_bar = ctk.CTkFrame(
        card,
        height=5,
        corner_radius=4,
        fg_color=PRIMARY,
        border_width=0,
    )
    accent_bar.pack(fill="x", padx=28, pady=(16, 0))

    # Punto brillante decorativo en el centro
    accent_dot = ctk.CTkFrame(
        accent_bar,
        width=5,
        height=5,
        corner_radius=100,
        fg_color=WHITE,
        border_width=0,
    )
    accent_dot.place(relx=0.5, rely=0.5, anchor="center")

    _crear_logo(card, size=(115, 115), pady=(6, 0))

    # Título SIN pack_propagate(False) SIN tamaño fijo → no aparecerá cuadro.
    ctk.CTkLabel(
        card,
        text="Inicio de sesión",
        font=TITLE_LG,
        text_color=TEXT_PRIMARY,
    ).pack(pady=(6, 2))

    # Barra inferior decorativa debajo del título
    deco_line = ctk.CTkFrame(
        card,
        width=68,
        height=4,
        corner_radius=100,
        fg_color=PRIMARY,
        border_width=0,
    )
    deco_line.pack(pady=(0, 6))

    ctk.CTkLabel(
        card,
        text="Ingresa tus credenciales de acceso",
        font=TEXT_SM,
        text_color=TEXT_MUTED,
    ).pack(pady=(0, 14))

    # Iconos tipográficos: evita depender de archivos gráficos externos.
    icono_usuario = None
    icono_cerrar = None
    icono_ver = None

    # =================================================
    # CAMPO USUARIO (con label + icono y focus ring)
    # SIN pack_propagate(False) para tamaño dinámico
    # =================================================
    usuario_wrap = ctk.CTkFrame(card, fg_color="transparent")
    usuario_wrap.pack(padx=42, pady=(2, 6), fill="x")

    ctk.CTkLabel(
        usuario_wrap,
        text="Usuario",
        font=LABEL_BOLD,
        text_color=TEXT_PRIMARY,
        anchor="w",
    ).pack(fill="x", pady=(0, 5))

    usuario_row = ctk.CTkFrame(
        usuario_wrap,
        height=50,
        corner_radius=12,
        fg_color=SURFACE,
        border_width=0,
    )
    usuario_row.pack(fill="x")

    user_icon = ctk.CTkLabel(
        usuario_row,
        text="👤",
        image=icono_usuario,
        width=42,
        anchor="center",
    )
    user_icon.pack(side="left", fill="y")

    entry_usuario = ctk.CTkEntry(
        usuario_row,
        placeholder_text="Ingresa tu nombre de usuario",
        height=46,
        corner_radius=0,
        border_width=0,
        fg_color="transparent",
        placeholder_text_color=TEXT_MUTED,
        font=TEXT_MD,
    )
    entry_usuario.pack(side="left", fill="both", expand=True, padx=(0, 10))
    entry_usuario.focus()

    # Focus ring visual para entry_usuario
    def _usuario_focus_in(_e=None):
        usuario_row.configure(
            fg_color=PRIMARY_50
        )

    def _usuario_focus_out(_e=None):
        usuario_row.configure(
            fg_color=SURFACE
        )
    entry_usuario.bind("<FocusIn>", _usuario_focus_in, add="+")
    entry_usuario.bind("<FocusOut>", _usuario_focus_out, add="+")

    # =================================================
    # CAMPO CONTRASEÑA (con label + icono y focus ring)
    # =================================================
    password_wrap = ctk.CTkFrame(card, fg_color="transparent")
    password_wrap.pack(padx=42, pady=(2, 4), fill="x")

    ctk.CTkLabel(
        password_wrap,
        text="Contraseña",
        font=LABEL_BOLD,
        text_color=TEXT_PRIMARY,
        anchor="w",
    ).pack(fill="x", pady=(0, 5))

    password_row = ctk.CTkFrame(
        password_wrap,
        height=50,
        corner_radius=12,
        fg_color=SURFACE,
        border_width=0,
    )
    password_row.pack(fill="x")

    pass_icon = ctk.CTkLabel(
        password_row,
        text="🔒",
        image=icono_cerrar,
        width=42,
        anchor="center",
    )
    pass_icon.pack(side="left", fill="y")

    password_visible = {"valor": False}

    def alternar_password():
        password_visible["valor"] = not password_visible["valor"]
        entry_password.configure(show="" if password_visible["valor"] else "*")

    btn_ver_password = ctk.CTkButton(
        password_row,
        text="👁",
        image=icono_ver,
        compound="center",
        width=44,
        height=40,
        corner_radius=10,
        fg_color=PRIMARY_50,
        hover_color=PRIMARY_100,
        text_color=PRIMARY,
        border_width=0,
        command=alternar_password,
    )
    btn_ver_password.pack(side="right", padx=(0, 5))

    entry_password = ctk.CTkEntry(
        password_row,
        placeholder_text="Ingresa tu contraseña",
        show="*",
        height=46,
        corner_radius=0,
        border_width=0,
        fg_color="transparent",
        placeholder_text_color=TEXT_MUTED,
        font=TEXT_MD,
    )
    entry_password.pack(side="left", fill="both", expand=True, padx=(0, 6))

    # Focus ring visual para entry_password
    def _pass_focus_in(_e=None):
        password_row.configure(
            fg_color=PRIMARY_50
        )

    def _pass_focus_out(_e=None):
        password_row.configure(
            fg_color=SURFACE
        )
    entry_password.bind("<FocusIn>", _pass_focus_in, add="+")
    entry_password.bind("<FocusOut>", _pass_focus_out, add="+")

    def iniciar_sesion():
        from security.login_guard import estado
        nickname = entry_usuario.get().strip()
        password = entry_password.get().strip()
        restante = estado(nickname)
        if restante > 0:
            minutos = max(1, (restante + 59) // 60)
            messagebox.showerror("Acceso bloqueado", f"Demasiados intentos. Intenta nuevamente en {minutos} minuto(s).")
            return

        if not nickname or not password:
            messagebox.showwarning("Campos vacíos", "Ingresa usuario y contraseña")
            return

        def tarea_login():
            servicios = _cargar_servicios_auth()
            contexto_login = servicios["obtener_contexto_login"]()
            direccion_ip = contexto_login["direccion_ip"]
            nombre_equipo = contexto_login["nombre_equipo"]
            ubicacion = contexto_login["ubicacion"]

            usuario = servicios["validar_login"](nickname, password)
            if usuario:
                servicios["registrar_bitacora_login"](
                    id_usuario=usuario.get("id_usuario"),
                    nickname=usuario.get("usu_nickname"),
                    estatus="CORRECTO",
                    descripcion="Inicio de sesión exitoso",
                    direccion_ip=direccion_ip,
                    nombre_equipo=nombre_equipo,
                    latitud=ubicacion["latitud"],
                    longitud=ubicacion["longitud"],
                    ciudad=ubicacion["ciudad"],
                    region=ubicacion["region"],
                    pais=ubicacion["pais"],
                )
                return {"acceso": True, "usuario": usuario, "ubicacion": ubicacion}

            servicios["registrar_bitacora_login"](
                id_usuario=None,
                nickname=nickname,
                estatus="FALLIDO",
                descripcion="Usuario o contraseña incorrectos",
                direccion_ip=direccion_ip,
                nombre_equipo=nombre_equipo,
                latitud=ubicacion["latitud"],
                longitud=ubicacion["longitud"],
                ciudad=ubicacion["ciudad"],
                region=ubicacion["region"],
                pais=ubicacion["pais"],
            )
            return {"acceso": False, "usuario": None, "ubicacion": ubicacion}

        def login_correcto(resultado):
            from security.login_guard import registrar_exito, registrar_fallo
            if not resultado["acceso"]:
                restante = registrar_fallo(nickname)
                mensaje = "Usuario o contraseña incorrectos"
                if restante > 0:
                    mensaje += "\n\nEl acceso quedó bloqueado temporalmente por seguridad."
                messagebox.showerror("Acceso denegado", mensaje)
                return
            registrar_exito(nickname)

            usuario = resultado["usuario"]
            establecer_usuario_actual(
                id_usuario=usuario.get("id_usuario"),
                usuario=usuario.get("usu_nickname"),
                nombre=usuario.get("usu_nombre"),
                apellido=usuario.get("usu_apellido"),
                usu_tipo=usuario.get("usu_tipo", 3),
                ubicacion=resultado.get("ubicacion") or {},
            )
            _cargar_servicios_auth()["registrar_movimiento"](
                modulo="Login",
                accion="INICIAR_SESION",
                descripcion="El usuario inició sesión correctamente",
            )
            messagebox.showinfo("Acceso correcto", f"Bienvenido, {usuario.get('usu_nombre')}")
            login_resultado["autenticado"] = True
            try:
                app.destroy()
            except Exception:
                app.quit()

        def login_error(_error):
            messagebox.showerror(
                "Error de conexión",
                "No fue posible validar el acceso. Revisa la conexión e intenta de nuevo.",
            )

        run_async(
            root=app,
            task=tarea_login,
            on_success=login_correcto,
            on_error=login_error,
            before=lambda: app.configure(cursor="watch"),
            after=lambda: app.configure(cursor=""),
        )

    # =================================================
    # BOTÓN INGRESAR
    # =================================================
    # El botón queda directamente sobre la tarjeta,
    # sin fondo/rectángulo permanente detrás.

    btn_ingresar = ctk.CTkButton(
        card,
        text="INGRESAR",
        height=50,
        corner_radius=16,
        fg_color=PRIMARY,
        hover_color=PRIMARY_700,
        border_width=0,
        text_color=WHITE,
        font=BUTTON_FONT,
        command=iniciar_sesion,
    )
    btn_ingresar.pack(
        padx=36,
        pady=(20, 2)
    )

    # =================================================
    # SEPARADOR + FOOTER
    # =================================================
    separator_wrap = ctk.CTkFrame(card, fg_color="transparent")
    separator_wrap.pack(padx=42, pady=(18, 4), fill="x")
    # Línea + glifo central decorativo
    sep_container = ctk.CTkFrame(separator_wrap, fg_color="transparent")
    sep_container.pack(fill="x", pady=6)
    sep_left = ctk.CTkFrame(
        sep_container,
        height=1,
        corner_radius=0,
        fg_color=DIVIDER,
        border_width=0,
    )
    sep_left.pack(side="left", fill="x", expand=True)
    sep_dot = ctk.CTkFrame(
        sep_container,
        width=26,
        height=26,
        corner_radius=100,
        fg_color=WHITE,
        border_width=1,
        border_color=DIVIDER,
    )
    sep_dot.pack(side="left", padx=10)
    ctk.CTkLabel(
        sep_dot,
        text="✦",
        width=24,
        height=24,
        text_color=PRIMARY,
        font=("Segoe UI Symbol", 10),
    ).place(relx=0.5, rely=0.5, anchor="center")
    sep_right = ctk.CTkFrame(
        sep_container,
        height=1,
        corner_radius=0,
        fg_color=DIVIDER,
        border_width=0,
    )
    sep_right.pack(side="left", fill="x", expand=True)

    footer_frame = ctk.CTkFrame(card, fg_color="transparent")
    footer_frame.pack(padx=28, pady=(4, 16), fill="x")
    ctk.CTkLabel(
        footer_frame,
        text=f"Sistema AXIA  ·  v{APP_VERSION}",
        font=CAPTION,
        text_color=TEXT_MUTED,
    ).pack(pady=(0, 1))
    ctk.CTkLabel(
        footer_frame,
        text="© 2026 Axia Comunicaciones · Todos los derechos reservados",
        font=TEXT_XS,
        text_color=TEXT_MUTED,
    ).pack(pady=(0, 0))

    app.bind("<Return>", lambda _event: iniciar_sesion())
    app.mainloop()
    return bool(login_resultado["autenticado"])
