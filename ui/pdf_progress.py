from __future__ import annotations

import functools
import queue
import threading

_context = threading.local()
_active = False


def progreso_pdf(texto, completados=None, total=None):
    eventos = getattr(_context, 'eventos', None)
    if eventos is not None:
        eventos.put(('progress', (texto, completados, total)))


def dialogo_pdf(callback, *args, **kwargs):
    eventos = getattr(_context, 'eventos', None)
    if eventos is None:
        return callback(*args, **kwargs)
    respuesta = queue.Queue(maxsize=1)
    eventos.put(('dialog', (callback, args, kwargs, respuesta)))
    ok, valor = respuesta.get()
    if not ok:
        raise valor
    return valor


def con_progreso_pdf(func=None, *, titulo="Generando documento PDF", ventana="AXIA · Generando PDF"):
    if func is None:
        return lambda f: con_progreso_pdf(f, titulo=titulo, ventana=ventana)
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        global _active
        if getattr(_context, 'eventos', None) is not None or threading.current_thread() is not threading.main_thread():
            return func(*args, **kwargs)
        import tkinter as tk
        root = tk._default_root
        if root is None or not root.winfo_exists():
            return func(*args, **kwargs)
        if _active:
            raise RuntimeError("Ya se está generando un documento PDF.")
        import customtkinter as ctk
        from ui.fonts import FONT_FAMILY
        parent = root
        focus = root.focus_get()
        if focus is not None:
            parent = focus.winfo_toplevel()
        prior_grab = root.grab_current()
        win = ctk.CTkToplevel(parent)
        win.withdraw()
        win.title(ventana)
        win.resizable(False, False)
        win.transient(parent)
        win.protocol('WM_DELETE_WINDOW', lambda: None)
        ctk.CTkLabel(win, text=titulo, font=(FONT_FAMILY, 18, 'bold')).pack(padx=28, pady=(24, 12))
        status = ctk.CTkLabel(win, text='Preparando documento…', font=(FONT_FAMILY, 12), wraplength=350)
        status.pack(padx=24, pady=(0, 12))
        bar = ctk.CTkProgressBar(win, width=340, height=12, progress_color='#2563EB', mode='indeterminate')
        bar.pack(padx=28, pady=(0, 12))
        detail = ctk.CTkLabel(win, text='Procesando…', font=(FONT_FAMILY, 11))
        detail.pack(padx=24, pady=(0, 22))
        win.update_idletasks()
        width, height = 410, max(190, win.winfo_reqheight())
        x = max(0, parent.winfo_rootx() + (parent.winfo_width() - width) // 2)
        y = max(0, parent.winfo_rooty() + (parent.winfo_height() - height) // 2)
        win.geometry(f'{width}x{height}+{x}+{y}')
        win.deiconify()
        win.wait_visibility()
        win.grab_set()
        bar.start()
        eventos = queue.Queue()
        resultado = []
        _active = True

        def worker():
            _context.eventos = eventos
            try:
                eventos.put(('done', (True, func(*args, **kwargs))))
            except BaseException as error:
                eventos.put(('done', (False, error)))
            finally:
                _context.eventos = None

        def poll():
            while True:
                try:
                    kind, value = eventos.get_nowait()
                except queue.Empty:
                    break
                if kind == 'progress':
                    texto, n, total = value
                    status.configure(text=texto)
                    if isinstance(total, int) and total > 0 and isinstance(n, int):
                        bar.stop()
                        bar.configure(mode='determinate')
                        bar.set(max(0, min(1, n / total)))
                        unidad = 'páginas incorporadas' if texto.startswith('Incorporando páginas') else 'elementos procesados'
                        detail.configure(text=f'{n} de {total} {unidad}')
                    else:
                        bar.stop()
                        bar.configure(mode='indeterminate')
                        bar.start()
                        detail.configure(text='Procesando…')
                elif kind == 'dialog':
                    callback, a, kw, response = value
                    try:
                        kw.setdefault('parent', win)
                        response.put((True, callback(*a, **kw)))
                    except BaseException as exc:
                        response.put((False, exc))
                    finally:
                        if win.winfo_exists():
                            win.grab_set()
                elif kind == 'done':
                    resultado.append(value)
                    bar.stop()
                    win.destroy()
                    return
            win.after(40, poll)

        try:
            threading.Thread(target=worker, name='AXIA-PDF', daemon=False).start()
            win.after(40, poll)
            parent.wait_window(win)
        finally:
            _active = False
            if prior_grab is not None and prior_grab.winfo_exists():
                prior_grab.grab_set()
        if not resultado:
            raise RuntimeError('La ventana de progreso se cerró antes de confirmar el PDF.')
        ok, value = resultado[0]
        if not ok:
            raise value
        return value
    return wrapper
