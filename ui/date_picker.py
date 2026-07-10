"""
=========================================================
MÓDULO: ui/date_picker.py
DESCRIPCIÓN:
Selector de fecha simple para campos CustomTkinter.

Objetivo:
- Evitar capturas manuales inconsistentes.
- Guardar fechas siempre como YYYY-MM-DD.
- No depender de librerías externas obligatorias.
- Mantener una sola ventana de calendario abierta para evitar
  duplicados y bloqueos visuales.
=========================================================
"""

from __future__ import annotations

import calendar
from datetime import date
import customtkinter as ctk


_calendario_activo = None


def _ventana_existe(ventana) -> bool:
    try:
        return ventana is not None and ventana.winfo_exists()
    except Exception:
        return False


def abrir_selector_fecha(parent, variable):
    """
    Abre un calendario pequeño y escribe la fecha seleccionada en formato ISO.

    Args:
        parent: ventana/contenedor dueño.
        variable: ctk.StringVar/tk.StringVar donde se guardará YYYY-MM-DD.

    Reglas de estabilidad:
    - Solo permite un calendario abierto a la vez.
    - Si ya existe, lo trae al frente en lugar de crear otro.
    - Al elegir fecha o cerrar con X, limpia la referencia global.
    """

    global _calendario_activo

    if _ventana_existe(_calendario_activo):
        try:
            _calendario_activo.lift()
            _calendario_activo.focus_force()
            return
        except Exception:
            _calendario_activo = None

    hoy = date.today()
    estado = {"year": hoy.year, "month": hoy.month}

    ventana = ctk.CTkToplevel(parent)
    _calendario_activo = ventana

    ventana.title("Seleccionar fecha")
    ventana.geometry("330x330")
    ventana.resizable(False, False)

    try:
        ventana.transient(parent.winfo_toplevel())
    except Exception:
        pass

    def cerrar_calendario():
        global _calendario_activo
        try:
            if _ventana_existe(ventana):
                ventana.destroy()
        finally:
            if _calendario_activo is ventana:
                _calendario_activo = None

    ventana.protocol("WM_DELETE_WINDOW", cerrar_calendario)
    ventana.lift()
    ventana.focus_force()

    marco = ctk.CTkFrame(ventana, fg_color="transparent")
    marco.pack(fill="both", expand=True, padx=12, pady=12)
    marco.grid_columnconfigure(tuple(range(7)), weight=1)

    encabezado = ctk.CTkFrame(marco, fg_color="transparent")
    encabezado.grid(row=0, column=0, columnspan=7, sticky="ew", pady=(0, 8))
    encabezado.grid_columnconfigure(1, weight=1)

    titulo = ctk.CTkLabel(encabezado, text="", font=("Montserrat", 15, "bold"))
    titulo.grid(row=0, column=1, sticky="ew")

    cuerpo = ctk.CTkFrame(marco, fg_color="transparent")
    cuerpo.grid(row=2, column=0, columnspan=7, sticky="nsew")
    for col in range(7):
        cuerpo.grid_columnconfigure(col, weight=1)

    def pintar():
        for w in cuerpo.winfo_children():
            w.destroy()

        meses = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        titulo.configure(text=f"{meses[estado['month']-1]} {estado['year']}")

        for col, dia in enumerate(["Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"]):
            ctk.CTkLabel(cuerpo, text=dia, font=("Montserrat", 11, "bold")).grid(row=0, column=col, padx=2, pady=2)

        semanas = calendar.monthcalendar(estado["year"], estado["month"])
        for r, semana in enumerate(semanas, start=1):
            for c, dia in enumerate(semana):
                if dia == 0:
                    ctk.CTkLabel(cuerpo, text="").grid(row=r, column=c, padx=2, pady=2)
                    continue

                def elegir(d=dia):
                    variable.set(date(estado["year"], estado["month"], d).isoformat())
                    cerrar_calendario()

                ctk.CTkButton(
                    cuerpo,
                    text=str(dia),
                    width=34,
                    height=28,
                    corner_radius=8,
                    command=elegir,
                ).grid(row=r, column=c, padx=2, pady=2)

    def anterior():
        estado["month"] -= 1
        if estado["month"] < 1:
            estado["month"] = 12
            estado["year"] -= 1
        pintar()

    def siguiente():
        estado["month"] += 1
        if estado["month"] > 12:
            estado["month"] = 1
            estado["year"] += 1
        pintar()

    ctk.CTkButton(encabezado, text="‹", width=42, command=anterior).grid(row=0, column=0, sticky="w")
    ctk.CTkButton(encabezado, text="›", width=42, command=siguiente).grid(row=0, column=2, sticky="e")

    pintar()
