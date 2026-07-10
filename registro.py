# =====================================================
# IMPORTACIÓN DE LIBRERÍAS
# =====================================================

import customtkinter as ctk
from tkinter import messagebox

# =====================================================
# IMPORTACIÓN DE FUNCIONES INTERNAS
# =====================================================

from utils import centrar_ventana
from core.background_tasks import run_async
from services.usuarios_service import registrar_usuario
from ui.assets import cargar_logo_axia, configurar_icono_ventana
from services.movimientos_service import registrar_movimiento

# =====================================================
# IMPORTACIÓN DE COLORES CORPORATIVOS
# =====================================================

from ui.colors import (
    PRIMARY,
    PRIMARY_DARK,
    WHITE,
    CONTENT_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    BUTTON_HOVER
)

# =====================================================
# IMPORTACIÓN DE FUENTES
# =====================================================

from ui.fonts import (
    TITLE_LG,
    TITLE_MD,
    TEXT_MD,
    TEXT_SM,
    BUTTON_FONT
)


# =====================================================
# FUNCIÓN PRINCIPAL: abrir_registro_usuario()
# =====================================================
def abrir_registro_usuario(app):
    """
    Abre la ventana para registrar un nuevo colaborador
    dentro del sistema AXIA.
    """

    # =================================================
    # CREAR VENTANA SECUNDARIA
    # =================================================

    ventana = ctk.CTkToplevel(app)
    ventana.title("Registro de Usuario")
    configurar_icono_ventana(ventana)

    centrar_ventana(
        ventana,
        1200,
        700
    )

    ventana.resizable(False, False)
    ventana.grab_set()

    # =================================================
    # LAYOUT GENERAL
    # =================================================

    layout = ctk.CTkFrame(
        ventana,
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
        width=300,
        fg_color=PRIMARY_DARK,
        corner_radius=0
    )
    panel_izquierdo.pack(
        side="left",
        fill="y"
    )
    panel_izquierdo.pack_propagate(False)

    logo_axia = cargar_logo_axia(size=(210, 210))

    ctk.CTkLabel(
        panel_izquierdo,
        image=logo_axia,
        text=""
    ).pack(
        pady=(70, 20)
    )

    panel_izquierdo.logo_axia = logo_axia

    ctk.CTkLabel(
        panel_izquierdo,
        text="Alta de colaborador",
        font=TEXT_MD,
        text_color=WHITE
    ).pack(
        pady=(0, 30)
    )

    ctk.CTkLabel(
        panel_izquierdo,
        text=(
            "Registra usuarios internos\n"
            "para acceder al sistema\n"
            "empresarial AXIA."
        ),
        font=TEXT_MD,
        text_color=WHITE,
        justify="center"
    ).pack(
        pady=20,
        padx=25
    )

    ctk.CTkLabel(
        panel_izquierdo,
        text="Gestión segura de usuarios",
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

    ctk.CTkLabel(
        panel_derecho,
        text="Registro de nuevo colaborador",
        font=TITLE_LG,
        text_color=TEXT_PRIMARY
    ).pack(
        pady=(25, 5),
        anchor="w",
        padx=35
    )

    ctk.CTkLabel(
        panel_derecho,
        text="Captura la información general, laboral y de acceso del usuario.",
        font=TEXT_MD,
        text_color=TEXT_SECONDARY
    ).pack(
        anchor="w",
        padx=35,
        pady=(0, 15)
    )

    # =================================================
    # CARD FORMULARIO
    # =================================================

    card_formulario = ctk.CTkScrollableFrame(
        panel_derecho,
        width=680,
        height=440,
        fg_color=WHITE,
        corner_radius=22
    )
    card_formulario.pack(
        padx=35,
        pady=(10, 8),
        fill="both",
        expand=False
    )

    entradas = {}

    # =================================================
    # HELPERS VISUALES
    # =================================================

    def crear_titulo_seccion(texto):
        """
        Crea un título de sección dentro del formulario.
        """

        ctk.CTkLabel(
            card_formulario,
            text=texto,
            font=TITLE_MD,
            text_color=PRIMARY
        ).pack(
            pady=(22, 8),
            anchor="w",
            padx=25
        )

    def crear_campo(clave, texto, ocultar=False):
        """
        Crea un campo de captura reutilizable.
        """

        ctk.CTkLabel(
            card_formulario,
            text=texto,
            font=TEXT_SM,
            text_color=TEXT_SECONDARY
        ).pack(
            anchor="w",
            padx=30,
            pady=(8, 2)
        )

        entrada = ctk.CTkEntry(
            card_formulario,
            placeholder_text=texto,
            width=600,
            height=38,
            corner_radius=12,
            font=TEXT_MD,
            show="*" if ocultar else ""
        )
        entrada.pack(
            padx=30,
            pady=(0, 4)
        )

        entradas[clave] = entrada

    # =================================================
    # CAMPOS DEL FORMULARIO
    # =================================================

    crear_titulo_seccion("Datos de acceso")
    crear_campo("usu_nickname", "Usuario / Nickname")
    crear_campo("usu_password", "Contraseña", ocultar=True)
    crear_campo("confirmar_password", "Confirmar contraseña", ocultar=True)

    crear_titulo_seccion("Datos personales")
    crear_campo("usu_nombre", "Nombre")
    crear_campo("usu_apellido", "Apellido")
    crear_campo("usu_rfc", "RFC")
    crear_campo("usu_curp", "CURP")
    crear_campo("usu_imss", "IMSS")
    crear_campo("usu_ine", "INE")
    crear_campo("usu_fechanac", "Fecha de nacimiento AAAA-MM-DD")

    crear_titulo_seccion("Domicilio")
    crear_campo("usu_calle", "Calle")
    crear_campo("usu_numero", "Número")
    crear_campo("usu_colonia", "Colonia")
    crear_campo("usu_municipio", "Municipio")
    crear_campo("usu_estado", "Estado")
    crear_campo("usu_cp", "Código Postal")

    crear_titulo_seccion("Contacto y datos laborales")
    crear_campo("usu_telefono", "Teléfono")
    crear_campo("usu_depto", "Departamento")
    crear_campo("usu_puesto", "Puesto")
    crear_campo("usu_regimen", "Régimen")

    # =================================================
    # FUNCIÓN: guardar_usuario()
    # =================================================

    def guardar_usuario():
        """
        Captura los datos del formulario y solicita el registro
        a la capa de servicios.

        La UI solo:
        - lee campos,
        - muestra mensajes,
        - registra movimiento visual/auditoría si el servicio confirma éxito.

        La lógica de validación, duplicados, hash y Supabase está en:
        services/usuarios_service.py
        """

        datos = {}

        # =============================================
        # OBTENER DATOS DEL FORMULARIO
        # =============================================
        for clave, entrada in entradas.items():
            datos[clave] = entrada.get().strip()

        # =============================================
        # REGISTRAR USUARIO EN SEGUNDO PLANO
        # =============================================
        # registrar_usuario() consulta Supabase. Si se ejecuta directamente
        # desde el botón, la ventana puede congelarse si internet está lento.

        def tarea_registro_usuario():
            return registrar_usuario(datos)

        def registro_correcto(resultado):
            creado, mensaje, datos_guardados = resultado

            if not creado:
                messagebox.showerror(
                    "No fue posible registrar el usuario",
                    mensaje
                )
                return

            registrar_movimiento(
                modulo="USUARIOS",
                accion="CREAR",
                descripcion=(
                    f"Se registró el usuario "
                    f"{datos_guardados['usu_nickname']}"
                ),
                registro_afectado=datos_guardados["usu_nickname"]
            )

            messagebox.showinfo(
                "Registro exitoso",
                mensaje
            )

            ventana.destroy()

        def registro_error(error):
            messagebox.showerror(
                "Error de conexión",
                "No fue posible registrar el usuario. Revisa la conexión e intenta de nuevo."
            )

        run_async(
            root=ventana,
            task=tarea_registro_usuario,
            on_success=registro_correcto,
            on_error=registro_error,
            before=lambda: ventana.configure(cursor="watch"),
            after=lambda: ventana.configure(cursor="")
        )

    # =================================================
    # BOTONES
    # =================================================

    frame_botones = ctk.CTkFrame(
        panel_derecho,
        fg_color="transparent"
    )
    frame_botones.pack(
        pady=(5, 18)
    )

    ctk.CTkButton(
        frame_botones,
        text="GUARDAR USUARIO",
        width=220,
        height=42,
        corner_radius=12,
        fg_color=PRIMARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=guardar_usuario
    ).grid(
        row=0,
        column=0,
        padx=10
    )

    ctk.CTkButton(
        frame_botones,
        text="Cancelar",
        width=170,
        height=42,
        corner_radius=12,
        fg_color="gray",
        font=BUTTON_FONT,
        command=ventana.destroy
    ).grid(
        row=0,
        column=1,
        padx=10
    )

    ventana.bind(
        "<Return>",
        lambda event: guardar_usuario()
    )