"""
=========================================================
MÓDULO: views/mi_bitacora_view.py
DESCRIPCIÓN:
Vista personal del usuario en sesión.

Nuevo comportamiento:
- La sección se muestra como "Mi Usuario".
- Presenta datos generales del usuario en modo solo lectura.
- Permite cambio de contraseña de la cuenta activa.
- Mantiene consulta de movimientos personales únicamente bajo búsqueda,
  sin cargar registros al abrir la pantalla.
=========================================================
"""

import customtkinter as ctk
from ui.form_fields import AxiaEntry, AxiaTextbox
from tkinter import messagebox

from core.date_utils import fecha_para_vista
from app_context import obtener_usuario_actual
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY, SECONDARY, BUTTON_HOVER
from ui.fonts import TITLE_MD, TEXT_MD, TEXT_SM, BUTTON_FONT, FONT_FAMILY
from services.movimientos_service import buscar_movimientos_usuario_actual
from services.export_service import exportar_registros_dialogo
from ui.detail_popup import mostrar_detalle_registro
from services.usuarios_service import obtener_usuario_por_id, cambiar_password_usuario_actual


CAMPOS_MOVIMIENTOS = [
    ("fecha_hora", "Fecha"),
    ("modulo", "Módulo"),
    ("accion", "Acción"),
    ("descripcion", "Descripción"),
    ("equipo", "Equipo"),
    ("ip_local", "IP"),
]

CAMPOS_OCULTOS_USUARIO = {
    "usu_password",
    "password",
    "confirmar_password",
}

ORDEN_CAMPOS_USUARIO = [
    "id_usuario",
    "usu_nickname",
    "usu_nombre",
    "usu_apellido",
    "usu_tipo",
    "usu_depto",
    "usu_puesto",
    "usu_correo",
    "usu_telefono",
    "usu_rfc",
    "usu_curp",
    "usu_imss",
    "usu_ine",
    "usu_fechanac",
    "usu_calle",
    "usu_numero",
    "usu_colonia",
    "usu_municipio",
    "usu_estado",
    "usu_cp",
    "usu_regimen",
    "fecha_registro",
    "fecha_actualizacion",
]

ETIQUETAS_USUARIO = {
    "id_usuario": "🆔 ID Usuario",
    "usu_nickname": "👤 Usuario",
    "usu_nombre": "🪪 Nombre",
    "usu_apellido": "🪪 Apellido",
    "usu_tipo": "🔐 Tipo/Rol",
    "usu_depto": "🏢 Departamento",
    "usu_puesto": "💼 Puesto",
    "usu_correo": "✉️ Correo electrónico de empresa",
    "usu_telefono": "📞 Teléfono",
    "usu_rfc": "🏛️ RFC",
    "usu_curp": "🧾 CURP",
    "usu_imss": "🏥 IMSS",
    "usu_ine": "🪪 INE",
    "usu_fechanac": "📅 Fecha nacimiento",
    "usu_calle": "🏠 Calle",
    "usu_numero": "# Número",
    "usu_colonia": "📍 Colonia",
    "usu_municipio": "📍 Municipio",
    "usu_estado": "📍 Estado",
    "usu_cp": "📮 C.P.",
    "usu_regimen": "📄 Régimen",
    "fecha_registro": "🕒 Fecha registro",
    "fecha_actualizacion": "🕒 Última actualización",
}


def _valor_visible(valor):
    if valor in (None, ""):
        return "No registrado"
    return str(valor)



def _normalizar_valor_usuario(campo, valor):
    """Convierte valores técnicos a texto legible para Mi Usuario."""
    if campo == "usu_tipo":
        mapa = {1: "Administrador", 2: "Jefe de Operaciones", 3: "Supervisor", 4: "Operador", 5: "Administrativo", 6: "Especial", "1": "Administrador", "2": "Jefe de Operaciones", "3": "Supervisor", "4": "Operador", "5": "Administrativo", "6": "Especial"}
        return mapa.get(valor, _valor_visible(valor))
    return _valor_visible(fecha_para_vista(campo, valor))

def _campos_usuario_ordenados(usuario):
    usuario = usuario or {}
    agregados = set()
    campos = []

    for campo in ORDEN_CAMPOS_USUARIO:
        if campo in usuario and campo not in CAMPOS_OCULTOS_USUARIO:
            campos.append((campo, usuario.get(campo)))
            agregados.add(campo)

    for campo in sorted(usuario.keys()):
        if campo not in agregados and campo not in CAMPOS_OCULTOS_USUARIO:
            campos.append((campo, usuario.get(campo)))

    return campos



def _columnas_perfil_para_ancho(ancho):
    """Distribución fluida sin cortar las fichas al estrechar la ventana.

    En escritorio ancho caben siete datos por fila; en tamaños intermedios,
    seis. Se mantiene un mínimo razonable de ancho por dato.
    """
    if ancho >= 1350:
        return 7
    if ancho >= 1120:
        return 6
    if ancho >= 930:
        return 5
    if ancho >= 740:
        return 4
    if ancho >= 550:
        return 3
    return 2


def _alto_texto_perfil(texto, ancho, *, etiqueta=False):
    """Reserva altura para las etiquetas largas sin recortar su contenido."""
    from math import ceil

    fuente_aproximada = 6.0 if etiqueta else 6.5
    lineas = max(1, ceil(len(str(texto)) * fuente_aproximada / max(ancho, 1)))
    return (17 if etiqueta else 19) * lineas + 2


def mostrar_mi_usuario(parent, app):
    """Renderiza la sección Mi Usuario."""

    for widget in parent.winfo_children():
        widget.destroy()

    usuario_ctx = obtener_usuario_actual()
    usuario = obtener_usuario_por_id(usuario_ctx.get("id_usuario")) or usuario_ctx

    estado = {"movimientos": []}

    contenedor = ctk.CTkScrollableFrame(parent, fg_color="transparent", corner_radius=0)
    contenedor.pack(fill="both", expand=True, padx=9, pady=3)

    # =================================================
    # DATOS GENERALES
    # =================================================
    card_datos = ctk.CTkFrame(contenedor, fg_color=WHITE, corner_radius=14)
    card_datos.pack(fill="x", pady=(0, 5))

    titulo_perfil = ctk.CTkLabel(
        card_datos,
        text="👤 Mi Usuario",
        font=TITLE_MD,
        text_color=TEXT_PRIMARY,
        anchor="w",
    )
    titulo_perfil.grid(row=0, column=0, columnspan=7, sticky="ew", padx=7, pady=(4, 0))

    subtitulo_perfil = ctk.CTkLabel(
        card_datos,
        text="Información de tu cuenta. Estos datos son de solo consulta.",
        font=TEXT_SM,
        text_color=TEXT_SECONDARY,
        anchor="w",
    )
    subtitulo_perfil.grid(row=1, column=0, columnspan=7, sticky="ew", padx=7, pady=(0, 2))

    # Las fichas se crean una única vez; al cambiar el tamaño de la ventana
    # solo se reordenan. No se alteran datos, consultas ni permisos.
    fichas = []
    for campo, valor in _campos_usuario_ordenados(usuario):
        etiqueta = ETIQUETAS_USUARIO.get(campo, campo.replace("_", " ").title())
        texto_valor = _normalizar_valor_usuario(campo, valor)
        bloque = ctk.CTkFrame(card_datos, fg_color="#F8FAFC", corner_radius=7,
                              border_width=1, border_color="#DFE7F1")
        bloque.grid_columnconfigure(0, weight=1)

        titulo_campo = ctk.CTkLabel(
            bloque, text=etiqueta, font=(FONT_FAMILY, 10),
            text_color=TEXT_SECONDARY, anchor="w", justify="left",
            height=19, wraplength=180,
        )
        titulo_campo.grid(row=0, column=0, sticky="ew", padx=4, pady=(3, 0))

        valor_campo = ctk.CTkLabel(
            bloque, text=texto_valor, font=(FONT_FAMILY, 11),
            text_color=TEXT_PRIMARY, anchor="w", justify="left",
            height=21, wraplength=180,
        )
        valor_campo.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 3))
        fichas.append((bloque, titulo_campo, valor_campo, etiqueta, texto_valor))

    estado_cuadricula = {"columnas": None, "ancho_texto": None}

    def acomodar_fichas(ancho_disponible):
        columnas = _columnas_perfil_para_ancho(ancho_disponible)
        # Se reserva espacio para bordes y los márgenes compactos de cada ficha.
        ancho_texto = max(88, int((ancho_disponible - 16) / columnas) - 18)
        if (estado_cuadricula["columnas"] == columnas and
                estado_cuadricula["ancho_texto"] is not None and
                abs(estado_cuadricula["ancho_texto"] - ancho_texto) < 8):
            return

        estado_cuadricula.update(columnas=columnas, ancho_texto=ancho_texto)
        for indice in range(7):
            card_datos.grid_columnconfigure(indice, weight=0, uniform="")
        card_datos.grid_columnconfigure(tuple(range(columnas)), weight=1, uniform="perfil_usuario")
        titulo_perfil.grid_configure(columnspan=columnas)
        subtitulo_perfil.grid_configure(columnspan=columnas)

        for indice, (bloque, titulo_campo, valor_campo, etiqueta, texto_valor) in enumerate(fichas):
            bloque.grid(row=2 + indice // columnas, column=indice % columnas,
                        sticky="nsew", padx=3, pady=2)
            titulo_campo.configure(
                wraplength=ancho_texto,
                height=_alto_texto_perfil(etiqueta, ancho_texto, etiqueta=True),
            )
            valor_campo.configure(
                wraplength=ancho_texto,
                height=_alto_texto_perfil(texto_valor, ancho_texto),
            )

    # La vista se adapta al tamaño real después del primer dibujo y al
    # maximizar/restaurar, sin reconstruir fichas ni ejecutar consultas.
    acomodar_fichas(1440)
    card_datos.bind("<Configure>", lambda evento: acomodar_fichas(evento.width), add="+")

    # =================================================
    # CAMBIO DE CONTRASEÑA
    # =================================================
    card_password = ctk.CTkFrame(contenedor, fg_color=WHITE, corner_radius=14)
    card_password.pack(fill="x", pady=(0, 8))
    card_password.grid_columnconfigure((0, 1, 2), weight=1, uniform="pwd")

    ctk.CTkLabel(
        card_password,
        text="🔐 Cambiar contraseña",
        font=TITLE_MD,
        text_color=TEXT_PRIMARY,
        anchor="w"
    ).grid(row=0, column=0, columnspan=3, sticky="ew", padx=8, pady=(6, 1))

    var_actual = ctk.StringVar()
    var_nueva = ctk.StringVar()
    var_confirmar = ctk.StringVar()

    campos_password = [
        ("Contraseña actual", var_actual),
        ("Nueva contraseña", var_nueva),
        ("Confirmar contraseña", var_confirmar),
    ]

    for columna, (etiqueta, variable) in enumerate(campos_password):
        wrapper = ctk.CTkFrame(card_password, fg_color="transparent")
        wrapper.grid(row=1, column=columna, sticky="ew", padx=8 if columna == 0 else (0, 16), pady=(3, 5))
        wrapper.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(wrapper, text=etiqueta, font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w").grid(row=0, column=0, sticky="w")
        AxiaEntry(wrapper, textvariable=variable, show="*", height=32).grid(row=1, column=0, sticky="ew", pady=(2, 0))

    def cambiar_password():
        ok, mensaje = cambiar_password_usuario_actual(
            password_actual=var_actual.get(),
            password_nuevo=var_nueva.get(),
            password_confirmacion=var_confirmar.get(),
        )
        if ok:
            var_actual.set("")
            var_nueva.set("")
            var_confirmar.set("")
            messagebox.showinfo("Contraseña actualizada", mensaje)
        else:
            messagebox.showerror("No fue posible actualizar", mensaje)

    ctk.CTkButton(
        card_password,
        text="💾 Actualizar contraseña",
        width=210,
        height=34,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=cambiar_password,
    ).grid(row=2, column=0, columnspan=3, sticky="e", padx=8, pady=(0, 6))

    # =================================================
    # MOVIMIENTOS PERSONALES BAJO BÚSQUEDA
    # =================================================
    card_mov = ctk.CTkFrame(contenedor, fg_color=WHITE, corner_radius=14)
    card_mov.pack(fill="both", expand=True)
    card_mov.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        card_mov,
        text="🕒 Mis movimientos",
        font=TITLE_MD,
        text_color=TEXT_PRIMARY,
        anchor="w"
    ).grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 1))

    ctk.CTkLabel(
        card_mov,
        text="No se cargan movimientos automáticamente. Ingresa un dato para buscar.",
        font=TEXT_SM,
        text_color=TEXT_SECONDARY,
        anchor="w"
    ).grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))

    barra = ctk.CTkFrame(card_mov, fg_color="transparent")
    barra.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 4))
    barra.grid_columnconfigure(0, weight=1)

    var_busqueda = ctk.StringVar()
    entry_busqueda = AxiaEntry(
        barra,
        textvariable=var_busqueda,
        placeholder_text="Buscar por fecha, módulo, acción, descripción, equipo o IP...",
        height=34,
    )
    entry_busqueda.grid(row=0, column=0, sticky="ew", padx=(0, 5))

    panel = ctk.CTkFrame(card_mov, fg_color="transparent")
    panel.grid(row=3, column=0, sticky="nsew", padx=0, pady=(0, 7))

    def limpiar_panel(mensaje="Ingresa un criterio de búsqueda para consultar tus movimientos."):
        for widget in panel.winfo_children():
            widget.destroy()
        ctk.CTkLabel(panel, text=mensaje, font=TEXT_SM, text_color=TEXT_SECONDARY).pack(anchor="w", padx=12, pady=9)

    def pintar(registros):
        for widget in panel.winfo_children():
            widget.destroy()

        if not registros:
            limpiar_panel("No se encontraron movimientos con ese criterio.")
            return

        encabezado = ctk.CTkFrame(panel, fg_color="#E2E8F0", corner_radius=10)
        encabezado.pack(fill="x", padx=9, pady=(3, 2))
        for columna, (_campo, titulo) in enumerate(CAMPOS_MOVIMIENTOS):
            peso = 2 if titulo == "Descripción" else 1
            encabezado.grid_columnconfigure(columna, weight=peso, uniform="mi_usuario_mov")
            ctk.CTkLabel(encabezado, text=titulo, font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w").grid(row=0, column=columna, sticky="ew", padx=4, pady=3)
        encabezado.grid_columnconfigure(len(CAMPOS_MOVIMIENTOS), weight=0)
        ctk.CTkLabel(encabezado, text="Ver", font=TEXT_SM, text_color=TEXT_PRIMARY).grid(row=0, column=len(CAMPOS_MOVIMIENTOS), padx=4, pady=3)

        for movimiento in registros[:100]:
            fila = ctk.CTkFrame(panel, fg_color="transparent", corner_radius=8)
            fila.pack(fill="x", padx=9, pady=1)
            for columna, (campo, _titulo) in enumerate(CAMPOS_MOVIMIENTOS):
                peso = 2 if campo == "descripcion" else 1
                fila.grid_columnconfigure(columna, weight=peso, uniform="mi_usuario_mov")
                valor = str(fecha_para_vista(campo, movimiento.get(campo, "")) or "-")
                ctk.CTkLabel(
                    fila,
                    text=valor,
                    font=TEXT_SM,
                    text_color=TEXT_SECONDARY,
                    anchor="w",
                    justify="left",
                    wraplength=260 if campo == "descripcion" else 140,
                ).grid(row=0, column=columna, sticky="ew", padx=4, pady=2)

            ctk.CTkButton(
                fila,
                text="👁",
                width=34,
                height=28,
                fg_color="#64748B",
                hover_color="#475569",
                command=lambda r=movimiento: mostrar_detalle_registro(parent, "Movimiento personal", r),
            ).grid(row=0, column=len(CAMPOS_MOVIMIENTOS), padx=4, pady=2)

    def buscar():
        termino = var_busqueda.get().strip()
        if not termino:
            messagebox.showwarning("Búsqueda requerida", "Ingresa un dato para consultar tus movimientos.")
            limpiar_panel()
            return
        registros = buscar_movimientos_usuario_actual(termino=termino, limite=100)
        estado["movimientos"] = registros or []
        pintar(estado["movimientos"])

    def limpiar():
        var_busqueda.set("")
        estado["movimientos"] = []
        limpiar_panel()

    ctk.CTkButton(barra, text="🔎 Buscar", width=120, height=34, fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=buscar).grid(row=0, column=1, padx=(0, 4))
    ctk.CTkButton(barra, text="↻ Limpiar", width=120, height=34, fg_color="#64748B", hover_color="#475569", font=BUTTON_FONT, command=limpiar).grid(row=0, column=2, padx=(0, 4))
    ctk.CTkButton(barra, text="⬇ Exportar", width=120, height=34, fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=lambda: exportar_registros_dialogo(estado.get("movimientos", []), "AXIA_mis_movimientos")).grid(row=0, column=3)

    entry_busqueda.bind("<Return>", lambda _event: buscar())
    # Sin autofocus: el usuario decide cuándo entrar al buscador.
    limpiar_panel()


# Compatibilidad temporal con el nombre anterior.
def mostrar_mi_bitacora(parent, app):
    mostrar_mi_usuario(parent, app)
