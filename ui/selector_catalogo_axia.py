"""Selector de producto maestro para secciones dinámicas de levantamientos.

Solo consulta. No contiene acciones de entradas, salidas ni edición de stock.
"""
from __future__ import annotations

from tkinter import messagebox, simpledialog
import customtkinter as ctk
from core.background_tasks import run_async
from ui.native_table import NativeTreeTable
from services.levantamiento_catalogo_axia import CatalogoAxiaLevantamientos


def abrir_selector_axia(parent, usuario: dict, al_elegir, *, servicio=None, titulo='Seleccionar producto AXIA'):
    svc = servicio or CatalogoAxiaLevantamientos()
    # La contraseña solo sirve para una sesión de lectura temporal en Edge Function.
    if not svc.token:
        password = simpledialog.askstring('Catálogo Maestro AXIA',
            'Confirma tu contraseña AXIA para consultar productos (solo lectura):',
            parent=parent.winfo_toplevel(), show='*')
        if not password:
            return
        nickname = str(usuario.get('usuario') or usuario.get('usu_nickname') or '').strip()
        if not nickname:
            messagebox.showerror('Catálogo AXIA', 'La cuenta actual no tiene nombre de usuario.', parent=parent)
            return
        try:
            svc.iniciar_lectura(nickname, password, usuario.get('id_usuario'))
        except Exception as exc:
            messagebox.showerror('Catálogo AXIA', str(exc), parent=parent)
            return

    win = ctk.CTkToplevel(parent)
    win.title(titulo)
    win.geometry('1040x590')
    win.minsize(790, 450)
    win.transient(parent.winfo_toplevel())
    win.grid_columnconfigure(0, weight=1)
    win.grid_rowconfigure(2, weight=1)
    ctk.CTkLabel(win, text='Catálogo Maestro AXIA · Selección para levantamiento',
                 font=('Montserrat', 16, 'bold')).grid(row=0, column=0, padx=15, pady=(14, 6), sticky='w')
    barra = ctk.CTkFrame(win, fg_color='transparent')
    barra.grid(row=1, column=0, sticky='ew', padx=15, pady=6)
    barra.grid_columnconfigure(0, weight=1)
    buscar = ctk.CTkEntry(barra, height=34, placeholder_text='Código AXIA, producto, categoría o familia')
    buscar.grid(row=0, column=0, sticky='ew', padx=(0, 8))
    estado = ctk.CTkLabel(win, text='Consulta de solo lectura. El levantamiento NO descuenta inventario.',
                          text_color='#475569', anchor='w')
    estado.grid(row=3, column=0, sticky='ew', padx=15, pady=(4, 0))
    tabla = NativeTreeTable(win, columns=[
        ('codigo_axia','Código AXIA',158), ('producto','Producto',355),
        ('categoria_axia','Categoría',170), ('familia_axia','Familia',205),
        ('saldo_actual','Existencia referencial',150),
    ], table_id='catalogo_axia_selector_lev', height=15)
    tabla.grid(row=2, column=0, sticky='nsew', padx=15, pady=5)
    def elegir(_=None):
        producto = tabla.selected_payload()
        if not producto:
            messagebox.showinfo('Catálogo AXIA', 'Selecciona un artículo de la tabla.', parent=win)
            return
        al_elegir(producto)
        win.destroy()
    tabla.tree.bind('<Double-1>', lambda e: win.after_idle(elegir), add='+')
    pie = ctk.CTkFrame(win, fg_color='transparent')
    pie.grid(row=4, column=0, sticky='e', padx=15, pady=(5, 12))
    ctk.CTkButton(pie, text='Cancelar', fg_color='#64748B', command=win.destroy).pack(side='left', padx=5)
    ctk.CTkButton(pie, text='Usar producto seleccionado', width=220, command=elegir).pack(side='left', padx=5)
    def consultar():
        criterio = buscar.get().strip()
        boton.configure(state='disabled')
        estado.configure(text='Consultando catálogo AXIA...')
        def ok(filas):
            if not win.winfo_exists(): return
            tabla.set_rows(filas)
            estado.configure(text=f'{len(filas)} resultados · Solo lectura · No descuenta inventario')
            boton.configure(state='normal')
        def err(exc):
            if not win.winfo_exists(): return
            boton.configure(state='normal')
            estado.configure(text='No se pudo consultar el catálogo. Comprueba tu sesión y la conexión.')
            messagebox.showerror('Catálogo AXIA', str(exc), parent=win)
        run_async(win, lambda: svc.buscar(criterio), on_success=ok, on_error=err)
    boton = ctk.CTkButton(barra, text='Buscar', width=100, command=consultar)
    boton.grid(row=0, column=1)
    buscar.bind('<Return>', lambda e: consultar())
    win.after(200, consultar)
    return win
