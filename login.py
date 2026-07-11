import customtkinter as ctk
from tkinter import messagebox

from ui.theme import aplicar_estilo_ventana
from ui.assets import cargar_logo_axia, configurar_icono_app
from app_context import establecer_usuario_actual
from services.movimientos_service import registrar_movimiento
from core.background_tasks import run_async
from services.auth_service import (
    obtener_contexto_login,
    validar_login,
    registrar_bitacora_login,
    cambiar_password_usuario,
)
from utils import centrar_ventana
from ui.colors import (
    PRIMARY,
    SECONDARY,
    WHITE,
    CONTENT_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    BUTTON_HOVER,
)
from ui.fonts import TITLE_LG, TITLE_MD, TEXT_MD, TEXT_SM, BUTTON_FONT


LOGIN_WIDTH = 520
LOGIN_HEIGHT = 620
PASSWORD_WIDTH = 520
PASSWORD_HEIGHT = 650
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

    root = ctk.CTkFrame(app, fg_color=CONTENT_BG, corner_radius=0)
    root.pack(fill="both", expand=True)

    card = ctk.CTkFrame(
        root,
        width=CARD_WIDTH,
        height=555,
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

    entry_password = ctk.CTkEntry(
        card,
        placeholder_text="Contraseña",
        show="*",
        width=340,
        height=44,
        corner_radius=12,
        font=TEXT_MD,
    )
    entry_password.pack(pady=4)

    def iniciar_sesion():
        nickname = entry_usuario.get().strip()
        password = entry_password.get().strip()

        if not nickname or not password:
            messagebox.showwarning("Campos vacíos", "Ingresa usuario y contraseña")
            return

        def tarea_login():
            contexto_login = obtener_contexto_login()
            direccion_ip = contexto_login["direccion_ip"]
            nombre_equipo = contexto_login["nombre_equipo"]
            ubicacion = contexto_login["ubicacion"]

            usuario = validar_login(nickname, password)
            if usuario:
                registrar_bitacora_login(
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
                return {"acceso": True, "usuario": usuario}

            registrar_bitacora_login(
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
            return {"acceso": False, "usuario": None}

        def login_correcto(resultado):
            if not resultado["acceso"]:
                messagebox.showerror("Acceso denegado", "Usuario o contraseña incorrectos")
                return

            usuario = resultado["usuario"]
            establecer_usuario_actual(
                id_usuario=usuario.get("id_usuario"),
                usuario=usuario.get("usu_nickname"),
                nombre=usuario.get("usu_nombre"),
                apellido=usuario.get("usu_apellido"),
                usu_tipo=usuario.get("usu_tipo", 3),
            )
            registrar_movimiento(
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

    def abrir_cambio_password():
        ventana = ctk.CTkToplevel(app)
        aplicar_estilo_ventana(ventana)
        configurar_icono_app(ventana)
        ventana.title("Cambiar contraseña - Sistema AXIA")
        centrar_ventana(ventana, PASSWORD_WIDTH, PASSWORD_HEIGHT)
        ventana.resizable(False, False)
        ventana.transient(app)
        ventana.grab_set()

        root_password = ctk.CTkFrame(ventana, fg_color=CONTENT_BG, corner_radius=0)
        root_password.pack(fill="both", expand=True)

        password_card = ctk.CTkFrame(
            root_password,
            width=CARD_WIDTH,
            height=585,
            fg_color=WHITE,
            corner_radius=22,
            border_width=1,
            border_color="#D8E1EC",
        )
        password_card.pack(expand=True, padx=19, pady=14)
        password_card.pack_propagate(False)

        _crear_logo(password_card, size=(82, 82), pady=(8, 1))

        ctk.CTkLabel(
            password_card,
            text="Cambiar contraseña",
            font=TITLE_MD,
            text_color=TEXT_PRIMARY,
        ).pack(pady=(1, 2))

        ctk.CTkLabel(
            password_card,
            text="Valida tu usuario y RFC",
            font=TEXT_MD,
            text_color=TEXT_SECONDARY,
        ).pack(pady=(0, 7))

        common_entry = {
            "width": 340,
            "height": 42,
            "corner_radius": 12,
            "font": TEXT_MD,
        }

        entry_nickname = ctk.CTkEntry(
            password_card,
            placeholder_text="Usuario / Nickname",
            **common_entry,
        )
        entry_nickname.pack(pady=3)
        entry_nickname.focus()

        entry_rfc = ctk.CTkEntry(password_card, placeholder_text="RFC", **common_entry)
        entry_rfc.pack(pady=3)

        entry_nueva_password = ctk.CTkEntry(
            password_card,
            placeholder_text="Nueva contraseña",
            show="*",
            **common_entry,
        )
        entry_nueva_password.pack(pady=3)

        entry_confirmar_password = ctk.CTkEntry(
            password_card,
            placeholder_text="Confirmar contraseña",
            show="*",
            **common_entry,
        )
        entry_confirmar_password.pack(pady=3)

        def guardar_nueva_password():
            nickname = entry_nickname.get().strip()
            rfc = entry_rfc.get().strip().upper()
            nueva_password = entry_nueva_password.get().strip()
            confirmar_password = entry_confirmar_password.get().strip()

            if not all((nickname, rfc, nueva_password, confirmar_password)):
                messagebox.showwarning("Campos vacíos", "Completa todos los campos")
                return
            if nueva_password != confirmar_password:
                messagebox.showerror("Error", "Las contraseñas no coinciden")
                return
            if len(nueva_password) < 4:
                messagebox.showwarning(
                    "Contraseña débil",
                    "La contraseña debe tener mínimo 4 caracteres",
                )
                return

            def tarea_cambio_password():
                return cambiar_password_usuario(nickname, rfc, nueva_password)

            def cambio_password_correcto(resultado):
                actualizado, mensaje = resultado
                if actualizado:
                    messagebox.showinfo("Contraseña actualizada", mensaje)
                    ventana.destroy()
                    return
                messagebox.showerror("Error", mensaje)

            def cambio_password_error(_error):
                messagebox.showerror(
                    "Error de conexión",
                    "No fue posible actualizar la contraseña. Intenta nuevamente.",
                )

            run_async(
                root=ventana,
                task=tarea_cambio_password,
                on_success=cambio_password_correcto,
                on_error=cambio_password_error,
                before=lambda: ventana.configure(cursor="watch"),
                after=lambda: ventana.configure(cursor=""),
            )

        ctk.CTkButton(
            password_card,
            text="ACTUALIZAR CONTRASEÑA",
            width=340,
            height=43,
            corner_radius=12,
            fg_color=PRIMARY,
            hover_color=BUTTON_HOVER,
            font=BUTTON_FONT,
            command=guardar_nueva_password,
        ).pack(pady=(9, 4))

        ctk.CTkButton(
            password_card,
            text="Cancelar",
            width=340,
            height=39,
            corner_radius=12,
            fg_color="transparent",
            border_width=1,
            border_color=SECONDARY,
            text_color=PRIMARY,
            hover_color="#E8F0FF",
            font=BUTTON_FONT,
            command=ventana.destroy,
        ).pack(pady=2)

        ventana.bind("<Return>", lambda _event: guardar_nueva_password())
        ventana.bind("<Escape>", lambda _event: ventana.destroy())

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
    ).pack(pady=(10, 4))

    ctk.CTkButton(
        card,
        text="Cambiar contraseña",
        width=340,
        height=39,
        corner_radius=12,
        fg_color="transparent",
        border_width=1,
        border_color=SECONDARY,
        text_color=PRIMARY,
        hover_color="#E8F0FF",
        font=BUTTON_FONT,
        command=abrir_cambio_password,
    ).pack(pady=2)

    ctk.CTkLabel(
        card,
        text="Sistema AXIA · v1.0",
        font=TEXT_SM,
        text_color=TEXT_SECONDARY,
    ).pack(pady=(7, 2))

    app.bind("<Return>", lambda _event: iniciar_sesion())
    app.mainloop()
    return bool(login_resultado["autenticado"])
