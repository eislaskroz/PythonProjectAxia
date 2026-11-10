"""Selector por campo de lo visible en el PDF comercial; no modifica la COT guardada."""
import customtkinter as ctk
from ui.colors import TEXT_PRIMARY
from tkinter import messagebox
from utils import centrar_ventana

CAMPOS_PDF = [
    ("Datos de AXIA", [("empresa", "Razón social"), ("rfc", "RFC"), ("domicilio_axia", "Domicilio AXIA"),
                        ("esi", "Ejecutiva de ventas"), ("correo_esi", "Correo ESI"), ("telefono_esi", "Teléfono ESI")]),
    ("Personal operativo", [("jefe", "Jefe de Operaciones"), ("supervisor", "Supervisor"),
                             ("dias", "Días"), ("personas", "Personas")]),
    ("Información de la cotización", [("fecha", "Fecha"), ("folio", "Folio de cotización"),
                                     ("levantamiento", "Folio del levantamiento"), ("cliente", "Cliente"),
                                     ("contacto", "Contacto"), ("sucursal", "Sucursal"), ("asunto", "Título / concepto")]),
    ("Condiciones comerciales", [("plan_pagos", "Plan de pagos"), ("vigencia", "Vigencia")]),
    ("Partidas y columnas", [("partidas", "Tabla de partidas"), ("lote", "Lote"), ("unidad", "Unidad / tipo"),
                              ("cantidad", "Cantidad"), ("modelo", "Modelo"), ("sku", "SKU"),
                              ("marca", "Marca"), ("concepto", "Concepto"), ("precio_unitario", "Precio unitario"),
                              ("importe", "Importe"), ("observaciones", "Observaciones")]),
    ("Totales", [("totales", "Mostrar totales"), ("subtotal", "Subtotal"), ("descuento", "Descuento"),
                 ("subtotal_desc", "Subtotal con descuento"), ("iva", "IVA"), ("total", "Total")]),
]
TODOS_CAMPOS_PDF = frozenset(k for _, items in CAMPOS_PDF for k, _ in items)


def solicitar_campos_pdf(parent):
    """Retorna conjunto de claves o None si se cancela."""
    raiz = parent.winfo_toplevel()
    ventana = ctk.CTkToplevel(raiz)
    ventana.withdraw()  # Evita mostrar la ventana antes de colocarla en el centro.
    ventana.title("AXIA · Seleccionar campos del PDF de cotización")
    ventana.transient(raiz)
    # Se adapta a pantallas pequeñas y evita que los botones queden fuera.
    alto = max(420, min(660, int(ventana.winfo_screenheight() * 0.82)))
    ventana.minsize(480, min(420, alto))
    resultado = {"valor": None}
    vars_ = {key: ctk.BooleanVar(master=ventana, value=True) for key in TODOS_CAMPOS_PDF}
    ctk.CTkLabel(ventana, text="¿Qué campos deseas incluir en el PDF?", font=("Montserrat", 17, "bold"), text_color=TEXT_PRIMARY).pack(anchor="w", padx=18, pady=(15, 3))
    ctk.CTkLabel(ventana, text="Aplica solo a este PDF; no modifica la cotización guardada.", text_color="#64748B").pack(anchor="w", padx=18, pady=(0, 10))
    body = ctk.CTkScrollableFrame(ventana)
    body.pack(fill="both", expand=True, padx=16, pady=(0, 8))
    for title, fields in CAMPOS_PDF:
        ctk.CTkLabel(body, text=title, font=("Montserrat", 13, "bold"), anchor="w").pack(fill="x", pady=(9, 3))
        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.pack(fill="x")
        grid.grid_columnconfigure((0, 1), weight=1)
        for i, (key, text) in enumerate(fields):
            ctk.CTkCheckBox(grid, text=text, variable=vars_[key], font=("Montserrat", 11)).grid(
                row=i // 2, column=i % 2, sticky="w", padx=5, pady=5)
    actions = ctk.CTkFrame(ventana, fg_color="transparent")
    actions.pack(fill="x", padx=18, pady=(3, 14))
    ctk.CTkButton(actions, text="Todos", width=80, command=lambda: [v.set(True) for v in vars_.values()]).pack(side="left", padx=(0, 6))
    ctk.CTkButton(actions, text="Ninguno", width=80, fg_color="#64748B", command=lambda: [v.set(False) for v in vars_.values()]).pack(side="left")
    def aceptar():
        elegidos = frozenset(k for k, v in vars_.items() if v.get())
        if not elegidos:
            messagebox.showwarning("PDF sin contenido", "Selecciona al menos un campo para generar el PDF.", parent=ventana)
            return
        resultado["valor"] = elegidos
        ventana.destroy()
    ctk.CTkButton(actions, text="Generar PDF", command=aceptar).pack(side="right", padx=(6, 0))
    ctk.CTkButton(actions, text="Cancelar", fg_color="#64748B", command=ventana.destroy).pack(side="right")
    centrar_ventana(ventana, 590, alto, padre=raiz)
    ventana.deiconify()
    ventana.lift()
    ventana.grab_set()
    ventana.wait_window()
    return resultado["valor"]
