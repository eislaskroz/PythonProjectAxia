import customtkinter as ctk
from ui.colors import TEXT_PRIMARY
from tkinter import messagebox

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


def _area_visible(ventana):
    """Área de trabajo visible, sin la barra de tareas cuando Windows la informa."""
    try:
        import ctypes
        from ctypes import wintypes
        rect = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0):
            return rect.left, rect.top, rect.right, rect.bottom
    except (AttributeError, ImportError, OSError):
        pass
    return 0, 0, ventana.winfo_screenwidth(), ventana.winfo_screenheight()


def _ubicar_dialogo(ventana, padre, ancho, alto):
    ventana.update_idletasks()
    x0, y0, x1, y1 = _area_visible(ventana)
    margen = 12
    ancho = min(ancho, max(1, x1 - x0 - 2 * margen))
    alto = min(alto, max(1, y1 - y0 - 2 * margen))
    try:
        padre.update_idletasks()
        px, py = padre.winfo_rootx(), padre.winfo_rooty()
        pw, ph = padre.winfo_width(), padre.winfo_height()
        if pw <= 1 or ph <= 1:
            raise ValueError("Ventana principal sin geometría")
        cx, cy = px + pw / 2, py + ph / 2
        if not (x0 <= cx < x1 and y0 <= cy < y1):
            raise ValueError("Ventana principal fuera de pantalla")
    except Exception:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    x = max(x0 + margen, min(round(cx - ancho / 2), x1 - margen - ancho))
    y = max(y0 + margen, min(round(cy - alto / 2), y1 - margen - alto))
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")


def solicitar_campos_pdf(parent):
    raiz = parent.winfo_toplevel()
    ventana = ctk.CTkToplevel(raiz)
    ventana.withdraw()
    ventana.title("AXIA · Seleccionar campos del PDF de cotización")
    ventana.transient(raiz)
    x0, y0, x1, y1 = _area_visible(ventana)
    alto = min(660, int((y1 - y0) * 0.82), y1 - y0 - 24)
    ventana.minsize(min(480, x1 - x0 - 24), min(420, alto))
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
    _ubicar_dialogo(ventana, raiz, 590, alto)
    ventana.deiconify()
    ventana.lift()
    ventana.grab_set()
    ventana.wait_window()
    return resultado["valor"]