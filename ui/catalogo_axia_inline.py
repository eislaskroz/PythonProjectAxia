"""Selector en línea: usa directamente el catálogo maestro (sin ventanas ni contraseña)."""
from __future__ import annotations
import unicodedata
from tkinter import ttk


def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(texto or '').casefold())
                   if not unicodedata.combining(c))


def etiqueta_producto(producto):
    return f"{producto.get('codigo_axia', '')} · {producto.get('producto', '')}"


class SelectorProductoAxia(ttk.Combobox):
    """Combobox con búsqueda al escribir, que nunca crea registros de inventario."""
    def __init__(self, parent, *, on_select, on_clear=None, productos=None, **kw):
        super().__init__(parent, state='normal', height=12, font=('Montserrat', 11), **kw)
        self._on_select = on_select
        self._on_clear = on_clear
        self._productos = []
        self._indice = {}
        self._ultimo_codigo = None
        self._actualizando = False
        self.configure(values=['Cargando Catálogo Maestro AXIA...'])
        self.bind('<KeyRelease>', self._filtrar, add='+')
        self.bind('<<ComboboxSelected>>', self._elegir, add='+')
        self.bind('<Return>', self._elegir, add='+')
        self.bind('<FocusOut>', self._validar, add='+')
        if productos:
            self.set_productos(productos)

    def set_productos(self, productos):
        self._productos = list(productos)
        self._indice = {etiqueta_producto(p): p for p in self._productos}
        if not self.get() or self.get().startswith('Cargando'):
            self.set('')
        self._filtrar()

    def _filtrar(self, event=None):
        if self._actualizando or (event and event.keysym in ('Up','Down','Return','Escape','Tab')):
            return
        texto_actual = self.get().strip()
        if event is not None and self._ultimo_codigo and not any(
            str(p.get('codigo_axia') or '') == self._ultimo_codigo and etiqueta_producto(p) == texto_actual
            for p in self._productos
        ):
            self._ultimo_codigo = None
            if self._on_clear:
                self._on_clear()
        texto = normalizar(texto_actual)
        encontrados = [clave for clave, prod in self._indice.items()
                       if not texto or texto in normalizar(' '.join((clave,
                       str(prod.get('categoria_axia','')), str(prod.get('familia_axia','')))))]
        self.configure(values=encontrados[:120])

    def _elegir(self, event=None):
        item = self._indice.get(self.get().strip())
        if item:
            self._ultimo_codigo = str(item.get('codigo_axia') or '')
            self._on_select(item)
        return None

    def _validar(self, event=None):
        # Evita que se guarde una búsqueda sin elegir un artículo de la lista.
        if self.get().strip() and self.get().strip() not in self._indice:
            self.set('')

    def mostrar_guardado(self, codigo, descripcion=''):
        codigo = str(codigo or '').strip()
        if codigo:
            coincidencia = next((key for key, p in self._indice.items()
                                 if str(p.get('codigo_axia')) == codigo), None)
            self.set(coincidencia or f'{codigo} · {descripcion}')
            self._ultimo_codigo = codigo
        elif descripcion:
            self.set(descripcion)

    def error_catalogo(self, texto):
        self.set('')
        self.configure(values=[texto])
