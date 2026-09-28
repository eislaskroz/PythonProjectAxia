"""Bandeja de Compras AXIA."""
from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

from app_context import obtener_usuario_actual
from core.background_tasks import run_async
from core.logger import configurar_logger
from security.permissions import puede_ver_compras, puede_convertir_cotizacion_a_orden
from services.cotizaciones_service import obtener_cotizaciones_en_compra
from services.ordenes_trabajo_service import convertir_cotizacion_a_trabajo
from services.axia_pdf_engine import AxiaPdfEngine
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY, BUTTON_HOVER
from ui.fonts import TITLE_MD, TEXT_MD, BUTTON_FONT
from ui.native_table import NativeTreeTable

logger = configurar_logger(__name__)


def _txt(reg, key):
    return str((reg or {}).get(key) or "").strip()


def _money(value):
    try:
        return f"${float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def mostrar_compras(parent, app=None):
    usuario = obtener_usuario_actual()
    if not puede_ver_compras(usuario):
        messagebox.showerror("Acceso denegado", "Este módulo está disponible para Compras (id=7) y Administrador.")
        return

    for widget in parent.winfo_children():
        widget.destroy()

    root = ctk.CTkFrame(parent, fg_color="transparent")
    root.pack(fill="both", expand=True, padx=14, pady=(4, 12))
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)

    cabecera = ctk.CTkFrame(root, fg_color=WHITE, corner_radius=16)
    cabecera.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    cabecera.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(cabecera, text="Compras", font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w").grid(
        row=0, column=0, sticky="ew", padx=14, pady=(10, 2)
    )
    ctk.CTkLabel(
        cabecera,
        text="Cotizaciones finalizadas por Ventas y pendientes de iniciar el proceso de compra. Desde aquí puedes revisar la cotización y convertirla en Orden de Trabajo.",
        font=TEXT_MD, text_color=TEXT_SECONDARY, anchor="w", wraplength=1100,
    ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

    panel = ctk.CTkFrame(root, fg_color=WHITE, corner_radius=16)
    panel.grid(row=1, column=0, sticky="nsew")
    panel.grid_columnconfigure(0, weight=1)
    panel.grid_rowconfigure(1, weight=1)

    lbl = ctk.CTkLabel(panel, text="Pendientes de compra (0)", font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w")
    lbl.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 5))

    tabla = NativeTreeTable(
        panel,
        columns=(
            ("cot", "Cotización", 130),
            ("lev", "Levantamiento", 130),
            ("cliente", "Cliente", 250),
            ("asunto", "Asunto", 300),
            ("total", "Total MXN", 135),
            ("fecha", "Finalizada", 155),
        ),
        height=22,
    )
    tabla.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))

    pie = ctk.CTkFrame(panel, fg_color="transparent")
    pie.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
    pie.grid_columnconfigure(0, weight=1)
    pie.grid_columnconfigure(1, weight=0)
    pie.grid_columnconfigure(2, weight=0)
    pie.grid_columnconfigure(3, weight=0)

    lbl_estado = ctk.CTkLabel(pie, text="Selecciona una cotización.", text_color=TEXT_SECONDARY, anchor="w")
    lbl_estado.grid(row=0, column=0, sticky="ew")

    def actualizar_botones(*_):
        seleccionado = tabla.selected_payload()
        estado = str((seleccionado or {}).get("cot_estatus") or "").strip().upper()
        habilitado = bool(seleccionado) and estado == "EN COMPRA X COTIZACIÓN"
        btn_preview.configure(state="normal" if seleccionado else "disabled")
        btn_convertir.configure(
            state="normal" if habilitado and puede_convertir_cotizacion_a_orden(usuario) else "disabled"
        )
        if seleccionado:
            lbl_estado.configure(
                text=f"Seleccionada: {_txt(seleccionado, 'cot_folio')} · {_txt(seleccionado, 'cot_cliente')} · {_money(seleccionado.get('cot_total'))}"
            )
        else:
            lbl_estado.configure(text="Selecciona una cotización.")

    def visualizar_cotizacion():
        cot = tabla.selected_payload()
        if not cot:
            messagebox.showinfo("Selecciona una cotización", "Selecciona primero una cotización de la tabla.")
            return
        try:
            AxiaPdfEngine.render_cotizacion(cot, abrir=True)
        except Exception as error:
            logger.exception("Error generando Preview PDF de cotización desde Compras")
            messagebox.showerror("Visualizar cotización", str(error))

    def convertir_cotizacion():
        cot = tabla.selected_payload()
        if not cot:
            messagebox.showinfo("Selecciona una cotización", "Selecciona primero una cotización de la tabla.")
            return
        if not puede_convertir_cotizacion_a_orden(usuario):
            messagebox.showerror("Acceso denegado", "Solo Compras (id=7) o Administrador puede convertir cotizaciones en OT.")
            return
        folio = _txt(cot, "cot_folio")
        lev = _txt(cot, "lev_folio")
        cliente = _txt(cot, "cot_cliente")
        if not messagebox.askyesno(
            "Convertir cotización en Orden de Trabajo",
            f"¿Confirmas convertir {folio} en una Orden de Trabajo?\n\n"
            f"Levantamiento: {lev}\n"
            f"Cliente: {cliente}\n\n"
            "AXIA validará que la cotización esté finalizada, recuperará el levantamiento origen, "
            "generará el ACO si todavía no existe y creará la OT.\n\n"
            "Esta acción no se puede duplicar para el mismo levantamiento.",
        ):
            return

        btn_convertir.configure(state="disabled")
        btn_preview.configure(state="disabled")
        lbl_estado.configure(text=f"Convirtiendo {folio} en Orden de Trabajo...", text_color=TEXT_SECONDARY)
        usuario_actual = dict(usuario or {})

        def ok(resultado):
            registro_ot = resultado[0] if isinstance(resultado, list) and resultado else {}
            folio_ot = _txt(registro_ot, "ot_folio") or "OT"
            aco = _txt(registro_ot, "_axia_aco_numero")
            detalle_aco = f"\nACO: {aco}" if aco else ""
            ya_existia = bool(registro_ot.get("_axia_ot_existente"))
            if ya_existia:
                lbl_estado.configure(text=f"Cotización sincronizada con {folio_ot}", text_color="#15803D")
                messagebox.showinfo(
                    "Orden de Trabajo existente",
                    f"La cotización {folio} corresponde al levantamiento {lev}, que ya estaba convertido en {folio_ot}.\n\n"
                    "No se creó una Orden de Trabajo duplicada. La cotización fue sincronizada y dejará de aparecer en Pendientes de compra.",
                )
            else:
                lbl_estado.configure(text=f"Conversión completada: {folio_ot}", text_color="#15803D")
                messagebox.showinfo(
                    "Orden de Trabajo creada",
                    f"La cotización {folio} se convirtió correctamente en {folio_ot}.{detalle_aco}\n\n"
                    "La cotización dejará de aparecer en Pendientes de compra.",
                )
            cargar()

        def error(err):
            logger.exception("No fue posible convertir %s a OT", folio)
            lbl_estado.configure(text=f"No se pudo convertir {folio}.", text_color="#B91C1C")
            messagebox.showerror("No fue posible convertir", str(err))
            actualizar_botones()

        run_async(
            parent.winfo_toplevel(),
            lambda: convertir_cotizacion_a_trabajo(cot, usuario_actual),
            ok,
            error,
        )

    def cargar():
        lbl_estado.configure(text="Consultando cotizaciones pendientes...", text_color=TEXT_SECONDARY)
        btn_preview.configure(state="disabled")
        btn_convertir.configure(state="disabled")

        def ok(registros):
            registros = list(registros or [])
            lbl.configure(text=f"Pendientes de compra ({len(registros)})")
            tabla.set_rows(
                registros,
                value_factory=lambda r: (
                    _txt(r, "cot_folio"),
                    _txt(r, "lev_folio"),
                    _txt(r, "cot_cliente"),
                    _txt(r, "cot_asunto"),
                    _money(r.get("cot_total")),
                    _txt(r, "cot_fecha_finalizacion")[:19].replace("T", " "),
                ),
            )
            actualizar_botones()
            if not registros:
                lbl_estado.configure(text="Sin cotizaciones pendientes.", text_color=TEXT_SECONDARY)

        def error(err):
            logger.exception("Error cargando Compras")
            lbl_estado.configure(text="No fue posible consultar las cotizaciones.", text_color="#B91C1C")
            messagebox.showerror("Compras", str(err))

        run_async(parent.winfo_toplevel(), obtener_cotizaciones_en_compra, ok, error)

    btn_preview = ctk.CTkButton(
        pie, text="👁 Visualizar Cotización", width=190, height=38,
        fg_color="#334155", hover_color=BUTTON_HOVER, font=BUTTON_FONT,
        command=visualizar_cotizacion, state="disabled",
    )
    btn_preview.grid(row=0, column=1, padx=(8, 0))

    btn_convertir = ctk.CTkButton(
        pie, text="✓ Convertir en Orden de Trabajo", width=240, height=38,
        fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT,
        command=convertir_cotizacion, state="disabled",
    )
    btn_convertir.grid(row=0, column=2, padx=(8, 0))

    ctk.CTkButton(
        pie, text="↻ Actualizar", width=145, height=38, fg_color=SECONDARY,
        hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=cargar,
    ).grid(row=0, column=3, padx=(8, 0))

    # NativeTreeTable expone callback de selección; lo conectamos aquí para
    # habilitar/deshabilitar las acciones en tiempo real.
    tabla._on_select = lambda _payload: actualizar_botones()

    cargar()
