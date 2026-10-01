"""Dashboard ejecutivo de Dirección General: resumen, etapas, alertas y trazabilidad."""
import customtkinter as ctk
from tkinter import ttk, messagebox, Canvas
from app_context import obtener_usuario_actual
from security.permissions import puede_ver_direccion_general
from services.direccion_general_service import obtener_panel_direccion
from ui.colors import (WHITE, TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY, SECONDARY,
                       BUTTON_HOVER, SUCCESS, WARNING, DANGER, BORDER, CONTENT_BG)
from ui.fonts import TEXT_SM, TEXT_MD, TITLE_MD, BUTTON_FONT

BLUE='#2563EB'; CYAN='#0891B2'; PURPLE='#7C3AED'; MUTED='#64748B'; SOFT='#EEF2F7'

def _fmt(v):
    if not v: return '—'
    return str(v).replace('T',' ')[:16]

def _dur(v, unit='h'):
    return '—' if v is None else f'{v:g} {unit}'

def _estado_color(e):
    e=str(e or '').upper()
    if 'FUERA' in e or e=='VENCIDO': return DANGER
    if 'POR VENCER' in e: return WARNING
    if 'FINALIZADO EN TIEMPO' in e: return SUCCESS
    if 'EN TIEMPO' in e: return SUCCESS
    return MUTED

def _etapa(r):
    if r.get('cierre'): return 'Cierre'
    if r.get('ot_folio'): return 'Ejecución'
    if r.get('cotizaciones',0): return 'Cotización'
    if r.get('fecha_autorizacion'): return 'Autorización'
    return 'Levantamiento'

def mostrar_direccion_general(parent, app):
    if not puede_ver_direccion_general(obtener_usuario_actual()):
        messagebox.showerror('Acceso denegado','Esta sección está reservada para Dirección General / Administrador.')
        return
    for w in parent.winfo_children(): w.destroy()
    root=ctk.CTkFrame(parent,fg_color='transparent'); root.pack(fill='both',expand=True,padx=14,pady=6)

    head=ctk.CTkFrame(root,fg_color=WHITE,corner_radius=16); head.pack(fill='x',pady=(0,8))
    ctk.CTkLabel(head,text='Dirección General · Control Operacional',font=TITLE_MD,text_color=TEXT_PRIMARY).pack(anchor='w',padx=14,pady=(10,2))
    ctk.CTkLabel(head,text='Resumen ejecutivo, alertas y trazabilidad del ciclo LEV → Autorización → COT → OT → OS.',font=TEXT_SM,text_color=TEXT_SECONDARY).pack(anchor='w',padx=14,pady=(0,10))

    cards=ctk.CTkFrame(root,fg_color='transparent'); cards.pack(fill='x',pady=(0,7))
    mid=ctk.CTkFrame(root,fg_color='transparent'); mid.pack(fill='x',pady=(0,7))
    attention=ctk.CTkFrame(mid,fg_color=WHITE,corner_radius=14)
    chart_card=ctk.CTkFrame(mid,fg_color=WHITE,corner_radius=14)
    mid.grid_columnconfigure(0,weight=1); mid.grid_columnconfigure(1,weight=1)
    attention.grid(row=0,column=0,sticky='nsew',padx=(0,4))
    chart_card.grid(row=0,column=1,sticky='nsew',padx=(4,0))

    ctk.CTkLabel(attention,text='⚠ Procesos que requieren atención',font=TEXT_MD,text_color=TEXT_PRIMARY).pack(anchor='w',padx=12,pady=(8,4))
    attention_body=ctk.CTkFrame(attention,fg_color='transparent'); attention_body.pack(fill='x',padx=8,pady=(0,8))
    ctk.CTkLabel(chart_card,text='▥ Distribución por etapa',font=TEXT_MD,text_color=TEXT_PRIMARY).pack(anchor='w',padx=12,pady=(8,2))
    chart=Canvas(chart_card,height=92,bg=WHITE,highlightthickness=0); chart.pack(fill='x',padx=12,pady=(0,7))

    controls=ctk.CTkFrame(root,fg_color=WHITE,corner_radius=14); controls.pack(fill='x',pady=(0,7))
    tabs=ctk.CTkSegmentedButton(controls,values=['Todos','Levantamientos','Autorización','Cotización','Ejecución','Cierre'],font=TEXT_SM)
    tabs.grid(row=0,column=0,sticky='w',padx=10,pady=9); tabs.set('Todos')
    search_var=ctk.StringVar()
    search=ctk.CTkEntry(controls,textvariable=search_var,width=260,placeholder_text='Buscar cliente, folio, servicio...')
    search.grid(row=0,column=1,sticky='e',padx=10,pady=9)
    controls.grid_columnconfigure(0,weight=1); controls.grid_columnconfigure(1,weight=0)

    status=ctk.CTkLabel(root,text='Consultando operación...',font=TEXT_SM,text_color=TEXT_SECONDARY); status.pack(anchor='w',pady=(0,4))
    table_shell=ctk.CTkFrame(root,fg_color=WHITE,corner_radius=14); table_shell.pack(fill='both',expand=True)
    cols=('folio','cliente','etapa','responsable','plan','avance','tiempo','estado','faltante')
    tree=ttk.Treeview(table_shell,columns=cols,show='headings',height=12)
    labels={'folio':'Folio','cliente':'Cliente','etapa':'Etapa actual','responsable':'Responsable','plan':'Plan','avance':'Avance','tiempo':'Tiempo','estado':'Estatus','faltante':'Siguiente / faltante'}
    widths={'folio':90,'cliente':150,'etapa':105,'responsable':145,'plan':85,'avance':65,'tiempo':80,'estado':145,'faltante':175}
    for c in cols: tree.heading(c,text=labels[c]); tree.column(c,width=widths[c],minwidth=55,anchor='w')
    sy=ttk.Scrollbar(table_shell,orient='vertical',command=tree.yview); sx=ttk.Scrollbar(table_shell,orient='horizontal',command=tree.xview)
    tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
    tree.grid(row=0,column=0,sticky='nsew',padx=(10,0),pady=(10,0)); sy.grid(row=0,column=1,sticky='ns',pady=(10,0)); sx.grid(row=1,column=0,sticky='ew',padx=(10,0),pady=(0,8))
    table_shell.grid_rowconfigure(0,weight=1); table_shell.grid_columnconfigure(0,weight=1)
    tree.tag_configure('danger',foreground=DANGER); tree.tag_configure('warning',foreground='#B45309'); tree.tag_configure('success',foreground='#15803D')

    data=[]; visible=[]
    def detail(_=None):
        sel=tree.selection()
        if not sel:return
        r=visible[int(sel[0])]
        win=ctk.CTkToplevel(parent); win.title(f"Trazabilidad {r['folio']}"); win.geometry('940x720'); win.grab_set()
        sc=ctk.CTkScrollableFrame(win,fg_color=CONTENT_BG); sc.pack(fill='both',expand=True,padx=10,pady=10)
        top=ctk.CTkFrame(sc,fg_color=WHITE,corner_radius=14); top.pack(fill='x',padx=5,pady=(3,7))
        ctk.CTkLabel(top,text=f"{r['folio']} · {r['cliente']}",font=TITLE_MD,text_color=TEXT_PRIMARY).pack(anchor='w',padx=12,pady=(10,2))
        ctk.CTkLabel(top,text=f"{r['tipo']}  ·  {_etapa(r)}  ·  {r['estado']}",font=TEXT_SM,text_color=_estado_color(r['estado'])).pack(anchor='w',padx=12,pady=(0,10))
        sections=[
          ('① Levantamiento', [('Realizado por',r['tecnico']),('Inicio',_fmt(r['inicio'])),('Requerimiento',r['requerimiento'] or '—'),('Plan',f"{r['dias_planeados']} días / {r['personas'] or '—'} personas")]),
          ('② Autorización', [('Autorizó',r['autorizado_por'] or 'Pendiente'),('Fecha',_fmt(r['fecha_autorizacion'])),('Respuesta',_dur(r['horas_autorizacion']))]),
          ('③ Cotización', [('Cotizaciones',r['cotizaciones']),('ESI',r['esi'] or '—'),('Primera cotización',_fmt(r['fecha_cotizacion'])),('Tiempo ESI',_dur(r['horas_esi'])),('Autorización cliente',_fmt(r['fecha_autorizacion_cliente'])),('Tiempo cliente',_dur(r['horas_cliente']))]),
          ('④ Ejecución', [('OT',r['ot_folio'] or 'Pendiente'),('Inicio',_fmt(r['ot_inicio'])),('Fecha límite',_fmt(r['fecha_limite'])),('Avance',f"{r['avance']}%"),('Situación',r['estado'])]),
          ('⑤ Cierre', [('OS',r['os_folio'] or 'Pendiente'),('Cierre',_fmt(r['cierre'])),('Tiempo total',_dur(r['dias_totales'],'d')),('Siguiente / faltante',r['faltante'])]),
        ]
        for title,items in sections:
            card=ctk.CTkFrame(sc,fg_color=WHITE,corner_radius=12); card.pack(fill='x',padx=5,pady=4)
            ctk.CTkLabel(card,text=title,font=TEXT_MD,text_color=PRIMARY).pack(anchor='w',padx=12,pady=(8,3))
            for k,v in items:
                row=ctk.CTkFrame(card,fg_color='transparent'); row.pack(fill='x',padx=12,pady=1)
                ctk.CTkLabel(row,text=k,width=170,anchor='w',font=TEXT_SM,text_color=TEXT_SECONDARY).pack(side='left')
                ctk.CTkLabel(row,text=str(v),anchor='w',justify='left',wraplength=680,font=TEXT_SM,text_color=TEXT_PRIMARY).pack(side='left',fill='x',expand=True)
            ctk.CTkLabel(card,text='').pack(pady=1)
    tree.bind('<Double-1>',detail)

    def apply_filter(*_):
        nonlocal visible
        stage=tabs.get(); q=search_var.get().strip().lower()
        stage_map={'Levantamientos':'Levantamiento','Autorización':'Autorización','Cotización':'Cotización','Ejecución':'Ejecución','Cierre':'Cierre'}
        visible=[]
        for r in data:
            if stage!='Todos' and _etapa(r)!=stage_map.get(stage): continue
            blob=' '.join(str(r.get(k,'') or '') for k in ('folio','cliente','tipo','tecnico','estado','faltante','ot_folio','os_folio')).lower()
            if q and q not in blob: continue
            visible.append(r)
        for i in tree.get_children(): tree.delete(i)
        for i,r in enumerate(visible):
            tag='danger' if r['estado']=='VENCIDO' or 'FUERA' in r['estado'] else 'warning' if r['estado']=='POR VENCER' else 'success' if 'EN TIEMPO' in r['estado'] else ''
            resp=r['esi'] if _etapa(r)=='Cotización' and r['esi'] else r['tecnico']
            tree.insert('', 'end', iid=str(i), tags=(tag,), values=(r['folio'],r['cliente'],_etapa(r),resp,f"{r['dias_planeados']}d/{r['personas'] or '—'}p",f"{r['avance']}%",_dur(r['dias_totales'],'d'),r['estado'],r['faltante']))
        status.configure(text=f'{len(visible)} de {len(data)} procesos · Doble clic para consultar el expediente completo.')

    tabs.configure(command=lambda _v:apply_filter()); search_var.trace_add('write',apply_filter)
    actions=ctk.CTkFrame(root,fg_color='transparent'); actions.pack(fill='x',pady=(7,0))
    btn_refresh=ctk.CTkButton(actions,text='↻ Actualizar',height=38,width=145,font=BUTTON_FONT,fg_color=SECONDARY,hover_color=BUTTON_HOVER,command=lambda:load())
    btn_detail=ctk.CTkButton(actions,text='👁 Ver trazabilidad',height=38,width=165,font=BUTTON_FONT,fg_color=PRIMARY,command=detail)
    btn_refresh.pack(side='right',padx=(4,0)); btn_detail.pack(side='right',padx=4)

    def load():
        nonlocal data
        status.configure(text='Consultando operación...'); parent.update_idletasks()
        try:data=obtener_panel_direccion()
        except Exception as e: messagebox.showerror('Dirección General',f'No fue posible cargar el panel.\n\n{e}'); return
        for w in cards.winfo_children():w.destroy()
        total=len(data); cerr=sum(bool(r['cierre']) for r in data); activos=total-cerr
        venc=sum(r['estado']=='VENCIDO' for r in data); tiempo=sum(r['estado']=='EN TIEMPO' for r in data)
        por_vencer=sum(r['estado']=='POR VENCER' for r in data)
        avg=round(sum(r['dias_totales'] for r in data if r.get('cierre') and r.get('dias_totales') is not None)/cerr,1) if cerr else 0
        specs=[('⚙','Activos',activos,PRIMARY),('✓','En tiempo',tiempo,SUCCESS),('◷','Por vencer',por_vencer,WARNING),('!','Vencidos',venc,DANGER),('■','Cerrados',cerr,CYAN)]
        for idx,(ico,t,v,col) in enumerate(specs):
            c=ctk.CTkFrame(cards,fg_color=WHITE,corner_radius=14); c.grid(row=0,column=idx,sticky='ew',padx=3); cards.grid_columnconfigure(idx,weight=1)
            ctk.CTkLabel(c,text=f'{ico}  {t}',font=TEXT_SM,text_color=TEXT_SECONDARY).pack(pady=(7,0)); ctk.CTkLabel(c,text=str(v),font=TITLE_MD,text_color=col).pack(pady=(0,6))
        ctk.CTkLabel(cards,text=f'Tiempo promedio de cierre: {avg:g} días' if cerr else 'Aún no hay procesos cerrados con tiempo medible',font=TEXT_SM,text_color=TEXT_SECONDARY).grid(row=1,column=0,columnspan=5,pady=(3,0))

        for w in attention_body.winfo_children():w.destroy()
        alerts=[('🔴','Vencidos',venc,DANGER),('🟠','Por vencer',por_vencer,WARNING),('🟡','Esperando autorización',sum(_etapa(r)=='Autorización' for r in data),'#CA8A04'),('🔵','En cotización / cliente',sum(_etapa(r)=='Cotización' for r in data),BLUE)]
        for i,(ico,lab,val,col) in enumerate(alerts):
            b=ctk.CTkFrame(attention_body,fg_color=SOFT,corner_radius=9); b.grid(row=i//2,column=i%2,sticky='ew',padx=3,pady=3); attention_body.grid_columnconfigure(i%2,weight=1)
            ctk.CTkLabel(b,text=f'{ico} {val}  {lab}',font=TEXT_SM,text_color=col).pack(anchor='w',padx=9,pady=6)

        counts={s:sum(_etapa(r)==s for r in data) for s in ('Levantamiento','Autorización','Cotización','Ejecución','Cierre')}
        chart.delete('all'); chart.update_idletasks(); w=max(chart.winfo_width(),420); h=90; mx=max(counts.values()) if counts else 1; mx=max(mx,1)
        names=list(counts); barw=max(35,(w-55)//len(names)-18)
        for i,n in enumerate(names):
            x=18+i*((w-36)/len(names)); bh=50*counts[n]/mx; y=62-bh
            chart.create_rectangle(x,y,x+barw,62,fill=SECONDARY,outline='')
            chart.create_text(x+barw/2,y-8,text=str(counts[n]),fill=TEXT_PRIMARY,font=('Arial',9,'bold'))
            chart.create_text(x+barw/2,77,text=n[:8],fill=TEXT_SECONDARY,font=('Arial',8))
        apply_filter()
    def _responsive_layout(event=None):
        # Responsive breakpoints use the real content width, not screen resolution.
        # This also behaves correctly with Windows display scaling.
        try:
            width=max(1, root.winfo_width())
            compact=width < 1120
            very_compact=width < 900
            # Executive cards: 5 in one row normally; wrap to 3+2 on compact widths.
            for i,c in enumerate(cards.winfo_children()):
                info=c.grid_info()
                if not info or i >= 5: continue
                cols=3 if compact else 5
                c.grid_configure(row=i//cols,column=i%cols,sticky='ew',padx=3,pady=2)
            for col in range(5): cards.grid_columnconfigure(col,weight=1 if (not compact or col<3) else 0)
            card_children=cards.winfo_children()
            if len(card_children)>5:
                card_children[5].grid_configure(row=2 if compact else 1,column=0,columnspan=3 if compact else 5)
            # Attention + chart become vertical when the content area is narrow.
            if compact:
                attention.grid_configure(row=0,column=0,columnspan=2,padx=0,pady=(0,4))
                chart_card.grid_configure(row=1,column=0,columnspan=2,padx=0,pady=(4,0))
            else:
                attention.grid_configure(row=0,column=0,columnspan=1,padx=(0,4),pady=0)
                chart_card.grid_configure(row=0,column=1,columnspan=1,padx=(4,0),pady=0)
            # Search moves under the stage tabs instead of squeezing them.
            if compact:
                search.grid_configure(row=1,column=0,columnspan=2,sticky='ew',padx=10,pady=(0,9))
            else:
                search.grid_configure(row=0,column=1,columnspan=1,sticky='e',padx=10,pady=9)
            # Keep action buttons readable at every supported size.
            actions.configure(height=48)
            actions.pack_propagate(False)
            if very_compact:
                btn_detail.configure(width=145); btn_refresh.configure(width=125)
            else:
                btn_detail.configure(width=165); btn_refresh.configure(width=145)
        except Exception:
            pass

    root.bind('<Configure>', _responsive_layout, add='+')
    root.after_idle(_responsive_layout)
    load()
