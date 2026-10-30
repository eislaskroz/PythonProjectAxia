"""Editor modular de obra civil: actualiza el registro existente mediante Edge.

No altera folios ni inserta registros; la versión histórica requiere migración
transaccional auditada en base de datos.
"""
import json
import customtkinter as ctk
from tkinter import messagebox
from app_context import obtener_usuario_actual
from core.background_tasks import run_async
from services.obra_civil_gateway import gestionar_obra_civil

SECCIONES = [
 ('Datos generales', [('obc_fecha','Fecha'),('obc_cliente','Cliente'),('obc_contacto','Contacto'),('obc_sucursal','Sucursal'),('obc_direccion','Dirección'),('obc_responsable_axia','Encargado del proyecto'),('obc_supervisor','Supervisor'),('obc_dias_trabajo','Días de trabajo'),('obc_personas_considerar','Personas a considerar')]),
 ('Proyecto y preparación', [('obc_tipo_giro','Tipo de giro'),('obc_nombre_proyecto','Nombre del proyecto'),('obc_superficie_disponible','Superficie disponible'),('obc_superficie_adecuada','Superficie adecuada'),('obc_planos_arquitectonicos','Planos arquitectónicos'),('obc_requiere_maquinaria','Requiere maquinaria'),('obc_permisos','Permisos')]),
 ('Acabados y entrega', [('obc_planos_acabados','Planos de acabados'),('obc_generacion_planos','Generación de planos'),('obc_etapa_acabados','Etapa de acabados'),('obc_obra_blanca','Obra blanca'),('obc_observaciones_iniciales','Observaciones iniciales'),('obc_observaciones_finales','Observaciones finales')]),
]
NUMERICOS = {'obc_dias_trabajo', 'obc_personas_considerar'}


def abrir_editor_obra_civil(padre, obra, al_guardar):
    folio = obra.get('obc_folio')
    if not folio or not obra.get('obc_id'):
        messagebox.showerror('Obra Civil', 'No se pudo identificar el registro completo.')
        return
    ventana = ctk.CTkToplevel(padre)
    ventana.title(f'Edición integral de Obra Civil · {folio}')
    sw, sh = ventana.winfo_screenwidth(), ventana.winfo_screenheight()
    w, h = min(sw, max(900, int(sw*.88))), min(sh, max(600, int(sh*.86)))
    ventana.geometry(f'{w}x{h}+{max(0,(sw-w)//2)}+{max(0,(sh-h)//2)}')
    ventana.transient(padre)
    ventana.grab_set()
    ctk.CTkLabel(ventana, text=f'Editar {folio}  |  Secciones bloqueadas por defecto',
                 font=ctk.CTkFont(size=19, weight='bold')).pack(anchor='w', padx=20, pady=(15,7))
    scroll = ctk.CTkScrollableFrame(ventana)
    scroll.pack(fill='both', expand=True, padx=16, pady=5)
    controles, bloqueos = {}, {}
    def seccion(titulo, campos):
        marco = ctk.CTkFrame(scroll)
        marco.pack(fill='x', pady=7, padx=4)
        cabeza = ctk.CTkFrame(marco, fg_color='transparent')
        cabeza.pack(fill='x', padx=14, pady=9)
        ctk.CTkLabel(cabeza, text=titulo, font=ctk.CTkFont(size=16,weight='bold')).pack(side='left')
        entradas=[]
        for clave, etiqueta in campos:
            fila=ctk.CTkFrame(marco,fg_color='transparent')
            fila.pack(fill='x',padx=14,pady=4)
            ctk.CTkLabel(fila,text=etiqueta,width=210,anchor='w').pack(side='left')
            valor=obra.get(clave)
            if clave in ('obc_observaciones_iniciales','obc_observaciones_finales'):
                control=ctk.CTkTextbox(fila,height=75)
                control.insert('1.0',str(valor if valor is not None else ''))
            else:
                control=ctk.CTkEntry(fila)
                control.insert(0,str(valor if valor is not None else ''))
            control.pack(side='left',fill='x',expand=True)
            control.configure(state='disabled')
            entradas.append(control)
            controles[clave]=control
        desbloqueado=ctk.BooleanVar(value=False)
        def toggle():
            estado='normal' if desbloqueado.get() else 'disabled'
            for c in entradas: c.configure(state=estado)
            boton.configure(text='🔓 Bloquear sección' if desbloqueado.get() else '🔒 Desbloquear sección')
        boton=ctk.CTkButton(cabeza,text='🔒 Desbloquear sección',width=200,
                             command=lambda: (desbloqueado.set(not desbloqueado.get()),toggle()))
        boton.pack(side='right')
        bloqueos[titulo]=desbloqueado
    for titulo, campos in SECCIONES: seccion(titulo,campos)
    # Los apartados técnicos almacenados como JSON se exponen por subapartado,
    # preservando los datos ocultos y los adjuntos existentes.
    ejecucion=obra.get('obc_ejecucion_json') or '{}'
    try: ejecucion=json.loads(ejecucion) if isinstance(ejecucion,str) else ejecucion
    except (ValueError,TypeError): ejecucion={}
    if not isinstance(ejecucion,dict): ejecucion={}
    claves_tecnicas=[
        ('Actividades de ejecución',[k for k in ejecucion if not k.startswith('_')]),
        ('Notas y personal', ['_notas_cliente','_datos_generales_axia']),
        ('Conceptos y EPP',['_conceptos_obra','_epp']),
        ('Alturas, riesgos y seguridad',['_acceso_alturas_riesgos']),
        ('Materiales y canalización',['_materiales_miscelaneos','_canalizacion_materiales']),
    ]
    json_controles={}
    for titulo, claves in claves_tecnicas:
        marco=ctk.CTkFrame(scroll); marco.pack(fill='x',padx=4,pady=7)
        superior=ctk.CTkFrame(marco,fg_color='transparent'); superior.pack(fill='x',padx=14,pady=8)
        ctk.CTkLabel(superior,text=titulo,font=ctk.CTkFont(size=16,weight='bold')).pack(side='left')
        txt=ctk.CTkTextbox(marco,height=155)
        txt.pack(fill='x',padx=14,pady=(0,12))
        txt.insert('1.0',json.dumps({k:ejecucion[k] for k in claves if k in ejecucion},indent=2,ensure_ascii=False))
        txt.configure(state='disabled')
        estado=ctk.BooleanVar(value=False)
        boton=ctk.CTkButton(superior,width=200,text='🔒 Desbloquear sección')
        def alternar(t=txt,s=estado,b=boton):
            s.set(not s.get()); t.configure(state='normal' if s.get() else 'disabled')
            b.configure(text='🔓 Bloquear sección' if s.get() else '🔒 Desbloquear sección')
        boton.configure(command=alternar); boton.pack(side='right')
        json_controles[titulo]=(estado,txt,claves)
    ctk.CTkLabel(scroll,text='Los anexos fotográficos y planos ya guardados permanecen intactos. '
                 'Los apartados técnicos avanzados requieren JSON válido.').pack(anchor='w',padx=12,pady=9)
    pie=ctk.CTkFrame(ventana);pie.pack(fill='x',padx=16,pady=12)
    estado_lbl=ctk.CTkLabel(pie,text='Se actualizará el mismo registro, sin duplicarlo.')
    estado_lbl.pack(side='left',padx=12)
    def guardar():
        cambios={}
        for titulo,campos in SECCIONES:
            if not bloqueos[titulo].get(): continue
            for clave,_ in campos:
                widget=controles[clave]
                valor=widget.get('1.0','end').strip() if isinstance(widget,ctk.CTkTextbox) else widget.get().strip()
                if clave in NUMERICOS:
                    try: valor=int(valor)
                    except ValueError:
                        messagebox.showwarning('Dato incorrecto',f'Introduce un número entero en {clave}.',parent=ventana);return
                if valor != (obra.get(clave) if obra.get(clave) is not None else ''):
                    cambios[clave]=valor
        nuevo=dict(ejecucion)
        for titulo,(activo,txt,claves) in json_controles.items():
            if not activo.get(): continue
            try: bloque=json.loads(txt.get('1.0','end'))
            except ValueError as e:
                messagebox.showerror('Detalle técnico',f'{titulo}: {e}',parent=ventana);return
            if not isinstance(bloque,dict) or set(bloque)-set(claves):
                messagebox.showerror('Detalle técnico',f'{titulo}: estructura o claves no válidas.',parent=ventana);return
            for clave in claves:
                if clave in bloque: nuevo[clave]=bloque[clave]
                else: nuevo.pop(clave,None)
        if nuevo!=ejecucion: cambios['obc_ejecucion_json']=json.dumps(nuevo,ensure_ascii=False)
        if not cambios:
            messagebox.showinfo('Sin cambios','No hay modificaciones que guardar.',parent=ventana);return
        if not str(cambios.get('obc_cliente',obra.get('obc_cliente')) or '').strip() or not str(cambios.get('obc_nombre_proyecto',obra.get('obc_nombre_proyecto')) or '').strip():
            messagebox.showwarning('Campos obligatorios','Cliente y nombre del proyecto son obligatorios.',parent=ventana);return
        guardar_btn.configure(state='disabled'); estado_lbl.configure(text='Guardando cambios...')
        usuario=obtener_usuario_actual() or {}
        def ok(resultado):
            if not isinstance(resultado,dict) or not resultado.get('obc_id'):
                error('El servidor no confirmó la modificación.');return
            al_guardar(resultado)
            messagebox.showinfo('Cambios guardados','Obra Civil actualizada sin crear un registro nuevo.',parent=ventana)
            ventana.destroy()
        def error(err):
            guardar_btn.configure(state='normal');estado_lbl.configure(text='No se guardaron los cambios.')
            messagebox.showerror('Error al actualizar Obra Civil',str(err),parent=ventana)
        run_async(ventana,lambda: gestionar_obra_civil('actualizar',usuario_id=usuario.get('id_usuario'),folio=folio,cambios=cambios),ok,error)
    guardar_btn=ctk.CTkButton(pie,text='Guardar cambios',width=160,command=guardar)
    guardar_btn.pack(side='right',padx=8)
    ctk.CTkButton(pie,text='Cancelar',width=110,fg_color='#64748b',command=ventana.destroy).pack(side='right',padx=8)
    ventana.protocol('WM_DELETE_WINDOW',ventana.destroy)
