"""Conversión administrativa de Órdenes de Servicio a Órdenes de Trabajo."""
from __future__ import annotations

import json
import customtkinter as ctk
from tkinter import messagebox

from app_context import obtener_usuario_actual
from ui.date_picker import asociar_selector_fecha
from core.background_tasks import run_async
from security.permissions import puede_convertir_levantamiento_a_orden
from services.ordenes_servicio_service import obtener_ordenes_servicio, buscar_ordenes_servicio, actualizar_orden_servicio
from services.ordenes_trabajo_service import (
    convertir_orden_servicio_a_trabajo,
    buscar_orden_trabajo_por_orden_servicio,
)
from services.operational_document_pdf import preview_orden_servicio, preview_orden_trabajo
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY, BUTTON_HOVER
from ui.fonts import TITLE_MD, TEXT_MD, TEXT_SM, BUTTON_FONT
from ui.native_table import NativeTreeTable


def _valor(registro, *campos, default=""):
    for campo in campos:
        valor = (registro or {}).get(campo)
        if valor not in (None, ""):
            return str(valor)
    return default


def mostrar_conversion_orden_trabajo(parent, app):
    usuario = obtener_usuario_actual()
    if not puede_convertir_levantamiento_a_orden(usuario):
        messagebox.showerror("Acceso denegado", "Esta función está reservada al personal Administrativo (usu_tipo=5).")
        return

    for widget in parent.winfo_children():
        widget.destroy()

    root = ctk.CTkFrame(parent, fg_color="transparent")
    root.pack(fill="both", expand=True, padx=14, pady=(4, 12))
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)

    search = ctk.CTkFrame(root, fg_color=WHITE, corner_radius=16)
    search.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    search.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(search, text="Convertir Orden de Servicio en Orden de Trabajo", font=TITLE_MD,
                 text_color=TEXT_PRIMARY, anchor="w").grid(row=0, column=0, columnspan=4, sticky="ew", padx=12, pady=(10, 2))
    ctk.CTkLabel(search, text="Busca una OS aceptada, ajusta la información operativa y genera la Orden de Trabajo.",
                 font=TEXT_MD, text_color=TEXT_SECONDARY, anchor="w").grid(row=1, column=0, columnspan=4, sticky="ew", padx=12, pady=(0, 8))
    var_search = ctk.StringVar()
    ent_search = ctk.CTkEntry(search, textvariable=var_search, height=40, placeholder_text="Folio OS, ACO, cliente, técnico o descripción")
    ent_search.grid(row=2, column=0, sticky="ew", padx=(12, 5), pady=(0, 10))

    body = ctk.CTkFrame(root, fg_color="transparent")
    body.grid(row=1, column=0, sticky="nsew")
    body.grid_columnconfigure(0, weight=5)
    body.grid_columnconfigure(1, weight=6)
    body.grid_rowconfigure(0, weight=1)

    left = ctk.CTkFrame(body, fg_color=WHITE, corner_radius=16)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
    left.grid_columnconfigure(0, weight=1)
    left.grid_rowconfigure(1, weight=1)
    ctk.CTkLabel(left, text="Órdenes de Servicio", font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w").grid(row=0, column=0, sticky="ew", padx=10, pady=(9, 4))
    table = NativeTreeTable(left, columns=(("folio", "Folio", 105), ("cliente", "Cliente", 190), ("tipo", "Tipo", 150), ("estatus", "Estatus", 75), ("fecha", "Fecha", 105)), height=20)
    table.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

    # Panel derecho: contenido desplazable + barra de acciones fija.
    # Los botones permanecen visibles mientras se revisa la Orden de Servicio.
    form_shell = ctk.CTkFrame(body, fg_color=WHITE, corner_radius=16)
    form_shell.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
    form_shell.grid_columnconfigure(0, weight=1)
    form_shell.grid_rowconfigure(0, weight=1)

    form = ctk.CTkScrollableFrame(form_shell, fg_color=WHITE, corner_radius=16)
    form.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 2))
    form.grid_columnconfigure(0, weight=1)
    form.grid_columnconfigure(1, weight=1)

    selected = {"record": None, "editando": False}
    editable_widgets = []
    vars_ = {
        "os_folio": ctk.StringVar(), "os_aco_numero": ctk.StringVar(), "os_cliente": ctk.StringVar(),
        "os_contacto": ctk.StringVar(), "os_sucursal": ctk.StringVar(), "os_supervisor": ctk.StringVar(),
        "os_tecnico": ctk.StringVar(), "ot_fecha": ctk.StringVar(), "ot_fecha_programada": ctk.StringVar(),
        "ot_jefe_operacion": ctk.StringVar(), "ot_esi": ctk.StringVar(), "ot_numero_dias": ctk.StringVar(value="1"),
        "ot_numero_personas": ctk.StringVar(value="1"), "ot_asunto": ctk.StringVar(),
    }

    def field(label, key, row, col, disabled=False):
        frame = ctk.CTkFrame(form, fg_color="transparent")
        frame.grid(row=row, column=col, sticky="ew", padx=5, pady=3)
        ctk.CTkLabel(frame, text=label, font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
        ent = ctk.CTkEntry(frame, textvariable=vars_[key], height=36)
        ent.pack(fill="x")
        if disabled:
            ent.configure(state="disabled")
        else:
            editable_widgets.append(ent)
            if "fecha" in label.lower():
                asociar_selector_fecha(ent, frame, vars_[key])
        return ent

    ctk.CTkLabel(form, text="Información para la Orden de Trabajo", font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w").grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=(4, 7))
    field("Folio OS", "os_folio", 1, 0, True)
    field("ACO", "os_aco_numero", 1, 1)
    field("Cliente", "os_cliente", 2, 0)
    field("Contacto", "os_contacto", 2, 1)
    field("Sucursal / ubicación", "os_sucursal", 3, 0)
    field("Supervisor", "os_supervisor", 3, 1)
    field("Técnico", "os_tecnico", 4, 0)
    field("Fecha OT", "ot_fecha", 4, 1)
    field("Fecha programada", "ot_fecha_programada", 5, 0)
    field("Jefe de operación", "ot_jefe_operacion", 5, 1)
    field("ESI / responsable", "ot_esi", 6, 0)
    field("Número de días", "ot_numero_dias", 6, 1)
    field("Número de personas", "ot_numero_personas", 7, 0)
    field("Asunto", "ot_asunto", 7, 1)

    box_frame = ctk.CTkFrame(form, fg_color="transparent")
    box_frame.grid(row=8, column=0, columnspan=2, sticky="ew", padx=5, pady=4)
    ctk.CTkLabel(box_frame, text="Descripción operativa", font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
    txt_description = ctk.CTkTextbox(box_frame, height=100)
    txt_description.pack(fill="x")
    editable_widgets.append(txt_description)

    part_frame = ctk.CTkFrame(form, fg_color="transparent")
    part_frame.grid(row=9, column=0, columnspan=2, sticky="ew", padx=5, pady=4)
    ctk.CTkLabel(part_frame, text="Partidas / conceptos JSON", font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
    txt_parts = ctk.CTkTextbox(part_frame, height=170)
    txt_parts.pack(fill="x")
    editable_widgets.append(txt_parts)

    status = ctk.CTkLabel(form, text="Selecciona una Orden de Servicio.", font=TEXT_SM, text_color=TEXT_SECONDARY, anchor="w", justify="left")
    status.grid(row=10, column=0, columnspan=2, sticky="ew", padx=6, pady=(6, 2))

    def set_text(box, value):
        box.delete("1.0", "end")
        box.insert("1.0", value or "")


    def set_edit_mode(enabled):
        selected["editando"] = bool(enabled)
        state = "normal" if enabled else "disabled"
        for widget in editable_widgets:
            try:
                widget.configure(state=state)
            except Exception:
                pass
        btn_edit.configure(state="disabled" if enabled else ("normal" if selected.get("record") else "disabled"))
        btn_save.configure(state="normal" if enabled else "disabled")
        if selected.get("record"):
            status.configure(
                text=("Modo edición habilitado. Guarda los cambios antes de convertir." if enabled else "Modo consulta. Usa Editar si necesitas modificar la Orden de Servicio."),
                text_color=TEXT_SECONDARY,
            )

    def save_changes():
        record = selected.get("record")
        if not record or not selected.get("editando"):
            return
        id_orden = record.get("id_orden")
        if not id_orden:
            messagebox.showerror("No se pudo guardar", "La Orden de Servicio no contiene id_orden.")
            return
        payload = {
            "os_aco_numero": vars_["os_aco_numero"].get().strip(),
            "os_cliente": vars_["os_cliente"].get().strip(),
            "os_contacto": vars_["os_contacto"].get().strip(),
            "os_sucursal": vars_["os_sucursal"].get().strip(),
            "os_supervisor": vars_["os_supervisor"].get().strip(),
            "os_tecnico": vars_["os_tecnico"].get().strip(),
            "os_fecha": vars_["ot_fecha"].get().strip() or None,
            "os_fecha_programada": vars_["ot_fecha_programada"].get().strip() or None,
            "os_encargado_servicio": vars_["ot_jefe_operacion"].get().strip(),
            "os_descripcion": txt_description.get("1.0", "end").strip(),
        }
        btn_save.configure(state="disabled")
        status.configure(text="Guardando cambios de la Orden de Servicio...", text_color=TEXT_SECONDARY)

        def ok(result):
            if not result:
                btn_save.configure(state="normal")
                status.configure(text="Supabase no confirmó la actualización.", text_color="#B91C1C")
                messagebox.showerror("No se pudo guardar", "Supabase no confirmó la actualización de la Orden de Servicio.")
                return
            record.update(payload)
            selected["record"] = record
            set_edit_mode(False)
            status.configure(text="Cambios guardados correctamente. Ya puedes convertir a OT.", text_color="#15803D")
            messagebox.showinfo("Cambios guardados", "La Orden de Servicio se actualizó correctamente.")
            search_records()

        run_async(parent.winfo_toplevel(), lambda: actualizar_orden_servicio(id_orden, payload), ok,
                  lambda e: (btn_save.configure(state="normal"), status.configure(text="No se pudieron guardar los cambios.", text_color="#B91C1C"), messagebox.showerror("Error al guardar", str(e))))

    def load_selected():
        record = table.selected_payload()
        if not record:
            messagebox.showinfo("Selecciona una orden", "Selecciona una fila de la tabla.")
            return
        selected["record"] = dict(record)
        for widget in editable_widgets:
            try:
                widget.configure(state="normal")
            except Exception:
                pass
        vars_["os_folio"].set(_valor(record, "os_folio"))
        vars_["os_aco_numero"].set(_valor(record, "os_aco_numero"))
        vars_["os_cliente"].set(_valor(record, "os_cliente"))
        vars_["os_contacto"].set(_valor(record, "os_contacto", "os_encargado"))
        vars_["os_sucursal"].set(_valor(record, "os_sucursal", "os_ubicacion"))
        vars_["os_supervisor"].set(_valor(record, "os_supervisor"))
        vars_["os_tecnico"].set(_valor(record, "os_tecnico", "os_tecnicos"))
        vars_["ot_fecha"].set(_valor(record, "os_fecha"))
        vars_["ot_fecha_programada"].set(_valor(record, "os_fecha_programada"))
        vars_["ot_jefe_operacion"].set(_valor(record, "os_encargado_servicio"))
        vars_["ot_esi"].set(_valor(record, "os_tecnico", "os_tecnicos"))
        vars_["ot_asunto"].set(_valor(record, "os_descripcion"))
        set_text(txt_description, _valor(record, "os_descripcion"))
        descripcion_os = _valor(record, "os_descripcion")
        concepto_base = f"Ejecución del servicio conforme a la Orden de Servicio {_valor(record, 'os_folio')}"
        default_parts = [{"partida": "1", "unidad": "Servicio", "cantidad": "1", "modelo": "", "marca": "", "concepto": concepto_base}]
        if _valor(record, "os_materiales"):
            default_parts.append({"partida": "2", "unidad": "Lote", "cantidad": "1", "modelo": "", "marca": "", "concepto": _valor(record, "os_materiales")})
        set_text(txt_parts, json.dumps(default_parts, ensure_ascii=False, indent=2))
        existing = buscar_orden_trabajo_por_orden_servicio(record.get("os_folio"))
        if existing:
            status.configure(text=f"Esta OS ya fue convertida en {existing.get('ot_folio', 'una OT')}.", text_color="#B45309")
            btn_convert.configure(state="disabled")
        else:
            status.configure(text="Revisa los datos, visualiza el PDF y convierte cuando esté lista para ejecución.", text_color="#15803D")
            btn_convert.configure(state="normal")
        btn_preview_os.configure(state="normal")
        set_edit_mode(False)

    def search_records():
        term = var_search.get().strip()
        records = buscar_ordenes_servicio(term) if term else obtener_ordenes_servicio()
        table.set_rows(records, value_factory=lambda record: (
            record.get("os_folio", ""), record.get("os_cliente", ""),
            record.get("os_tipo_servicio", ""), record.get("os_estatus", ""),
            record.get("os_fecha") or record.get("fecha_registro", ""),
        ))

    def draft_ot():
        record = selected["record"]
        if not record:
            raise ValueError("Selecciona una Orden de Servicio.")
        try:
            parts = json.loads(txt_parts.get("1.0", "end").strip() or "[]")
            if not isinstance(parts, list):
                raise ValueError
        except Exception as error:
            raise ValueError("Partidas / conceptos debe contener una lista JSON válida.") from error
        return {
            "ot_folio": "SE ASIGNA AL GUARDAR", "ot_aco_numero": vars_["os_aco_numero"].get().strip(),
            "ot_cliente": vars_["os_cliente"].get().strip(), "ot_contacto": vars_["os_contacto"].get().strip(),
            "ot_sucursal": vars_["os_sucursal"].get().strip(), "ot_supervisor": vars_["os_supervisor"].get().strip(),
            "ot_tecnico": vars_["os_tecnico"].get().strip(), "ot_fecha": vars_["ot_fecha"].get().strip(),
            "ot_fecha_programada": vars_["ot_fecha_programada"].get().strip(), "ot_jefe_operacion": vars_["ot_jefe_operacion"].get().strip(),
            "ot_esi": vars_["ot_esi"].get().strip(), "ot_numero_dias": vars_["ot_numero_dias"].get().strip(),
            "ot_numero_personas": vars_["ot_numero_personas"].get().strip(), "ot_asunto": vars_["ot_asunto"].get().strip(),
            "ot_descripcion": txt_description.get("1.0", "end").strip(), "ot_partidas_json": parts,
        }

    def preview_os():
        if selected["record"]:
            preview_orden_servicio(selected["record"])

    def convert():
        try:
            draft = draft_ot()
            required = [draft["ot_cliente"], draft["ot_asunto"], draft["ot_numero_dias"], draft["ot_numero_personas"]]
            if not all(required):
                raise ValueError("Completa cliente, asunto, número de días y número de personas.")
        except Exception as error:
            messagebox.showwarning("Información incompleta", str(error))
            return
        if selected.get("editando"):
            messagebox.showwarning("Edición pendiente", "Guarda los cambios antes de convertir a Orden de Trabajo.")
            return
        if not messagebox.askyesno("Confirmar conversión", f"¿Convertir {selected['record'].get('os_folio')} en Orden de Trabajo?"):
            return
        btn_convert.configure(state="disabled")
        status.configure(text="Creando Orden de Trabajo...", text_color=TEXT_SECONDARY)

        def ok(result):
            folio = result[0].get("ot_folio", "OT") if result else "OT"
            status.configure(text=f"Conversión completada: {folio}", text_color="#15803D")
            messagebox.showinfo("Orden de Trabajo creada", f"La Orden de Servicio se convirtió correctamente en {folio}.")
            search_records()

        run_async(parent.winfo_toplevel(), lambda: convertir_orden_servicio_a_trabajo(selected["record"], draft, usuario), ok,
                  lambda e: (btn_convert.configure(state="normal"), status.configure(text="No se completó la conversión.", text_color="#B91C1C"), messagebox.showerror("Error al convertir", str(e))))

    ctk.CTkButton(search, text="🔎 Buscar", width=130, height=40, fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=search_records).grid(row=2, column=1, padx=4, pady=(0, 10))
    ctk.CTkButton(search, text="↻ Recientes", width=135, height=40, fg_color="#334155", hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=lambda: (var_search.set(""), search_records())).grid(row=2, column=2, padx=(0, 12), pady=(0, 10))
    ent_search.bind("<Return>", lambda _e: search_records())

    # Barra fija: no forma parte del área desplazable del formulario.
    actions = ctk.CTkFrame(form_shell, fg_color=WHITE, corner_radius=0)
    actions.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 10))
    actions.grid_columnconfigure((0, 1), weight=1)

    ctk.CTkButton(actions, text="📥 Cargar seleccionado", command=load_selected).grid(
        row=0, column=0, sticky="ew", padx=4, pady=4
    )
    btn_preview_os = ctk.CTkButton(actions, text="👁 PDF Orden de Servicio", command=preview_os, state="disabled")
    btn_preview_os.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

    edit_row = ctk.CTkFrame(actions, fg_color="transparent")
    edit_row.grid(row=1, column=0, columnspan=2, sticky="ew")
    edit_row.grid_columnconfigure((0, 1, 2), weight=1)
    btn_edit = ctk.CTkButton(edit_row, text="✎ Editar", command=lambda: set_edit_mode(True), state="disabled")
    btn_edit.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
    btn_save = ctk.CTkButton(edit_row, text="💾 Guardar", command=save_changes, state="disabled")
    btn_save.grid(row=0, column=1, sticky="ew", padx=4, pady=4)
    btn_convert = ctk.CTkButton(
        edit_row, text="✓ Convertir a OT", fg_color=SECONDARY, hover_color=BUTTON_HOVER,
        command=convert, state="disabled",
    )
    btn_convert.grid(row=0, column=2, sticky="ew", padx=4, pady=4)

    search_records()
