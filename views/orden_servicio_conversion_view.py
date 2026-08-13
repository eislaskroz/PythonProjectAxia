"""Conversión administrativa de levantamientos a órdenes de trabajo."""

import json
import customtkinter as ctk
from tkinter import messagebox

from app_context import obtener_usuario_actual
from ui.date_picker import asociar_selector_fecha
from core.background_tasks import run_async
from core.logger import configurar_logger
from security.permissions import puede_convertir_levantamiento_a_orden
from services.levantamientos_service import obtener_levantamientos, buscar_levantamientos, actualizar_levantamiento
from services.ordenes_trabajo_service import convertir_levantamiento_a_trabajo, buscar_orden_trabajo_por_levantamiento
from services.pdf_registro_service import generar_pdf_registro
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY, BUTTON_HOVER
from ui.fonts import TITLE_MD, TEXT_MD, TEXT_SM, BUTTON_FONT
from ui.native_table import NativeTreeTable

logger = configurar_logger(__name__)


def _valor(registro, *campos, default=""):
    for campo in campos:
        valor = (registro or {}).get(campo)
        if valor not in (None, ""):
            return str(valor)
    return default


def mostrar_conversion_orden_servicio(parent, app):
    usuario = obtener_usuario_actual()
    if not puede_convertir_levantamiento_a_orden(usuario):
        messagebox.showerror(
            "Acceso denegado",
            "Esta función está reservada al personal Administrativo (usu_tipo=5).",
        )
        return

    for widget in parent.winfo_children():
        widget.destroy()

    contenedor = ctk.CTkFrame(parent, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=14, pady=(4, 12))
    contenedor.grid_columnconfigure(0, weight=1)
    contenedor.grid_rowconfigure(1, weight=1)

    busqueda = ctk.CTkFrame(contenedor, fg_color=WHITE, corner_radius=16)
    busqueda.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    busqueda.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(busqueda, text="Convertir levantamiento en Orden de Trabajo", font=TITLE_MD,
                 text_color=TEXT_PRIMARY, anchor="w").grid(row=0, column=0, columnspan=4, sticky="ew", padx=12, pady=(10, 2))
    ctk.CTkLabel(
        busqueda,
        text="Busca un levantamiento, revisa sus datos y habilita la edición solo cuando sea necesario antes de convertirlo.",
        font=TEXT_MD, text_color=TEXT_SECONDARY, anchor="w",
    ).grid(row=1, column=0, columnspan=4, sticky="ew", padx=12, pady=(0, 8))

    var_busqueda = ctk.StringVar()
    entrada = ctk.CTkEntry(busqueda, textvariable=var_busqueda, height=40,
                           placeholder_text="Folio, ACO, cliente, técnico o tipo de levantamiento")
    entrada.grid(row=2, column=0, sticky="ew", padx=(12, 5), pady=(0, 10))

    cuerpo = ctk.CTkFrame(contenedor, fg_color="transparent")
    cuerpo.grid(row=1, column=0, sticky="nsew")
    cuerpo.grid_columnconfigure(0, weight=5)
    cuerpo.grid_columnconfigure(1, weight=6)
    cuerpo.grid_rowconfigure(0, weight=1)

    panel_lista = ctk.CTkFrame(cuerpo, fg_color=WHITE, corner_radius=16)
    panel_lista.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
    panel_lista.grid_columnconfigure(0, weight=1)
    panel_lista.grid_rowconfigure(1, weight=1)
    lbl_resultados = ctk.CTkLabel(panel_lista, text="Levantamientos", font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w")
    lbl_resultados.grid(row=0, column=0, sticky="ew", padx=10, pady=(9, 4))
    tabla = NativeTreeTable(
        panel_lista,
        columns=(("folio", "Folio", 105), ("cliente", "Cliente", 190), ("tipo", "Tipo", 150),
                 ("estatus", "Estatus", 75), ("fecha", "Fecha", 105)),
        height=20,
    )
    tabla.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

    # Panel derecho: contenido desplazable + barra de acciones fija.
    # Los botones no deben desplazarse junto con el formulario.
    panel_form_shell = ctk.CTkFrame(cuerpo, fg_color=WHITE, corner_radius=16)
    panel_form_shell.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
    panel_form_shell.grid_columnconfigure(0, weight=1)
    panel_form_shell.grid_rowconfigure(0, weight=1)

    panel_form = ctk.CTkScrollableFrame(panel_form_shell, fg_color=WHITE, corner_radius=16)
    panel_form.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 2))
    panel_form.grid_columnconfigure(0, weight=1)
    panel_form.grid_columnconfigure(1, weight=1)

    seleccionado = {"registro": None, "editando": False}
    widgets_editables = []
    vars_campos = {
        "lev_folio": ctk.StringVar(), "lev_aco_numero": ctk.StringVar(), "lev_cliente": ctk.StringVar(),
        "lev_contacto": ctk.StringVar(), "lev_correo": ctk.StringVar(), "lev_telefono": ctk.StringVar(),
        "lev_direccion": ctk.StringVar(), "lev_ubicacion": ctk.StringVar(), "lev_fecha_realizacion": ctk.StringVar(),
        "lev_fecha_programada": ctk.StringVar(), "lev_supervisor": ctk.StringVar(), "lev_tecnico": ctk.StringVar(),
        "lev_tipo": ctk.StringVar(), "lev_modalidad_operativa": ctk.StringVar(), "lev_prioridad": ctk.StringVar(),
    }

    def campo(label, key, row, col, disabled=False):
        marco = ctk.CTkFrame(panel_form, fg_color="transparent")
        marco.grid(row=row, column=col, sticky="ew", padx=5, pady=3)
        ctk.CTkLabel(marco, text=label, font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
        ent = ctk.CTkEntry(marco, textvariable=vars_campos[key], height=36)
        ent.pack(fill="x")
        if disabled:
            ent.configure(state="disabled")
        else:
            widgets_editables.append(ent)
            if "fecha" in label.lower():
                asociar_selector_fecha(ent, marco, vars_campos[key])
        return ent

    ctk.CTkLabel(panel_form, text="Información editable", font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w").grid(
        row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=(4, 7))
    campo("Folio del levantamiento", "lev_folio", 1, 0, True)
    campo("ACO", "lev_aco_numero", 1, 1)
    campo("Cliente", "lev_cliente", 2, 0)
    campo("Contacto", "lev_contacto", 2, 1)
    campo("Correo", "lev_correo", 3, 0)
    campo("Teléfono", "lev_telefono", 3, 1)
    campo("Dirección", "lev_direccion", 4, 0)
    campo("Ubicación", "lev_ubicacion", 4, 1)
    campo("Fecha de realización", "lev_fecha_realizacion", 5, 0)
    campo("Fecha programada", "lev_fecha_programada", 5, 1)
    campo("Supervisor", "lev_supervisor", 6, 0)
    campo("Técnico", "lev_tecnico", 6, 1)
    campo("Tipo de levantamiento", "lev_tipo", 7, 0)
    campo("Modalidad operativa", "lev_modalidad_operativa", 7, 1)
    campo("Prioridad", "lev_prioridad", 8, 0)

    def textbox(label, row, height=85):
        marco = ctk.CTkFrame(panel_form, fg_color="transparent")
        marco.grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=4)
        ctk.CTkLabel(marco, text=label, font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
        box = ctk.CTkTextbox(marco, height=height)
        box.pack(fill="x")
        widgets_editables.append(box)
        return box

    txt_descripcion = textbox("Descripción del levantamiento", 9, 105)
    txt_requerimientos = textbox("Requerimientos", 10, 90)
    txt_observaciones = textbox("Observaciones", 11, 75)
    txt_detalle = textbox("Detalle técnico JSON", 12, 150)

    lbl_estado = ctk.CTkLabel(panel_form, text="Selecciona un levantamiento para continuar.", font=TEXT_SM,
                              text_color=TEXT_SECONDARY, anchor="w", justify="left")
    lbl_estado.grid(row=13, column=0, columnspan=2, sticky="ew", padx=6, pady=(6, 2))

    def _set_modo_edicion(habilitado):
        seleccionado["editando"] = bool(habilitado)
        estado = "normal" if habilitado else "disabled"
        for widget in widgets_editables:
            try:
                widget.configure(state=estado)
            except Exception:
                pass
        # El folio siempre es de solo lectura.
        btn_editar.configure(state="disabled" if habilitado else ("normal" if seleccionado.get("registro") else "disabled"))
        btn_guardar.configure(state="normal" if habilitado else "disabled")
        if seleccionado.get("registro"):
            lbl_estado.configure(
                text=("Modo edición habilitado. Guarda los cambios antes de continuar." if habilitado
                      else "Modo consulta. Usa Editar si necesitas modificar información."),
                text_color=TEXT_SECONDARY,
            )

    def poner_texto(box, valor):
        # CTkTextbox acepta ``state`` en configure(), pero algunas versiones de
        # CustomTkinter no lo exponen mediante cget(). Consultarlo provocaba:
        # ValueError: 'state' is not a supported argument.
        # Durante la carga siempre habilitamos temporalmente el textbox;
        # _set_modo_edicion(False) se encarga de bloquearlo al terminar.
        try:
            box.configure(state="normal")
        except Exception:
            pass
        box.delete("1.0", "end")
        box.insert("1.0", valor or "")

    def cargar_seleccion():
        registro = tabla.selected_payload()
        if not registro:
            messagebox.showinfo("Selecciona un levantamiento", "Selecciona una fila de la tabla.")
            return
        seleccionado["registro"] = dict(registro)
        # Habilita temporalmente para cargar los valores y vuelve a bloquear al final.
        for widget in widgets_editables:
            try:
                widget.configure(state="normal")
            except Exception:
                pass
        for key, var in vars_campos.items():
            var.set(_valor(registro, key))
        poner_texto(txt_descripcion, _valor(registro, "lev_descripcion"))
        poner_texto(txt_requerimientos, _valor(registro, "lev_requerimientos"))
        poner_texto(txt_observaciones, _valor(registro, "lev_observaciones"))
        detalle = registro.get("lev_detalle_tecnico_json")
        if isinstance(detalle, (dict, list)):
            detalle = json.dumps(detalle, ensure_ascii=False, indent=2)
        poner_texto(txt_detalle, str(detalle or ""))
        existente = buscar_orden_trabajo_por_levantamiento(
            registro.get("lev_folio"), registro.get("id_levantamiento")
        )
        btn_preview.configure(state="normal")
        _set_modo_edicion(False)
        if existente:
            lbl_estado.configure(text=f"Este levantamiento ya fue convertido en {existente.get('ot_folio', 'una OT')}.", text_color="#B45309")
            btn_convertir.configure(state="disabled")
            btn_editar.configure(state="disabled")
        else:
            lbl_estado.configure(text="Modo consulta. Revisa los datos; usa Editar solo si necesitas realizar cambios.", text_color=TEXT_SECONDARY)
            btn_convertir.configure(state="normal")

    def filas(registros):
        registros = registros or []
        lbl_resultados.configure(text=f"Levantamientos ({len(registros)})")
        tabla.set_rows(registros, value_factory=lambda r: (
            _valor(r, "lev_folio"), _valor(r, "lev_cliente"),
            " / ".join(filter(None, [_valor(r, "lev_tipo"), _valor(r, "lev_modalidad_operativa")])),
            _valor(r, "lev_estatus"), _valor(r, "lev_fecha_programada", "lev_fecha_realizacion", "fecha_registro"),
        ))

    def ejecutar_busqueda():
        termino = var_busqueda.get().strip()
        tarea = (lambda: buscar_levantamientos(termino)) if termino else (lambda: obtener_levantamientos())
        lbl_resultados.configure(text="Consultando...")
        run_async(parent.winfo_toplevel(), tarea, lambda r: filas((r or [])[:100]),
                  lambda e: messagebox.showerror("Error", f"No fue posible consultar levantamientos.\n\n{e}"))

    def _capturar_cambios():
        obligatorios = ("lev_cliente", "lev_contacto", "lev_direccion", "lev_supervisor", "lev_tecnico", "lev_tipo")
        faltantes = [k for k in obligatorios if not vars_campos[k].get().strip()]
        if not txt_descripcion.get("1.0", "end").strip():
            faltantes.append("lev_descripcion")
        if faltantes:
            raise ValueError("Completa cliente, contacto, dirección, supervisor, técnico, tipo y descripción.")
        detalle_texto = txt_detalle.get("1.0", "end").strip()
        if detalle_texto:
            try:
                detalle = json.loads(detalle_texto)
            except json.JSONDecodeError as exc:
                raise ValueError(f"El detalle técnico contiene JSON inválido: {exc}") from exc
        else:
            detalle = {}
        cambios = {k: v.get().strip() for k, v in vars_campos.items() if k != "lev_folio"}
        try:
            cambios["lev_prioridad"] = int(cambios.get("lev_prioridad") or 2)
        except ValueError as exc:
            raise ValueError("La prioridad debe ser un número entero.") from exc
        cambios.update({
            "lev_descripcion": txt_descripcion.get("1.0", "end").strip(),
            "lev_requerimientos": txt_requerimientos.get("1.0", "end").strip(),
            "lev_observaciones": txt_observaciones.get("1.0", "end").strip(),
            "lev_detalle_tecnico_json": detalle,
        })
        return cambios

    def guardar_cambios():
        original = seleccionado.get("registro")
        if not original:
            messagebox.showwarning("Selecciona un levantamiento", "Primero carga un levantamiento de la tabla.")
            return
        if not seleccionado.get("editando"):
            return
        try:
            cambios = _capturar_cambios()
        except ValueError as exc:
            messagebox.showwarning("Información inválida", str(exc))
            return
        id_levantamiento = original.get("id_levantamiento")
        if not id_levantamiento:
            messagebox.showerror("No se pudo guardar", "El levantamiento seleccionado no contiene id_levantamiento.")
            return
        btn_guardar.configure(state="disabled")
        lbl_estado.configure(text="Guardando cambios del levantamiento...", text_color=TEXT_SECONDARY)

        def ok(resultado):
            if not resultado:
                btn_guardar.configure(state="normal")
                lbl_estado.configure(text="Supabase no confirmó la actualización.", text_color="#B91C1C")
                messagebox.showerror("No se pudo guardar", "Supabase no confirmó la actualización del levantamiento.")
                return
            original.update(cambios)
            seleccionado["registro"] = original
            _set_modo_edicion(False)
            lbl_estado.configure(text="Cambios guardados correctamente. Ya puedes previsualizar o convertir.", text_color="#15803D")
            messagebox.showinfo("Cambios guardados", "La información del levantamiento se actualizó correctamente.")

        run_async(
            parent.winfo_toplevel(),
            lambda: actualizar_levantamiento(id_levantamiento, cambios),
            ok,
            lambda e: (btn_guardar.configure(state="normal"), lbl_estado.configure(text="No se pudieron guardar los cambios.", text_color="#B91C1C"), messagebox.showerror("Error al guardar", str(e))),
        )

    def validar_y_convertir():
        original = seleccionado.get("registro")
        if not original:
            messagebox.showwarning("Selecciona un levantamiento", "Primero carga un levantamiento de la tabla.")
            return
        if seleccionado.get("editando"):
            messagebox.showwarning("Edición pendiente", "Guarda o finaliza la edición antes de convertir el levantamiento.")
            return
        try:
            cambios = _capturar_cambios()
        except ValueError as exc:
            messagebox.showwarning("Información inválida", str(exc))
            return
        if not messagebox.askyesno(
            "Confirmar conversión",
            f"Se creará una Orden de Trabajo desde {original.get('lev_folio')}.\n\n"
            "El levantamiento quedará marcado como En proceso y ya no podrá convertirse de nuevo.\n\n¿Continuar?",
        ):
            return
        btn_convertir.configure(state="disabled")
        lbl_estado.configure(text="Creando orden de trabajo...", text_color=TEXT_SECONDARY)

        def ok(resultado):
            folio_ot = resultado[0].get("ot_folio") if isinstance(resultado, list) and resultado else "generada"
            lbl_estado.configure(text=f"Conversión finalizada: {folio_ot}", text_color="#15803D")
            messagebox.showinfo("Orden de Trabajo creada", f"El levantamiento {original.get('lev_folio')} se convirtió correctamente en {folio_ot}.")
            ejecutar_busqueda()

        run_async(
            parent.winfo_toplevel(),
            lambda: convertir_levantamiento_a_trabajo(original, cambios, usuario),
            ok,
            lambda e: (btn_convertir.configure(state="normal"), lbl_estado.configure(text="No se completó la conversión.", text_color="#B91C1C"), messagebox.showerror("Error al convertir", str(e))),
        )

    def _registro_levantamiento_para_pdf():
        """Reconstruye el levantamiento actual con el mismo contrato del operador.

        La vista administrativa trabaja con el registro persistido, donde ``lev_tipo``
        es un código general. La plantilla maestra del levantamiento necesita además
        la especialidad real (p. ej. Redes Voz y Datos), guardada dentro del detalle
        técnico. Normalizarla aquí garantiza que Operador y Administrativo rendericen
        exactamente el mismo documento.
        """
        original = dict(seleccionado.get("registro") or {})
        detalle_texto = txt_detalle.get("1.0", "end").strip()
        try:
            detalle = json.loads(detalle_texto) if detalle_texto else {}
        except json.JSONDecodeError as exc:
            raise ValueError(f"El detalle técnico contiene JSON inválido: {exc}") from exc
        if not isinstance(detalle, dict):
            detalle = {}

        especialidad = str(
            detalle.get("tipo_levantamiento")
            or original.get("lev_tipo_levantamiento")
            or ""
        ).strip()
        modalidad = str(
            vars_campos["lev_modalidad_operativa"].get().strip()
            or detalle.get("modalidad_operativa")
            or original.get("lev_modalidad_operativa")
            or ""
        ).strip()

        original.update({
            "lev_folio": vars_campos["lev_folio"].get().strip(),
            "lev_aco_numero": vars_campos["lev_aco_numero"].get().strip(),
            "lev_cliente": vars_campos["lev_cliente"].get().strip(),
            "lev_contacto": vars_campos["lev_contacto"].get().strip(),
            "lev_correo": vars_campos["lev_correo"].get().strip(),
            "lev_telefono": vars_campos["lev_telefono"].get().strip(),
            "lev_direccion": vars_campos["lev_direccion"].get().strip(),
            "lev_ubicacion": vars_campos["lev_ubicacion"].get().strip(),
            "lev_fecha_realizacion": vars_campos["lev_fecha_realizacion"].get().strip(),
            "lev_fecha_programada": vars_campos["lev_fecha_programada"].get().strip(),
            "lev_supervisor": vars_campos["lev_supervisor"].get().strip(),
            "lev_tecnico": vars_campos["lev_tecnico"].get().strip(),
            "lev_tipo": vars_campos["lev_tipo"].get().strip(),
            "lev_tipo_levantamiento": especialidad,
            "lev_modalidad_operativa": modalidad,
            "lev_descripcion": txt_descripcion.get("1.0", "end").strip(),
            "lev_requerimientos": txt_requerimientos.get("1.0", "end").strip(),
            "lev_observaciones": txt_observaciones.get("1.0", "end").strip(),
            "lev_detalle_tecnico_json": json.dumps(detalle, ensure_ascii=False),
        })
        return original

    def previsualizar_levantamiento():
        if not seleccionado.get("registro"):
            messagebox.showinfo("Selecciona un levantamiento", "Carga primero un levantamiento.")
            return
        try:
            registro_pdf = _registro_levantamiento_para_pdf()
            generar_pdf_registro(
                registro_pdf,
                {"titulo_pdf": "Levantamientos", "campo_folio": "lev_folio"},
                abrir=True,
            )
        except Exception as exc:
            logger.exception("No fue posible generar el PDF homologado del levantamiento.")
            messagebox.showerror("Preview PDF", f"No fue posible generar el PDF del levantamiento.\n\n{exc}")

    ctk.CTkButton(busqueda, text="🔎 Buscar", width=130, height=40, fg_color=SECONDARY,
                  hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=ejecutar_busqueda).grid(row=2, column=1, padx=4, pady=(0, 10))
    ctk.CTkButton(busqueda, text="↻ Recientes", width=135, height=40, fg_color="#334155",
                  hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=lambda: (var_busqueda.set(""), ejecutar_busqueda())).grid(row=2, column=2, padx=(0, 12), pady=(0, 10))
    entrada.bind("<Return>", lambda _e: ejecutar_busqueda())

    # Barra fija: queda visible aunque el usuario haga scroll en el formulario.
    acciones = ctk.CTkFrame(panel_form_shell, fg_color=WHITE, corner_radius=0)
    acciones.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 10))
    acciones.grid_columnconfigure(0, weight=1)

    fila_consulta = ctk.CTkFrame(acciones, fg_color="transparent")
    fila_consulta.grid(row=0, column=0, sticky="e", pady=(0, 5))
    ctk.CTkButton(fila_consulta, text="📥 Cargar seleccionado", width=180, command=cargar_seleccion).pack(side="left", padx=4)
    btn_preview = ctk.CTkButton(fila_consulta, text="👁 PDF Levantamiento", width=180, command=previsualizar_levantamiento, state="disabled")
    btn_preview.pack(side="left", padx=4)

    fila_edicion = ctk.CTkFrame(acciones, fg_color="transparent")
    fila_edicion.grid(row=1, column=0, sticky="e")
    btn_editar = ctk.CTkButton(fila_edicion, text="✎ Editar", width=125, command=lambda: _set_modo_edicion(True), state="disabled")
    btn_editar.pack(side="left", padx=4)
    btn_guardar = ctk.CTkButton(fila_edicion, text="💾 Guardar", width=125, command=guardar_cambios, state="disabled")
    btn_guardar.pack(side="left", padx=4)
    btn_convertir = ctk.CTkButton(fila_edicion, text="✓ Convertir a OT", width=170, fg_color=SECONDARY,
                                  hover_color=BUTTON_HOVER, command=validar_y_convertir, state="disabled")
    btn_convertir.pack(side="left", padx=4)

    _set_modo_edicion(False)
    ejecutar_busqueda()
