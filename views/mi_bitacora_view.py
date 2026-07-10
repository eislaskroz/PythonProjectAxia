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
from tkinter import messagebox

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
    "usu_correo": "✉️ Correo",
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
        mapa = {1: "Administrador", 2: "Supervisor", 3: "Usuario operativo", "1": "Administrador", "2": "Supervisor", "3": "Usuario operativo"}
        return mapa.get(valor, _valor_visible(valor))
    return _valor_visible(valor)

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


def mostrar_mi_usuario(parent, app):
    """Renderiza la sección Mi Usuario."""

    for widget in parent.winfo_children():
        widget.destroy()

    usuario_ctx = obtener_usuario_actual()
    usuario = obtener_usuario_por_id(usuario_ctx.get("id_usuario")) or usuario_ctx

    estado = {"movimientos": []}

    contenedor = ctk.CTkScrollableFrame(parent, fg_color="transparent", corner_radius=0)
    contenedor.pack(fill="both", expand=True, padx=18, pady=6)

    # =================================================
    # DATOS GENERALES
    # =================================================
    card_datos = ctk.CTkFrame(contenedor, fg_color=WHITE, corner_radius=14)
    card_datos.pack(fill="x", pady=(0, 12))
    columnas_datos = 4
    card_datos.grid_columnconfigure(tuple(range(columnas_datos)), weight=1, uniform="datos_usuario")

    ctk.CTkLabel(
        card_datos,
        text="👤 Mi Usuario",
        font=TITLE_MD,
        text_color=TEXT_PRIMARY,
        anchor="w"
    ).grid(row=0, column=0, columnspan=columnas_datos, sticky="ew", padx=16, pady=(12, 2))

    ctk.CTkLabel(
        card_datos,
        text="Información de tu cuenta. Estos datos son de solo consulta.",
        font=TEXT_SM,
        text_color=TEXT_SECONDARY,
        anchor="w"
    ).grid(row=1, column=0, columnspan=columnas_datos, sticky="ew", padx=16, pady=(0, 8))

    fila = 2
    columna = 0
    for campo, valor in _campos_usuario_ordenados(usuario):
        etiqueta = ETIQUETAS_USUARIO.get(campo, campo.replace("_", " ").title())
        bloque = ctk.CTkFrame(card_datos, fg_color="#F8FAFC", corner_radius=10)
        bloque.grid(
            row=fila,
            column=columna,
            sticky="ew",
            padx=(16 if columna == 0 else 6, 16 if columna == columnas_datos - 1 else 6),
            pady=4,
        )
        bloque.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            bloque,
            text=etiqueta,
            font=(FONT_FAMILY, 11),
            text_color=TEXT_SECONDARY,
            anchor="w"
        ).grid(row=0, column=0, sticky="ew", padx=10, pady=(6, 0))

        ctk.CTkLabel(
            bloque,
            text=_normalizar_valor_usuario(campo, valor),
            font=(FONT_FAMILY, 12),
            text_color=TEXT_PRIMARY,
            anchor="w",
            wraplength=220
        ).grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

        columna += 1
        if columna >= columnas_datos:
            columna = 0
            fila += 1

    # =================================================
    # CAMBIO DE CONTRASEÑA
    # =================================================
    card_password = ctk.CTkFrame(contenedor, fg_color=WHITE, corner_radius=14)
    card_password.pack(fill="x", pady=(0, 16))
    card_password.grid_columnconfigure((0, 1, 2), weight=1, uniform="pwd")

    ctk.CTkLabel(
        card_password,
        text="🔐 Cambiar contraseña",
        font=TITLE_MD,
        text_color=TEXT_PRIMARY,
        anchor="w"
    ).grid(row=0, column=0, columnspan=3, sticky="ew", padx=16, pady=(12, 2))

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
        wrapper.grid(row=1, column=columna, sticky="ew", padx=16 if columna == 0 else (0, 16), pady=(6, 10))
        wrapper.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(wrapper, text=etiqueta, font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkEntry(wrapper, textvariable=variable, show="*", height=32).grid(row=1, column=0, sticky="ew", pady=(4, 0))

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
    ).grid(row=2, column=0, columnspan=3, sticky="e", padx=16, pady=(0, 12))

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
    ).grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 2))

    ctk.CTkLabel(
        card_mov,
        text="No se cargan movimientos automáticamente. Ingresa un dato para buscar.",
        font=TEXT_SM,
        text_color=TEXT_SECONDARY,
        anchor="w"
    ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

    barra = ctk.CTkFrame(card_mov, fg_color="transparent")
    barra.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
    barra.grid_columnconfigure(0, weight=1)

    var_busqueda = ctk.StringVar()
    entry_busqueda = ctk.CTkEntry(
        barra,
        textvariable=var_busqueda,
        placeholder_text="Buscar por fecha, módulo, acción, descripción, equipo o IP...",
        height=34,
    )
    entry_busqueda.grid(row=0, column=0, sticky="ew", padx=(0, 10))

    panel = ctk.CTkFrame(card_mov, fg_color="transparent")
    panel.grid(row=3, column=0, sticky="nsew", padx=0, pady=(0, 14))

    def limpiar_panel(mensaje="Ingresa un criterio de búsqueda para consultar tus movimientos."):
        for widget in panel.winfo_children():
            widget.destroy()
        ctk.CTkLabel(panel, text=mensaje, font=TEXT_SM, text_color=TEXT_SECONDARY).pack(anchor="w", padx=24, pady=18)

    def pintar(registros):
        for widget in panel.winfo_children():
            widget.destroy()

        if not registros:
            limpiar_panel("No se encontraron movimientos con ese criterio.")
            return

        encabezado = ctk.CTkFrame(panel, fg_color="#E2E8F0", corner_radius=10)
        encabezado.pack(fill="x", padx=18, pady=(6, 4))
        for columna, (_campo, titulo) in enumerate(CAMPOS_MOVIMIENTOS):
            peso = 2 if titulo == "Descripción" else 1
            encabezado.grid_columnconfigure(columna, weight=peso, uniform="mi_usuario_mov")
            ctk.CTkLabel(encabezado, text=titulo, font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w").grid(row=0, column=columna, sticky="ew", padx=8, pady=6)
        encabezado.grid_columnconfigure(len(CAMPOS_MOVIMIENTOS), weight=0)
        ctk.CTkLabel(encabezado, text="Ver", font=TEXT_SM, text_color=TEXT_PRIMARY).grid(row=0, column=len(CAMPOS_MOVIMIENTOS), padx=8, pady=6)

        for movimiento in registros[:100]:
            fila = ctk.CTkFrame(panel, fg_color="transparent", corner_radius=8)
            fila.pack(fill="x", padx=18, pady=2)
            for columna, (campo, _titulo) in enumerate(CAMPOS_MOVIMIENTOS):
                peso = 2 if campo == "descripcion" else 1
                fila.grid_columnconfigure(columna, weight=peso, uniform="mi_usuario_mov")
                valor = str(movimiento.get(campo, "") or "-")
                ctk.CTkLabel(
                    fila,
                    text=valor,
                    font=TEXT_SM,
                    text_color=TEXT_SECONDARY,
                    anchor="w",
                    justify="left",
                    wraplength=260 if campo == "descripcion" else 140,
                ).grid(row=0, column=columna, sticky="ew", padx=8, pady=5)

            ctk.CTkButton(
                fila,
                text="👁",
                width=34,
                height=28,
                fg_color="#64748B",
                hover_color="#475569",
                command=lambda r=movimiento: mostrar_detalle_registro(parent, "Movimiento personal", r),
            ).grid(row=0, column=len(CAMPOS_MOVIMIENTOS), padx=8, pady=3)

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

    ctk.CTkButton(barra, text="🔎 Buscar", width=120, height=34, fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=buscar).grid(row=0, column=1, padx=(0, 8))
    ctk.CTkButton(barra, text="↻ Limpiar", width=120, height=34, fg_color="#64748B", hover_color="#475569", font=BUTTON_FONT, command=limpiar).grid(row=0, column=2, padx=(0, 8))
    ctk.CTkButton(barra, text="⬇ Exportar", width=120, height=34, fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=lambda: exportar_registros_dialogo(estado.get("movimientos", []), "AXIA_mis_movimientos")).grid(row=0, column=3)

    entry_busqueda.bind("<Return>", lambda _event: buscar())
    entry_busqueda.focus_set()
    limpiar_panel()


# Compatibilidad temporal con el nombre anterior.
def mostrar_mi_bitacora(parent, app):
    mostrar_mi_usuario(parent, app)
