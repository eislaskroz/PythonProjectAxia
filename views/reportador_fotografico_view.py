"""Reportador Fotográfico 100% nativo CustomTkinter, sin navegador ni login propio.

Replica los flujos de captura, 50 actividades, 1-5 fotos, OS 1-4,
historial, borradores recuperables, PDF, finalización y reapertura.
Los usuarios se administran en el módulo común AXIA Usuarios.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox
from uuid import uuid4
import os
import tempfile

import customtkinter as ctk
from PIL import Image, ImageOps

from services import reportador_fotografico_service as rf
from security.permissions import obtener_tipo_usuario
from app_context import obtener_usuario_actual
from utils import centrar_ventana

AZUL = '#102B4B'
AZUL_CLARO = '#0369F8'
FONDO = '#F4F7FA'
BLANCO = '#FFFFFF'
BORDE = '#CBDDE8'
TEXTO = '#122A42'
MUTED = '#64748B'
VERDE = '#16803C'
ROJO = '#CC2838'


def mostrar_reportador_fotografico(parent, app):
    if not rf.permite_reportador():
        messagebox.showerror('Permiso denegado', 'Acceso exclusivo para usuarios 1, 2, 3 y 4.')
        return
    ReportadorFotografico(parent, app)


class ReportadorFotografico:
    def __init__(self, parent, app):
        self.app = app
        self.parent = parent
        self.report_id = None
        self.estado = 'BORRADOR'
        self.draft_key = str(uuid4())
        self.fields = {}
        self.activities = []
        self.autosave_job = None
        self.restoring = False
        self.contenedor = ctk.CTkFrame(parent, fg_color=FONDO, corner_radius=0)
        self.contenedor.pack(fill='both', expand=True)
        self._header()
        self.content = ctk.CTkFrame(self.contenedor, fg_color='transparent')
        self.content.pack(fill='both', expand=True, padx=12, pady=(5, 8))
        self.panel()

    def _header(self):
        bar = ctk.CTkFrame(self.contenedor, fg_color=BLANCO, border_width=1,
                           border_color=BORDE, corner_radius=10, height=61)
        bar.pack(fill='x', padx=12, pady=(9, 2))
        row = ctk.CTkFrame(bar, fg_color='transparent')
        row.pack(fill='x', padx=15, pady=9)
        ctk.CTkLabel(row, text='AXIA  |  Reportador fotográfico', text_color=AZUL,
                     font=ctk.CTkFont(size=18, weight='bold')).pack(side='left')
        for text, cb in [('Panel', self.panel), ('Nuevo reporte', self.nuevo),
                         ('Historial', self.historial)]:
            ctk.CTkButton(row, text=text, width=115, height=36, command=cb,
                          fg_color=AZUL_CLARO if text == 'Nuevo reporte' else AZUL,
                          hover_color='#15466B').pack(side='right', padx=3)

    def _clear(self):
        if self.autosave_job:
            try:
                self.contenedor.after_cancel(self.autosave_job)
            except Exception:
                pass
            self.autosave_job = None
        for widget in self.content.winfo_children():
            widget.destroy()
        self.fields = {}
        self.activities = []

    def _scroll(self):
        frame = ctk.CTkScrollableFrame(self.content, fg_color='transparent',
                                       scrollbar_button_color='#7A9CB4',
                                       scrollbar_button_hover_color=AZUL_CLARO)
        frame.pack(fill='both', expand=True)
        return frame

    def _panel(self, parent, title: str, subtitle: str = ''):
        frame = ctk.CTkFrame(parent, fg_color=BLANCO, border_color=BORDE,
                             border_width=1, corner_radius=10)
        frame.pack(fill='x', padx=3, pady=7)
        ctk.CTkLabel(frame, text=title, text_color=AZUL,
                     font=ctk.CTkFont(size=15, weight='bold'),
                     anchor='w').pack(fill='x', padx=16, pady=(14, 2))
        if subtitle:
            ctk.CTkLabel(frame, text=subtitle, text_color=MUTED,
                         font=ctk.CTkFont(size=11), anchor='w', wraplength=820).pack(fill='x', padx=16)
        return frame

    def _button(self, parent, text, command, *, kind='blue', width=145):
        bg = {'blue': AZUL_CLARO, 'navy': AZUL, 'green': VERDE,
              'red': ROJO, 'grey': '#526578'}.get(kind, AZUL_CLARO)
        return ctk.CTkButton(parent, text=text, command=command, width=width,
                             height=36, corner_radius=9, fg_color=bg, hover_color='#174A70')

    def _error(self, error):
        messagebox.showerror('AXIA Reportador', str(error), parent=self.contenedor.winfo_toplevel())

    def panel(self):
        self._clear()
        area = self._scroll()
        actor = obtener_usuario_actual()
        card = self._panel(area, 'Panel principal',
                           f"Bienvenido, {actor.get('nombre') or actor.get('usuario')}. Gestiona reportes de servicio, fotografías y órdenes de servicio.")
        actions = ctk.CTkFrame(card, fg_color='transparent')
        actions.pack(fill='x', padx=15, pady=15)
        self._button(actions, '+ Crear reporte', self.nuevo).pack(side='left', padx=5)
        self._button(actions, 'Historial', self.historial, kind='navy').pack(side='left', padx=5)
        try:
            reportes = rf.listar_reportes()
            pend = sum(x.get('estado') == 'BORRADOR' for x in reportes)
            fini = sum(x.get('estado') == 'FINALIZADO' for x in reportes)
            msg = f'Reportes recientes: {len(reportes)}   |   Borradores: {pend}   |   Finalizados: {fini}'
        except Exception as exc:
            msg = f'No se pudo consultar Supabase: {exc}'
        ctk.CTkLabel(card, text=msg, text_color=TEXTO, anchor='w',
                     wraplength=850).pack(fill='x', padx=20, pady=(0, 15))
        try:
            drafts = rf.listar_autoguardados()
        except Exception:
            drafts = []
        if drafts:
            box = self._panel(area, 'Borradores recuperables',
                              'La captura se guarda temporalmente en Supabase. Las fotos se suben al guardar el reporte.')
            for draft in drafts[:10]:
                row = ctk.CTkFrame(box, fg_color=FONDO, corner_radius=7)
                row.pack(fill='x', padx=14, pady=3)
                data = draft.get('datos') or {}
                label = f"{data.get('aco') or 'Sin ACO'}  ·  {draft.get('actualizado_en', '')[:16]}"
                ctk.CTkLabel(row, text=label, text_color=TEXTO, anchor='w').pack(side='left', padx=10)
                self._button(row, 'Recuperar', lambda d=draft: self.recuperar(d), width=110).pack(side='right', padx=8, pady=5)
                self._button(row, 'Eliminar', lambda d=draft: self.eliminar_borrador(d),
                             kind='red', width=100).pack(side='right', padx=(2, 0), pady=5)

    def eliminar_borrador(self, draft: dict):
        """Quita un único autoguardado; no borra el reporte formal ni sus fotos."""
        clave = str(draft.get('clave') or '').strip()
        if not clave:
            self._error('El borrador no tiene identificador válido para eliminarlo.')
            return
        datos = draft.get('datos') or {}
        aco = str(datos.get('aco') or 'Sin ACO')
        if not messagebox.askyesno(
            'Eliminar borrador',
            f'¿Eliminar definitivamente el autoguardado de {aco}?\n\n'
            'Esta acción no elimina un reporte ya guardado ni sus fotografías.',
            parent=self.contenedor.winfo_toplevel(),
        ):
            return
        try:
            rf.borrar_autoguardado(clave)
        except Exception as exc:
            self._error(f'No se pudo eliminar el borrador: {exc}')
            return
        # Al refrescar se cancela cualquier autoguardado pendiente de esta vista.
        # Si se elimina el borrador que estaba abierto, se reinicia su identidad
        # para que no vuelva a crearse con la misma clave por accidente.
        if self.draft_key == clave:
            self.draft_key = str(uuid4())
        self.panel()

    def recuperar(self, draft: dict):
        self.nuevo(datos=draft.get('datos') or {}, id_reporte=draft.get('reporte_id'),
                   draft_key=draft['clave'])

    def historial(self, buscar: str = ''):
        self._clear()
        area = self._scroll()
        card = self._panel(area, 'Historial de reportes', 'Buscar por ACO, cliente o servicio. Los finalizados se consultan en modo lectura.')
        filtro = ctk.CTkFrame(card, fg_color='transparent')
        filtro.pack(fill='x', padx=16, pady=10)
        entrada = ctk.CTkEntry(filtro, width=350, height=36, placeholder_text='Buscar ACO, cliente o servicio')
        entrada.insert(0, buscar)
        entrada.pack(side='left', padx=(0, 8))
        self._button(filtro, 'Buscar', lambda: self.historial(entrada.get()), width=90).pack(side='left')
        self._button(filtro, '+ Nuevo', self.nuevo, width=90).pack(side='right')
        try:
            rows = rf.listar_reportes(buscar)
        except Exception as exc:
            self._error(exc)
            rows = []
        if not rows:
            ctk.CTkLabel(card, text='Sin reportes para mostrar.', text_color=MUTED).pack(pady=20)
        for r in rows:
            item = ctk.CTkFrame(card, fg_color=FONDO, border_color=BORDE, border_width=1, corner_radius=7)
            item.pack(fill='x', padx=14, pady=5)
            ctk.CTkLabel(item, text=f"{r.get('aco','')}  ·  {r.get('cliente','')}  ·  {r.get('nombre_servicio','')}",
                         text_color=AZUL, anchor='w', font=ctk.CTkFont(size=12, weight='bold'))\
                .pack(fill='x', padx=10, pady=(8, 1))
            ctk.CTkLabel(item, text=f"Fecha: {rf.fecha_para_mostrar(r.get('fecha_servicio',''))}   |   Estado: {r.get('estado','')}   |   ID: {r.get('id_reporte','')}",
                         text_color=MUTED, anchor='w').pack(fill='x', padx=10)
            opts = ctk.CTkFrame(item, fg_color='transparent')
            opts.pack(fill='x', padx=8, pady=8)
            id_ = int(r['id_reporte'])
            self._button(opts, 'Ver / Editar', lambda n=id_: self.abrir(n), width=112).pack(side='left', padx=3)
            self._button(opts, 'Órdenes OS', lambda n=id_: self.ordenes(n), width=105, kind='navy').pack(side='left', padx=3)
            self._button(opts, 'PDF', lambda n=id_: self.vista_pdf(n), width=70, kind='grey').pack(side='left', padx=3)
            if r['estado'] == 'BORRADOR':
                self._button(opts, 'Finalizar', lambda n=id_: self.estado_cambiar(n, 'finalizar'), width=100, kind='green').pack(side='right', padx=4)
            elif obtener_tipo_usuario(obtener_usuario_actual()) == 1:
                self._button(opts, 'Reabrir', lambda n=id_: self.estado_cambiar(n, 'reabrir'), width=100, kind='navy').pack(side='right', padx=4)

    def estado_cambiar(self, id_reporte: int, accion: str):
        verbo = 'finalizar y bloquear' if accion == 'finalizar' else 'reabrir para editar'
        if not messagebox.askyesno('Confirmar', f'¿Deseas {verbo} el reporte #{id_reporte}?'):
            return
        try:
            rf.cambiar_estado(id_reporte, accion)
            self.historial()
        except Exception as exc:
            self._error(exc)

    def _aplicar_aco(self, aco: dict) -> None:
        """Completa datos de db_acos sin sobrescribir al autor ni la fecha."""
        if self.estado == 'FINALIZADO':
            return
        equivalencias = {
            'aco': 'aco_numero',
            'cliente': 'cliente',
            'sucursal': 'sucursal',
            'nombre_servicio': 'nombre_servicio',
        }
        for destino, origen in equivalencias.items():
            campo = self.fields.get(destino)
            if campo is None:
                continue
            # El ACO solo se selecciona del catálogo; los otros campos pueden
            # corregirse si el maestro aún no tiene el dato disponible.
            if destino == 'aco':
                campo.configure(state='normal')
            campo.delete(0, 'end')
            campo.insert(0, str(aco.get(origen) or ''))
            if destino == 'aco':
                campo.configure(state='disabled')
        self._changed()
        if not aco.get('sucursal') or not aco.get('nombre_servicio'):
            messagebox.showinfo('Datos incompletos del ACO',
                'El ACO seleccionado no tiene toda la información de sucursal o servicio. '
                'Completa únicamente los campos faltantes antes de guardar.')

    def _abrir_selector_aco(self) -> None:
        """Buscador autenticado de ACOs sin navegar fuera de AXIA."""
        if self.estado == 'FINALIZADO':
            return
        dialog = ctk.CTkToplevel(self.contenedor)
        dialog.title('Seleccionar ACO de AXIA')
        centrar_ventana(dialog, 760, 590, padre=self.contenedor.winfo_toplevel())
        dialog.minsize(610, 420)
        dialog.transient(self.contenedor.winfo_toplevel())
        dialog.configure(fg_color=FONDO)
        ctk.CTkLabel(dialog, text='Selecciona un ACO registrado en AXIA',
                     font=ctk.CTkFont(size=18, weight='bold'), text_color=AZUL).pack(
                         fill='x', padx=18, pady=(18, 8))
        search = ctk.CTkFrame(dialog, fg_color='transparent')
        search.pack(fill='x', padx=18, pady=6)
        entrada = ctk.CTkEntry(search, height=37, placeholder_text='Número de ACO o cliente')
        entrada.pack(side='left', fill='x', expand=True, padx=(0, 9))
        resultados = ctk.CTkScrollableFrame(dialog, fg_color=BLANCO, border_width=1,
                                             border_color=BORDE)
        resultados.pack(fill='both', expand=True, padx=18, pady=(8, 16))
        def buscar(_event=None):
            for hijo in resultados.winfo_children():
                hijo.destroy()
            try:
                datos = rf.consultar_acos(entrada.get().strip())
            except Exception as exc:
                ctk.CTkLabel(resultados, text=f'Error al consultar ACOs: {exc}',
                             text_color=ROJO, wraplength=670).pack(pady=14)
                return
            if not datos:
                ctk.CTkLabel(resultados, text='No se encontraron ACOs para esta búsqueda.',
                             text_color=MUTED).pack(pady=14)
            for aco in datos:
                fila = ctk.CTkFrame(resultados, fg_color=FONDO, corner_radius=7)
                fila.pack(fill='x', padx=5, pady=4)
                numero = str(aco.get('aco_numero') or '')
                cliente = str(aco.get('cliente') or 'Sin cliente')
                sucursal = str(aco.get('sucursal') or 'Sin sucursal')
                ctk.CTkLabel(fila, text=f'{numero}  ·  {cliente}  ·  {sucursal}',
                             text_color=TEXTO, anchor='w').pack(side='left', fill='x',
                                                                  expand=True, padx=10, pady=10)
                def elegir(item=aco):
                    try:
                        detalle = rf.consultar_aco(str(item.get('aco_numero') or ''))
                    except Exception as exc:
                        self._error(exc)
                        return
                    dialog.destroy()
                    self._aplicar_aco(detalle)
                self._button(fila, 'Seleccionar', elegir, width=100).pack(side='right', padx=8)
        self._button(search, 'Buscar', buscar, width=95).pack(side='right')
        entrada.bind('<Return>', buscar, add='+')
        dialog.after(150, buscar)

    def nuevo(self, datos: dict | None = None, id_reporte: int | None = None, draft_key: str | None = None):
        self._clear()
        self.report_id = id_reporte
        self.draft_key = draft_key or str(uuid4())
        self.estado = str((datos or {}).get('estado') or 'BORRADOR')
        self.restoring = True
        area = self._scroll()
        card = self._panel(area, 'Nuevo reporte fotográfico' if not id_reporte else f'Reporte #{id_reporte}',
                           'Datos generales, actividades y evidencias. Máximo 50 actividades y 5 fotografías por actividad.')
        fields = ctk.CTkFrame(card, fg_color='transparent')
        fields.pack(fill='x', padx=15, pady=8)
        fields.grid_columnconfigure((0, 1), weight=1)
        metadata = [('aco', 'ACO'), ('cliente', 'Cliente'), ('sucursal', 'Sucursal o sitio'),
                    ('nombre_servicio', 'Nombre del servicio'), ('tecnico_responsable', 'Técnico responsable'),
                    ('fecha_servicio', 'Fecha (DD-MM-AAAA)')]
        values = datos or {}
        for i, (name, label) in enumerate(metadata):
            cell = ctk.CTkFrame(fields, fg_color='transparent')
            cell.grid(row=i//2, column=i%2, sticky='ew', padx=6, pady=5)
            ctk.CTkLabel(cell, text=label, text_color=TEXTO, anchor='w').pack(fill='x')
            acol = ctk.CTkFrame(cell, fg_color='transparent') if name == 'aco' else None
            if acol is not None:
                acol.pack(fill='x')
            ent = ctk.CTkEntry(acol or cell, height=35, border_color=BORDE,
                               placeholder_text='DD-MM-AAAA' if name=='fecha_servicio' else '')
            if name == 'aco':
                ent.pack(side='left', fill='x', expand=True)
                self._button(acol, 'Seleccionar ACO', self._abrir_selector_aco,
                             kind='navy', width=145).pack(side='right', padx=(8, 0))
            else:
                ent.pack(fill='x')
            ent.insert(0, (rf.fecha_para_mostrar(values.get(name)) if values.get(name) else date.today().strftime('%d-%m-%Y')) if name == 'fecha_servicio' else str(values.get(name) or ''))
            if name == 'aco':
                ent.configure(state='disabled')
            else:
                ent.bind('<KeyRelease>', self._changed, add='+')
            self.fields[name] = ent
        ctk.CTkLabel(card, text='Observaciones generales (opcional)', text_color=TEXTO,
                     anchor='w').pack(fill='x', padx=20)
        obs = ctk.CTkTextbox(card, height=79, fg_color=FONDO, border_color=BORDE, border_width=1)
        obs.pack(fill='x', padx=18, pady=(3, 10))
        obs.insert('1.0', str(values.get('observaciones') or ''))
        obs.bind('<KeyRelease>', self._changed, add='+')
        self.fields['observaciones'] = obs
        block = self._panel(area, 'Actividades y evidencias',
                            'Selecciona de 1 a 5 fotos por actividad. Puedes agregar, cambiar o eliminar cada foto sin afectar las demás.')
        self.activity_host = ctk.CTkFrame(block, fg_color='transparent')
        self.activity_host.pack(fill='x', padx=12, pady=6)
        acts = values.get('actividades') or [rf.nueva_actividad()]
        for act in acts[:rf.MAX_ACTIVIDADES]:
            self._add_activity(act)
        if self.estado != 'FINALIZADO':
            self._button(block, '+ Agregar actividad', self._add_activity,
                         kind='navy', width=185).pack(pady=(5, 12))
        actions = ctk.CTkFrame(area, fg_color='transparent')
        actions.pack(fill='x', padx=8, pady=12)
        if self.estado != 'FINALIZADO':
            self._button(actions, 'Guardar borrador', self.guardar,
                         kind='green', width=172).pack(side='right', padx=5)
        self._button(actions, 'Historial', self.historial, kind='grey').pack(side='left', padx=5)
        if id_reporte:
            self._button(actions, 'Órdenes OS', lambda: self.ordenes(self.report_id), kind='navy', width=125).pack(side='right', padx=5)
            self._button(actions, 'PDF', lambda: self.vista_pdf(self.report_id), kind='grey', width=90).pack(side='right', padx=5)
        if self.estado == 'FINALIZADO':
            self._bloquear_edicion()
        self.restoring = False

    def _bloquear_edicion(self):
        for entry in self.fields.values():
            entry.configure(state='disabled')
        for act in self.activities:
            for field in ('titulo', 'descripcion'):
                act[field].configure(state='disabled')
            act['cantidad'].configure(state='disabled')
            act['checkbox'].configure(state='disabled')
            for btn in act['buttons']:
                btn.configure(state='disabled')

    def _changed(self, _event=None):
        if self.restoring or self.estado == 'FINALIZADO':
            return
        if self.autosave_job:
            try:
                self.contenedor.after_cancel(self.autosave_job)
            except Exception:
                pass
        self.autosave_job = self.contenedor.after(2200, self._autoguardar)

    def _autoguardar(self):
        self.autosave_job = None
        try:
            if self.fields and self.estado != 'FINALIZADO':
                rf.guardar_autoguardado(self.draft_key, self.report_id, self._snapshot())
        except Exception:
            # Fallo de red temporal; no bloquear al técnico mientras escribe.
            pass

    def _add_activity(self, data: dict | None = None):
        if len(self.activities) >= rf.MAX_ACTIVIDADES:
            messagebox.showwarning('Límite', f'Máximo {rf.MAX_ACTIVIDADES} actividades por reporte.')
            return
        item = data or rf.nueva_actividad()
        key = item.get('clave') or str(uuid4())
        box = ctk.CTkFrame(self.activity_host, fg_color=FONDO, border_color=BORDE,
                           border_width=1, corner_radius=9)
        box.pack(fill='x', padx=4, pady=7)
        top = ctk.CTkFrame(box, fg_color='transparent')
        top.pack(fill='x', padx=12, pady=(8, 4))
        heading = ctk.CTkLabel(top, text=f'Actividad {len(self.activities)+1}', text_color=AZUL,
                               font=ctk.CTkFont(size=13, weight='bold'))
        heading.pack(side='left')
        activity = {'clave': key, 'box': box, 'heading': heading, 'buttons': [], 'pendientes': {},
                    'fotos': {int(n): str(name) for n, name in item.get('fotos', {}).items()}}
        self.activities.append(activity)
        for label, fn in [('↑', lambda a=activity: self._reordenar(a, -1)),
                          ('↓', lambda a=activity: self._reordenar(a, 1)),
                          ('×', lambda a=activity: self._quitar_actividad(a))]:
            b = self._button(top, label, fn, kind='red' if label=='×' else 'navy', width=38)
            b.pack(side='right', padx=3)
            activity['buttons'].append(b)
        ctk.CTkLabel(box, text='Título *', text_color=TEXTO, anchor='w').pack(fill='x', padx=13)
        title = ctk.CTkEntry(box, height=34, border_color=BORDE)
        title.pack(fill='x', padx=13, pady=3)
        title.insert(0, str(item.get('titulo') or ''))
        title.bind('<KeyRelease>', self._changed, add='+')
        activity['titulo'] = title
        desc_head = ctk.CTkFrame(box, fg_color='transparent')
        desc_head.pack(fill='x', padx=12, pady=(3, 0))
        enable = ctk.BooleanVar(value=bool(item.get('descripcion_habilitada', True)))
        checkbox = ctk.CTkCheckBox(desc_head, text='Incluir descripción (opcional)', variable=enable,
                                   text_color=TEXTO, checkbox_width=19, checkbox_height=19)
        checkbox.pack(side='left')
        activity['enable'] = enable
        activity['checkbox'] = checkbox
        desc = ctk.CTkTextbox(box, height=62, fg_color=BLANCO, border_width=1, border_color=BORDE)
        desc.pack(fill='x', padx=13, pady=(4, 6))
        desc.insert('1.0', str(item.get('descripcion') or ''))
        desc.bind('<KeyRelease>', self._changed, add='+')
        activity['descripcion'] = desc
        def actualizar_descripcion():
            if enable.get():
                desc.pack(fill='x', padx=13, pady=(4, 6), after=desc_head)
            else:
                desc.pack_forget()
            self._changed()
        checkbox.configure(command=actualizar_descripcion)
        if not enable.get():
            desc.pack_forget()
        count_row = ctk.CTkFrame(box, fg_color='transparent')
        count_row.pack(fill='x', padx=13, pady=4)
        ctk.CTkLabel(count_row, text='Fotografías requeridas (1 a 5):', text_color=TEXTO).pack(side='left', padx=(0, 10))
        count = ctk.CTkOptionMenu(count_row, values=['1','2','3','4','5'], width=80,
                                  command=lambda _value: self._cantidad_cambio(activity),
                                  fg_color=AZUL_CLARO)
        count.set(str(item.get('cantidad_fotos') or 2))
        count.pack(side='left')
        activity['cantidad'] = count
        elegir_fotos = self._button(count_row, 'Elegir fotos',
                                  lambda a=activity: self._elegir_fotos(a), width=120)
        elegir_fotos.pack(side='right')
        activity['buttons'].append(elegir_fotos)
        preview = ctk.CTkFrame(box, fg_color='transparent')
        preview.pack(fill='x', padx=10, pady=(3, 12))
        activity['preview'] = preview
        self._actualizar_fotos(activity)
        if self.estado == 'FINALIZADO':
            title.configure(state='disabled')
            desc.configure(state='disabled')
            count.configure(state='disabled')
            checkbox.configure(state='disabled')
            for btn in activity['buttons']:
                btn.configure(state='disabled')
        self._changed()

    def _reordenar(self, activity: dict, offset: int):
        pos = self.activities.index(activity)
        nextpos = pos + offset
        if not 0 <= nextpos < len(self.activities):
            return
        self.activities.pop(pos)
        self.activities.insert(nextpos, activity)
        for index, act in enumerate(self.activities, 1):
            act['box'].pack_forget()
            act['box'].pack(fill='x', padx=4, pady=7)
            act['heading'].configure(text=f'Actividad {index}')
        self._changed()

    def _quitar_actividad(self, activity: dict):
        if len(self.activities) <= 1:
            messagebox.showwarning('Actividad', 'Se requiere al menos una actividad.')
            return
        if not messagebox.askyesno('Quitar actividad', '¿Eliminar esta actividad del borrador? Sus fotos guardadas se desvincularán al guardar.'):
            return
        self.activities.remove(activity)
        activity['box'].destroy()
        for idx, act in enumerate(self.activities, 1):
            act['heading'].configure(text=f'Actividad {idx}')
        self._changed()

    def _cantidad_cambio(self, activity):
        qty = int(activity['cantidad'].get())
        extras = [n for n in activity['pendientes'] if n > qty]
        extras += [n for n in activity['fotos'] if n > qty]
        if extras and not messagebox.askyesno('Eliminar fotos sobrantes',
                 'Al guardar se quitarán las fotos por encima de la nueva cantidad. ¿Continuar?'):
            activity['cantidad'].set(str(max(extras)))
            return
        activity['pendientes'] = {n:p for n,p in activity['pendientes'].items() if n<=qty}
        activity['fotos'] = {n:p for n,p in activity['fotos'].items() if n<=qty}
        self._actualizar_fotos(activity)
        self._changed()

    def _elegir_fotos(self, activity: dict):
        qty = int(activity['cantidad'].get())
        paths = filedialog.askopenfilenames(parent=self.contenedor.winfo_toplevel(),
                  title=f'Selecciona exactamente {qty} fotografías',
                  filetypes=[('Imágenes', '*.jpg *.jpeg *.png *.webp')])
        if not paths:
            return
        if len(paths) != qty:
            messagebox.showwarning('Fotografías', f'Selecciona exactamente {qty} imágenes.')
            return
        for path in paths:
            try:
                rf.preparar_jpeg(path)
            except Exception as exc:
                self._error(exc)
                return
        activity['pendientes'] = dict(enumerate(paths, 1))
        self._actualizar_fotos(activity)
        self._changed()

    def _cambiar_foto(self, act: dict, slot: int):
        """Reemplaza solo la fotografía indicada, sin tocar los demás espacios."""
        if self.estado == 'FINALIZADO':
            return
        path = filedialog.askopenfilename(
            parent=self.contenedor.winfo_toplevel(),
            title=f'Selecciona la fotografía {slot}',
            filetypes=[('Imágenes', '*.jpg *.jpeg *.png *.webp')],
        )
        if not path:
            return
        try:
            rf.preparar_jpeg(path)
        except Exception as exc:
            self._error(exc)
            return
        act['pendientes'][slot] = path
        self._actualizar_fotos(act)
        self._changed()

    def _eliminar_foto(self, act: dict, slot: int):
        """Elimina exclusivamente un espacio de evidencia del borrador.

        Una foto ya subida se elimina inmediatamente de Supabase mediante la
        operación existente 'quitar_imagen'; las demás no se modifican.
        """
        if self.estado == 'FINALIZADO':
            return
        pendiente = slot in act['pendientes']
        guardada = slot in act['fotos'] and self.report_id is not None
        if not pendiente and not guardada:
            return
        explicacion = (
            f'¿Eliminar únicamente la Foto {slot} de esta actividad?\n\n'
            'Las demás fotografías permanecerán intactas.'
        )
        if guardada:
            explicacion += '\n\nLa fotografía guardada se eliminará del servidor.'
        if not messagebox.askyesno(
            'Eliminar fotografía', explicacion,
            parent=self.contenedor.winfo_toplevel(),
        ):
            return
        # No modificar la pantalla si Supabase rechaza la eliminación.
        if guardada:
            try:
                rf.quitar_imagen(self.report_id, slot, act['clave'])
            except Exception as exc:
                self._error(f'No se pudo eliminar la Foto {slot}: {exc}')
                return
        act['pendientes'].pop(slot, None)
        act['fotos'].pop(slot, None)
        self._actualizar_fotos(act)
        self._changed()

    def _actualizar_fotos(self, act):
        for widget in act['preview'].winfo_children():
            widget.destroy()
        qty = int(act['cantidad'].get())
        for slot in range(1, qty+1):
            box = ctk.CTkFrame(act['preview'], fg_color=BLANCO,
                               border_color=BORDE, border_width=1, corner_radius=7)
            box.pack(side='left', padx=3, pady=5, ipadx=4)
            ctk.CTkLabel(box, text=f'Foto {slot}', text_color=AZUL).pack(padx=8, pady=(5, 0))
            local = act['pendientes'].get(slot)
            saved = slot in act['fotos']
            if local:
                try:
                    with Image.open(local) as f:
                        thumb = ImageOps.exif_transpose(f).convert('RGB')
                        thumb.thumbnail((110, 72))
                    photo = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=thumb.size)
                    label = ctk.CTkLabel(box, text='', image=photo)
                    label.photo = photo
                    label.pack(pady=2)
                except Exception:
                    pass
            ctk.CTkLabel(box, text='Nueva' if local else ('Guardada' if saved else 'Pendiente'),
                         text_color=VERDE if (saved or local) else MUTED,
                         font=ctk.CTkFont(size=10)).pack(padx=8, pady=(0, 5))
            if saved and self.report_id and not local:
                self._button(box, 'Ver', lambda n=slot,a=act: self._preview_foto(self.report_id,n,a['clave']),
                             width=60, kind='grey').pack(pady=(0, 3))
            if self.estado != 'FINALIZADO':
                # Cada recuadro controla únicamente su propio número de foto.
                # Incluso un espacio vacío admite cargar una sola imagen.
                self._button(box, 'Cambiar' if (local or saved) else 'Agregar',
                             lambda n=slot,a=act: self._cambiar_foto(a, n),
                             width=72, kind='blue').pack(padx=5, pady=(1, 3))
                if local or saved:
                    self._button(box, 'Eliminar',
                                 lambda n=slot,a=act: self._eliminar_foto(a, n),
                                 width=72, kind='red').pack(padx=5, pady=(0, 5))

    def _snapshot(self) -> dict:
        values = {key: widget.get().strip() for key, widget in self.fields.items() if key!='observaciones'}
        values['fecha_servicio'] = rf.fecha_para_guardar(values['fecha_servicio'])
        if 'observaciones' in self.fields:
            values['observaciones'] = self.fields['observaciones'].get('1.0','end-1c').strip()
        values['actividades'] = []
        for a in self.activities:
            values['actividades'].append({
                'clave': a['clave'], 'titulo': a['titulo'].get().strip(),
                'descripcion': a['descripcion'].get('1.0','end-1c').strip() if a['enable'].get() else '',
                'descripcion_habilitada': bool(a['enable'].get()),
                'cantidad_fotos': int(a['cantidad'].get()),
            })
        return values

    def guardar(self):
        if self.estado == 'FINALIZADO':
            self._error('No puedes editar reportes finalizados.')
            return
        try:
            datos = self._snapshot()
            rf.validar_captura(datos)
            id_ = rf.guardar_reporte(self.report_id, datos)
            self.report_id = id_
            errors = []
            for act in self.activities:
                for slot, path in list(act['pendientes'].items()):
                    try:
                        rf.subir_imagen(id_, path, slot, act['clave'])
                        act['fotos'][slot] = Path(path).name
                        del act['pendientes'][slot]
                    except Exception as exc:
                        errors.append(f"{act['titulo'].get()} · Foto {slot}: {exc}")
            if errors:
                self._error('Se guardó el borrador, pero faltó subir alguna imagen:\n'+'\n'.join(errors[:4])+
                            '\nGuarda nuevamente cuando se restablezca la conexión.')
                return
            try:
                rf.borrar_autoguardado(self.draft_key)
            except Exception:
                pass
            messagebox.showinfo('Reporte guardado', f'Borrador #{id_} guardado correctamente.')
            self.abrir(id_)
        except Exception as exc:
            self._error(exc)

    def abrir(self, id_reporte: int):
        try:
            data = rf.obtener_reporte(id_reporte)
        except Exception as exc:
            self._error(exc)
            return
        values = dict(data['reporte'])
        fotos = {}
        for f in data.get('fotos') or []:
            fotos.setdefault(str(f['clave_actividad']), {})[int(f['numero'])] = f.get('nombre_original') or 'Foto'
        values['actividades'] = []
        for act in data.get('actividades') or []:
            item = dict(act)
            item['fotos'] = fotos.get(str(act['clave']), {})
            values['actividades'].append(item)
        self.nuevo(values, id_reporte)

    def _preview_foto(self, id_reporte: int, numero: int, clave: str | None=None, *, os=False):
        try:
            from io import BytesIO
            content = rf.leer_imagen(id_reporte, numero, clave, os=os)
            with Image.open(BytesIO(content)) as f:
                photo = f.convert('RGB').copy()
            photo.thumbnail((820, 600))
            win = ctk.CTkToplevel(self.contenedor)
            win.title('AXIA · Imagen de evidencia')
            centrar_ventana(win, 880, 660, padre=self.contenedor.winfo_toplevel())
            win.transient(self.contenedor.winfo_toplevel())
            ctkimg = ctk.CTkImage(light_image=photo, dark_image=photo, size=photo.size)
            label = ctk.CTkLabel(win, text='', image=ctkimg)
            label.photo = ctkimg
            label.pack(expand=True, fill='both', padx=15, pady=15)
        except Exception as exc:
            self._error(exc)

    def ordenes(self, id_reporte: int):
        try:
            detalle = rf.obtener_reporte(id_reporte)
        except Exception as exc:
            self._error(exc)
            return
        self._clear()
        self.report_id = id_reporte
        reporte = detalle['reporte']
        final = reporte.get('estado') == 'FINALIZADO'
        photos = {int(f['numero']): f for f in detalle.get('ordenes') or []}
        area = self._scroll()
        card = self._panel(area, f'Órdenes de Servicio · {reporte.get("aco")}',
                           'Selecciona entre 1 y 4 órdenes. Todas serán obligatorias antes de finalizar.')
        row = ctk.CTkFrame(card, fg_color='transparent')
        row.pack(fill='x', padx=15, pady=10)
        ctk.CTkLabel(row, text='Cantidad de OS:', text_color=TEXTO).pack(side='left', padx=5)
        qty = ctk.CTkOptionMenu(row, values=['1','2','3','4'], fg_color=AZUL_CLARO, width=80)
        qty.set(str(reporte.get('cantidad_os') or 1))
        qty.pack(side='left')
        pending = {}
        list_frame = ctk.CTkFrame(card, fg_color='transparent')
        list_frame.pack(fill='x', padx=15)

        def render(_ignored=None):
            for child in list_frame.winfo_children():
                child.destroy()
            for n in range(1, int(qty.get())+1):
                child = ctk.CTkFrame(list_frame, fg_color=FONDO, border_color=BORDE,
                                     border_width=1, corner_radius=8)
                child.pack(fill='x', pady=4)
                ctk.CTkLabel(child, text=f'Orden de Servicio {n}', text_color=AZUL,
                             font=ctk.CTkFont(weight='bold')).pack(side='left', padx=12, pady=12)
                state = 'Nueva imagen' if n in pending else ('Documento guardado' if n in photos else 'Pendiente')
                ctk.CTkLabel(child, text=state, text_color=VERDE if n in photos or n in pending else MUTED).pack(side='left', padx=10)
                if n in photos:
                    self._button(child, 'Ver', lambda slot=n: self._preview_foto(id_reporte, slot, os=True),
                                 width=70, kind='grey').pack(side='right', padx=4)
                if not final:
                    def select(slot=n):
                        chosen = filedialog.askopenfilename(parent=self.contenedor.winfo_toplevel(),
                                  filetypes=[('Imágenes', '*.jpg *.jpeg *.png *.webp')])
                        if chosen:
                            try:
                                rf.preparar_jpeg(chosen)
                                pending[slot] = chosen
                                render()
                            except Exception as exc:
                                self._error(exc)
                    self._button(child, 'Elegir imagen', select, width=122).pack(side='right', padx=4)
        qty.configure(command=render)
        render()
        if final:
            qty.configure(state='disabled')
            ctk.CTkLabel(card, text='FINALIZADO · Solo lectura', text_color=VERDE).pack(pady=15)
        else:
            def save():
                try:
                    rf.definir_cantidad_os(id_reporte, int(qty.get()))
                    errors = []
                    for n, path in list(pending.items()):
                        if n > int(qty.get()):
                            continue
                        try:
                            rf.subir_imagen(id_reporte, path, n, os=True)
                        except Exception as exc:
                            errors.append(f'OS {n}: {exc}')
                    if errors:
                        self._error('Cantidad de OS guardada, imágenes pendientes:\n'+'\n'.join(errors))
                        return
                    messagebox.showinfo('Órdenes de Servicio', 'Documentos guardados.')
                    self.ordenes(id_reporte)
                except Exception as exc:
                    self._error(exc)
            self._button(card, 'Guardar Órdenes de Servicio', save, kind='green', width=260).pack(pady=12)
        actions = ctk.CTkFrame(area, fg_color='transparent')
        actions.pack(fill='x', pady=10)
        self._button(actions, 'Volver al reporte', lambda: self.abrir(id_reporte), kind='navy').pack(side='left', padx=5)
        self._button(actions, 'Vista previa PDF', lambda: self.vista_pdf(id_reporte), width=160).pack(side='right', padx=5)

    def vista_pdf(self, id_reporte: int):
        try:
            from io import BytesIO
            import fitz
            from services.reportador_fotografico_pdf import generar_pdf_bytes
            detalle = rf.obtener_reporte(id_reporte)
            root = Path(__file__).resolve().parent.parent
            pdfbytes = generar_pdf_bytes(detalle, logo_path=str(root/'assets'/'LogoAxia-Full.png'))
            doc = fitz.open(stream=pdfbytes, filetype='pdf')
            if not doc.page_count:
                raise rf.ErrorReportador('El PDF se generó sin páginas.')
            win = ctk.CTkToplevel(self.contenedor)
            win.title(f"AXIA · PDF {_filename(detalle['reporte'].get('aco'))}")
            centrar_ventana(win, 900, 780, padre=self.contenedor.winfo_toplevel())
            win.transient(self.contenedor.winfo_toplevel())
            toolbar = ctk.CTkFrame(win, fg_color=BLANCO)
            toolbar.pack(fill='x', padx=10, pady=8)
            view = ctk.CTkFrame(win, fg_color=FONDO)
            view.pack(fill='both', expand=True, padx=12, pady=(0, 10))
            page = {'index': 0}
            label = ctk.CTkLabel(view, text='')
            label.pack(expand=True, padx=8, pady=8)
            contador = ctk.CTkLabel(toolbar, text='', text_color=AZUL)
            contador.pack(side='left', padx=10)

            def show():
                pos = page['index']
                page_obj = doc[pos]
                scale = min(1.32, 780 / float(page_obj.rect.width), 640 / float(page_obj.rect.height))
                pix = page_obj.get_pixmap(matrix=fitz.Matrix(scale,scale), alpha=False)
                pil = Image.frombytes('RGB', (pix.width,pix.height), pix.samples)
                thumb = ctk.CTkImage(light_image=pil, dark_image=pil, size=pil.size)
                label.configure(image=thumb)
                label.image = thumb
                contador.configure(text=f'Página {pos+1} de {doc.page_count}')

            def shift(offset):
                page['index'] = (page['index'] + offset) % doc.page_count
                show()

            def saveas():
                path = filedialog.asksaveasfilename(parent=win,
                        defaultextension='.pdf', initialfile=_filename(detalle['reporte'].get('aco')),
                        filetypes=[('Documento PDF','*.pdf')])
                if path:
                    Path(path).write_bytes(pdfbytes)
                    messagebox.showinfo('PDF', 'Documento PDF guardado.', parent=win)

            self._button(toolbar, '◀ Anterior', lambda: shift(-1), width=100, kind='navy').pack(side='left', padx=4)
            self._button(toolbar, 'Siguiente ▶', lambda: shift(1), width=100, kind='navy').pack(side='left', padx=4)
            self._button(toolbar, 'Guardar PDF', saveas, width=133, kind='green').pack(side='right', padx=8)
            win.protocol('WM_DELETE_WINDOW', lambda: (doc.close(),win.destroy()))
            show()
        except Exception as exc:
            self._error(exc)


def _filename(aco: object) -> str:
    key = ''.join(c if c.isalnum() or c in '-_' else '_' for c in str(aco or 'REPORTE'))[:70]
    return f'AXIA_{key}.pdf'
