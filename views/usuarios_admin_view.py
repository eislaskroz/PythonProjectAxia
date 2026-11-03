
"""
=========================================================
MÓDULO: views/usuarios_admin_view.py
DESCRIPCIÓN:
Vista administrativa para buscar, crear y modificar usuarios.
=========================================================
"""

import customtkinter as ctk
from ui.form_fields import AxiaEntry, AxiaTextbox
from ui.iconos import cargar_icono
_AXIA_ICON_BUSCAR = cargar_icono("buscar.png", (18, 18))
_AXIA_ICON_BUSCAR_BLANCO = cargar_icono("buscar.png", (16, 16), blanco=True)
from tkinter import messagebox, simpledialog
from pathlib import Path
from PIL import Image

from app_context import obtener_usuario_actual
from security.permissions import puede_ver_usuarios, puede_editar_expedientes_rrhh
from ui.date_picker import abrir_selector_fecha
from ui.native_table import NativeTreeTable
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY, BUTTON_HOVER
from ui.fonts import TEXT_MD, TEXT_SM, BUTTON_FONT
from services.usuarios_service import (
    buscar_usuarios,
    crear_usuario_admin,
    actualizar_usuario_admin,
    UsuarioServiceError,
)
from services.rrhh_usuarios_service import (
    CAMPOS_RRHH, buscar_usuarios_rrhh, actualizar_usuario_rrhh,
    alta_usuario_rrhh, baja_usuario_rrhh,
)


CAMPOS_USUARIO = [
    ("usu_nickname", "Usuario / Nickname", True),
    ("usu_password", "Nueva contraseña", False),
    ("usu_nombre", "Nombre", True),
    ("usu_apellido", "Apellido", True),
    ("usu_tipo", "Tipo de usuario (1-10)", True),
    ("usu_rfc", "RFC", False),
    ("usu_curp", "CURP", False),
    ("usu_imss", "IMSS", False),
    ("usu_ine", "INE", False),
    ("usu_fechanac", "Fecha nacimiento", False),
    ("usu_telefono", "Teléfono", False),
    ("usu_correo", "Correo electrónico de empresa", False),
    ("usu_depto", "Departamento", False),
    ("usu_puesto", "Puesto", False),
    ("usu_calle", "Calle", False),
    ("usu_numero", "Número", False),
    ("usu_colonia", "Colonia", False),
    ("usu_municipio", "Municipio", False),
    ("usu_estado", "Estado", False),
    ("usu_cp", "Código Postal", False),
    ("usu_regimen", "Régimen", False),
]


def mostrar_usuarios_admin(parent, app):
    """
    Renderiza la administración de usuarios.
    """

    usuario_activo = obtener_usuario_actual()
    if not puede_ver_usuarios(usuario_activo):
        messagebox.showerror(
            "Acceso denegado",
            "Tu nivel de usuario no tiene permiso para administrar usuarios."
        )
        app.mostrar_vista_inicio_aco()
        return

    solo_rrhh = puede_editar_expedientes_rrhh(usuario_activo)

    def solicitar_clave_rrhh(proposito):
        return simpledialog.askstring(
            'Validación de Recursos Humanos',
            f'Confirma tu contraseña para {proposito}:',
            show='*', parent=app,
        )

    for widget in parent.winfo_children():
        widget.destroy()

    estado = {
        "seleccionado": None,
        "resultados": [],
        "variables": {},
        "entradas": {},
        "modo": "lectura",
    }

    contenedor = ctk.CTkFrame(parent, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=14, pady=4)

    # RH: búsqueda y resultados comparten una misma franja, 50/50.
    # Los demás perfiles conservan su presentación y navegación existentes.
    franja_rrhh = None
    if solo_rrhh:
        franja_rrhh = ctk.CTkFrame(contenedor, fg_color="transparent")
        franja_rrhh.pack(fill="x", pady=(0, 6))
        franja_rrhh.grid_columnconfigure(0, weight=1, uniform="rrhh_superior")
        franja_rrhh.grid_columnconfigure(1, weight=1, uniform="rrhh_superior")
        franja_rrhh.grid_rowconfigure(0, weight=1)

    barra = ctk.CTkFrame(
        franja_rrhh if solo_rrhh else contenedor,
        fg_color=WHITE if solo_rrhh else "transparent",
        corner_radius=16 if solo_rrhh else 0,
    )
    if solo_rrhh:
        barra.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ctk.CTkLabel(
            barra, text="Buscar empleado", font=("Montserrat", 16, "bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 2))
    else:
        barra.pack(fill="x", pady=(0, 5))
    barra.grid_columnconfigure(0, weight=1)
    fila_busqueda = 1 if solo_rrhh else 0

    var_busqueda = ctk.StringVar()
    carpeta_iconos = Path(__file__).resolve().parent.parent / "assets" / "iconos"
    with Image.open(carpeta_iconos / "buscar.png") as imagen_buscar:
        imagen_buscar = imagen_buscar.convert("RGBA")
    icono_buscar = ctk.CTkImage(
        light_image=imagen_buscar,
        dark_image=imagen_buscar,
        size=(20, 20)
    )
    imagen_buscar_blanca = Image.new("RGBA", imagen_buscar.size, (255, 255, 255, 0))
    imagen_buscar_blanca.putalpha(imagen_buscar.getchannel("A"))
    icono_buscar_blanco = ctk.CTkImage(
        light_image=imagen_buscar_blanca,
        dark_image=imagen_buscar_blanca,
        size=(16, 16)
    )

    buscador = ctk.CTkFrame(
        barra,
        fg_color="#F8FAFC",
        corner_radius=12,
        border_width=1,
        border_color="#D9E2EC",
    )
    buscador.grid(
        row=fila_busqueda, column=0, sticky="ew",
        padx=(10, 5) if solo_rrhh else (0, 5),
        pady=(0, 7) if solo_rrhh else 0,
    )
    buscador.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(
        buscador,
        text="",
        image=icono_buscar,
        width=28,
        height=38,
        anchor="center",
    ).grid(row=0, column=0, sticky="ns", padx=(12, 8), pady=6)

    entry_busqueda = AxiaEntry(
        buscador,
        textvariable=var_busqueda,
        height=38,
        fg_color="transparent",
        border_width=0,
        font=("Segoe UI", 13),
    )
    entry_busqueda.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=6)

    # Texto de ayuda integrado al campo; no crea un rectángulo blanco sobre el gris.
    entry_busqueda.configure(
        placeholder_text=(
            'Nombre, usuario o correo...' if solo_rrhh
            else 'Buscar usuario por nickname, nombre, apellido o correo empresarial...'
        ),
        placeholder_text_color="#64748B",
    )

    btn_buscar = ctk.CTkButton(
        barra,
        text="Buscar",
        image=icono_buscar_blanco,
        compound="left",
        width=120,
        height=38,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=lambda: cargar_resultados(var_busqueda.get()),
    )
    btn_buscar.grid(
        row=fila_busqueda, column=1,
        padx=(0, 10) if solo_rrhh else 0,
        pady=(0, 7) if solo_rrhh else 0,
    )
    if solo_rrhh:
        ctk.CTkLabel(
            barra,
            text="Busca empleados, registra altas y administra bajas sin borrar el historial.",
            font=TEXT_SM, text_color=TEXT_SECONDARY,
            anchor="w", justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 4))

    cuerpo = ctk.CTkFrame(contenedor, fg_color="transparent")
    cuerpo.pack(fill="both", expand=True)

    if solo_rrhh:
        # El expediente se expande a todo el ancho justo debajo de la franja.
        cuerpo.grid_columnconfigure(0, weight=1)
        cuerpo.grid_rowconfigure(0, weight=1)
    else:
        cuerpo.grid_columnconfigure(0, weight=1)
        cuerpo.grid_columnconfigure(1, weight=2)
        cuerpo.grid_rowconfigure(0, weight=1)

    panel_resultados = ctk.CTkFrame(
        franja_rrhh if solo_rrhh else cuerpo,
        fg_color=WHITE,
        corner_radius=16,
    )
    if solo_rrhh:
        panel_resultados.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
    else:
        panel_resultados.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    panel_resultados.grid_rowconfigure(1, weight=1)
    panel_resultados.grid_columnconfigure(0, weight=1)

    lbl_resultados = ctk.CTkLabel(
        panel_resultados, text="Resultados (0)", font=("Montserrat", 16, "bold"),
        text_color=TEXT_PRIMARY, anchor="w",
    )
    lbl_resultados.grid(
        row=0,
        column=0,
        sticky="ew",
        padx=9,
        pady=(5, 2) if solo_rrhh else (8, 3),
    )

    tabla_resultados = NativeTreeTable(
        panel_resultados,
        columns=(
            ("nickname", "Usuario", 120),
            ("nombre", "Nombre completo", 210),
            ("tipo", "Tipo", 70),
        ) if not solo_rrhh else (
            ("nickname", "Usuario", 100),
            ("nombre", "Nombre completo", 205),
            ("tipo", "Rol", 50),
            ("estado", "Estado", 105),
        ),
        on_select=lambda usuario: cargar_en_formulario(usuario),
        on_open=lambda usuario: cargar_en_formulario(usuario),
        # Dos filas visibles en RH reducen ~30% la altura del bloque superior;
        # el desplazamiento de la tabla permite seguir consultando los resultados.
        height=2 if solo_rrhh else 18,
     table_id="usuarios_catalogo",)
    tabla_resultados.grid(
        row=1,
        column=0,
        sticky="nsew",
        padx=8,
        pady=(0, 3) if solo_rrhh else (0, 5),
    )

    panel_formulario = ctk.CTkScrollableFrame(
        cuerpo,
        fg_color=WHITE,
        corner_radius=16,
    )
    if solo_rrhh:
        panel_formulario.grid(row=0, column=0, sticky="nsew")
    else:
        panel_formulario.grid(row=0, column=1, sticky="nsew")

    ctk.CTkLabel(
        panel_formulario,
        text="Expediente de personal" if solo_rrhh else "Datos del usuario",
        font=("Montserrat", 18, "bold"),
        text_color=TEXT_PRIMARY,
    ).pack(anchor="w", padx=10, pady=(9, 3))

    if solo_rrhh:
        ctk.CTkLabel(
            panel_formulario,
            text=("Recursos Humanos: alta y baja laboral de personal, y actualización "
                  "de expedientes. Los roles, las contraseñas y el acceso a "
                  "las aplicaciones los habilita el Administrador."),
            font=TEXT_SM,
            text_color=TEXT_SECONDARY,
            justify="left",
            anchor="w",
            wraplength=980 if solo_rrhh else 620,
        ).pack(fill="x", padx=10, pady=(0, 7))

    form_grid = ctk.CTkFrame(
        panel_formulario,
        fg_color="transparent",
    )
    form_grid.pack(fill="x", padx=10, pady=(0, 6))
    form_grid.grid_columnconfigure(0, weight=1)
    form_grid.grid_columnconfigure(1, weight=1)
    form_grid.grid_columnconfigure(2, weight=1)

    total_columnas_formulario = 3

    # RH puede identificar la cuenta, pero no tiene necesidad de ver ni de
    # editar el control de contraseña. Para Admin y Jefe no cambia la pantalla.
    campos_visibles = [
        dato for dato in CAMPOS_USUARIO
        if not (solo_rrhh and dato[0] == "usu_password")
    ]
    for indice, (campo, etiqueta, obligatorio) in enumerate(campos_visibles):
        fila = indice // total_columnas_formulario
        columna = indice % total_columnas_formulario

        wrapper = ctk.CTkFrame(
            form_grid,
            fg_color="transparent",
        )
        wrapper.grid(
            row=fila,
            column=columna,
            sticky="ew",
            padx=(0, 4) if columna == 0 else ((4, 4) if columna == 1 else (4, 0)),
            pady=2,
        )
        wrapper.grid_columnconfigure(0, weight=1)

        texto = f"{etiqueta}{' *' if obligatorio else ''}"
        icono = (
            "✉️"
            if campo == "usu_correo"
            else (
                "📍"
                if campo in (
                    "usu_calle",
                    "usu_numero",
                    "usu_colonia",
                    "usu_municipio",
                    "usu_estado",
                    "usu_cp",
                )
                else "•"
            )
        )

        ctk.CTkLabel(
            wrapper,
            text=f"{icono} {texto}",
            font=TEXT_SM,
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        var = ctk.StringVar()
        estado["variables"][campo] = var

        entry = AxiaEntry(
            wrapper,
            textvariable=var,
            height=36,
            show="*" if campo == "usu_password" else None,
        )
        entry.grid(row=1, column=0, sticky="ew", pady=(1, 0))

        if "fecha" in campo.lower():
            entry.bind(
                "<Button-1>",
                lambda _event, var=var, entry=entry, wrapper=wrapper: (
                    abrir_selector_fecha(wrapper, var)
                    if str(entry.cget("state")) == "normal" else None
                ),
            )

        entry.configure(state="disabled")
        estado["entradas"][campo] = entry

    # =====================================================
    # BOTONES DE ACCIÓN CENTRADOS
    # =====================================================

    acciones = ctk.CTkFrame(
        panel_formulario,
        fg_color="transparent",
    )
    acciones.pack(fill="x", padx=10, pady=(8, 12))

    # Columnas laterales flexibles para centrar los botones
    acciones.grid_columnconfigure(0, weight=1)
    acciones.grid_columnconfigure(1, weight=0)
    acciones.grid_columnconfigure(2, weight=0)
    acciones.grid_columnconfigure(3, weight=1)

    # Cargar iconos desde assets/iconos
    carpeta_iconos = (
        Path(__file__).resolve().parent.parent
        / "assets"
        / "iconos"
    )

    def cargar_icono_blanco(nombre_archivo):
        ruta_icono = carpeta_iconos / nombre_archivo

        if not ruta_icono.exists():
            return None

        imagen = Image.open(ruta_icono).convert("RGBA")

        # Convertir el icono a blanco conservando su transparencia
        transparencia = imagen.getchannel("A")
        imagen_blanca = Image.new(
            "RGBA",
            imagen.size,
            (255, 255, 255, 255),
        )
        imagen_blanca.putalpha(transparencia)

        return ctk.CTkImage(
            light_image=imagen_blanca,
            dark_image=imagen_blanca,
            size=(18, 18),
        )

    # Icono de Guardar nuevo
    icono_guardar = cargar_icono_blanco("guardar.png")

    # Icono de Actualizar seleccionado
    icono_actualizar = cargar_icono_blanco("limpiar.png")

    # Botón 1: Guardar nuevo
    btn_guardar = ctk.CTkButton(
        acciones,
        text="Guardar nuevo",
        image=icono_guardar,
        compound="left",
        width=150,
        height=38,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=lambda: guardar_nuevo(),
    )
    btn_guardar.grid(
        row=0,
        column=1,
        padx=(0, 6),
    )
    if solo_rrhh:
        btn_guardar.configure(text='Registrar alta')

    # Botón 2: Actualizar seleccionado
    btn_actualizar = ctk.CTkButton(
        acciones,
        text="Actualizar seleccionado",
        image=icono_actualizar,
        compound="left",
        width=190,
        height=38,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=lambda: actualizar_seleccionado(),
    )
    btn_actualizar.grid(
        row=0,
        column=2,
        padx=(6, 0),
    )

    btn_baja = None
    if solo_rrhh:
        btn_baja = ctk.CTkButton(
            acciones, text="Dar de baja", width=145, height=38,
            fg_color="#C52C35", hover_color="#9A1F27", font=BUTTON_FONT,
            command=lambda: dar_de_baja_seleccionado(), state="disabled",
        )
        btn_baja.grid(row=0, column=3, padx=(10, 0))
        acciones.grid_columnconfigure(3, weight=0)
        acciones.grid_columnconfigure(4, weight=1)

    estado_laboral = None
    if solo_rrhh:
        estado_laboral = ctk.CTkLabel(
            panel_formulario,
            text="Selecciona un empleado o pulsa Registrar alta.",
            text_color=TEXT_SECONDARY, font=TEXT_SM, anchor="w",
        )
        estado_laboral.pack(fill="x", padx=12, pady=(0, 7))

    def puede_baja_actual():
        seleccionado = estado.get('seleccionado')
        if not solo_rrhh or not seleccionado or seleccionado.get('usu_activo') is not True:
            return False
        if int(seleccionado.get('usu_tipo') or 0) in (1, 10):
            return False
        return str(seleccionado.get('id_usuario')) != str(usuario_activo.get('id_usuario'))

    def estado_empleado_label(usuario):
        if usuario.get('usu_activo') is not True:
            return 'BAJA'
        return 'ACTIVO' if usuario.get('usu_acceso_habilitado') is True else 'ALTA PENDIENTE'

    def bloquear_formulario():
        """Bloquea todos los campos para evitar ediciones accidentales."""
        for entry in estado["entradas"].values():
            entry.configure(state="disabled")

        estado["modo"] = "lectura"
        btn_guardar.configure(text='Registrar alta' if solo_rrhh else 'Guardar nuevo')
        btn_actualizar.configure(text="Actualizar seleccionado")
        if solo_rrhh:
            btn_baja.configure(state='normal' if puede_baja_actual() else 'disabled')


    def desbloquear_formulario(modo):
        """Desbloquea campos únicamente cuando se va a crear o actualizar."""
        estado["modo"] = modo

        for campo, entry in estado["entradas"].items():
            autorizado = not solo_rrhh or (
                (modo == 'editar' and campo in CAMPOS_RRHH)
                or (modo == 'nuevo' and (campo == 'usu_nickname' or campo in CAMPOS_RRHH))
            )
            entry.configure(state='normal' if autorizado else 'disabled')

        if solo_rrhh:
            btn_baja.configure(state='disabled')
        if modo == "nuevo":
            btn_guardar.configure(text="✓ Confirmar alta" if solo_rrhh else "✓ Confirmar guardado")
            btn_actualizar.configure(text="Actualizar seleccionado")

        elif modo == "editar":
            btn_guardar.configure(text='Registrar alta' if solo_rrhh else 'Guardar nuevo')
            btn_actualizar.configure(text="✓ Confirmar actualización")

    def datos_formulario():
        datos = {
            campo: variable.get().strip()
            for campo, variable in estado["variables"].items()
        }
        datos["confirmar_password"] = datos.get("usu_password", "")
        return datos

    def limpiar_formulario():
        estado["seleccionado"] = None
        for variable in estado["variables"].values():
            variable.set("")
        if solo_rrhh:
            estado["variables"]["usu_tipo"].set("4")
            estado_laboral.configure(text="Nueva alta · Rol inicial 4 (Operador) · Acceso pendiente del Administrador")

    def cargar_en_formulario(usuario):
        estado["seleccionado"] = usuario

        for campo, variable in estado["variables"].items():
            if campo == "usu_password":
                variable.set("")
            else:
                variable.set(str(usuario.get(campo, "") or ""))

        bloquear_formulario()
        if solo_rrhh:
            estado_laboral.configure(text=f"Estado laboral: {estado_empleado_label(usuario)}")

    def crear_item_resultado(usuario, texto):
        """
        Crea un resultado alineado a la izquierda.
        """

        item = ctk.CTkFrame(
            panel_resultados,
            fg_color="transparent",
            corner_radius=10,
        )
        item.pack(fill="x", padx=6, pady=2)

        label = ctk.CTkLabel(
            item,
            text=texto,
            anchor="w",
            justify="left",
            font=TEXT_SM,
            text_color=TEXT_PRIMARY,
            wraplength=320,
        )
        label.pack(fill="x", padx=5, pady=4, anchor="w")

        item.bind(
            "<Button-1>",
            lambda _event, seleccionado=usuario: cargar_en_formulario(seleccionado),
        )
        label.bind(
            "<Button-1>",
            lambda _event, seleccionado=usuario: cargar_en_formulario(seleccionado),
        )

    def pintar_resultados():
        lbl_resultados.configure(
            text=f"Resultados ({len(estado['resultados'])})"
        )

        tabla_resultados.set_rows(
            estado["resultados"],
            value_factory=lambda usuario: (
                usuario.get("usu_nickname", "-"),
                f"{usuario.get('usu_nombre', '')} "
                f"{usuario.get('usu_apellido', '')}".strip(),
                usuario.get("usu_tipo", "-"),
            ) if not solo_rrhh else (
                usuario.get('usu_nickname', '-'),
                f"{usuario.get('usu_nombre', '')} {usuario.get('usu_apellido', '')}".strip(),
                usuario.get('usu_tipo', '-'),
                estado_empleado_label(usuario),
            ),
        )

    def cargar_resultados(termino=""):
        termino = (termino or "").strip()

        if not termino:
            estado["resultados"] = []
            pintar_resultados()
            messagebox.showwarning(
                "Búsqueda requerida",
                "Ingresa un dato para buscar usuarios.",
            )
            return

        try:
            if solo_rrhh:
                clave = solicitar_clave_rrhh('consultar expedientes')
                if not clave:
                    return
                estado["resultados"] = buscar_usuarios_rrhh(termino, clave)
            else:
                estado["resultados"] = buscar_usuarios(termino)

        except UsuarioServiceError as error:
            estado["resultados"] = []
            pintar_resultados()
            messagebox.showerror(
                "Error al consultar usuarios",
                str(error),
            )
            return

        pintar_resultados()

        if not estado["resultados"]:
            messagebox.showinfo(
                "Sin coincidencias",
                "No se encontraron usuarios que coincidan con la búsqueda.",
            )

    def guardar_nuevo():
        if estado.get("modo") != "nuevo":
            limpiar_formulario()
            desbloquear_formulario("nuevo")
            return

        if solo_rrhh:
            if not messagebox.askyesno('Confirmar alta laboral',
                '¿Registrar este expediente como nuevo empleado?\n\n'
                'La cuenta NO podrá iniciar sesión hasta que el Administrador configure sus credenciales.'):
                return
            motivo = simpledialog.askstring('Motivo de alta',
                'Describe el motivo del alta (mínimo 8 caracteres):', parent=app)
            if motivo is None:
                return
            clave = solicitar_clave_rrhh('registrar un alta laboral')
            if not clave:
                return
            datos = datos_formulario()
            exito, mensaje, _ = alta_usuario_rrhh(datos, clave, motivo)
        else:
            exito, mensaje, _ = crear_usuario_admin(datos_formulario())

        if exito:
            messagebox.showinfo('Usuarios', mensaje)
            termino = datos_formulario().get('usu_nickname') if solo_rrhh else var_busqueda.get()
            limpiar_formulario()
            bloquear_formulario()
            if solo_rrhh:
                var_busqueda.set(termino)
            cargar_resultados(termino)
        else:
            messagebox.showerror("Usuarios", mensaje)

    def dar_de_baja_seleccionado():
        if not puede_baja_actual():
            messagebox.showwarning('Baja restringida',
                'Selecciona un empleado activo que no sea Administrador ni Recursos Humanos.')
            return
        empleado = estado['seleccionado']
        nombre = f"{empleado.get('usu_nombre','')} {empleado.get('usu_apellido','')}".strip()
        if not messagebox.askyesno('Confirmar baja laboral',
            f"¿Dar de baja a {nombre}?\n\n"
            'Se conservarán su expediente y todos los registros históricos. '
            'La contraseña actual quedará invalidada. La operación requiere confirmación.'):
            return
        motivo = simpledialog.askstring('Motivo de baja laboral',
            'Describe el motivo de baja (mínimo 8 caracteres):', parent=app)
        if motivo is None:
            return
        clave = solicitar_clave_rrhh('registrar la baja laboral')
        if not clave:
            return
        exito, mensaje, _ = baja_usuario_rrhh(empleado, clave, motivo)
        if exito:
            messagebox.showinfo('Recursos Humanos', mensaje)
            limpiar_formulario()
            bloquear_formulario()
            cargar_resultados(var_busqueda.get())
        else:
            messagebox.showerror('Recursos Humanos', mensaje)

    def actualizar_seleccionado():
        seleccionado = estado.get("seleccionado")

        if not seleccionado:
            messagebox.showwarning(
                "Usuarios",
                "Selecciona un usuario de la lista.",
            )
            return

        if estado.get("modo") != "editar":
            desbloquear_formulario("editar")
            return

        confirmar = messagebox.askyesno(
            "Confirmar actualización",
            "¿Estás seguro de modificar los datos de este usuario en la base de datos?"
        )

        if not confirmar:
            return

        if solo_rrhh:
            motivo = simpledialog.askstring('Motivo de actualización',
                'Describe el motivo de la actualización (mínimo 8 caracteres):', parent=app)
            if motivo is None:
                return
            clave = solicitar_clave_rrhh('guardar cambios en el expediente')
            if not clave:
                return
            exito, mensaje, _ = actualizar_usuario_rrhh(
                seleccionado.get('id_usuario'), datos_formulario(),
                seleccionado, clave, motivo,
            )
        else:
            exito, mensaje, _ = actualizar_usuario_admin(
                seleccionado.get("id_usuario"), datos_formulario(),
            )

        if exito:
            messagebox.showinfo("Usuarios", mensaje)
            bloquear_formulario()
            cargar_resultados(var_busqueda.get())
        else:
            messagebox.showerror("Usuarios", mensaje)

    entry_busqueda.bind(
        "<Return>",
        lambda _event: cargar_resultados(var_busqueda.get()),
    )

    bloquear_formulario()
    pintar_resultados()
