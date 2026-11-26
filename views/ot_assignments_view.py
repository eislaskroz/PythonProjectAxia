import customtkinter as ctk
from tkinter import messagebox
from ui.fonts import TITLE_MD, TEXT_MD, BUTTON_FONT
from ui.colors import SECONDARY, BUTTON_HOVER
from services.ot_assignments_service import consultar_asignaciones


def abrir_asignaciones(parent, ot_id):
    try:
        data = consultar_asignaciones(ot_id)
    except Exception as exc:
        messagebox.showerror('Asignaciones', str(exc), parent=parent)
        return
    ot = data['ot']
    rows = data['assignments']
    active = [r for r in rows if r['activo']]
    expected = sorted(r['id_asignacion'] for r in active)
    selected = {r['id_usuario'] for r in active}
    win = ctk.CTkToplevel(parent)
    win.title('Asignación de personal · '+ot['ot_folio'])
    win.geometry('760x680')
    win.minsize(580, 480)
    win.transient(parent)
    win.grab_set()
    ctk.CTkLabel(win, text='Asignación de personal · '+ot['ot_folio'], font=TITLE_MD).pack(pady=(14,4))
    ctk.CTkLabel(win, text='Responsables históricos: '+str(ot.get('ot_jefe_operacion') or '—')+' / '+str(ot.get('ot_supervisor') or '—'), font=TEXT_MD, wraplength=680).pack(padx=12)
    ctk.CTkLabel(win, text='Selecciona un jefe, un supervisor y los técnicos autorizados.\nLas asignaciones de seguridad son independientes de los textos históricos de la OT.', font=TEXT_MD, wraplength=680).pack(padx=12,pady=8)
    body=ctk.CTkScrollableFrame(win)
    body.pack(fill='both',expand=True,padx=12,pady=6)
    choices={}
    eligible={u['id_usuario'] for u in data['users']}
    for role, title in [(2,'Jefe de Operaciones'),(3,'Supervisor'),(4,'Técnicos')]:
        ctk.CTkLabel(body,text=title,font=TITLE_MD).pack(anchor='w',pady=(8,3))
        for u in data['users']:
            if int(u['usu_tipo'])!=role: continue
            uid=u['id_usuario']
            var=ctk.BooleanVar(value=uid in selected)
            choices[uid]=(var,role)
            label=' '.join(str(u.get(k) or '') for k in ('usu_nombre','usu_apellido')).strip()+' ('+str(u['usu_nickname'])+')'
            ctk.CTkCheckBox(body,text=label,variable=var,font=TEXT_MD).pack(anchor='w',pady=3)
    if selected-eligible:
        ctk.CTkLabel(body,text='Asignaciones activas no elegibles: '+', '.join(map(str,sorted(selected-eligible)))+'. Se desactivarán al guardar.',wraplength=600,font=TEXT_MD).pack(pady=6)
    ctk.CTkLabel(body,text='Historial de asignaciones',font=TITLE_MD).pack(anchor='w',pady=(12,4))
    for r in rows:
        ctk.CTkLabel(body,text=f"ID {r['id_usuario']} · {r['rol_operativo']} · {'Activa' if r['activo'] else 'Baja'} · {r.get('asignado_en','')} · por {r.get('asignado_por_id') or 'migración'} · baja por {r.get('desactivado_por_id') or '—'}",font=TEXT_MD,wraplength=630,justify='left').pack(anchor='w')
    def save():
        users=[uid for uid,(var,_) in choices.items() if var.get()]
        if any(sum(1 for uid in users if choices[uid][1]==role)>1 for role in (2,3)):
            messagebox.showwarning('Asignaciones','Selecciona máximo un jefe y un supervisor.',parent=win);return
        if not messagebox.askyesno('Confirmar','¿Guardar esta selección? Las asignaciones omitidas serán desactivadas.',parent=win):return
        button.configure(state='disabled')
        try:
            consultar_asignaciones(ot_id,'save',expected,users)
        except Exception as exc:
            messagebox.showerror('Asignaciones',str(exc),parent=win)
            button.configure(state='normal');return
        messagebox.showinfo('Asignaciones','Asignaciones guardadas correctamente.',parent=win)
        win.destroy()
    button=ctk.CTkButton(win,text='Guardar asignaciones',font=BUTTON_FONT,fg_color=SECONDARY,hover_color=BUTTON_HOVER,command=save,state='disabled' if ot['ot_estatus']==3 else 'normal')
    button.pack(pady=10)
