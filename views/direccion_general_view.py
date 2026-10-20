
"""Dashboard ejecutivo de Dirección General: resumen, etapas, alertas y trazabilidad."""
from pathlib import Path
from PIL import Image
import customtkinter as ctk
from ui.form_fields import AxiaEntry, AxiaTextbox
from tkinter import ttk, messagebox, Canvas

from app_context import obtener_usuario_actual
from security.permissions import puede_ver_direccion_general
from services.direccion_general_service import obtener_panel_direccion

from ui.colors import (
    WHITE, TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY, SECONDARY,
    BUTTON_HOVER, SUCCESS, WARNING, DANGER, BORDER, CONTENT_BG
)
from ui.fonts import TEXT_SM, TEXT_MD, TITLE_MD, BUTTON_FONT


BLUE = '#2563EB'
CYAN = '#0891B2'
PURPLE = '#7C3AED'
MUTED = '#64748B'
SOFT = '#EEF2F7'

# Bordes de los contenedores principales.
CONTAINER_BORDER = '#647B96'
CONTAINER_BORDER_WIDTH = 2


def _fmt(v):
    if not v:
        return '—'
    return str(v).replace('T', ' ')[:16]


def _dur(v, unit='h'):
    return '—' if v is None else f'{v:g} {unit}'


def _estado_color(e):
    e = str(e or '').upper()
    if 'FUERA' in e or e == 'VENCIDO':
        return DANGER
    if 'POR VENCER' in e:
        return WARNING
    if 'FINALIZADO EN TIEMPO' in e:
        return SUCCESS
    if 'EN TIEMPO' in e:
        return SUCCESS
    return MUTED


def _etapa(r):
    if r.get('cierre'):
        return 'Cierre'
    if r.get('ot_folio'):
        return 'Ejecución'
    if r.get('cotizaciones', 0):
        return 'Cotización'
    if r.get('fecha_autorizacion'):
        return 'Autorización'
    return 'Levantamiento'


def _icono_blanco(ruta):
    """Convierte el icono a blanco y conserva su canal de transparencia."""
    with Image.open(ruta) as imagen:
        imagen_rgba = imagen.convert('RGBA')

    alpha = imagen_rgba.getchannel('A')
    imagen_blanca = Image.new(
        'RGBA',
        imagen_rgba.size,
        (255, 255, 255, 255)
    )
    imagen_blanca.putalpha(alpha)

    return imagen_blanca


def mostrar_direccion_general(parent, app):
    if not puede_ver_direccion_general(obtener_usuario_actual()):
        messagebox.showerror(
            'Acceso denegado',
            'Esta sección está reservada para Dirección General / Administrador.'
        )
        return

    for w in parent.winfo_children():
        w.destroy()

    # Página completa con desplazamiento vertical.
    root = ctk.CTkScrollableFrame(
        parent,
        fg_color='transparent',
        scrollbar_button_color=SECONDARY,
        scrollbar_button_hover_color=BUTTON_HOVER
    )
    root.pack(fill='both', expand=True, padx=14, pady=6)

    # Encabezado.
    head = ctk.CTkFrame(
        root,
        fg_color=WHITE,
        corner_radius=16,
        border_width=CONTAINER_BORDER_WIDTH,
        border_color=CONTAINER_BORDER
    )
    head.pack(fill='x', pady=(0, 8))

    ctk.CTkLabel(
        head,
        text='Dirección General · Control Operacional',
        font=TITLE_MD,
        text_color=TEXT_PRIMARY
    ).pack(anchor='w', padx=14, pady=(10, 2))

    ctk.CTkLabel(
        head,
        text='Resumen ejecutivo, alertas y trazabilidad del ciclo LEV → Autorización → COT → OT → OS.',
        font=TEXT_SM,
        text_color=TEXT_SECONDARY
    ).pack(anchor='w', padx=14, pady=(0, 10))

    cards = ctk.CTkFrame(root, fg_color='transparent')
    cards.pack(fill='x', pady=(0, 7))

    mid = ctk.CTkFrame(root, fg_color='transparent')
    mid.pack(fill='x', pady=(0, 7))

    attention = ctk.CTkFrame(
        mid,
        fg_color=WHITE,
        corner_radius=14,
        border_width=CONTAINER_BORDER_WIDTH,
        border_color=CONTAINER_BORDER
    )
    chart_card = ctk.CTkFrame(
        mid,
        fg_color=WHITE,
        corner_radius=14,
        border_width=CONTAINER_BORDER_WIDTH,
        border_color=CONTAINER_BORDER
    )

    mid.grid_columnconfigure(0, weight=1)
    mid.grid_columnconfigure(1, weight=1)

    attention.grid(row=0, column=0, sticky='nsew', padx=(0, 4))
    chart_card.grid(row=0, column=1, sticky='nsew', padx=(4, 0))

    ctk.CTkLabel(
        attention,
        text='⚠ Procesos que requieren atención',
        font=TEXT_MD,
        text_color=TEXT_PRIMARY
    ).pack(anchor='w', padx=12, pady=(8, 4))

    attention_body = ctk.CTkFrame(attention, fg_color='transparent')
    attention_body.pack(fill='x', padx=8, pady=(0, 8))

    ctk.CTkLabel(
        chart_card,
        text='▥ Distribución por etapa',
        font=TEXT_MD,
        text_color=TEXT_PRIMARY
    ).pack(anchor='w', padx=12, pady=(8, 2))

    # Gráfica sin borde interior.
    chart = Canvas(
        chart_card,
        height=92,
        bg=WHITE,
        highlightthickness=0,
        bd=0,
        relief='flat'
    )
    chart.pack(fill='x', padx=12, pady=(0, 7))

    # Contenedor de pestañas y buscador.
    controls = ctk.CTkFrame(
        root,
        fg_color=WHITE,
        corner_radius=18,
        border_width=CONTAINER_BORDER_WIDTH,
        border_color=CONTAINER_BORDER
    )
    controls.pack(fill='x', pady=(0, 7))

    class _TabGroup:
        def __init__(self, parent, values):
            self.values = list(values)
            self._active = self.values[0]
            self._command = None

            # Contenedor sin borde para eliminar las líneas exteriores.
            self.frame = ctk.CTkFrame(
                parent,
                fg_color='transparent',
                corner_radius=16,
                border_width=0
            )
            self.buttons = []

            for idx, value in enumerate(self.values):
                btn = ctk.CTkButton(
                    self.frame,
                    text=value,
                    width=120,
                    height=34,
                    corner_radius=10,
                    fg_color='#F8FAFC',
                    hover_color='#EAF0F7',
                    text_color='#1F2937',
                    border_width=0,
                    font=('Segoe UI', 11, 'bold'),
                    command=lambda v=value: self._set_active(v)
                )
                btn.grid(
                    row=0,
                    column=idx,
                    padx=0,
                    sticky='nsew'
                )
                self.frame.grid_columnconfigure(idx, weight=1)
                self.buttons.append(btn)

            self.frame.grid(row=0, column=0, sticky='w', padx=10, pady=9)
            self.set(self._active)

        def _set_active(self, value):
            self._active = value

            for btn in self.buttons:
                active = btn.cget('text') == value
                btn.configure(
                    fg_color='#0A5BD7' if active else '#F8FAFC',
                    hover_color='#094FBE' if active else '#EAF0F7',
                    text_color='#FFFFFF' if active else '#1F2937'
                )

            if self._command is not None:
                self._command(value)

        def configure(self, command=None):
            self._command = command

        def get(self):
            return self._active

        def set(self, value):
            self._set_active(value)

    tabs = _TabGroup(
        controls,
        ['Todos', 'Levantamientos', 'Autorización', 'Cotización', 'Ejecución', 'Cierre']
    )
    tabs.set('Todos')

    search_var = ctk.StringVar()

    # Buscador con borde más fuerte.
    search_wrap = ctk.CTkFrame(
        controls,
        fg_color='#F8FAFC',
        corner_radius=12,
        border_width=2,
        border_color=CONTAINER_BORDER
    )
    search_wrap.grid(row=0, column=1, sticky='e', padx=10, pady=9)
    search_wrap.grid_columnconfigure(1, weight=1)

    carpeta_iconos = Path(__file__).resolve().parent.parent / 'assets' / 'iconos'

    with Image.open(carpeta_iconos / 'buscar.png') as imagen_buscar:
        imagen_buscar = imagen_buscar.convert('RGBA').copy()

    icono_buscar = ctk.CTkImage(
        light_image=imagen_buscar,
        dark_image=imagen_buscar,
        size=(18, 18)
    )

    ctk.CTkLabel(
        search_wrap,
        text='',
        image=icono_buscar,
        width=24,
        height=34,
        anchor='center'
    ).grid(row=0, column=0, sticky='ns', padx=(12, 8), pady=6)

    search = AxiaEntry(
        search_wrap,
        textvariable=search_var,
        width=260,
        fg_color='transparent',
        border_width=0,
        text_color=TEXT_PRIMARY
    )
    search.grid(row=0, column=1, sticky='ew', padx=(0, 12), pady=6)

    # Placeholder superpuesto del buscador.
    placeholder = ctk.CTkLabel(
        search,
        text='Buscar cliente, folio, servicio...',
        font=('Segoe UI', 12),
        text_color='#64748B',
        anchor='w',
        justify='left',
        fg_color='transparent'
    )
    placeholder.place(relx=0.02, rely=0.5, anchor='w')

    def _placeholder_busqueda(event=None):
        valor = search_var.get()
        tiene_texto = bool(str(valor).strip())
        tiene_foco = search.focus_get() == search

        if tiene_texto or tiene_foco:
            placeholder.place_forget()
        else:
            placeholder.place(relx=0.02, rely=0.5, anchor='w')

    placeholder.bind('<Button-1>', lambda event: search.focus_set())
    search_var.trace_add('write', lambda *_: _placeholder_busqueda())
    search.bind('<FocusIn>', _placeholder_busqueda)
    search.bind('<FocusOut>', _placeholder_busqueda)
    _placeholder_busqueda()

    controls.grid_columnconfigure(0, weight=1)
    controls.grid_columnconfigure(1, weight=0)

    status = ctk.CTkLabel(
        root,
        text='Consultando operación...',
        font=TEXT_SM,
        text_color=TEXT_SECONDARY
    )
    status.pack(anchor='w', pady=(0, 4))

    # Tabla con contorno reforzado y barras propias.
    table_shell = ctk.CTkFrame(
        root,
        fg_color=WHITE,
        corner_radius=14,
        border_width=CONTAINER_BORDER_WIDTH,
        border_color=CONTAINER_BORDER
    )
    table_shell.pack(fill='x', expand=False)

    cols = (
        'folio', 'cliente', 'etapa', 'responsable', 'plan',
        'avance', 'tiempo', 'estado', 'faltante'
    )
    tree = ttk.Treeview(table_shell, columns=cols, show='headings', height=12)

    labels = {
        'folio': 'Folio',
        'cliente': 'Cliente',
        'etapa': 'Etapa actual',
        'responsable': 'Responsable',
        'plan': 'Plan',
        'avance': 'Avance',
        'tiempo': 'Tiempo',
        'estado': 'Estatus',
        'faltante': 'Siguiente / faltante'
    }
    widths = {
        'folio': 90,
        'cliente': 150,
        'etapa': 105,
        'responsable': 145,
        'plan': 85,
        'avance': 65,
        'tiempo': 80,
        'estado': 145,
        'faltante': 175
    }

    for c in cols:
        tree.heading(c, text=labels[c])
        tree.column(c, width=widths[c], minwidth=55, anchor='w')

    sy = ttk.Scrollbar(table_shell, orient='vertical', command=tree.yview)
    sx = ttk.Scrollbar(table_shell, orient='horizontal', command=tree.xview)
    tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)

    tree.grid(row=0, column=0, sticky='nsew', padx=(10, 0), pady=(10, 0))
    sy.grid(row=0, column=1, sticky='ns', pady=(10, 0))
    sx.grid(row=1, column=0, sticky='ew', padx=(10, 0), pady=(0, 8))

    table_shell.grid_rowconfigure(0, weight=1)
    table_shell.grid_columnconfigure(0, weight=1)

    tree.tag_configure('danger', foreground=DANGER)
    tree.tag_configure('warning', foreground='#B45309')
    tree.tag_configure('success', foreground='#15803D')

    data = []
    visible = []

    def detail(_=None):
        sel = tree.selection()
        if not sel:
            return

        r = visible[int(sel[0])]

        win = ctk.CTkToplevel(parent)
        win.title(f"Trazabilidad {r['folio']}")
        win.geometry('940x720')
        win.grab_set()

        sc = ctk.CTkScrollableFrame(win, fg_color=CONTENT_BG)
        sc.pack(fill='both', expand=True, padx=10, pady=10)

        top = ctk.CTkFrame(
            sc,
            fg_color=WHITE,
            corner_radius=14,
            border_width=CONTAINER_BORDER_WIDTH,
            border_color=CONTAINER_BORDER
        )
        top.pack(fill='x', padx=5, pady=(3, 7))

        ctk.CTkLabel(
            top,
            text=f"{r['folio']} · {r['cliente']}",
            font=TITLE_MD,
            text_color=TEXT_PRIMARY
        ).pack(anchor='w', padx=12, pady=(10, 2))

        ctk.CTkLabel(
            top,
            text=f"{r['tipo']}  ·  {_etapa(r)}  ·  {r['estado']}",
            font=TEXT_SM,
            text_color=_estado_color(r['estado'])
        ).pack(anchor='w', padx=12, pady=(0, 10))

        sections = [
            ('① Levantamiento', [
                ('Realizado por', r['tecnico']),
                ('Inicio', _fmt(r['inicio'])),
                ('Requerimiento', r['requerimiento'] or '—'),
                ('Plan', f"{r['dias_planeados']} días / {r['personas'] or '—'} personas")
            ]),
            ('② Autorización', [
                ('Autorizó', r['autorizado_por'] or 'Pendiente'),
                ('Fecha', _fmt(r['fecha_autorizacion'])),
                ('Respuesta', _dur(r['horas_autorizacion']))
            ]),
            ('③ Cotización', [
                ('Cotizaciones', r['cotizaciones']),
                ('ESI', r['esi'] or '—'),
                ('Primera cotización', _fmt(r['fecha_cotizacion'])),
                ('Tiempo ESI', _dur(r['horas_esi'])),
                ('Autorización cliente', _fmt(r['fecha_autorizacion_cliente'])),
                ('Tiempo cliente', _dur(r['horas_cliente']))
            ]),
            ('④ Ejecución', [
                ('OT', r['ot_folio'] or 'Pendiente'),
                ('Inicio', _fmt(r['ot_inicio'])),
                ('Fecha límite', _fmt(r['fecha_limite'])),
                ('Avance', f"{r['avance']}%"),
                ('Situación', r['estado'])
            ]),
            ('⑤ Cierre', [
                ('OS', r['os_folio'] or 'Pendiente'),
                ('Cierre', _fmt(r['cierre'])),
                ('Tiempo total', _dur(r['dias_totales'], 'd')),
                ('Siguiente / faltante', r['faltante'])
            ]),
        ]

        for title, items in sections:
            card = ctk.CTkFrame(
                sc,
                fg_color=WHITE,
                corner_radius=12,
                border_width=CONTAINER_BORDER_WIDTH,
                border_color=CONTAINER_BORDER
            )
            card.pack(fill='x', padx=5, pady=4)

            ctk.CTkLabel(
                card,
                text=title,
                font=TEXT_MD,
                text_color=PRIMARY
            ).pack(anchor='w', padx=12, pady=(8, 3))

            for k, v in items:
                row = ctk.CTkFrame(card, fg_color='transparent')
                row.pack(fill='x', padx=12, pady=1)

                ctk.CTkLabel(
                    row,
                    text=k,
                    width=170,
                    anchor='w',
                    font=TEXT_SM,
                    text_color=TEXT_SECONDARY
                ).pack(side='left')

                ctk.CTkLabel(
                    row,
                    text=str(v),
                    anchor='w',
                    justify='left',
                    wraplength=680,
                    font=TEXT_SM,
                    text_color=TEXT_PRIMARY
                ).pack(side='left', fill='x', expand=True)

            ctk.CTkLabel(card, text='').pack(pady=1)

    tree.bind('<Double-1>', detail)

    def apply_filter(*_):
        nonlocal visible

        stage = tabs.get()
        q = search_var.get().strip().lower()

        stage_map = {
            'Levantamientos': 'Levantamiento',
            'Autorización': 'Autorización',
            'Cotización': 'Cotización',
            'Ejecución': 'Ejecución',
            'Cierre': 'Cierre'
        }

        visible = []

        for r in data:
            if stage != 'Todos' and _etapa(r) != stage_map.get(stage):
                continue

            blob = ' '.join(
                str(r.get(k, '') or '')
                for k in (
                    'folio', 'cliente', 'tipo', 'tecnico', 'estado',
                    'faltante', 'ot_folio', 'os_folio'
                )
            ).lower()

            if q and q not in blob:
                continue

            visible.append(r)

        for i in tree.get_children():
            tree.delete(i)

        for i, r in enumerate(visible):
            tag = (
                'danger'
                if r['estado'] == 'VENCIDO' or 'FUERA' in r['estado']
                else 'warning'
                if r['estado'] == 'POR VENCER'
                else 'success'
                if 'EN TIEMPO' in r['estado']
                else ''
            )

            resp = (
                r['esi']
                if _etapa(r) == 'Cotización' and r['esi']
                else r['tecnico']
            )

            tree.insert(
                '',
                'end',
                iid=str(i),
                tags=(tag,),
                values=(
                    r['folio'],
                    r['cliente'],
                    _etapa(r),
                    resp,
                    f"{r['dias_planeados']}d/{r['personas'] or '—'}p",
                    f"{r['avance']}%",
                    _dur(r['dias_totales'], 'd'),
                    r['estado'],
                    r['faltante']
                )
            )

        status.configure(
            text=f'{len(visible)} de {len(data)} procesos · Doble clic para consultar el expediente completo.'
        )

    tabs.configure(command=lambda _v: apply_filter())
    search_var.trace_add('write', apply_filter)

    # Botones inferiores: iconos blancos y negritas.
    imagen_detalle = _icono_blanco(carpeta_iconos / 'detalle.png')
    imagen_limpiar = _icono_blanco(carpeta_iconos / 'limpiar.png')

    icono_detalle = ctk.CTkImage(
        light_image=imagen_detalle,
        dark_image=imagen_detalle,
        size=(25, 25)
    )

    icono_actualizar = ctk.CTkImage(
        light_image=imagen_limpiar,
        dark_image=imagen_limpiar,
        size=(25, 25)
    )

    actions = ctk.CTkFrame(root, fg_color='transparent')
    actions.pack(fill='x', pady=(10, 2))

    FONT_ACTIONS = ('Segoe UI', 13, 'bold')

    btn_refresh = ctk.CTkButton(
        actions,
        text='Actualizar',
        image=icono_actualizar,
        compound='left',
        height=48,
        width=175,
        corner_radius=12,
        border_width=1,
        border_color='#52708F',
        font=FONT_ACTIONS,
        text_color=WHITE,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        anchor='center',
        command=lambda: load()
    )

    btn_detail = ctk.CTkButton(
        actions,
        text='Ver trazabilidad',
        image=icono_detalle,
        compound='left',
        height=48,
        width=195,
        corner_radius=12,
        border_width=1,
        border_color='#1747A6',
        font=FONT_ACTIONS,
        text_color=WHITE,
        fg_color=PRIMARY,
        hover_color='#1747A6',
        anchor='center',
        command=detail
    )

    btn_refresh.pack(side='right', padx=(8, 2))
    btn_detail.pack(side='right', padx=(2, 8))

    def load():
        nonlocal data

        status.configure(text='Consultando operación...')
        parent.update_idletasks()

        try:
            data = obtener_panel_direccion()
        except Exception as e:
            messagebox.showerror(
                'Dirección General',
                f'No fue posible cargar el panel.\n\n{e}'
            )
            return

        for w in cards.winfo_children():
            w.destroy()

        total = len(data)
        cerr = sum(bool(r['cierre']) for r in data)
        activos = total - cerr
        venc = sum(r['estado'] == 'VENCIDO' for r in data)
        tiempo = sum(r['estado'] == 'EN TIEMPO' for r in data)
        por_vencer = sum(r['estado'] == 'POR VENCER' for r in data)

        avg = (
            round(
                sum(
                    r['dias_totales']
                    for r in data
                    if r.get('cierre') and r.get('dias_totales') is not None
                ) / cerr,
                1
            )
            if cerr else 0
        )

        specs = [
            ('⚙', 'Activos', activos, PRIMARY),
            ('✓', 'En tiempo', tiempo, SUCCESS),
            ('◷', 'Por vencer', por_vencer, WARNING),
            ('!', 'Vencidos', venc, DANGER),
            ('■', 'Cerrados', cerr, CYAN)
        ]

        for idx, (ico, t, v, col) in enumerate(specs):
            c = ctk.CTkFrame(
                cards,
                fg_color=WHITE,
                corner_radius=14,
                border_width=CONTAINER_BORDER_WIDTH,
                border_color=CONTAINER_BORDER
            )
            c.grid(row=0, column=idx, sticky='ew', padx=3)
            cards.grid_columnconfigure(idx, weight=1)

            ctk.CTkLabel(
                c,
                text=f'{ico}  {t}',
                font=TEXT_SM,
                text_color=TEXT_SECONDARY
            ).pack(pady=(7, 0))

            ctk.CTkLabel(
                c,
                text=str(v),
                font=TITLE_MD,
                text_color=col
            ).pack(pady=(0, 6))

        ctk.CTkLabel(
            cards,
            text=(
                f'Tiempo promedio de cierre: {avg:g} días'
                if cerr else 'Aún no hay procesos cerrados con tiempo medible'
            ),
            font=TEXT_SM,
            text_color=TEXT_SECONDARY
        ).grid(row=1, column=0, columnspan=5, pady=(3, 0))

        for w in attention_body.winfo_children():
            w.destroy()

        alerts = [
            ('🔴', 'Vencidos', venc, DANGER),
            ('🟠', 'Por vencer', por_vencer, WARNING),
            (
                '🟡',
                'Esperando autorización',
                sum(_etapa(r) == 'Autorización' for r in data),
                '#CA8A04'
            ),
            (
                '🔵',
                'En cotización / cliente',
                sum(_etapa(r) == 'Cotización' for r in data),
                BLUE
            )
        ]

        for i, (ico, lab, val, col) in enumerate(alerts):
            b = ctk.CTkFrame(
                attention_body,
                fg_color=SOFT,
                corner_radius=9,
                border_width=1.5,
                border_color=CONTAINER_BORDER
            )
            b.grid(
                row=i // 2,
                column=i % 2,
                sticky='ew',
                padx=3,
                pady=3
            )
            attention_body.grid_columnconfigure(i % 2, weight=1)

            ctk.CTkLabel(
                b,
                text=f'{ico} {val}  {lab}',
                font=TEXT_SM,
                text_color=col
            ).pack(anchor='w', padx=9, pady=6)

        counts = {
            s: sum(_etapa(r) == s for r in data)
            for s in (
                'Levantamiento',
                'Autorización',
                'Cotización',
                'Ejecución',
                'Cierre'
            )
        }

        chart.delete('all')
        chart.update_idletasks()

        w = max(chart.winfo_width(), 420)
        mx = max(counts.values()) if counts else 1
        mx = max(mx, 1)
        names = list(counts)
        barw = max(35, (w - 55) // len(names) - 18)

        for i, n in enumerate(names):
            x = 18 + i * ((w - 36) / len(names))
            bh = 50 * counts[n] / mx
            y = 62 - bh

            chart.create_rectangle(
                x, y, x + barw, 62,
                fill=SECONDARY,
                outline=''
            )
            chart.create_text(
                x + barw / 2,
                y - 8,
                text=str(counts[n]),
                fill=TEXT_PRIMARY,
                font=('Arial', 9, 'bold')
            )
            chart.create_text(
                x + barw / 2,
                77,
                text=n[:8],
                fill=TEXT_SECONDARY,
                font=('Arial', 8)
            )

        apply_filter()

    def _responsive_layout(event=None):
        try:
            width = max(1, root.winfo_width())
            compact = width < 1120
            very_compact = width < 900

            for i, c in enumerate(cards.winfo_children()):
                info = c.grid_info()
                if not info or i >= 5:
                    continue

                cols = 3 if compact else 5
                c.grid_configure(
                    row=i // cols,
                    column=i % cols,
                    sticky='ew',
                    padx=3,
                    pady=2
                )

            for col in range(5):
                cards.grid_columnconfigure(
                    col,
                    weight=1 if (not compact or col < 3) else 0
                )

            card_children = cards.winfo_children()
            if len(card_children) > 5:
                card_children[5].grid_configure(
                    row=2 if compact else 1,
                    column=0,
                    columnspan=3 if compact else 5
                )

            if compact:
                attention.grid_configure(
                    row=0,
                    column=0,
                    columnspan=2,
                    padx=0,
                    pady=(0, 4)
                )
                chart_card.grid_configure(
                    row=1,
                    column=0,
                    columnspan=2,
                    padx=0,
                    pady=(4, 0)
                )
            else:
                attention.grid_configure(
                    row=0,
                    column=0,
                    columnspan=1,
                    padx=(0, 4),
                    pady=0
                )
                chart_card.grid_configure(
                    row=0,
                    column=1,
                    columnspan=1,
                    padx=(4, 0),
                    pady=0
                )

            if compact:
                search_wrap.grid_configure(
                    row=1,
                    column=0,
                    columnspan=2,
                    sticky='ew',
                    padx=10,
                    pady=(0, 9)
                )
            else:
                search_wrap.grid_configure(
                    row=0,
                    column=1,
                    columnspan=1,
                    sticky='e',
                    padx=10,
                    pady=9
                )

            # Más espacio vertical para los botones inferiores.
            actions.configure(height=58)
            actions.pack_propagate(False)

            # Ajuste de ancho para ventanas pequeñas.
            if very_compact:
                btn_detail.configure(width=160)
                btn_refresh.configure(width=140)
            else:
                btn_detail.configure(width=195)
                btn_refresh.configure(width=175)

        except Exception:
            pass

    root.bind('<Configure>', _responsive_layout, add='+')
    root.after_idle(_responsive_layout)
    load()
