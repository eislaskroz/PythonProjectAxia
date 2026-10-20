"""Editor administrativo reutilizable para OT y Bitácoras Operativas.

Replica el patrón de revisión segura usado en LEV -> OS:
- Cargar seleccionado
- PDF del documento
- Editar
- Guardar
- Acción de avance/cierre
Los botones permanecen fijos; solo el formulario se desplaza.
"""
from __future__ import annotations
from ui.form_fields import AxiaEntry, AxiaTextbox

import json
from pathlib import Path
import customtkinter as ctk
from ui.iconos import cargar_icono
_AXIA_ICON_BUSCAR = cargar_icono("buscar.png", (18, 18))
_AXIA_ICON_BUSCAR_BLANCO = cargar_icono("buscar.png", (16, 16), blanco=True)
from tkinter import messagebox
from PIL import Image

from core.background_tasks import run_async
from core.search_utils import normalizar_termino_busqueda
from services.pdf_registro_service import previsualizar_pdf_registro
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY, BUTTON_HOVER
from ui.fonts import TITLE_MD, TEXT_MD, TEXT_SM, BUTTON_FONT
from ui.native_table import NativeTreeTable


def _value(record, *keys, default=""):
    for key in keys:
        value = (record or {}).get(key)
        if value not in (None, ""):
            return str(value)
    return default


def mostrar_admin_operational_editor(parent, app, config):
    for widget in parent.winfo_children():
        widget.destroy()

    root = ctk.CTkFrame(parent, fg_color="transparent")
    root.pack(fill="both", expand=True, padx=14, pady=(4, 12))
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)

    search = ctk.CTkFrame(root, fg_color=WHITE, corner_radius=16)
    search.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    search.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(search, text=f"Administración de {config['titulo']}", font=TITLE_MD,
                 text_color=TEXT_PRIMARY, anchor="w").grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=(10, 2))
    ctk.CTkLabel(search, text=config.get("subtitulo", "Busca un registro, revísalo y habilita la edición solo cuando sea necesario."),
                 font=TEXT_MD, text_color=TEXT_SECONDARY, anchor="w").grid(row=1, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 8))
    var_search = ctk.StringVar()
    buscador = ctk.CTkFrame(
        search,
        fg_color="#F8FAFC",
        corner_radius=12,
        border_width=1,
        border_color="#D9E2EC",
    )
    buscador.grid(row=2, column=0, sticky="ew", padx=(12, 5), pady=(0, 10))
    buscador.grid_columnconfigure(1, weight=1)

    carpeta_iconos = Path(__file__).resolve().parent.parent / "assets" / "iconos"
    with Image.open(carpeta_iconos / "buscar.png") as imagen_buscar:
        imagen_buscar = imagen_buscar.convert("RGBA")
    icono_buscar = ctk.CTkImage(light_image=imagen_buscar, dark_image=imagen_buscar, size=(20, 20))
    imagen_buscar_blanca = Image.new("RGBA", imagen_buscar.size, (255, 255, 255, 0))
    imagen_buscar_blanca.putalpha(imagen_buscar.getchannel("A"))
    icono_buscar_blanco = ctk.CTkImage(light_image=imagen_buscar_blanca, dark_image=imagen_buscar_blanca, size=(16, 16))
    with Image.open(carpeta_iconos / "reciente.png") as imagen_reciente:
        imagen_reciente = imagen_reciente.convert("RGBA")
    imagen_reciente_blanca = Image.new("RGBA", imagen_reciente.size, (255, 255, 255, 0))
    imagen_reciente_blanca.putalpha(imagen_reciente.getchannel("A"))
    icono_reciente = ctk.CTkImage(light_image=imagen_reciente_blanca, dark_image=imagen_reciente_blanca, size=(16, 16))

    ctk.CTkLabel(
        buscador,
        text="",
        image=icono_buscar,
        width=28,
        height=38,
        anchor="center",
    ).grid(row=0, column=0, sticky="ns", padx=(12, 8), pady=6)

    ent_search = AxiaEntry(
        buscador,
        textvariable=var_search,
        height=38,
        fg_color="transparent",
        border_width=0,
        font=("Segoe UI", 13),
    )
    ent_search.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=6)

    placeholder = ctk.CTkLabel(
        buscador,
        text="Realiza tu búsqueda",
        font=("Segoe UI", 13),
        text_color="#64748B",
        anchor="w",
        justify="left",
    )
    placeholder.place(in_=ent_search, relx=0.02, rely=0.5, anchor="w")

    def _placeholder_busqueda(event=None):
        valor = var_search.get()
        tiene_texto = bool(valor.strip())
        tiene_foco = ent_search.focus_get() == ent_search
        if tiene_texto or tiene_foco:
            placeholder.place_forget()
        else:
            placeholder.place(in_=ent_search, relx=0.02, rely=0.5, anchor="w")

    var_search.trace_add("write", lambda *_: _placeholder_busqueda())
    ent_search.bind("<FocusIn>", _placeholder_busqueda)
    ent_search.bind("<FocusOut>", _placeholder_busqueda)
    ent_search.bind("<KeyRelease>", _placeholder_busqueda)
    _placeholder_busqueda()

    body = ctk.CTkFrame(root, fg_color="transparent")
    body.grid(row=1, column=0, sticky="nsew")
    body.grid_columnconfigure(0, weight=5)
    body.grid_columnconfigure(1, weight=6)
    body.grid_rowconfigure(0, weight=1)

    left = ctk.CTkFrame(body, fg_color=WHITE, corner_radius=16)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
    left.grid_columnconfigure(0, weight=1)
    left.grid_rowconfigure(1, weight=1)
    lbl_results = ctk.CTkLabel(left, text=config["titulo"], font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w")
    lbl_results.grid(row=0, column=0, sticky="ew", padx=10, pady=(9, 4))
    table = NativeTreeTable(left, columns=(("folio", "Folio", 115), ("aco", "ACO", 135), ("cliente", "Cliente", 190),
                                                ("estatus", "Estatus", 80), ("fecha", "Fecha", 110)), height=20)
    table.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

    shell = ctk.CTkFrame(body, fg_color=WHITE, corner_radius=16)
    shell.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
    shell.grid_columnconfigure(0, weight=1)
    shell.grid_rowconfigure(0, weight=1)
    form = ctk.CTkScrollableFrame(shell, fg_color=WHITE, corner_radius=16)
    form.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 2))
    form.grid_columnconfigure(0, weight=1)
    form.grid_columnconfigure(1, weight=1)

    selected = {"record": None, "editando": False}
    vars_ = {}
    widgets = []
    textboxes = {}

    ctk.CTkLabel(form, text=f"Información de {config['titulo_singular']}", font=TITLE_MD,
                 text_color=TEXT_PRIMARY, anchor="w").grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=(4, 7))

    row = 1
    for index, field in enumerate(config["campos"]):
        key = field["key"]
        label = field["label"]
        kind = field.get("kind", "entry")
        readonly = field.get("readonly", False)
        col = index % 2 if kind == "entry" else 0
        if kind != "entry" and index % 2:
            row += 1
        frame = ctk.CTkFrame(form, fg_color="transparent")
        if kind == "entry":
            frame.grid(row=row, column=col, sticky="ew", padx=5, pady=3)
        else:
            frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=4)
        ctk.CTkLabel(frame, text=label, font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
        if kind == "entry":
            var = ctk.StringVar()
            vars_[key] = var
            widget = AxiaEntry(frame, textvariable=var, height=36)
            widget.pack(fill="x")
            if readonly:
                widget.configure(state="disabled")
            else:
                widgets.append(widget)
            if col == 1:
                row += 1
        else:
            widget = AxiaTextbox(frame, height=field.get("height", 100))
            widget.pack(fill="x")
            textboxes[key] = widget
            widgets.append(widget)
            row += 1

    status = ctk.CTkLabel(form, text=f"Selecciona {config['articulo']} {config['titulo_singular']} para continuar.",
                          font=TEXT_SM, text_color=TEXT_SECONDARY, anchor="w", justify="left")
    status.grid(row=row + 1, column=0, columnspan=2, sticky="ew", padx=6, pady=(6, 2))

    def set_text(box, value):
        try:
            box.configure(state="normal")
        except Exception:
            pass
        box.delete("1.0", "end")
        box.insert("1.0", value or "")

    def set_edit_mode(enabled):
        selected["editando"] = bool(enabled)
        state = "normal" if enabled else "disabled"
        for widget in widgets:
            try:
                widget.configure(state=state)
            except Exception:
                pass
        btn_edit.configure(state="disabled" if enabled else ("normal" if selected.get("record") else "disabled"))
        btn_save.configure(state="normal" if enabled else "disabled")
        if selected.get("record"):
            status.configure(text=("Modo edición habilitado. Guarda los cambios antes de continuar." if enabled
                                   else "Modo consulta. Usa Editar solo si necesitas modificar información."),
                             text_color=TEXT_SECONDARY)

    def _widget_alive(widget):
        try:
            return bool(widget.winfo_exists())
        except Exception:
            return False

    def render(records):
        # Una consulta puede terminar después de que el usuario cambió de módulo.
        # En ese caso CustomTkinter ya destruyó los labels/botones de esta vista y
        # cualquier configure() provocaría TclError: invalid command name.
        if not _widget_alive(root) or not _widget_alive(lbl_results):
            return
        records = records or []
        lbl_results.configure(text=f"{config['titulo']} ({len(records)})")
        table.set_rows(records, value_factory=lambda r: (
            _value(r, config["campo_folio"]),
            _value(r, *config["campos_aco"]),
            _value(r, *config["campos_cliente"]),
            _value(r, *config["campos_estatus"]),
            _value(r, *config["campos_fecha"]),
        ))

    def search_records():
        if not _widget_alive(root):
            return
        term = normalizar_termino_busqueda(var_search.get().strip())
        task = (lambda: config["buscar"](term)) if term else (lambda: config["obtener_todos"]())
        if _widget_alive(lbl_results):
            lbl_results.configure(text="Consultando...")

        def search_error(exc):
            if _widget_alive(root):
                messagebox.showerror("Error", f"No fue posible consultar registros.\n\n{exc}")

        run_async(parent.winfo_toplevel(), task, lambda r: render((r or [])[:100]), search_error)

    def load_selected():
        record = table.selected_payload()
        if not record:
            messagebox.showinfo("Selecciona un registro", "Selecciona una fila de la tabla.")
            return
        selected["record"] = dict(record)
        for widget in widgets:
            try:
                widget.configure(state="normal")
            except Exception:
                pass
        for field in config["campos"]:
            key = field["key"]
            value = record.get(key, "")
            if field.get("kind", "entry") == "entry":
                vars_[key].set("" if value is None else str(value))
            else:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False, indent=2)
                set_text(textboxes[key], "" if value is None else str(value))
        set_edit_mode(False)
        btn_pdf.configure(state="normal")
        btn_action.configure(state="normal")
        status.configure(text="Modo consulta. Revisa los datos; usa Editar solo si necesitas cambios.", text_color=TEXT_SECONDARY)

    def capture_payload():
        payload = {}
        for field in config["campos"]:
            if field.get("readonly"):
                continue
            key = field["key"]
            if field.get("kind", "entry") == "entry":
                value = vars_[key].get().strip()
            else:
                value = textboxes[key].get("1.0", "end").strip()
                if field.get("json") and value:
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"{field['label']} contiene JSON inválido: {exc}") from exc
            if field.get("integer") and value not in (None, ""):
                try:
                    value = int(value)
                except ValueError as exc:
                    raise ValueError(f"{field['label']} debe ser un número entero.") from exc
            payload[key] = value if value != "" else None if field.get("nullable") else ""
        return payload

    def save_changes():
        record = selected.get("record")
        if not record or not selected.get("editando"):
            return
        try:
            payload = capture_payload()
        except ValueError as exc:
            messagebox.showwarning("Información inválida", str(exc))
            return
        record_id = record.get(config["id_field"])
        if record_id in (None, ""):
            messagebox.showerror("No se pudo guardar", f"El registro no contiene {config['id_field']}.")
            return
        btn_save.configure(state="disabled")
        status.configure(text="Guardando cambios...", text_color=TEXT_SECONDARY)

        def ok(result):
            if not _widget_alive(root):
                return
            if not result:
                if _widget_alive(btn_save):
                    btn_save.configure(state="normal")
                messagebox.showerror("No se pudo guardar", "Supabase no confirmó la actualización.")
                return
            record.update(payload)
            selected["record"] = record
            set_edit_mode(False)
            status.configure(text="Cambios guardados correctamente.", text_color="#15803D")
            messagebox.showinfo("Cambios guardados", f"{config['titulo_singular']} actualizado correctamente.")
            search_records()
        def save_error(exc):
            if not _widget_alive(root):
                return
            if _widget_alive(btn_save):
                btn_save.configure(state="normal")
            messagebox.showerror("Error al guardar", str(exc))

        run_async(parent.winfo_toplevel(), lambda: config["actualizar"](record_id, payload), ok, save_error)

    def preview_pdf():
        record = selected.get("record")
        if record:
            previsualizar_pdf_registro(record, config["pdf_config"])

    def final_action():
        record = selected.get("record")
        if not record:
            return
        if selected.get("editando"):
            messagebox.showwarning("Edición pendiente", "Guarda los cambios antes de continuar.")
            return
        config["accion"](record, status, search_records)

    ctk.CTkButton(search, text="Buscar", image=icono_buscar_blanco, compound="left", width=130, height=40, corner_radius=10, fg_color="#2563EB",
                  hover_color="#1D4ED8", text_color=WHITE, font=BUTTON_FONT, command=search_records).grid(row=2, column=1, padx=4, pady=(0, 10))
    ctk.CTkButton(search, text="Recientes", image=icono_reciente, compound="left", width=135, height=40, corner_radius=10, fg_color="#334155",
                  hover_color="#475569", text_color=WHITE, font=BUTTON_FONT, command=lambda: (var_search.set(""), search_records())).grid(row=2, column=2, padx=(0, 12), pady=(0, 10))
    ent_search.bind("<Return>", lambda _e: search_records())

    actions = ctk.CTkFrame(shell, fg_color=WHITE, corner_radius=0)
    actions.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 10))
    actions.grid_columnconfigure((0, 1), weight=1)

    carpeta_iconos = Path(__file__).resolve().parent.parent / "assets" / "iconos"

    def cargar_icono_boton(nombre):
        with Image.open(carpeta_iconos / nombre) as imagen:
            imagen = imagen.convert("RGBA")
        icono_blanco = Image.new("RGBA", imagen.size, (255, 255, 255, 0))
        icono_blanco.putalpha(imagen.getchannel("A"))
        return ctk.CTkImage(
            light_image=icono_blanco,
            dark_image=icono_blanco,
            size=(18, 18)
        )

    icono_detalle = cargar_icono_boton("detalle.png")
    icono_pdf = cargar_icono_boton("pdf.png")
    icono_editar = cargar_icono_boton("lapiz.png")
    icono_guardar = cargar_icono_boton("guardar.png")
    icono_votar = cargar_icono_boton("votar.png")

    ctk.CTkButton(actions, text="Cargar seleccionado", image=icono_detalle, compound="left", width=190, height=40, corner_radius=10,
                  fg_color="#2563EB", hover_color="#1D4ED8", text_color=WHITE,
                  border_width=0, font=BUTTON_FONT, command=load_selected).grid(row=0, column=0, sticky="ew", padx=4, pady=4)
    btn_pdf = ctk.CTkButton(actions, text=config["pdf_text"], image=icono_pdf, compound="left", width=190, height=40, corner_radius=10,
                           fg_color="#2563EB", hover_color="#1D4ED8", text_color=WHITE,
                           border_width=0, font=BUTTON_FONT, command=preview_pdf, state="disabled")
    btn_pdf.grid(row=0, column=1, sticky="ew", padx=4, pady=4)
    row_actions = ctk.CTkFrame(actions, fg_color="transparent")
    row_actions.grid(row=1, column=0, columnspan=2, sticky="ew")
    row_actions.grid_columnconfigure((0, 1, 2), weight=1)
    btn_edit = ctk.CTkButton(row_actions, text="Editar", image=icono_editar, compound="left", width=140, height=40, corner_radius=10,
                            fg_color="#3B82F6", hover_color="#2563EB", text_color=WHITE,
                            border_width=0, font=BUTTON_FONT, command=lambda: set_edit_mode(True), state="disabled")
    btn_edit.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
    btn_save = ctk.CTkButton(row_actions, text="Guardar", image=icono_guardar, compound="left", width=140, height=40, corner_radius=10,
                            fg_color=SECONDARY, hover_color=BUTTON_HOVER, text_color=WHITE,
                            border_width=0, font=BUTTON_FONT, command=save_changes, state="disabled")
    btn_save.grid(row=0, column=1, sticky="ew", padx=4, pady=4)
    btn_action = ctk.CTkButton(row_actions, text=config["accion_text"], image=icono_votar, compound="left", width=170, height=40, corner_radius=10,
                              fg_color=SECONDARY, hover_color=BUTTON_HOVER, text_color=WHITE,
                              border_width=0, font=BUTTON_FONT, command=final_action, state="disabled")
    btn_action.grid(row=0, column=2, sticky="ew", padx=4, pady=4)

    search_records()
