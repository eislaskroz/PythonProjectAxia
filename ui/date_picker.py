"""Selector de fecha ligero basado en controles ttk/tkcalendar."""
from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date, datetime
from tkinter import ttk

from core.logger import configurar_logger

logger = configurar_logger(__name__)
_calendario_activo = None

try:
    from tkcalendar import Calendar as TkCalendar
except Exception:  # dependencia opcional durante desarrollo
    TkCalendar = None


def _ventana_existe(ventana) -> bool:
    try:
        return ventana is not None and ventana.winfo_exists()
    except Exception:
        return False


def abrir_selector_fecha(parent, variable):
    """Abre un calendario ttk y guarda la selección como YYYY-MM-DD."""
    global _calendario_activo
    if _ventana_existe(_calendario_activo):
        _calendario_activo.lift()
        _calendario_activo.focus_force()
        return

    root = parent.winfo_toplevel()
    ventana = tk.Toplevel(root)
    _calendario_activo = ventana
    ventana.title("Seleccionar fecha")
    ventana.resizable(False, False)
    ventana.transient(root)
    ventana.grab_set()

    def cerrar():
        global _calendario_activo
        try:
            ventana.grab_release()
        except Exception:
            pass
        ventana.destroy()
        if _calendario_activo is ventana:
            _calendario_activo = None

    ventana.protocol("WM_DELETE_WINDOW", cerrar)
    contenedor = ttk.Frame(ventana, padding=8)
    contenedor.pack(fill="both", expand=True)

    inicial = date.today()
    try:
        inicial = datetime.strptime(variable.get(), "%Y-%m-%d").date()
    except Exception:
        pass

    if TkCalendar is not None:
        calendario_widget = TkCalendar(
            contenedor,
            selectmode="day",
            year=inicial.year,
            month=inicial.month,
            day=inicial.day,
            date_pattern="yyyy-mm-dd",
            locale="es_MX",
        )
        calendario_widget.pack(fill="both", expand=True)

        def aceptar():
            variable.set(calendario_widget.get_date())
            cerrar()

        botones = ttk.Frame(contenedor)
        botones.pack(fill="x", pady=(8, 0))
        ttk.Button(botones, text="Cancelar", command=cerrar).pack(side="right")
        ttk.Button(botones, text="Aceptar", command=aceptar).pack(side="right", padx=(0, 6))
        calendario_widget.bind("<Double-1>", lambda _e: aceptar())
    else:
        # Respaldo sin dependencia externa: calendario mensual construido solo con ttk.
        estado = {"year": inicial.year, "month": inicial.month}
        header = ttk.Frame(contenedor)
        header.pack(fill="x")
        titulo = ttk.Label(header, anchor="center")
        titulo.pack(side="left", fill="x", expand=True)
        cuerpo = ttk.Frame(contenedor)
        cuerpo.pack(fill="both", expand=True, pady=(6, 0))

        def pintar():
            for widget in cuerpo.winfo_children():
                widget.destroy()
            titulo.configure(text=f"{calendar.month_name[estado['month']].capitalize()} {estado['year']}")
            for col, dia in enumerate(("Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do")):
                ttk.Label(cuerpo, text=dia, anchor="center").grid(row=0, column=col, padx=2, pady=2)
            for fila, semana in enumerate(calendar.monthcalendar(estado["year"], estado["month"]), 1):
                for col, dia in enumerate(semana):
                    if dia:
                        ttk.Button(cuerpo, text=str(dia), width=4, command=lambda d=dia: elegir(d)).grid(row=fila, column=col, padx=1, pady=1)

        def elegir(dia):
            variable.set(date(estado["year"], estado["month"], dia).isoformat())
            cerrar()

        def mover(delta):
            estado["month"] += delta
            if estado["month"] < 1:
                estado["month"], estado["year"] = 12, estado["year"] - 1
            elif estado["month"] > 12:
                estado["month"], estado["year"] = 1, estado["year"] + 1
            pintar()

        ttk.Button(header, text="‹", width=4, command=lambda: mover(-1)).pack(side="left")
        ttk.Button(header, text="›", width=4, command=lambda: mover(1)).pack(side="right")
        pintar()

    ventana.update_idletasks()
    x = root.winfo_rootx() + max(20, (root.winfo_width() - ventana.winfo_reqwidth()) // 2)
    y = root.winfo_rooty() + max(20, (root.winfo_height() - ventana.winfo_reqheight()) // 3)
    ventana.geometry(f"+{x}+{y}")
    ventana.focus_force()
