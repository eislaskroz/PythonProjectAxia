"""Regresión del sombreado global de campos sin necesitar una pantalla real."""

import importlib.util
import sys
import types
from pathlib import Path


class _WidgetSimulado:
    def __init__(self, *args, **kwargs):
        self.opciones = kwargs.copy()

    def configure(self, *args, **kwargs):
        self.opciones.update(kwargs)
        return self.opciones


def _cargar_estilos(monkeypatch):
    fake = types.ModuleType("customtkinter")
    fake.CTkEntry = _WidgetSimulado
    fake.CTkTextbox = _WidgetSimulado
    monkeypatch.setitem(sys.modules, "customtkinter", fake)
    ruta = Path(__file__).resolve().parents[2] / "ui" / "form_fields.py"
    spec = importlib.util.spec_from_file_location("_axia_campos_prueba", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_entrada_reacciona_al_estado_sin_perder_valor(monkeypatch):
    estilos = _cargar_estilos(monkeypatch)
    entrada = estilos.AxiaEntry(textvariable="captura", state="normal", height=31)
    assert entrada.opciones["fg_color"] == estilos.CAMPO_HABILITADO
    assert entrada.opciones["textvariable"] == "captura"
    entrada.configure(state="disabled")
    assert entrada.opciones["fg_color"] == estilos.CAMPO_DESHABILITADO
    assert entrada.opciones["state"] == "disabled"
    entrada.configure(state="normal")
    assert entrada.opciones["fg_color"] == estilos.CAMPO_HABILITADO
    assert entrada.opciones["height"] == 31


def test_texto_multilinea_readonly_y_estado(monkeypatch):
    estilos = _cargar_estilos(monkeypatch)
    campo = estilos.AxiaTextbox(height=260, wrap="word", state="readonly")
    assert campo.opciones["fg_color"] == estilos.CAMPO_SOLO_LECTURA
    campo.configure(state="disabled")
    assert campo.opciones["fg_color"] == estilos.CAMPO_DESHABILITADO
    assert campo.opciones["height"] == 260
    assert campo.opciones["wrap"] == "word"


def test_proyecto_no_usa_ctk_entry_sin_estilo():
    raiz = Path(__file__).resolve().parents[2]
    archivos = [raiz / "app.py", raiz / "login.py", raiz / "registro.py", *(raiz / "views").glob("*.py")]
    for archivo in archivos:
        contenido = archivo.read_text(encoding="utf-8-sig")
        assert "ctk.CTkEntry(" not in contenido, archivo.name
        assert "ctk.CTkTextbox(" not in contenido, archivo.name


def test_sidebar_mantiene_acciones_y_mismo_estilo():
    raiz = Path(__file__).resolve().parents[2]
    src = (raiz / "ui" / "app_sidebar.py").read_text(encoding="utf8")
    assert 'boton = tk.Canvas(' in src
    assert 'font=("Segoe UI", 11, "normal")' in src
    assert 'crear_boton_sidebar(acciones_sesion, "⏻ Cerrar AXIA", on_exit)' in src
    assert 'crear_boton_sidebar(acciones_sesion, "🔒 Salir", on_logout or on_exit)' in src
    assert '"👤 Mi Usuario"' in src
