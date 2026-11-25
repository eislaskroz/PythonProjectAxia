"""Diálogos corporativos AXIA compatibles con tkinter.messagebox."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

_INSTALLED = False
_ORIGINALS = {}


def _show(kind, title=None, message=None, **options):
    buttons = {
        'showinfo': [('Aceptar', 'ok')],
        'showwarning': [('Aceptar', 'ok')],
        'showerror': [('Aceptar', 'ok')],
        'askyesno': [('No', False), ('Sí', True)],
        'askokcancel': [('Cancelar', False), ('Aceptar', True)],
        'askretrycancel': [('Cancelar', False), ('Reintentar', True)],
        'askyesnocancel': [('Cancelar', None), ('No', False), ('Sí', True)],
        'askquestion': [('No', 'no'), ('Sí', 'yes')],
    }[kind]
    fallback = {'askyesnocancel': None, 'askquestion': 'no'}.get(kind, False)
    if kind.startswith('show'):
        fallback = 'ok'
    parent = options.get('parent')
    owner = parent if parent is not None and getattr(parent, 'winfo_exists', lambda: False)() else tk._default_root
    temporary = None
    if owner is None:
        temporary = tk.Tk()
        temporary.withdraw()
        owner = temporary
    try:
        dialog = ctk.CTkToplevel(owner)
        dialog.withdraw()
        dialog.title(str(title or 'AXIA'))
        dialog.resizable(False, False)
        dialog.configure(fg_color='#FFFFFF')
        try:
            from ui.assets import configurar_icono_ventana
            configurar_icono_ventana(dialog)
        except (OSError, tk.TclError):
            pass
        dialog.transient(owner)
        dialog.grid_columnconfigure(0, weight=1)
        accent = '#DC2626' if kind == 'showerror' else '#C98712' if kind == 'showwarning' else '#000A8B'
        header = ctk.CTkFrame(dialog, fg_color='#F2F6FC', corner_radius=0, height=55)
        header.grid(row=0, column=0, sticky='ew')
        header.grid_propagate(False)
        ctk.CTkLabel(header, text=str(title or 'AXIA'), font=('Poppins', 16, 'bold'),
                     text_color=accent).pack(side='left', padx=22, pady=12)
        body = ctk.CTkFrame(dialog, fg_color='#FFFFFF', corner_radius=0)
        body.grid(row=1, column=0, sticky='nsew', padx=23, pady=(18, 12))
        dialog.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(body, text=str(message or ''), font=('Poppins', 12),
                     text_color='#152538', justify='left', anchor='w',
                     wraplength=440).pack(fill='both', expand=True)
        footer = ctk.CTkFrame(dialog, fg_color='#FFFFFF', corner_radius=0)
        footer.grid(row=2, column=0, sticky='e', padx=20, pady=(6, 20))
        outcome = {'result': fallback}

        def choose(value):
            outcome['result'] = value
            dialog.destroy()

        for caption, value in buttons:
            ctk.CTkButton(footer, text=caption, width=110, height=36,
                          font=('Poppins', 12, 'bold'), corner_radius=9,
                          fg_color=accent if value in (True, 'yes', 'ok') else '#E9EFF7',
                          text_color='#FFFFFF' if value in (True, 'yes', 'ok') else '#152538',
                          hover_color='#2145A9' if value in (True, 'yes', 'ok') else '#D6E1EF',
                          command=lambda v=value: choose(v)).pack(side='left', padx=5)
        dialog.protocol('WM_DELETE_WINDOW', lambda: choose(fallback))
        dialog.update_idletasks()
        width = 500
        height = max(190, min(540, body.winfo_reqheight() + 143))
        x = owner.winfo_rootx() + (max(owner.winfo_width(), width) - width) // 2
        y = owner.winfo_rooty() + (max(owner.winfo_height(), height) - height) // 2
        dialog.geometry(f'{width}x{height}+{max(0,x)}+{max(0,y)}')
        dialog.deiconify()
        dialog.grab_set()
        dialog.focus_force()
        dialog.bind('<Escape>', lambda _e: choose(fallback))
        dialog.bind('<Return>', lambda _e: choose(buttons[-1][1]))
        owner.wait_window(dialog)
        return outcome['result']
    finally:
        if temporary is not None:
            temporary.destroy()


def install_axia_dialogs():
    global _INSTALLED
    if _INSTALLED:
        return
    for name in ('showinfo', 'showwarning', 'showerror', 'askyesno', 'askokcancel',
                 'askretrycancel', 'askyesnocancel', 'askquestion'):
        original = getattr(messagebox, name)
        _ORIGINALS[name] = original
        def replacement(title=None, message=None, _name=name, **options):
            try:
                return _show(_name, title, message, **options)
            except Exception:
                return _ORIGINALS[_name](title, message, **options)
        setattr(messagebox, name, replacement)
    _INSTALLED = True
