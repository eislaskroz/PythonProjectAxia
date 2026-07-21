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


COLUMNAS = {
    "movimientos": [
        ("fecha_hora", "Fecha"), ("usuario", "Usuario"), ("modulo", "Módulo"),
        ("accion", "Acción"), ("descripcion", "Descripción"),
        ("equipo", "Equipo"), ("ip_local", "IP local"),
    ],
    "accesos": [
        ("fecha_hora", "Fecha"), ("usu_nickname", "Usuario"), ("estatus", "Estado"),
        ("descripcion", "Descripción"), ("nombre_equipo", "Equipo"),
        ("direccion_ip", "IP local"), ("ciudad", "Ubicación"),
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
        text="La ubicación geográfica solo aparece cuando AXIA_ENABLE_IP_GEOLOCATION=1.",
        font=TEXT_SM, text_color=TEXT_SECONDARY,
    )
    aviso.pack(side="right", padx=8)

    panel = ctk.CTkScrollableFrame(contenedor, fg_color=WHITE, corner_radius=16)
    panel.pack(fill="both", expand=True)

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
        for widget in panel.winfo_children():
            widget.destroy()
        actualizar_metricas(registros)
        nombre = "accesos" if estado["tipo"] == "accesos" else "movimientos"
        ctk.CTkLabel(
            panel, text=f"{nombre.capitalize()} encontrados ({len(registros)})",
            font=("Montserrat", 16, "bold"), text_color=TEXT_PRIMARY, anchor="w",
        ).pack(anchor="w", padx=9, pady=(8, 4))
        if not registros:
            ctk.CTkLabel(
                panel, text="Ingresa al menos un filtro y presiona Buscar.",
                font=TEXT_SM, text_color=TEXT_SECONDARY, anchor="w",
            ).pack(anchor="w", padx=9, pady=4)
            return

        columnas = COLUMNAS[estado["tipo"]]
        header = ctk.CTkFrame(panel, fg_color="#F4F7FB", corner_radius=10)
        header.pack(fill="x", padx=9, pady=(0, 2))
        for columna, (campo, etiqueta) in enumerate(columnas):
            peso = 2 if campo == "descripcion" else 1
            header.grid_columnconfigure(columna, weight=peso, uniform="auditoria")
            ctk.CTkLabel(header, text=etiqueta, font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w").grid(
                row=0, column=columna, sticky="ew", padx=4, pady=4
            )

        for registro in registros[:100]:
            fila = ctk.CTkFrame(panel, fg_color="transparent")
            fila.pack(fill="x", padx=9, pady=1)
            for columna, (campo, _etiqueta) in enumerate(columnas):
                peso = 2 if campo == "descripcion" else 1
                fila.grid_columnconfigure(columna, weight=peso, uniform="auditoria")
                valor = str(registro.get(campo, "") or "-")
                if campo == "estatus":
                    valor = "✅ CORRECTO" if valor.upper() == "CORRECTO" else f"⚠ {valor}"
                if campo == "ciudad" and estado["tipo"] == "accesos":
                    partes = [registro.get("ciudad"), registro.get("region"), registro.get("pais")]
                    valor = ", ".join(str(p) for p in partes if p and p != "No disponible") or "No disponible"
                ctk.CTkLabel(
                    fila, text=valor, font=TEXT_SM, text_color=TEXT_SECONDARY, anchor="w",
                    justify="left", wraplength=260 if campo == "descripcion" else 150,
                ).grid(row=0, column=columna, sticky="ew", padx=4, pady=2)
            acciones_fila = ctk.CTkFrame(fila, fg_color="transparent")
            acciones_fila.grid(row=0, column=len(columnas), sticky="e", padx=4, pady=2)
            ctk.CTkButton(
                acciones_fila, text="👁", width=34, height=28, fg_color="#64748B",
                hover_color="#475569",
                command=lambda r=registro: mostrar_detalle_registro(parent, "Registro de auditoría", r),
            ).pack(side="left", padx=(0, 2))
            ctk.CTkButton(
                acciones_fila, text="⬇", width=34, height=28, fg_color=SECONDARY,
                hover_color=BUTTON_HOVER,
                command=lambda r=registro: exportar_registros_dialogo(r, "AXIA_registro_auditoria"),
            ).pack(side="left")

        if len(registros) > 100:
            ctk.CTkLabel(
                panel, text=f"Mostrando los 100 más recientes de {len(registros)} registros.",
                font=TEXT_SM, text_color=TEXT_SECONDARY, anchor="e",
            ).pack(anchor="e", padx=9, pady=(4, 8))

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
