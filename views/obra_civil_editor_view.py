"""Modal de edición que reutiliza la interfaz ORIGINAL de Obra Civil.

No contiene una copia simplificada ni editores JSON. El folio versionado se
asigna exclusivamente en Supabase al confirmar una modificación real.
"""
import customtkinter as ctk
from tkinter import messagebox


def abrir_editor_obra_civil(padre, obra, al_guardar):
    if not (isinstance(obra,dict) and obra.get('obc_folio') and obra.get('obc_id')):
        messagebox.showerror('Obra Civil','No se pudo identificar la obra completa.',parent=padre)
        return
    ventana=ctk.CTkToplevel(padre)
    ventana.title(f"Edición integral de Obra Civil · {obra['obc_folio']}")
    sw,sh=ventana.winfo_screenwidth(),ventana.winfo_screenheight()
    w,h=min(sw,max(980,int(sw*.91))),min(sh,max(650,int(sh*.9)))
    ventana.geometry(f'{w}x{h}+{max(0,(sw-w)//2)}+{max(0,(sh-h)//2)}')
    ventana.transient(padre)
    host=ctk.CTkFrame(ventana,fg_color='transparent')
    host.pack(fill='both',expand=True)
    try:
        from views.obra_civil_view import mostrar_obra_civil
        # app no se utiliza para navegar ni autoguardar durante la edición.
        mostrar_obra_civil(host, app=None, obra_edicion=obra, al_guardar=al_guardar)
    except Exception:
        ventana.destroy()
        raise
    ventana.grab_set()
    return ventana
