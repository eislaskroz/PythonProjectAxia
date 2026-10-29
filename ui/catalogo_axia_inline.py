"""Selector en línea del Catálogo Maestro AXIA para Levantamientos.

Presenta la DESCRIPCIÓN en primer término (no el folio interno), ofrece
búsqueda sobre el catálogo COMPLETO y muestra su clasificación y existencia.
La selección conserva internamente el codigo_axia y nunca registra movimientos.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from tkinter import ttk
import tkinter as tk
import unicodedata


def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(texto or '').casefold())
                   if not unicodedata.combining(c))


def etiqueta_producto(producto):
    """Texto que reconoce el técnico; el código universal queda oculto."""
    return str(producto.get('producto') or 'Producto sin descripción').strip()


def etiquetas_catalogo(productos):
    """Etiquetas distintas para referencias que comparten la misma descripción.

    No se fusionan artículos que tengan códigos AXIA diferentes. Si todos los
    atributos visibles coinciden, el ordinal evita que una entrada reemplace a
    otra en el Combobox; el código continúa siendo la identidad interna.
    """
    nombres = [etiqueta_producto(p) for p in productos]
    repetidos = Counter(nombres)
    generados = defaultdict(int)
    etiquetas = []
    for p, nombre in zip(productos, nombres):
        if repetidos[nombre] == 1:
            propuesta = nombre
        else:
            extras = [str(p.get(k) or '').strip() for k in
                      ('familia_axia', 'departamento_origen', 'unidad_inventario')]
            detalle = ' / '.join(v for v in extras if v)
            propuesta = f'{nombre} — {detalle}' if detalle else nombre
        generados[propuesta] += 1
        # Algunos artículos siguen siendo equivalentes visualmente: no ocultar ninguno.
        etiquetas.append((propuesta, generados[propuesta]))
    totales = Counter(propuesta for propuesta, _ in etiquetas)
    return [f'{etiqueta} (registro {numero}/{totales[etiqueta]})'
            if totales[etiqueta] > 1 else etiqueta
            for etiqueta, numero in etiquetas]


def detalle_producto(producto):
    """Datos relevantes para el técnico, sin proveedores ni precios internos."""
    if not producto:
        return ''
    items = [(k, producto.get(v)) for k, v in (
        ('Categoría', 'categoria_axia'), ('Familia', 'familia_axia'),
        ('Departamento', 'departamento_origen'), ('Unidad', 'unidad_inventario'),
        ('Saldo registrado', 'saldo_actual'),
    )]
    contexto = '  ·  '.join(f'{nombre}: {valor}' for nombre, valor in items if valor is not None and str(valor).strip())
    return f"{etiqueta_producto(producto)}\n{contexto}" if contexto else etiqueta_producto(producto)


class SelectorProductoAxia(ttk.Frame):
    """Búsqueda por nombre, medidas, familia, categoría y departamento.

    La lista NO está limitada a los primeros 120 elementos. Las 1,886 referencias
    quedan disponibles con desplazamiento; teclear reduce las coincidencias.
    El campo secundario presenta la información descriptiva del artículo.
    """
    def __init__(self, parent, *, on_select, on_clear=None, productos=None, **kw):
        super().__init__(parent)
        self._on_select = on_select
        self._on_clear = on_clear
        self._productos = []
        self._indice = {}
        self._buscadores = {}
        self._ultimo_codigo = None
        self._ultima_etiqueta = None
        self._pendiente_descripcion = ''
        self._actualizando = False
        self._combo = ttk.Combobox(self, state='normal', height=16,
                                   font=('Montserrat', 11), **kw)
        self._combo.pack(fill='x', expand=True)
        self._informacion = tk.Label(self, text='Cargando Catálogo Maestro...',
                                     font=('Montserrat', 9), fg='#52677E',
                                     bg='#F7F9FC', anchor='w', justify='left',
                                     wraplength=520)
        self._informacion.pack(fill='x', pady=(1, 0))
        self._combo.bind('<KeyRelease>', self._filtrar, add='+')
        self._combo.bind('<<ComboboxSelected>>', self._elegir, add='+')
        self._combo.bind('<Return>', self._elegir, add='+')
        self._combo.bind('<FocusOut>', self._validar, add='+')
        if productos:
            self.set_productos(productos)

    def get(self):
        return self._combo.get()

    def set(self, value):
        self._combo.set(value)

    def configure(self, cnf=None, **kw):
        # La vista habilita o bloquea el selector completo mediante state.
        state = kw.pop('state', None)
        if state is not None:
            self._combo.configure(state=state)
        if 'values' in kw:
            self._combo.configure(values=kw.pop('values'))
        if cnf is not None or kw:
            return super().configure(cnf, **kw)
        return None

    config = configure

    def set_productos(self, productos):
        self._productos = list(productos)
        etiquetas = etiquetas_catalogo(self._productos)
        self._indice = dict(zip(etiquetas, self._productos))
        self._buscadores = {
            etiqueta: normalizar(' '.join(str(p.get(k) or '') for k in (
                'producto', 'categoria_axia', 'familia_axia', 'departamento_origen',
                'unidad_inventario', 'codigo_axia',
            ))) for etiqueta, p in self._indice.items()
        }
        if self._ultimo_codigo:
            self.mostrar_guardado(self._ultimo_codigo, self._pendiente_descripcion)
        elif self.get().startswith('Cargando'):
            self.set('')
        self._filtrar()

    def _filtrar(self, event=None):
        if self._actualizando or (event and event.keysym in ('Up', 'Down', 'Return', 'Escape', 'Tab')):
            return
        texto = self.get().strip()
        if event and self._ultimo_codigo and texto != self._ultima_etiqueta:
            self._ultimo_codigo = None
            self._ultima_etiqueta = None
            if self._on_clear:
                self._on_clear()
            self._informacion.configure(text='Selecciona una opción de la lista para vincular el producto.')
        if texto in self._indice:
            prod = self._indice[texto]
            encontrados = [texto]
            self._informacion.configure(text=detalle_producto(prod))
        else:
            filtro = normalizar(texto)
            encontrados = [etiqueta for etiqueta, buscar in self._buscadores.items()
                           if not filtro or filtro in buscar]
            self._informacion.configure(text=(
                f'{len(encontrados)} de {len(self._productos)} productos disponibles · '
                'Busca por nombre, medida, categoría o familia.'))
        # Sin tope artificial: todos los artículos cargados están disponibles.
        self._combo.configure(values=encontrados)

    def _elegir(self, event=None):
        item = self._indice.get(self.get().strip())
        if item:
            self._ultimo_codigo = str(item.get('codigo_axia') or '')
            self._ultima_etiqueta = self.get().strip()
            self._pendiente_descripcion = etiqueta_producto(item)
            self._informacion.configure(text=detalle_producto(item))
            self._on_select(item)
        return None

    def _validar(self, event=None):
        # No conviertas texto escrito libremente en una referencia de catálogo.
        if self.get().strip() in self._indice:
            if self._ultimo_codigo != str(self._indice[self.get().strip()].get('codigo_axia') or ''):
                self._elegir()
        elif self.get().strip():
            if self._ultimo_codigo:
                self.mostrar_guardado(self._ultimo_codigo, self._pendiente_descripcion)
            elif not self._pendiente_descripcion:
                self.set('')

    def mostrar_guardado(self, codigo, descripcion=''):
        codigo = str(codigo or '').strip()
        self._ultimo_codigo = codigo or None
        self._ultima_etiqueta = None
        self._pendiente_descripcion = str(descripcion or '').strip()
        coincidencia = next(((k, p) for k, p in self._indice.items()
                             if str(p.get('codigo_axia') or '') == codigo), None) if codigo else None
        if coincidencia:
            self.set(coincidencia[0])
            self._ultima_etiqueta = coincidencia[0]
            self._informacion.configure(text=detalle_producto(coincidencia[1]))
        else:
            # La referencia histórica sigue visible aunque esté desactivada en catálogo.
            self.set(self._pendiente_descripcion)
            self._informacion.configure(text=(
                'Referencia histórica conservada; el artículo ya no está disponible en el catálogo activo.'
                if codigo else 'Partida histórica sin Código AXIA; se conserva su descripción.'))

    def error_catalogo(self, texto):
        self.set('')
        self._informacion.configure(text=texto)
        self._combo.configure(values=[])
