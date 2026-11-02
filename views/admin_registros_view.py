"""Consola de mantenimiento para administradores AXIA.

El cliente no edita ni borra directamente Supabase: cada operación pasa por
Edge Function + RPC transaccional con contraseña/rol verificados en el servidor.
"""
from __future__ import annotations
import json
from tkinter import messagebox
import customtkinter as ctk
from app_context import obtener_usuario_actual
from security.permissions import es_admin
from core.background_tasks import run_async
from services.admin_registros_service import TIPOS, EDITABLES, ejecutar
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY
from ui.form_fields import AxiaEntry, AxiaTextbox
from ui.native_table import NativeTreeTable
from views.admin_registros_formularios import FormularioSeccionado


def _formato(valor):
    if valor is None:
        return ""
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False, indent=2)
    if isinstance(valor, bool):
        return "true" if valor else "false"
    return str(valor)


def _convertir(original, texto, campo):
    """Reconstruye los tipos existentes; deja que PostgreSQL valide el esquema."""
    s = texto.strip()
    if isinstance(original, (dict, list)):
        resultado = json.loads(s)
        if not isinstance(resultado, type(original)):
            raise ValueError(f"{campo}: se esperaba JSON del mismo tipo")
        return resultado
    if isinstance(original, bool):
        if s.lower() not in ("true", "false"):
            raise ValueError(f"{campo}: escribe true o false")
        return s.lower() == "true"
    if isinstance(original, int):
        return int(s) if s else None
    if isinstance(original, float):
        return float(s) if s else None
    if original is None:
        if not s:
            return None
        if campo.endswith("_json"):
            return json.loads(s)
        return s
    if campo.endswith("_json") and s and isinstance(original, str):
        # Algunos esquemas históricos guardan el JSON como texto: no cambiar tipo.
        json.loads(s)
    return texto if texto else ""


def mostrar_admin_registros(parent, app):
    if not es_admin(obtener_usuario_actual()):
        messagebox.showerror("Acceso denegado", "Únicamente el Administrador puede gestionar registros.")
        return
    root=parent.winfo_toplevel()
    cont=ctk.CTkFrame(parent, fg_color="transparent")
    cont.pack(fill="both", expand=True, padx=12, pady=7)
    top=ctk.CTkFrame(cont, fg_color=WHITE, corner_radius=12)
    top.pack(fill="x", pady=(0,8))
    ctk.CTkLabel(top, text="Administración de Registros",font=("Montserrat",20,"bold"),text_color=TEXT_PRIMARY).pack(anchor="w",padx=13,pady=(9,2))
    ctk.CTkLabel(top, text="Solo Administrador · Cambios auditados · Sin eliminación en cascada · Folios y relaciones protegidos",
                 text_color=TEXT_SECONDARY,font=("Montserrat",11)).pack(anchor="w",padx=13,pady=(0,8))
    controles=ctk.CTkFrame(top,fg_color="transparent")
    controles.pack(fill="x", padx=10, pady=(0,10))
    tipo=ctk.StringVar(value=next(iter(TIPOS)))
    entrada_tipo=ctk.CTkOptionMenu(controles,values=list(TIPOS),variable=tipo,width=190,height=32)
    entrada_tipo.pack(side="left",padx=(0,7))
    buscar=AxiaEntry(controles,placeholder_text="Folio, ACO, cliente o descripción",height=32,width=250)
    buscar.pack(side="left",fill="x",expand=True,padx=(0,6))
    clave=AxiaEntry(controles,placeholder_text="Contraseña de Administrador",show="●",height=32,width=195)
    clave.pack(side="left",padx=(0,6))

    estado={"pagina":1,"total":0,"activo":False}
    resultado=ctk.CTkFrame(cont,fg_color=WHITE,corner_radius=12)
    resultado.pack(fill="both",expand=True)
    status=ctk.CTkLabel(resultado,text="Ingresa tu contraseña y pulsa Buscar.",anchor="w",text_color=TEXT_SECONDARY)
    status.pack(fill="x",padx=10,pady=8)
    tabla=NativeTreeTable(resultado,columns=(
        ("folio","Folio",150),("cliente","Cliente",275),("estado","Estatus",105),
        ("fecha","Fecha",150),("id","ID",90)),height=16,table_id="admin_registros_axia")
    tabla.pack(fill="both",expand=True,padx=9,pady=(0,8))
    footer=ctk.CTkFrame(resultado,fg_color="transparent")
    footer.pack(fill="x",padx=9,pady=(0,11))
    botones=ctk.CTkFrame(footer,fg_color="transparent")
    botones.pack(side="left")

    def tabla_actual():
        return TIPOS[tipo.get()]

    def correr(task, on_success, mensaje):
        status.configure(text=mensaje)
        def fallo(error):
            status.configure(text="Operación fallida; no se confirmó ningún cambio.")
            messagebox.showerror("Administración de Registros",str(error),parent=root)
        run_async(root=root,task=task,on_success=on_success,on_error=fallo)

    def listar():
        tab,idcol,folio,cliente,estatus,fecha=tabla_actual()
        if not clave.get():
            messagebox.showwarning("Contraseña requerida","Ingresa la contraseña de Administrador.",parent=root)
            return
        pagina=estado['pagina']
        pwd=clave.get()
        def pintar(datos):
            registros=datos.get('registros') or []
            estado['total']=int(datos.get('total') or 0)
            tabla.set_rows(registros,value_factory=lambda r:(
                r.get(folio) or '',r.get(cliente) or '',r.get(estatus) if r.get(estatus) is not None else '',
                r.get(fecha) or '',r.get(idcol) or ''))
            status.configure(text=f"{estado['total']} registros encontrados · Página {pagina} · 50 por página")
        correr(lambda: ejecutar(tab,'listar',pwd,pagina=pagina,buscar=buscar.get().strip()),pintar,"Consultando... ")

    def nuevo_tipo(_value=None):
        estado['pagina']=1
        tabla.clear()
        status.configure(text="Selecciona Buscar para consultar el nuevo módulo.")
    entrada_tipo.configure(command=nuevo_tipo)

    def seleccionar():
        registro=tabla.selected_payload()
        if not registro:
            messagebox.showinfo("Seleccionar registro","Selecciona una fila de la tabla.",parent=root)
            return None
        return registro

    def abrir_detalle(editar=False, eliminar=False):
        registro=seleccionar()
        if registro is None:return
        tab,idcol,folio,*_=tabla_actual()
        identificador=str(registro[idcol]); pwd=clave.get()
        if not pwd:
            messagebox.showwarning("Contraseña requerida","Escribe tu contraseña primero.",parent=root)
            return
        def mostrar(respuesta):
            actual=respuesta.get('registro')
            if not isinstance(actual,dict):
                messagebox.showerror("Registro","No se obtuvo el detalle del servidor.",parent=root)
                return
            dialogo_registro(tab,actual,clave,root,editar=editar,eliminar=eliminar,on_guardado=listar)
            status.configure(text=f"Registro consultado: {actual.get(folio,'')}")
        correr(lambda: ejecutar(tab,'obtener',pwd,id=identificador),mostrar,"Consultando detalle... ")

    ctk.CTkButton(controles,text="Buscar",width=100,height=32,command=lambda:(estado.update(pagina=1),listar())).pack(side="left")
    ctk.CTkButton(botones,text="Ver detalle",width=118,height=32,command=abrir_detalle).pack(side="left",padx=3)
    ctk.CTkButton(botones,text="Editar",width=102,height=32,fg_color=SECONDARY,command=lambda:abrir_detalle(editar=True)).pack(side="left",padx=3)
    ctk.CTkButton(botones,text="Eliminar",width=105,height=32,fg_color="#B91C1C",hover_color="#991B1B",command=lambda:abrir_detalle(eliminar=True)).pack(side="left",padx=3)

    def abrir_historial():
        tab,*_=tabla_actual()
        pwd=clave.get()
        if not pwd:
            messagebox.showwarning("Contraseña requerida","Ingresa la contraseña del Administrador.",parent=root)
            return
        def mostrar_historial(data):
            win=ctk.CTkToplevel(root)
            win.title(f"Historial de administración · {tipo.get()}")
            win.geometry("980x520")
            win.transient(root)
            ctk.CTkLabel(win,text="Últimos 75 cambios, incluidos registros eliminados",
                font=("Montserrat",15,"bold")).pack(anchor="w",padx=15,pady=10)
            tabla_auditoria=NativeTreeTable(win,columns=(
                ("fecha","Fecha",155),("folio","Folio",145),("accion","Acción",100),
                ("usuario","Administrador",175),("motivo","Motivo",320)),
                table_id="axia_admin_historial",height=15)
            tabla_auditoria.pack(fill="both",expand=True,padx=12,pady=(0,10))
            filas=data.get("historial") or []
            tabla_auditoria.set_rows(filas,value_factory=lambda r:(r.get('fecha',''),r.get('folio',''),
                r.get('accion',''),r.get('actor_usuario',''),r.get('motivo','')))
            ctk.CTkButton(win,text="Cerrar",width=115,command=win.destroy).pack(pady=(0,10))
        correr(lambda:ejecutar(tab,'auditoria',pwd),mostrar_historial,"Consultando historial protegido...")

    ctk.CTkButton(botones,text="Historial de cambios",width=155,height=32,
                  fg_color="#475569",command=abrir_historial).pack(side="left",padx=3)

    ctk.CTkButton(footer,text="Anterior",width=87,height=30,command=lambda:(estado.update(pagina=max(1,estado['pagina']-1)),listar())).pack(side="right",padx=3)
    ctk.CTkButton(footer,text="Siguiente",width=90,height=30,command=lambda:(estado.update(pagina=estado['pagina']+1),listar()) if estado['pagina']*50<estado['total'] else None).pack(side="right",padx=3)
    buscar.bind("<Return>",lambda _:(estado.update(pagina=1),listar()))


def dialogo_registro(tabla, original, clave, root, *, editar=False, eliminar=False, on_guardado=None):
    spec=next((v for v in TIPOS.values() if v[0]==tabla),None)
    if spec is None:return
    _,idcol,folcol,_,_,_=spec
    folio=str(original.get(folcol) or '')
    identificador=str(original.get(idcol) or '')
    ventana=ctk.CTkToplevel(root)
    ventana.title(f"{'Eliminar' if eliminar else 'Editar' if editar else 'Consultar'} {folio}")
    ventana.geometry("920x710")
    ventana.minsize(690,480)
    ventana.transient(root)
    marco=ctk.CTkFrame(ventana,fg_color="transparent")
    marco.pack(fill="both",expand=True,padx=12,pady=8)
    ctk.CTkLabel(marco,text=f"{folio}   |   {identificador}",font=("Montserrat",18,"bold")).pack(anchor="w",pady=4)
    ctk.CTkLabel(marco,text="Los folios, IDs, relaciones, firmas y evidencias no se modifican aquí.",text_color="#64748B").pack(anchor="w",pady=(0,8))
    zona=ctk.CTkScrollableFrame(marco,fg_color="#F7F9FC")
    zona.pack(fill="both",expand=True)
    widgets={}
    campos=() if editar or eliminar else tuple(original.keys())
    for campo in campos:
        if campo not in original:continue
        valor=original[campo]
        fila=ctk.CTkFrame(zona,fg_color="transparent")
        fila.pack(fill="x",padx=8,pady=3)
        ctk.CTkLabel(fila,text=campo,width=240,anchor="w").pack(side="left",padx=(0,10))
        texto=_formato(valor)
        es_largo=isinstance(valor,(dict,list)) or campo.endswith('_json') or len(texto)>140
        if editar:
            if es_largo:
                widget=AxiaTextbox(fila,height=94)
                widget.insert('1.0',texto)
            else:
                widget=AxiaEntry(fila,height=30)
                widget.insert(0,texto)
            widget.pack(side="left",fill="x",expand=True)
            widgets[campo]=(widget,valor,es_largo)
        else:
            if es_largo:
                visual=AxiaTextbox(fila,height=95)
                visual.insert('1.0',texto)
                visual.configure(state="disabled")
                visual.pack(side="left",fill="x",expand=True)
            else:
                ctk.CTkLabel(fila,text=texto,justify="left",anchor="w",wraplength=530).pack(
                    side="left",fill="x",expand=True)
    formulario_admin = FormularioSeccionado(zona, tabla, original, root=root) if editar else None
    if eliminar:
        ctk.CTkLabel(zona,text="La eliminación es permanente. Se guarda una copia del registro en el historial.\n"
                     "Si tiene registros relacionados, el servidor rechazará la operación.",
                     text_color="#B91C1C",justify="left").pack(anchor="w",padx=10,pady=12)
    if not (editar or eliminar):
        ctk.CTkButton(marco,text="Cerrar",command=ventana.destroy).pack(side="right",pady=7)
        return
    pie=ctk.CTkFrame(marco,fg_color="transparent")
    pie.pack(fill="x",pady=(9,0))
    motivo=AxiaEntry(pie,placeholder_text="Motivo del cambio (mínimo 8 caracteres)",height=34)
    motivo.pack(fill="x",pady=(0,6))
    if eliminar:
        confirma=AxiaEntry(pie,placeholder_text=f"Escribe exactamente el folio: {folio}",height=34)
        confirma.pack(fill="x",pady=(0,6))
    else:confirma=None
    # No se conserva la clave del módulo como autorización para un borrado.
    clave_confirmacion=AxiaEntry(pie,placeholder_text="Confirma la contraseña de Administrador",show="●",height=34)
    clave_confirmacion.pack(fill="x",pady=(0,7))
    acciones=ctk.CTkFrame(pie,fg_color="transparent")
    acciones.pack(fill="x")
    ctk.CTkButton(acciones,text="Cancelar",width=110,fg_color="#64748B",command=ventana.destroy).pack(side="right",padx=3)
    btn=ctk.CTkButton(acciones,text="Eliminar definitivamente" if eliminar else "Guardar cambios",
                       width=185,fg_color="#B91C1C" if eliminar else SECONDARY)
    btn.pack(side="right",padx=3)

    def aplicar():
        causa=motivo.get().strip()
        if len(causa)<8:
            messagebox.showwarning("Motivo requerido","Describe el motivo en al menos 8 caracteres.",parent=ventana)
            return
        pwd=clave_confirmacion.get()
        if not pwd:
            messagebox.showwarning("Contraseña requerida","Confirma la contraseña para esta operación.",parent=ventana)
            return
        args={'id':identificador,'antes':original,'motivo':causa}
        if eliminar:
            if confirma.get().strip()!=folio:
                messagebox.showwarning("Confirmación","Escribe exactamente el folio antes de eliminar.",parent=ventana)
                return
            if not messagebox.askyesno("Confirmar eliminación",f"¿Eliminar {folio} definitivamente?\n"
                 "Se conservará el historial de auditoría.",parent=ventana):return
            args['confirmacion']=folio
            accion='eliminar'
        else:
            try:
                cambios = formulario_admin.cambios()
            except (ValueError,TypeError,json.JSONDecodeError,KeyError) as err:
                messagebox.showerror("Dato inválido",str(err),parent=ventana)
                return
            if not cambios:
                messagebox.showinfo("Sin cambios","No modificaste ningún campo.",parent=ventana)
                return
            args['cambios']=cambios
            accion='editar'
        btn.configure(state="disabled",text="Procesando...")
        def confirmado(data):
            clave_confirmacion.delete(0,'end')
            messagebox.showinfo("Cambio confirmado",f"Operación aplicada al folio {folio}.\n"
                        "El servidor guardó un registro de auditoría.",parent=ventana)
            ventana.destroy()
            if callable(on_guardado):on_guardado()
        def error(err):
            if ventana.winfo_exists():
                btn.configure(state="normal",text="Eliminar definitivamente" if eliminar else "Guardar cambios")
                if eliminar:
                    texto = (f"{err}\n\n"
                             "La eliminación no quedó confirmada. Consulta nuevamente el "
                             "registro antes de intentar otra operación. "
                             "No se realizan borrados en cascada desde este módulo.")
                    messagebox.showerror("Eliminación no confirmada", texto, parent=ventana)
                else:
                    messagebox.showerror("Operación no aplicada",str(err),parent=ventana)
        run_async(root=root,task=lambda: ejecutar(tabla,accion,pwd,**args),on_success=confirmado,on_error=error)
    btn.configure(command=aplicar)
    ventana.after(120,ventana.focus_force)
