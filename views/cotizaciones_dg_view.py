"""Dirección General (rol 9): bandeja de aprobación de cotizaciones."""
from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

from app_context import obtener_usuario_actual
from core.background_tasks import run_async
from security.permissions import puede_autorizar_cotizacion_dg
from services.cotizaciones_service import obtener_cotizaciones_pendientes_dg, autorizar_cotizacion_dg
from services.axia_pdf_engine import AxiaPdfEngine
from views.cotizacion_pdf_opciones import solicitar_campos_pdf
from ui.native_table import NativeTreeTable
from ui.colors import WHITE, TEXT_SECONDARY, SECONDARY


def mostrar_cotizaciones_dg(parent, app=None):
    usuario = obtener_usuario_actual()
    if not puede_autorizar_cotizacion_dg(usuario):
        messagebox.showerror("Acceso denegado", "Esta bandeja corresponde a DG (9) o Administrador (1).")
        return
    for widget in parent.winfo_children():
        widget.destroy()
    root = ctk.CTkFrame(parent, fg_color="transparent")
    root.pack(fill="both", expand=True, padx=14, pady=10)
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)
    ctk.CTkLabel(root, text="Cotizaciones pendientes de autorización — DG", font=("Montserrat", 19, "bold"), anchor="w").grid(
        row=0, column=0, sticky="ew", pady=(0, 9))
    panel = ctk.CTkFrame(root, fg_color=WHITE)
    panel.grid(row=1, column=0, sticky="nsew")
    panel.grid_columnconfigure(0, weight=1)
    panel.grid_rowconfigure(1, weight=1)
    lbl = ctk.CTkLabel(panel, text="Consultando cotizaciones...", text_color=TEXT_SECONDARY)
    lbl.grid(row=0, column=0, sticky="w", padx=12, pady=6)
    tabla = NativeTreeTable(panel, columns=(("folio", "Cotización", 135), ("lev", "Levantamiento", 130),
        ("cliente", "Cliente", 260), ("asunto", "Título / concepto", 310), ("total", "Total MXN", 140)),
        height=21, table_id="cotizaciones_pendientes_dg")
    tabla.grid(row=1, column=0, sticky="nsew", padx=12, pady=5)
    botones = ctk.CTkFrame(panel, fg_color="transparent")
    botones.grid(row=2, column=0, sticky="e", padx=12, pady=12)

    def seleccionado():
        return tabla.selected_payload()

    def preview():
        cot = seleccionado()
        if not cot:
            messagebox.showinfo("Cotización", "Selecciona una cotización.")
            return
        opciones = solicitar_campos_pdf(parent)
        if opciones is None:
            return
        try:
            AxiaPdfEngine.render_cotizacion(cot, abrir=True, campos_visibles=opciones)
        except Exception as exc:
            messagebox.showerror("PDF", str(exc))

    def autorizar():
        cot = seleccionado()
        if not cot:
            messagebox.showinfo("Cotización", "Selecciona una cotización.")
            return
        folio = str(cot.get("cot_folio") or "")
        if not messagebox.askyesno("Autorizar para Compras", f"¿Autorizar {folio} y liberar a Compras (7)?\n\nEsta acción quedará registrada."):
            return
        btn_aut.configure(state="disabled")
        run_async(parent.winfo_toplevel(), lambda: autorizar_cotizacion_dg(cot, usuario),
            lambda reg: (messagebox.showinfo("Autorizada", f"{folio} se envió a Compras."), cargar()),
            lambda exc: (messagebox.showerror("No fue posible autorizar", str(exc)), btn_aut.configure(state="normal")))

    def cargar():
        lbl.configure(text="Consultando cotizaciones pendientes de DG...")
        btn_aut.configure(state="disabled")
        def listo(registros):
            filas = list(registros or [])
            tabla.set_rows(filas, value_factory=lambda x: (
                str(x.get("cot_folio") or ""), str(x.get("lev_folio") or ""),
                str(x.get("cot_cliente") or ""), str(x.get("cot_asunto") or ""),
                f"${float(x.get('cot_total') or 0):,.2f}"))
            lbl.configure(text=f"Pendientes de DG ({len(filas)})")
            btn_aut.configure(state="normal" if filas else "disabled")
        run_async(parent.winfo_toplevel(), obtener_cotizaciones_pendientes_dg, listo,
                  lambda exc: messagebox.showerror("Cotizaciones DG", str(exc)))

    ctk.CTkButton(botones, text="Actualizar", width=115, command=cargar).pack(side="left", padx=5)
    ctk.CTkButton(botones, text="Vista previa PDF", width=160, command=preview).pack(side="left", padx=5)
    btn_aut = ctk.CTkButton(botones, text="Autorizar y enviar a Compras", fg_color=SECONDARY,
                            width=230, command=autorizar, state="disabled")
    btn_aut.pack(side="left", padx=5)
    cargar()
