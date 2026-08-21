import customtkinter as ctk
from tkinter import messagebox

from ui.theme import aplicar_estilo_ventana
from ui.assets import cargar_logo_axia, configurar_icono_app
from app_context import establecer_usuario_actual
from core.background_tasks import run_async
from utils import centrar_ventana
from ui.colors import (
    PRIMARY,
    WHITE,
    CONTENT_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    BUTTON_HOVER,
)
from ui.fonts import TITLE_LG, TITLE_MD, TEXT_MD, TEXT_SM, BUTTON_FONT



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
LOGIN_HEIGHT = 570
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

    root = ctk.CTkFrame(app, fg_color=CONTENT_BG, corner_radius=0)
    root.pack(fill="both", expand=True)

    card = ctk.CTkFrame(
        root,
        width=CARD_WIDTH,
        height=505,
        fg_color=WHITE,
        corner_radius=22,
        border_width=1,
        border_color="#D8E1EC",
    )
    card.pack(expand=True, padx=19, pady=15)
    card.pack_propagate(False)

    _crear_logo(card, size=(105, 105), pady=(9, 2))

    ctk.CTkLabel(
        card,
        text="Inicio de sesión",
        font=TITLE_LG,
        text_color=TEXT_PRIMARY,
    ).pack(pady=(1, 2))

    ctk.CTkLabel(
        card,
        text="Ingresa tus credenciales",
        font=TEXT_MD,
        text_color=TEXT_SECONDARY,
    ).pack(pady=(0, 9))

    entry_usuario = ctk.CTkEntry(
        card,
        placeholder_text="Usuario",
        width=340,
        height=44,
        corner_radius=12,
        font=TEXT_MD,
    )
    entry_usuario.pack(pady=4)
    entry_usuario.focus()

    password_row = ctk.CTkFrame(card, width=340, height=44, fg_color="transparent")
    password_row.pack(pady=4)
    password_row.pack_propagate(False)

    entry_password = ctk.CTkEntry(
        password_row,
        placeholder_text="Contraseña",
        show="*",
        width=292,
        height=44,
        corner_radius=12,
        font=TEXT_MD,
    )
    entry_password.pack(side="left", fill="y")

    password_visible = {"valor": False}

    def alternar_password():
        password_visible["valor"] = not password_visible["valor"]
        entry_password.configure(show="" if password_visible["valor"] else "*")
        btn_ver_password.configure(text="🙈" if password_visible["valor"] else "👁")

    btn_ver_password = ctk.CTkButton(
        password_row,
        text="👁",
        width=42,
        height=44,
        corner_radius=12,
        fg_color="#E9EFF6",
        hover_color="#D8E3EF",
        text_color=TEXT_PRIMARY,
        font=("Segoe UI Emoji", 16),
        command=alternar_password,
    )
    btn_ver_password.pack(side="right", fill="y")

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

    ctk.CTkButton(
        card,
        text="INGRESAR",
        width=340,
        height=45,
        corner_radius=12,
        fg_color=PRIMARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=iniciar_sesion,
    ).pack(pady=(12, 8))


    ctk.CTkLabel(
        card,
        text="Sistema AXIA · v2.01.8",
        font=TEXT_SM,
        text_color=TEXT_SECONDARY,
    ).pack(pady=(14, 2))

    app.bind("<Return>", lambda _event: iniciar_sesion())
    app.mainloop()
    return bool(login_resultado["autenticado"])
