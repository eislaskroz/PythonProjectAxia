"""Vista administrativa unificada de auditoría AXIA.

Permite consultar por separado:
- Movimientos funcionales dentro del sistema.
- Intentos de inicio de sesión correctos y fallidos.
"""

import customtkinter as ctk
from tkinter import messagebox

from app_context import obtener_usuario_actual
from security.permissions import puede_ver_auditoria
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY, SECONDARY, BUTTON_HOVER
from ui.fonts import TEXT_MD, TEXT_SM, BUTTON_FONT
from services.auditoria_service import (
    buscar_accesos_auditoria,
    buscar_movimientos_auditoria,
    resumen_registros,
)
from services.export_service import exportar_registros_dialogo
from ui.detail_popup import mostrar_detalle_registro
from ui.native_table import NativeTreeTable


COLUMNAS = {
    "movimientos": [
        ("fecha_hora", "Fecha"), ("usuario", "Usuario"), ("modulo", "Módulo"),
        ("accion", "Acción"), ("descripcion", "Descripción"),
        ("equipo", "Equipo"), ("ip_local", "IP local"),
        ("ciudad", "Ubicación"), ("latitud", "GPS"),
    ],
    "accesos": [
        ("fecha_hora", "Fecha"), ("usu_nickname", "Usuario"), ("estatus", "Estado"),
        ("descripcion", "Descripción"), ("nombre_equipo", "Equipo"),
        ("direccion_ip", "IP local"), ("ciudad", "Ubicación"),
        ("latitud", "GPS"),
    ],
}


def mostrar_auditoria(parent, app):
    usuario_activo = obtener_usuario_actual()
    if not puede_ver_auditoria(usuario_activo):
        messagebox.showerror("Acceso denegado", "La auditoría de accesos y movimientos está reservada al Administrador.")
        app.mostrar_vista_inicio_aco()
        return

    for widget in parent.winfo_children():
        widget.destroy()

    estado = {"tipo": "movimientos", "registros": [], "filtrados": []}

    contenedor = ctk.CTkFrame(parent, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=14, pady=4)

    encabezado = ctk.CTkFrame(contenedor, fg_color="transparent")
    encabezado.pack(fill="x", pady=(0, 5))

    ctk.CTkLabel(
        encabezado, text="Auditoría del sistema", font=("Montserrat", 19, "bold"),
        text_color=TEXT_PRIMARY,
    ).pack(side="left")

    var_tipo = ctk.StringVar(value="Movimientos del sistema")
    selector_tipo = ctk.CTkSegmentedButton(
        encabezado,
        values=["Movimientos del sistema", "Inicios de sesión"],
        variable=var_tipo,
        command=lambda _valor: cambiar_tipo(),
        selected_color=PRIMARY,
        selected_hover_color=SECONDARY,
    )
    selector_tipo.pack(side="right")

    resumen = ctk.CTkFrame(contenedor, fg_color=WHITE, corner_radius=16)
    resumen.pack(fill="x", pady=(0, 5))
    resumen.grid_columnconfigure((0, 1, 2), weight=1)
    labels_metrica = []
    for columna in range(3):
        titulo = ctk.CTkLabel(resumen, text="-", font=TEXT_SM, text_color=TEXT_SECONDARY, anchor="w")
        titulo.grid(row=0, column=columna, sticky="w", padx=9, pady=(6, 0))
        valor = ctk.CTkLabel(resumen, text="0", font=TEXT_MD, text_color=PRIMARY, anchor="w")
        valor.grid(row=1, column=columna, sticky="w", padx=9, pady=(0, 6))
        labels_metrica.append((titulo, valor))

    filtros = ctk.CTkFrame(contenedor, fg_color=WHITE, corner_radius=16)
    filtros.pack(fill="x", pady=(0, 5))
    filtros.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="filtros")

    variables = {clave: ctk.StringVar() for clave in ("fecha", "usuario", "categoria", "equipo", "ip")}
    etiquetas_filtro = {}
    campos_filtro = [
        ("fecha", "📅 Fecha"), ("usuario", "👤 Usuario"), ("categoria", "🧩 Módulo"),
        ("equipo", "💻 Equipo"), ("ip", "🌐 Dirección IP"),
    ]
    for columna, (clave, etiqueta) in enumerate(campos_filtro):
        wrapper = ctk.CTkFrame(filtros, fg_color="transparent")
        wrapper.grid(row=0, column=columna, sticky="ew", padx=5, pady=(5, 4))
        wrapper.grid_columnconfigure(0, weight=1)
        label = ctk.CTkLabel(wrapper, text=etiqueta, font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w")
        label.grid(row=0, column=0, sticky="w")
        etiquetas_filtro[clave] = label
        entry = ctk.CTkEntry(wrapper, textvariable=variables[clave], height=34)
        entry.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        entry.bind("<Return>", lambda _event: aplicar_filtros())

    acciones = ctk.CTkFrame(contenedor, fg_color="transparent")
    acciones.pack(fill="x", pady=(0, 5))
    ctk.CTkButton(
        acciones, text="🔎 Buscar", width=120, height=38, fg_color=SECONDARY,
        hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=lambda: aplicar_filtros(),
    ).pack(side="left", padx=(0, 4))
    ctk.CTkButton(
        acciones, text="↻ Limpiar filtros", width=150, height=38, fg_color="#64748B",
        hover_color="#475569", font=BUTTON_FONT, command=lambda: limpiar_filtros(),
    ).pack(side="left", padx=(0, 4))
    ctk.CTkButton(
        acciones, text="⬇ Exportar filtrados", width=170, height=38, fg_color=SECONDARY,
        hover_color=BUTTON_HOVER, font=BUTTON_FONT,
        command=lambda: exportar_registros_dialogo(
            estado.get("filtrados", []),
            "AXIA_auditoria_accesos" if estado["tipo"] == "accesos" else "AXIA_auditoria_movimientos",
        ),
    ).pack(side="left")

    aviso = ctk.CTkLabel(
        acciones,
        text="AXIA registra ubicación aproximada por IP pública en accesos y movimientos.",
        font=TEXT_SM, text_color=TEXT_SECONDARY,
    )
    aviso.pack(side="right", padx=8)

    panel = ctk.CTkFrame(contenedor, fg_color=WHITE, corner_radius=16)
    panel.pack(fill="both", expand=True)
    panel.grid_rowconfigure(1, weight=1)
    panel.grid_columnconfigure(0, weight=1)
    lbl_tabla = ctk.CTkLabel(
        panel, text="Registros encontrados (0)", font=("Montserrat", 16, "bold"),
        text_color=TEXT_PRIMARY, anchor="w",
    )
    lbl_tabla.grid(row=0, column=0, sticky="ew", padx=9, pady=(8, 4))
    tabla_auditoria = NativeTreeTable(panel, columns=(), height=18)
    tabla_auditoria.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 4))
    acciones_tabla = ctk.CTkFrame(panel, fg_color="transparent")
    acciones_tabla.grid(row=2, column=0, sticky="e", padx=8, pady=(0, 8))

    def ver_seleccionado():
        registro = tabla_auditoria.selected_payload()
        if registro:
            mostrar_detalle_registro(parent, "Registro de auditoría", registro)
        else:
            messagebox.showinfo("Selecciona un registro", "Selecciona una fila para consultar su detalle.")

    def exportar_seleccionado():
        registro = tabla_auditoria.selected_payload()
        if registro:
            exportar_registros_dialogo(registro, "AXIA_registro_auditoria")
        else:
            messagebox.showinfo("Selecciona un registro", "Selecciona una fila para exportarla.")

    ctk.CTkButton(acciones_tabla, text="👁 Ver detalle", width=120, command=ver_seleccionado).pack(side="left", padx=3)
    ctk.CTkButton(acciones_tabla, text="⬇ Exportar", width=110, command=exportar_seleccionado).pack(side="left", padx=3)

    def actualizar_metricas(registros):
        valores = resumen_registros(registros, estado["tipo"])
        titulos = ("Registros", "Usuarios", "Fallidos") if estado["tipo"] == "accesos" else ("Movimientos", "Usuarios", "Módulos")
        for indice, (titulo, valor) in enumerate(zip(titulos, valores)):
            labels_metrica[indice][0].configure(text=titulo)
            labels_metrica[indice][1].configure(text=str(valor))

    def coincide_filtros(registro):
        if estado["tipo"] == "accesos":
            valores = {
                "fecha": registro.get("fecha_hora"), "usuario": registro.get("usu_nickname"),
                "categoria": registro.get("estatus"), "equipo": registro.get("nombre_equipo"),
                "ip": registro.get("direccion_ip"),
            }
        else:
            valores = {
                "fecha": registro.get("fecha_hora"), "usuario": registro.get("usuario"),
                "categoria": f"{registro.get('modulo', '')} {registro.get('accion', '')}",
                "equipo": registro.get("equipo"), "ip": registro.get("ip_local"),
            }
        return all(
            not variables[clave].get().strip()
            or variables[clave].get().strip().lower() in str(valor or "").lower()
            for clave, valor in valores.items()
        )

    def pintar_tabla(registros):
        actualizar_metricas(registros)
        nombre = "Accesos" if estado["tipo"] == "accesos" else "Movimientos"
        lbl_tabla.configure(text=f"{nombre} encontrados ({len(registros)})")
        columnas = COLUMNAS[estado["tipo"]]
        tabla_auditoria.set_columns([
            (campo, etiqueta, 260 if campo == "descripcion" else 130)
            for campo, etiqueta in columnas
        ])

        def valores(registro):
            salida = []
            for campo, _etiqueta in columnas:
                valor = str(registro.get(campo, "") or "-")
                if campo == "estatus":
                    valor = "CORRECTO" if valor.upper() == "CORRECTO" else valor
                if campo == "ciudad":
                    partes = [registro.get("ciudad"), registro.get("region"), registro.get("pais")]
                    valor = ", ".join(str(p) for p in partes if p and p != "No disponible") or "No disponible"
                elif campo == "latitud":
                    lat = registro.get("latitud")
                    lon = registro.get("longitud")
                    if lat and lon and str(lat) != "No disponible" and str(lon) != "No disponible":
                        valor = f"{lat}, {lon}"
                    else:
                        valor = "No disponible"
                salida.append(valor)
            return salida

        tabla_auditoria.set_rows(registros[:100], value_factory=valores)

    def aplicar_filtros():
        termino = " ".join(v.get().strip() for v in variables.values() if v.get().strip()).strip()
        if not termino:
            messagebox.showwarning("Búsqueda requerida", "Ingresa al menos un filtro para consultar auditoría.")
            pintar_tabla([])
            return
        consulta = buscar_accesos_auditoria if estado["tipo"] == "accesos" else buscar_movimientos_auditoria
        registros = consulta(termino=termino, limite=200) or []
        filtrados = [r for r in registros if coincide_filtros(r)]
        estado["registros"] = registros
        estado["filtrados"] = filtrados
        pintar_tabla(filtrados)

    def limpiar_filtros():
        for variable in variables.values():
            variable.set("")
        estado["registros"] = []
        estado["filtrados"] = []
        pintar_tabla([])

    def cambiar_tipo():
        estado["tipo"] = "accesos" if var_tipo.get() == "Inicios de sesión" else "movimientos"
        etiquetas_filtro["categoria"].configure(text="🔐 Estado" if estado["tipo"] == "accesos" else "🧩 Módulo / acción")
        limpiar_filtros()

    cambiar_tipo()
