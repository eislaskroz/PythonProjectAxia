# =====================================================
# IMPORTACIÓN DE LIBRERÍAS
# =====================================================
# Librería para crear interfaces gráficas modernas
import customtkinter as ctk

from ui.theme import aplicar_fuente_tk, aplicar_estilo_ventana

# Messagebox permite mostrar ventanas emergentes:
# advertencias, errores e información
from tkinter import messagebox

from ui.assets import cargar_logo_axia
from ui.assets import configurar_icono_app
from app_context import establecer_usuario_actual
from services.movimientos_service import registrar_movimiento

from core.background_tasks import run_async

from services.auth_service import (
    obtener_contexto_login,
    validar_login,
    registrar_bitacora_login,
    cambiar_password_usuario
)

# =====================================================
# IMPORTACIÓN DE FUNCIONES INTERNAS
# =====================================================
# Función para centrar ventanas en pantalla
from utils import centrar_ventana


# =====================================================
# IMPORTACIÓN DE COLORES CORPORATIVOS
# =====================================================
from ui.colors import (
    PRIMARY,        # Azul principal
    PRIMARY_DARK,   # Azul oscuro corporativo
    SECONDARY,      # Azul secundario
    WHITE,          # Blanco
    CONTENT_BG,     # Fondo general
    TEXT_PRIMARY,   # Texto principal
    TEXT_SECONDARY, # Texto secundario
    BUTTON_HOVER    # Color hover de botones
)

# =====================================================
# IMPORTACIÓN DE FUENTES
# =====================================================
from ui.fonts import (
    TITLE_LG,     # Títulos grandes
    TITLE_MD,     # Títulos medianos
    TEXT_MD,      # Texto normal
    TEXT_SM,      # Texto pequeño
    BUTTON_FONT   # Fuente de botones
)

# =====================================================
# LÓGICA DE NEGOCIO
# =====================================================
"""
La validación de login, cambio de contraseña, bitácora y contexto
del equipo ya no viven en este archivo.

Este archivo queda enfocado en la interfaz gráfica.
La lógica empresarial está en services/auth_service.py.
"""

# =====================================================
# FUNCIÓN PRINCIPAL LOGIN
# =====================================================
def abrir_login():
    """
    Abre la ventana de inicio de sesión.

    Esta ventana permite:
        - iniciar sesión
        - cambiar contraseña
        - registrar bitácora de acceso
        - capturar IP, equipo y geolocalización
    """

    # =================================================
    # CREAR VENTANA PRINCIPAL
    # =================================================
    app = ctk.CTk()
    aplicar_estilo_ventana(app)

    # Resultado del flujo de login.
    # True  = credenciales correctas, main.py debe abrir AXIA.
    # False = usuario cerró el Login o salió sin autenticarse.
    login_resultado = {"autenticado": False}

    def cerrar_login_sin_acceso():
        """Cierra la ventana Login sin iniciar sesión."""
        login_resultado["autenticado"] = False
        try:
            app.destroy()
        except Exception:
            app.quit()

    app.protocol("WM_DELETE_WINDOW", cerrar_login_sin_acceso)

    # Ícono de ventana
    configurar_icono_app(app)

    # Título de ventana
    app.title("Login - Sistema AXIA")

    # Centramos la ventana
    centrar_ventana(app, 1200, 700)

    # Evita que el usuario cambie tamaño
    app.resizable(False, False)

    # =================================================
    # LAYOUT PRINCIPAL
    # =================================================
    """
    layout será el contenedor general.
    Dentro colocaremos:
        - panel izquierdo corporativo
        - panel derecho con formulario login
    """
    layout = ctk.CTkFrame(
        app,
        fg_color=CONTENT_BG,
        corner_radius=0
    )
    layout.pack(
        fill="both",
        expand=True
    )

    # =================================================
    # PANEL IZQUIERDO CORPORATIVO
    # =================================================
    panel_izquierdo = ctk.CTkFrame(
        layout,
        width=360,
        fg_color=PRIMARY_DARK,
        corner_radius=0
    )
    panel_izquierdo.pack(
        side="left",
        fill="y"
    )

    # Evita que el panel cambie de tamaño
    panel_izquierdo.pack_propagate(False)

    # =================================================
    # MARCA / NOMBRE EMPRESA
    # =================================================
    logo_axia = cargar_logo_axia(size=(240, 240))

    ctk.CTkLabel(
        panel_izquierdo,
        image=logo_axia,
        text=""
    ).pack(pady=(80, 25))

    panel_izquierdo.logo_axia = logo_axia

    # =================================================
    # TEXTO INFERIOR DEL PANEL
    # =================================================
    ctk.CTkLabel(
        panel_izquierdo,
        text="Plataforma interna en desarrollo - V 01.0",
        font=TEXT_SM,
        text_color=WHITE
    ).pack(
        side="bottom",
        pady=35
    )

    # =================================================
    # PANEL DERECHO
    # =================================================
    panel_derecho = ctk.CTkFrame(
        layout,
        fg_color=CONTENT_BG,
        corner_radius=0
    )
    panel_derecho.pack(
        side="left",
        fill="both",
        expand=True
    )

    # =================================================
    # CARD LOGIN
    # =================================================
    """
    La card es el contenedor visual blanco
    donde están los campos de usuario y contraseña.
    """
    card = ctk.CTkFrame(
        panel_derecho,
        width=390,
        height=430,
        fg_color=WHITE,
        corner_radius=22
    )
    card.pack(pady=65)

    # Evita que la card cambie su tamaño
    card.pack_propagate(False)

    # =================================================
    # TÍTULO LOGIN
    # =================================================
    ctk.CTkLabel(
        card,
        text="Inicio de sesión",
        font=TITLE_LG,
        text_color=TEXT_PRIMARY
    ).pack(pady=(35, 8))

    # =================================================
    # SUBTÍTULO LOGIN
    # =================================================
    ctk.CTkLabel(
        card,
        text="Ingresa tus credenciales",
        font=TEXT_MD,
        text_color=TEXT_SECONDARY
    ).pack(pady=(0, 25))

    # =================================================
    # CAMPO USUARIO
    # =================================================
    entry_usuario = ctk.CTkEntry(
        card,
        placeholder_text="Usuario",
        width=300,
        height=43,
        corner_radius=12,
        font=TEXT_MD
    )
    entry_usuario.pack(pady=8)

    # Coloca el cursor automáticamente en este campo
    entry_usuario.focus()

    # =================================================
    # CAMPO CONTRASEÑA
    # =================================================
    entry_password = ctk.CTkEntry(
        card,
        placeholder_text="Contraseña",

        # Oculta caracteres
        show="*",
        width=300,
        height=43,
        corner_radius=12,
        font=TEXT_MD
    )
    entry_password.pack(pady=8)

    # =================================================
    # FUNCIÓN INICIAR SESIÓN
    # =================================================
    def iniciar_sesion():
        """
        Valida usuario y contraseña.
        Si el acceso es correcto:
            - registra bitácora CORRECTO
            - abre menú principal
        Si el acceso falla:
            - registra bitácora FALLIDO
            - muestra error
        """

        # Obtiene valores de los campos
        nickname = entry_usuario.get().strip()
        password = entry_password.get().strip()

        # Validación de campos vacíos
        if nickname == "" or password == "":
            messagebox.showwarning(
                "Campos vacíos",
                "Ingresa usuario y contraseña"
            )
            return

        # =============================================
        # EJECUTAR LOGIN EN SEGUNDO PLANO
        # =============================================
        # Las llamadas a Supabase y a servicios externos pueden tardar.
        # Si se ejecutan directo en el hilo principal, la ventana se congela.
        # Por eso todo el proceso pesado corre dentro de tarea_login().

        def tarea_login():
            """
            Ejecuta la validación completa sin tocar widgets de la UI.

            Importante:
            Esta función corre en un hilo secundario.
            Aquí NO se deben mostrar messagebox ni modificar ventanas.
            """
            contexto_login = obtener_contexto_login()

            direccion_ip = contexto_login["direccion_ip"]
            nombre_equipo = contexto_login["nombre_equipo"]
            ubicacion = contexto_login["ubicacion"]

            usuario = validar_login(
                nickname,
                password
            )

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
                    pais=ubicacion["pais"]
                )

                return {
                    "acceso": True,
                    "usuario": usuario
                }

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
                pais=ubicacion["pais"]
            )

            return {
                "acceso": False,
                "usuario": None
            }

        def login_correcto(resultado):
            """Procesa el resultado del login en el hilo principal de la UI."""
            if not resultado["acceso"]:
                messagebox.showerror(
                    "Acceso denegado",
                    "Usuario o contraseña incorrectos"
                )
                return

            usuario = resultado["usuario"]

            id_usuario = usuario.get("id_usuario")
            nombre = usuario.get("usu_nombre")
            apellido = usuario.get("usu_apellido")
            nickname_usuario = usuario.get("usu_nickname")
            usu_tipo = usuario.get("usu_tipo", 3)

            establecer_usuario_actual(
                id_usuario=id_usuario,
                usuario=nickname_usuario,
                nombre=nombre,
                apellido=apellido,
                usu_tipo=usu_tipo
            )

            # Este registro también usa Supabase, pero no bloquea el acceso.
            # Si falla, el logger del servicio lo registrará.
            registrar_movimiento(
                modulo="Login",
                accion="INICIAR_SESION",
                descripcion="El usuario inició sesión correctamente"
            )

            messagebox.showinfo(
                "Acceso correcto",
                f"Bienvenido, {nombre}"
            )

            # Flujo estable de sesión:
            # - Login SOLO valida credenciales y deja usuario en app_context.
            # - No abre la app principal desde aquí para evitar dos raíces CTk.
            # - main.py recibe True, destruye Login y abre AXIA limpio.
            login_resultado["autenticado"] = True
            try:
                app.destroy()
            except Exception:
                app.quit()

        def login_error(error):
            """Muestra un error controlado si la tarea de login revienta."""
            messagebox.showerror(
                "Error de conexión",
                "No fue posible validar el acceso. Revisa la conexión e intenta de nuevo."
            )

        run_async(
            root=app,
            task=tarea_login,
            on_success=login_correcto,
            on_error=login_error,
            before=lambda: app.configure(cursor="watch"),
            after=lambda: app.configure(cursor="")
        )

    # =================================================
    # FUNCIÓN CAMBIO DE CONTRASEÑA
    # =================================================
    def abrir_cambio_password():
        """
        Abre una ventana secundaria con diseño corporativo
        para permitir el cambio de contraseña.
        Validación utilizada:
            - Usuario / Nickname
            - RFC
        Flujo:
            1. Usuario captura nickname y RFC.
            2. Captura nueva contraseña.
            3. Confirma nueva contraseña.
            4. Se valida la información.
            5. Se actualiza la contraseña en Supabase.
        """

        # =============================================
        # CREAR VENTANA SECUNDARIA
        # =============================================
        ventana = ctk.CTkToplevel(app)
        ventana.title("Cambiar contraseña")
        centrar_ventana(
            ventana,
            1200,
            700
        )
        ventana.resizable(False, False)
        """
        grab_set():
        Bloquea la ventana principal mientras esta
        ventana secundaria se encuentra abierta.
        """
        ventana.grab_set()

        # =============================================
        # LAYOUT GENERAL
        # =============================================
        """
        Layout principal de la ventana.
        Tendrá dos secciones:
            - Panel izquierdo corporativo.
            - Panel derecho con formulario.
        """
        layout = ctk.CTkFrame(
            ventana,
            fg_color=CONTENT_BG,
            corner_radius=0
        )
        layout.pack(
            fill="both",
            expand=True
        )

        # =============================================
        # PANEL IZQUIERDO CORPORATIVO
        # =============================================
        panel_izquierdo = ctk.CTkFrame(
            layout,
            width=280,
            fg_color=PRIMARY_DARK,
            corner_radius=0
        )
        panel_izquierdo.pack(
            side="left",
            fill="y"
        )
        panel_izquierdo.pack_propagate(False)

        # =========================================================
        # LOGOTIPO CORPORATIVO AXIA
        # =========================================================
        # Carga del logo institucional desde el módulo assets
        logo_axia = cargar_logo_axia(size=(230, 230))

        # Label contenedor del logotipo
        ctk.CTkLabel(
            panel_izquierdo,
            image=logo_axia,
            text=""
        ).pack(
            pady=(70, 25)
        )

        # Referencia persistente de imagen
        # Evita que Python elimine la imagen por el garbage collector
        panel_izquierdo.logo_axia = logo_axia

        # =============================================
        # SUBTÍTULO PANEL IZQUIERDO
        # =============================================
        ctk.CTkLabel(
            panel_izquierdo,
            text="Seguridad de acceso",
            font=TEXT_MD,
            text_color=WHITE
        ).pack(
            pady=(0, 30)
        )

        # =============================================
        # DESCRIPCIÓN CORPORATIVA
        # =============================================
        ctk.CTkLabel(
            panel_izquierdo,
            text=(
                "Actualiza tu contraseña\n"
                "de forma segura usando\n"
                "tu usuario y RFC."
            ),
            font=TEXT_MD,
            text_color=WHITE,
            justify="center"
        ).pack(
            pady=20,
            padx=25
        )

        # =============================================
        # NOTA INFERIOR
        # =============================================
        ctk.CTkLabel(
            panel_izquierdo,
            text="Validación interna",
            font=TEXT_SM,
            text_color=WHITE
        ).pack(
            side="bottom",
            pady=30
        )

        # =============================================
        # PANEL DERECHO
        # =============================================
        panel_derecho = ctk.CTkFrame(
            layout,
            fg_color=CONTENT_BG,
            corner_radius=0
        )
        panel_derecho.pack(
            side="left",
            fill="both",
            expand=True
        )

        # =============================================
        # CARD FORMULARIO
        # =============================================
        """
        Card blanca donde se colocan los campos
        del cambio de contraseña.
        """
        card = ctk.CTkFrame(
            panel_derecho,
            width=1200,
            height=700,
            fg_color=WHITE,
            corner_radius=22
        )
        card.pack(
            pady=40
        )
        card.pack_propagate(False)

        # =============================================
        # TÍTULO FORMULARIO
        # =============================================
        ctk.CTkLabel(
            card,
            text="Cambiar contraseña",
            font=TITLE_MD,
            text_color=TEXT_PRIMARY
        ).pack(
            pady=(28, 6)
        )

        # =============================================
        # SUBTÍTULO FORMULARIO
        # =============================================
        ctk.CTkLabel(
            card,
            text="Valida tu usuario y RFC",
            font=TEXT_MD,
            text_color=TEXT_SECONDARY
        ).pack(
            pady=(0, 20)
        )

        # =============================================
        # CAMPO NICKNAME
        # =============================================
        entry_nickname = ctk.CTkEntry(
            card,
            placeholder_text="Usuario / Nickname",
            width=300,
            height=40,
            corner_radius=12,
            font=TEXT_MD
        )
        entry_nickname.pack(
            pady=7
        )
        entry_nickname.focus()

        # =============================================
        # CAMPO RFC
        # =============================================
        entry_rfc = ctk.CTkEntry(
            card,
            placeholder_text="RFC",
            width=300,
            height=40,
            corner_radius=12,
            font=TEXT_MD
        )
        entry_rfc.pack(
            pady=7
        )

        # =============================================
        # CAMPO NUEVA CONTRASEÑA
        # =============================================
        entry_nueva_password = ctk.CTkEntry(
            card,
            placeholder_text="Nueva contraseña",
            show="*",
            width=300,
            height=40,
            corner_radius=12,
            font=TEXT_MD
        )
        entry_nueva_password.pack(
            pady=7
        )

        # =============================================
        # CAMPO CONFIRMAR CONTRASEÑA
        # =============================================
        entry_confirmar_password = ctk.CTkEntry(
            card,
            placeholder_text="Confirmar contraseña",
            show="*",
            width=300,
            height=40,
            corner_radius=12,
            font=TEXT_MD
        )
        entry_confirmar_password.pack(
            pady=7
        )

        # =============================================
        # FUNCIÓN GUARDAR NUEVA CONTRASEÑA
        # =============================================
        def guardar_nueva_password():
            """
            Valida la información capturada
            y solicita la actualización de contraseña
            en la base de datos Supabase.
            """
            # Obtener valores del formulario
            nickname = entry_nickname.get().strip()
            """
            Convertimos RFC a mayúsculas para evitar errores
            de captura por minúsculas.
            """
            rfc = entry_rfc.get().strip().upper()
            nueva_password = entry_nueva_password.get().strip()
            confirmar_password = entry_confirmar_password.get().strip()

            # =========================================
            # VALIDAR CAMPOS VACÍOS
            # =========================================
            if (
                nickname == ""
                or rfc == ""
                or nueva_password == ""
                or confirmar_password == ""
            ):
                messagebox.showwarning(
                    "Campos vacíos",
                    "Completa todos los campos"
                )
                return

            # =========================================
            # VALIDAR COINCIDENCIA DE CONTRASEÑAS
            # =========================================
            if nueva_password != confirmar_password:
                messagebox.showerror(
                    "Error",
                    "Las contraseñas no coinciden"
                )
                return

            # =========================================
            # VALIDAR LONGITUD MÍNIMA
            # =========================================
            if len(nueva_password) < 4:
                messagebox.showwarning(
                    "Contraseña débil",
                    "La contraseña debe tener mínimo 4 caracteres"
                )
                return

            # =========================================
            # ACTUALIZAR CONTRASEÑA EN SEGUNDO PLANO
            # =========================================
            # La actualización viaja a Supabase; se ejecuta fuera del hilo
            # principal para evitar que la ventana se congele.

            def tarea_cambio_password():
                return cambiar_password_usuario(
                    nickname,
                    rfc,
                    nueva_password
                )

            def cambio_password_correcto(resultado):
                actualizado, mensaje = resultado

                if actualizado:
                    messagebox.showinfo(
                        "Contraseña actualizada",
                        mensaje
                    )
                    ventana.destroy()
                    return

                messagebox.showerror(
                    "Error",
                    mensaje
                )

            def cambio_password_error(error):
                messagebox.showerror(
                    "Error de conexión",
                    "No fue posible actualizar la contraseña. Intenta nuevamente."
                )

            run_async(
                root=ventana,
                task=tarea_cambio_password,
                on_success=cambio_password_correcto,
                on_error=cambio_password_error,
                before=lambda: ventana.configure(cursor="watch"),
                after=lambda: ventana.configure(cursor="")
            )

        # =============================================
        # BOTÓN ACTUALIZAR CONTRASEÑA
        # =============================================
        ctk.CTkButton(
            card,
            text="ACTUALIZAR CONTRASEÑA",
            width=300,
            height=42,
            corner_radius=12,
            fg_color=PRIMARY,
            hover_color=BUTTON_HOVER,
            font=BUTTON_FONT,
            command=guardar_nueva_password
        ).pack(
            pady=(22, 8)
        )

        # =============================================
        # BOTÓN CANCELAR
        # =============================================
        ctk.CTkButton(
            card,
            text="Cancelar",
            width=300,
            height=38,
            corner_radius=12,
            fg_color="gray",
            font=BUTTON_FONT,
            command=ventana.destroy
        ).pack(
            pady=5
        )

        # =============================================
        # ATAJO ENTER
        # =============================================
        """
        Permite guardar la nueva contraseña
        presionando Enter.
        """
        ventana.bind(
            "<Return>",
            lambda event: guardar_nueva_password()
        )

    # =================================================
    # BOTÓN INGRESAR
    # =================================================
    ctk.CTkButton(
        card,
        text="INGRESAR",
        width=300,
        height=45,
        corner_radius=12,
        fg_color=PRIMARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=iniciar_sesion
    ).pack(pady=(25, 10))

    # =================================================
    # BOTÓN CAMBIAR CONTRASEÑA
    # =================================================
    ctk.CTkButton(
        card,
        text="Cambiar contraseña",
        width=300,
        height=38,
        corner_radius=12,
        fg_color="transparent",
        border_width=1,
        border_color=SECONDARY,
        text_color=PRIMARY,
        hover_color="#e8f0ff",
        font=BUTTON_FONT,
        command=abrir_cambio_password
    ).pack(pady=6)


    # =================================================
    # FOOTER
    # =================================================
    ctk.CTkLabel(
        card,
        text="Sistema v1.0",
        font=TEXT_SM,
        text_color=TEXT_SECONDARY
    ).pack(pady=(18, 5))

    # =================================================
    # ATAJO ENTER
    # =================================================
    """
    Permite iniciar sesión presionando Enter.
    """
    app.bind(
        "<Return>",
        lambda event: iniciar_sesion()
    )

    # =================================================
    # LOOP PRINCIPAL
    # =================================================
    app.mainloop()

    return bool(login_resultado["autenticado"])
