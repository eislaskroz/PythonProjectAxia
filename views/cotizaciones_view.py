"""Módulo comercial de cotizaciones formales para Ventas."""
from __future__ import annotations
from ui.form_fields import AxiaEntry, AxiaTextbox

import customtkinter as ctk
from tkinter import messagebox, filedialog
from pathlib import Path
from PIL import Image

from app_context import obtener_usuario_actual
from core.background_tasks import run_async
from core.logger import configurar_logger
from security.permissions import puede_cotizar_levantamientos
from services.cotizaciones_service import (
    obtener_levantamientos_para_cotizar,
    obtener_cotizaciones_pendientes_compras,
    obtener_cotizaciones_en_compra,
    obtener_cotizaciones_seguimiento_dg,
    obtener_levantamiento_de_cotizacion,
    cargar_cotizacion,
    datos_generales_cotizacion,
    construir_partidas_comerciales,
    guardar_cotizacion_comercial,
    finalizar_cotizacion_para_compras,
    ESTATUS_BORRADOR,
    ESTATUS_EN_COMPRA,
    ESTATUS_PENDIENTE_DG,
)
from services.axia_pdf_engine import AxiaPdfEngine
from views.cotizacion_pdf_opciones import solicitar_campos_pdf
from services.cotizacion_partidas import es_lote_servicio
from services.usuarios_service import obtener_nombres_usuarios_por_tipos
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY, BUTTON_HOVER
from ui.iconos import cargar_icono
from ui.fonts import TITLE_MD, TEXT_MD, TEXT_SM, BUTTON_FONT
from ui.native_table import NativeTreeTable
from ui.numeric_masks import aplicar_mascara_numerica, MONEY, NUMBER, INTEGER

logger = configurar_logger(__name__)


def _texto(registro, clave):
    return str((registro or {}).get(clave) or "").strip()


def _num(value):
    try:
        return float(str(value or "0").replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def mostrar_cotizaciones(parent, app=None):
    usuario = obtener_usuario_actual()
    if not puede_cotizar_levantamientos(usuario):
        messagebox.showerror("Acceso denegado", "Este módulo está disponible para Ventas (id=6) y Administrador.")
        return

    for widget in parent.winfo_children():
        widget.destroy()

    estado = {"registro": None, "cotizacion": {}, "vars": {}, "partidas": [], "partida_vars": [], "editables": [], "modo_edicion": False}
    registros_cache = []
    cotizaciones_cache = []
    autorizadas_cache = []

    root = ctk.CTkFrame(parent, fg_color="transparent")
    root.pack(fill="both", expand=True, padx=14, pady=(4, 12))
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(2, weight=1)

    # La barra de control permanece visible; las bandejas se pueden plegar sin
    # reconstruir el formulario ni perder valores de la cotización activa.
    barra_bandejas = ctk.CTkFrame(root, fg_color="transparent")
    barra_bandejas.grid(row=0, column=0, sticky="ew", pady=(0, 4))
    barra_bandejas.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        barra_bandejas, text="Selección de cotizaciones y levantamientos",
        font=TEXT_SM, text_color=TEXT_SECONDARY, anchor="w",
    ).grid(row=0, column=0, sticky="w")

    superior = ctk.CTkFrame(root, fg_color="transparent")
    superior.grid(row=1, column=0, sticky="ew", pady=(0, 8))
    bandejas_visibles = {"valor": True}

    def mostrar_bandejas(visible=None):
        if visible is None:
            visible = not bandejas_visibles["valor"]
        bandejas_visibles["valor"] = bool(visible)
        if visible:
            superior.grid(row=1, column=0, sticky="ew", pady=(0, 8))
            btn_bandejas.configure(text="▲ Ocultar paneles")
        else:
            superior.grid_remove()
            btn_bandejas.configure(text="▼ Mostrar paneles")

    btn_bandejas = ctk.CTkButton(
        barra_bandejas, text="▲ Ocultar paneles", width=180, height=34,
        font=BUTTON_FONT, fg_color="#123C57", hover_color="#1D5678",
        command=mostrar_bandejas,
    )
    btn_bandejas.grid(row=0, column=1, sticky="e", padx=(8, 0))
    # Tres bandejas: flujo LEV -> COT editable (BORRADOR) -> COT autorizada (EN COMPRA).
    for indice in range(3):
        superior.grid_columnconfigure(indice, weight=1, uniform="top")

    bandeja = ctk.CTkFrame(superior, fg_color=WHITE, corner_radius=16)
    bandeja.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
    bandeja.grid_columnconfigure(0, weight=1)
    lbl_lista = ctk.CTkLabel(bandeja, text="Levantamientos Preautorizados", font=TITLE_MD,
                            text_color=TEXT_PRIMARY, anchor="w")
    lbl_lista.grid(row=0, column=0, sticky="ew", padx=10, pady=(6, 3))
    tabla = NativeTreeTable(
        bandeja, columns=(("folio", "Folio", 105), ("cliente", "Cliente", 150),
                          ("tipo", "Tipo", 140), ("fecha", "Fecha", 95)), height=3,
     table_id="cotizaciones_levantamientos",)
    tabla.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 5))

    bandeja_cot = ctk.CTkFrame(superior, fg_color=WHITE, corner_radius=16)
    bandeja_cot.grid(row=0, column=1, sticky="nsew", padx=5)
    bandeja_cot.grid_columnconfigure(0, weight=1)
    lbl_cotizaciones = ctk.CTkLabel(bandeja_cot, text="Cotizaciones Realizadas",
                                    font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w")
    lbl_cotizaciones.grid(row=0, column=0, sticky="ew", padx=10, pady=(6, 3))
    columnas_cot = (("folio", "Cotización", 115), ("levantamiento", "Levantamiento", 120),
                    ("cliente", "Cliente", 150), ("fecha", "Fecha", 100))
    tabla_cot = NativeTreeTable(bandeja_cot, columns=columnas_cot, height=3, table_id="cotizaciones_borradores")
    tabla_cot.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 5))

    bandeja_aut = ctk.CTkFrame(superior, fg_color=WHITE, corner_radius=16)
    bandeja_aut.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
    bandeja_aut.grid_columnconfigure(0, weight=1)
    lbl_autorizadas = ctk.CTkLabel(bandeja_aut, text="En DG / Compras",
                                   font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w")
    lbl_autorizadas.grid(row=0, column=0, sticky="ew", padx=10, pady=(6, 3))
    tabla_aut = NativeTreeTable(bandeja_aut, columns=columnas_cot, height=3, table_id="cotizaciones_autorizadas")
    tabla_aut.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 5))

    detalle_card = ctk.CTkFrame(root, fg_color=WHITE, corner_radius=16)
    detalle_card.grid(row=2, column=0, sticky="nsew"); detalle_card.grid_columnconfigure(0, weight=1); detalle_card.grid_rowconfigure(1, weight=1)
    info = ctk.CTkFrame(detalle_card, fg_color="transparent")
    info.grid(row=0, column=0, sticky="ew", padx=14, pady=(8,3)); info.grid_columnconfigure(0, weight=1)
    lbl_titulo = ctk.CTkLabel(info, text="Selecciona un levantamiento", font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w")
    lbl_titulo.grid(row=0, column=0, sticky="ew")
    lbl_detalle = ctk.CTkLabel(info, text="La cotización se guardará en una tabla propia con folio COT-XXXXX.", font=TEXT_SM, text_color=TEXT_SECONDARY, anchor="w")
    lbl_detalle.grid(row=1, column=0, sticky="ew", pady=(2,0))

    scroll = ctk.CTkScrollableFrame(detalle_card, fg_color="#F8FAFC", corner_radius=12)
    scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=5)
    for col in range(4): scroll.grid_columnconfigure(col, weight=1)

    icono_detalle = cargar_icono("detalle.png", (18, 18), blanco=True)
    icono_lapiz = cargar_icono("lapiz.png", (18, 18), blanco=True)
    icono_guardar = cargar_icono("guardar.png", (18, 18), blanco=True)
    icono_finalizar = cargar_icono("finalizar.png", (18, 18), blanco=True)

    acciones = ctk.CTkFrame(detalle_card, fg_color="transparent")
    acciones.grid(row=2, column=0, sticky="ew", padx=14, pady=(4,10)); acciones.grid_columnconfigure(0, weight=1)
    lbl_total = ctk.CTkLabel(acciones, text="Total: $0.00 MXN", font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="e")
    lbl_total.grid(row=0, column=0, sticky="e", padx=(0,10))

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
    icono_lapiz = cargar_icono_boton("lapiz.png")
    icono_votar = cargar_icono_boton("votar.png")
    icono_finalizar = cargar_icono_boton("finalizar.png")
    icono_abrir = cargar_icono_boton("abrir.png")

    btn_pdf = ctk.CTkButton(acciones, text="PDF Cotización (Preview)", image=icono_detalle, compound="left", width=185, height=42, corner_radius=10,
                            fg_color="#2563EB", hover_color="#1D4ED8", text_color=WHITE,
                            border_width=0, font=BUTTON_FONT, state="disabled")
    btn_pdf.grid(row=0, column=1, padx=(0,8))
    btn_modificar = ctk.CTkButton(acciones, text="Modificar cotización", image=icono_lapiz, compound="left", width=180, height=42, corner_radius=10,
                                  fg_color="#2563EB", hover_color="#1D4ED8", text_color=WHITE,
                                  border_width=0, font=BUTTON_FONT, state="disabled")
    btn_modificar.grid(row=0, column=2, padx=(0,8))
    btn_guardar = ctk.CTkButton(acciones, text="Guardar cotización", image=icono_votar, compound="left", width=190, height=42, corner_radius=10,
                                fg_color=SECONDARY, hover_color=BUTTON_HOVER, text_color=WHITE,
                                border_width=0, font=BUTTON_FONT, state="disabled")
    btn_guardar.grid(row=0, column=3, padx=(0,8))
    btn_finalizar = ctk.CTkButton(acciones, text="Finalizar cotización", image=icono_finalizar, compound="left", width=185, height=42, corner_radius=10,
                                  fg_color="#2563EB", hover_color="#1D4ED8", text_color=WHITE,
                                  border_width=0, font=BUTTON_FONT, state="disabled")
    btn_finalizar.grid(row=0, column=4)
    lbl_validacion = ctk.CTkLabel(acciones, text="Carga un levantamiento para iniciar la cotización.",
                                  font=TEXT_SM, text_color=TEXT_SECONDARY, anchor="e")
    lbl_validacion.grid(row=1, column=0, columnspan=5, sticky="e", pady=(4,0))

    def limpiar():
        for w in scroll.winfo_children(): w.destroy()
        estado["vars"] = {}; estado["partidas"] = []; estado["partida_vars"] = []; estado["cotizacion"] = {}; estado["editables"] = []
        estado["modo_edicion"] = False
        estado["supervisores_validos"] = frozenset()
        for boton in (btn_guardar, btn_pdf, btn_modificar, btn_finalizar):
            boton.configure(state="disabled")
        lbl_total.configure(text="Total: $0.00 MXN")
        lbl_validacion.configure(text="Carga un levantamiento para iniciar la cotización.", text_color=TEXT_SECONDARY)

    def recalcular(*_):
        subtotal = sum(_num(pv["importe"].get()) for pv in estado["partida_vars"])
        desc = _num(estado["vars"].get("cot_descuento_pct", ctk.StringVar(value="0")).get()) if estado["vars"] else 0
        iva_pct = _num(estado["vars"].get("cot_iva_pct", ctk.StringVar(value="16")).get()) if estado["vars"] else 16
        subtotal_desc = subtotal - (subtotal * desc / 100.0)
        total = subtotal_desc + (subtotal_desc * iva_pct / 100.0)
        lbl_total.configure(text=f"Total: ${total:,.2f} MXN")

    def add_field(parent_frame, row, col, label, key, value="", readonly=False, colspan=1):
        ctk.CTkLabel(parent_frame, text=label, font=("Montserrat", 10), text_color=TEXT_PRIMARY, anchor="w").grid(
            row=row*2, column=col, columnspan=colspan, sticky="ew", padx=4, pady=(1,0))
        var = ctk.StringVar(value=str(value or "")); estado["vars"][key] = var
        ent = AxiaEntry(parent_frame, textvariable=var, height=25, font=("Montserrat", 11))
        ent.grid(row=row*2+1, column=col, columnspan=colspan, sticky="ew", padx=4, pady=(0,2))
        if key in {"cot_dias", "cot_personas", "cot_vigencia"}:
            aplicar_mascara_numerica(ent, var, INTEGER)
        elif key in {"cot_descuento_pct", "cot_iva_pct"}:
            aplicar_mascara_numerica(ent, var, NUMBER)
        if readonly:
            ent.configure(state="disabled")
        else:
            estado["editables"].append(ent)
        var.trace_add("write", lambda *_: actualizar_estado_botones())
        return var

    def add_select(parent_frame, row, col, label, key, values, value="", colspan=1, placeholder=None):
        ctk.CTkLabel(parent_frame, text=label, font=("Montserrat", 10), text_color=TEXT_PRIMARY, anchor="w").grid(
            row=row*2, column=col, columnspan=colspan, sticky="ew", padx=4, pady=(1,0))
        opciones = [str(x).strip() for x in (values or []) if str(x).strip()]
        hay_personal = bool(opciones)
        if placeholder:
            # Supervisor: no asignar automáticamente a la primera persona del
            # catálogo si el levantamiento carece de supervisor válido.
            opciones.insert(0, placeholder if hay_personal else "SIN SUPERVISORES REGISTRADOS")
        actual = str(value or "").strip()
        coincidencia = next((op for op in opciones if op.casefold() == actual.casefold()), None)
        actual = coincidencia if coincidencia is not None else (opciones[0] if opciones else "")
        var = ctk.StringVar(value=actual); estado["vars"][key] = var
        menu = ctk.CTkOptionMenu(parent_frame, variable=var, values=opciones or ["SIN PERSONAL REGISTRADO"], height=25, font=("Montserrat", 11))
        menu.grid(row=row*2+1, column=col, columnspan=colspan, sticky="ew", padx=4, pady=(0,2))
        if not hay_personal:
            menu.configure(state="disabled")
        else:
            estado["editables"].append(menu)
        var.trace_add("write", lambda *_: actualizar_estado_botones())
        return var

    def validar_captura_completa():
        """Valida que Preview/Guardar nunca operen sobre una cotización incompleta."""
        if not estado.get("registro"):
            return False, "Selecciona y carga un levantamiento."

        etiquetas = {
            "cot_fecha": "Fecha de Cotización",
            "lev_folio": "No. Levantamiento",
            "cot_cliente": "Cliente",
            "cot_contacto": "Contacto",
            "cot_sucursal": "Sucursal",
            "cot_asunto": "Asunto",
            "cot_esi": "ESI / Ejecutiva de Ventas",
            "cot_esi_correo": "Correo ESI",
            "cot_esi_telefono": "Teléfono ESI",
            "cot_jefe_operaciones": "Jefe de Operaciones",
            "cot_supervisor": "Supervisor",
            "cot_dias": "Días",
            "cot_personas": "Personas",
            "cot_plan_pagos": "Plan de Pagos",
            "cot_vigencia": "Vigencia de Cotización",
        }
        for key, etiqueta in etiquetas.items():
            var = estado.get("vars", {}).get(key)
            valor = str(var.get() if var is not None else "").strip()
            if not valor or valor in {"*", "-"}:
                return False, f"Falta completar correctamente: {etiqueta}."

        # Nunca permitir que el valor de ayuda se guarde como supervisor.
        # Las cotizaciones ya finalizadas conservan su responsable histórico,
        # aunque haya sido dado de baja o renombrado en el catálogo.
        supervisor = str(estado["vars"]["cot_supervisor"].get()).strip()
        supervisores_validos = estado.get("supervisores_validos", frozenset())
        cot_previa = estado.get("cotizacion") or {}
        finalizada_previa = str(cot_previa.get("cot_estatus") or "").strip().upper() in {ESTATUS_PENDIENTE_DG, ESTATUS_EN_COMPRA}
        supervisor_historico = str(cot_previa.get("cot_supervisor") or "").strip()
        if supervisor not in supervisores_validos and not (finalizada_previa and supervisor == supervisor_historico):
            return False, "Selecciona un Supervisor válido (usu_tipo = 3)."

        correo = str(estado["vars"]["cot_esi_correo"].get()).strip()
        if "@" not in correo or "." not in correo.rsplit("@", 1)[-1]:
            return False, "El Correo ESI no tiene un formato válido."
        if _num(estado["vars"]["cot_dias"].get()) <= 0:
            return False, "Días debe ser mayor que cero."
        if _num(estado["vars"]["cot_personas"].get()) <= 0:
            return False, "Personas debe ser mayor que cero."

        descuento = _num(estado["vars"].get("cot_descuento_pct").get())
        iva = _num(estado["vars"].get("cot_iva_pct").get())
        if descuento < 0 or descuento > 100:
            return False, "Descuento % debe estar entre 0 y 100."
        if iva < 0 or iva > 100:
            return False, "IVA % debe estar entre 0 y 100."

        partidas = estado.get("partida_vars") or []
        if not partidas:
            return False, "La cotización no contiene partidas comerciales."
        requeridos_texto = {
            "unidad_tipo": "Unidad / Tipo", "concepto": "Concepto", "proveedor": "Proveedor",
            "modelo": "Modelo", "sku": "SKU", "marca": "Marca",
        }
        for idx, pv in enumerate(partidas, 1):
            if es_lote_servicio({k: v.get() for k, v in pv.items()}, idx - 1, len(partidas)):
                if not str(pv["unidad_tipo"].get()).strip() or not str(pv["concepto"].get()).strip():
                    return False, f"Lote {idx}: completa Unidad / Tipo y Concepto del servicio."
                if _num(pv["importe"].get()) <= 0:
                    return False, f"Lote {idx}: captura el Importe del servicio."
                continue
            for key, etiqueta in requeridos_texto.items():
                valor = str(pv.get(key).get() if pv.get(key) is not None else "").strip()
                if not valor:
                    return False, f"Lote {idx}: falta {etiqueta}. Usa N/A cuando no aplique."
            if _num(pv["cantidad"].get()) <= 0:
                return False, f"Lote {idx}: Cantidad debe ser mayor que cero."
            if _num(pv["precio_lista"].get()) <= 0:
                return False, f"Lote {idx}: P. Lista debe ser mayor que cero."
            utilidad_txt = str(pv["utilidad_pct"].get()).strip()
            if utilidad_txt == "":
                return False, f"Lote {idx}: captura Utilidad %."
            if _num(utilidad_txt) < 0:
                return False, f"Lote {idx}: Utilidad % no puede ser negativa."
            if _num(pv["precio_unitario"].get()) <= 0 or _num(pv["importe"].get()) <= 0:
                return False, f"Lote {idx}: los importes calculados no son válidos."
        return True, "Cotización completa."

    def actualizar_estado_botones(*_):
        valida, mensaje = validar_captura_completa()
        cot = estado.get("cotizacion") or {}
        finalizada = str(cot.get("cot_estatus") or ESTATUS_BORRADOR).strip().upper() != ESTATUS_BORRADOR if cot else False
        modo = bool(estado.get("modo_edicion"))
        btn_pdf.configure(state="normal" if valida else "disabled")
        btn_guardar.configure(state="normal" if (modo and valida and not finalizada) else "disabled")
        btn_modificar.configure(state="normal" if (cot and not finalizada and not modo) else "disabled")
        btn_finalizar.configure(state="normal" if (cot and valida and not finalizada and not modo) else "disabled")
        if finalizada:
            lbl_validacion.configure(text="Cotización enviada a DG o autorizada para Compras.", text_color="#15803D")
        elif not valida:
            lbl_validacion.configure(text=f"Pendiente: {mensaje}", text_color="#B45309")
        elif cot and not modo:
            lbl_validacion.configure(text="Cotización completa. Usa Modificar para editar o Finalizar para enviarla a Dirección General.", text_color="#15803D")
        else:
            lbl_validacion.configure(text="Cotización completa. Preview y Guardar están habilitados.", text_color="#15803D")

    def render(registro, forzar_edicion=False):
        limpiar(); estado["registro"] = registro
        cot = cargar_cotizacion(registro)
        base = datos_generales_cotizacion(registro, usuario)
        if cot:
            base.update({k:v for k,v in cot.items() if v is not None})
        # El título de la cotización representa el NOMBRE DEL SERVICIO del
        # levantamiento (lev_descripcion), no su categoría/tipo técnico.
        # Conservamos la referencia del levantamiento aun en cotizaciones
        # previamente guardadas con el título anterior.
        nombre_servicio = str(registro.get("lev_descripcion") or "").strip()
        if nombre_servicio:
            base["cot_asunto"] = nombre_servicio
        estado["cotizacion"] = dict(cot)
        estatus = str(cot.get("cot_estatus") or ESTATUS_BORRADOR).strip().upper() if cot else ESTATUS_BORRADOR
        finalizada = bool(cot) and estatus != ESTATUS_BORRADOR
        estado["modo_edicion"] = (not bool(cot) or bool(forzar_edicion)) and not finalizada

        # Fecha de Supabase -> DD/MM/AAAA.
        fecha = str(base.get("cot_fecha") or "")
        if len(fecha) >= 10 and "-" in fecha:
            try:
                from datetime import datetime
                base["cot_fecha"] = datetime.strptime(fecha[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception: pass

        ctk.CTkLabel(scroll, text="Datos generales de cotización", font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w").grid(
            row=0, column=0, columnspan=4, sticky="ew", padx=6, pady=(4,2))
        general = ctk.CTkFrame(scroll, fg_color=WHITE, corner_radius=10)
        general.grid(row=1, column=0, columnspan=4, sticky="ew", padx=4, pady=(0,8))
        # 7 columnas y 3 filas compactas: el encabezado ocupa considerablemente
        # menos altura sin perder los datos ni sus claves de almacenamiento.
        for c in range(7):
            general.grid_columnconfigure(c, weight=1, uniform="generales")

        add_field(general,0,0,"No. Cotización","cot_folio",base.get("cot_folio"),True)
        add_field(general,0,1,"Fecha de Cotización","cot_fecha",base.get("cot_fecha"),True)
        add_field(general,0,2,"No. Levantamiento","lev_folio",base.get("lev_folio"),True)
        add_field(general,0,3,"Cliente","cot_cliente",base.get("cot_cliente"),True)
        add_field(general,0,4,"Contacto","cot_contacto",base.get("cot_contacto"),True)
        add_field(general,0,5,"Sucursal","cot_sucursal",base.get("cot_sucursal"),True,2)
        add_field(general,1,0,"Asunto","cot_asunto",base.get("cot_asunto"),True,2)
        # La ESI se obtiene del usuario autenticado (tipo 6), sin permitir
        # reasignarla manualmente. Si la cotización ya existía, se conserva
        # su ESI original para evitar alterar la autoría al consultarla.
        add_field(general,1,2,"ESI / Ejecutiva de Ventas","cot_esi",base.get("cot_esi"),True)
        add_field(general,1,3,"Correo ESI","cot_esi_correo",base.get("cot_esi_correo"),True)
        add_field(general,1,4,"Teléfono ESI","cot_esi_telefono",base.get("cot_esi_telefono"),True)

        # Los puestos no se infieren por usu_puesto: se filtran por db_usuarios.usu_tipo.
        jefes_operaciones = obtener_nombres_usuarios_por_tipos([2])
        add_select(general,1,5,"Jefe de Operaciones","cot_jefe_operaciones",jefes_operaciones,base.get("cot_jefe_operaciones"),2)

        supervisores = obtener_nombres_usuarios_por_tipos([3])
        estado["supervisores_validos"] = frozenset(supervisores)
        supervisor_anterior = str(base.get("cot_supervisor") or "").strip()
        if finalizada and supervisor_anterior not in estado["supervisores_validos"]:
            # Histórico autorizado: solo consulta, sin forzar una nueva asignación.
            add_field(general,2,0,"Supervisor","cot_supervisor",supervisor_anterior,True)
        else:
            add_select(general,2,0,"Supervisor","cot_supervisor",supervisores,supervisor_anterior,
                       placeholder="SELECCIONA UN SUPERVISOR")

        add_field(general,2,1,"Días","cot_dias",base.get("cot_dias"),True)
        add_field(general,2,2,"Personas","cot_personas",base.get("cot_personas"),True)
        add_field(general,2,3,"Plan de Pagos","cot_plan_pagos",base.get("cot_plan_pagos") or "PPD")

        add_field(general,2,4,"Vigencia de Cotización","cot_vigencia",base.get("cot_vigencia"))
        vd=add_field(general,2,5,"Descuento %","cot_descuento_pct",base.get("cot_descuento_pct",0))
        vi=add_field(general,2,6,"IVA %","cot_iva_pct",base.get("cot_iva_pct",16))
        vd.trace_add("write", recalcular); vi.trace_add("write", recalcular)

        ctk.CTkLabel(scroll, text="Partidas comerciales", font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w").grid(
            row=2, column=0, columnspan=4, sticky="ew", padx=6, pady=(4,2))
        partidas = construir_partidas_comerciales(registro, cot)
        estado["partidas"] = partidas
        cont = ctk.CTkFrame(scroll, fg_color="transparent")
        cont.grid(row=3, column=0, columnspan=4, sticky="ew")
        cont.grid_columnconfigure(0, weight=1)

        for i, item in enumerate(partidas):
            servicio = es_lote_servicio(item, i, len(partidas))
            card = ctk.CTkFrame(cont, fg_color=WHITE, corner_radius=10)
            card.grid(row=i, column=0, sticky="ew", padx=4, pady=2)
            # 24 columnas: anchos proporcionales al contenido, no cajas uniformes gigantes.
            for c in range(24):
                card.grid_columnconfigure(c, weight=1, uniform="partida_compacta")

            # Todas las variables originales siguen vivas incluso con el panel plegado:
            # los cálculos, el guardado, el PDF y los permisos usan estas variables.
            vars_item = {
                key: ctk.StringVar(value=str(value) if value is not None else "")
                for key, value in item.items()
            }
            todas_las_claves = (
                "unidad_tipo", "cantidad", "proveedor", "modelo", "sku", "marca",
                "concepto", "precio_lista", "costo", "utilidad_pct", "precio_venta",
                "precio_unitario", "importe", "observaciones",
            )
            for key in todas_las_claves:
                vars_item.setdefault(key, ctk.StringVar(value=""))

            encabezado = ctk.CTkLabel(
                card,
                text=f"Lote {item.get('lote', i+1)} · {item.get('concepto', '')}",
                font=("Montserrat", 11, "bold"), text_color=TEXT_PRIMARY,
                anchor="w", justify="left", wraplength=1240,
            )
            encabezado.grid(row=0, column=0, columnspan=24, sticky="ew", padx=7, pady=(4, 1))
            vars_item["concepto"].trace_add(
                "write", lambda *_args, pv=vars_item, header=encabezado, lote=item.get("lote", i+1):
                header.configure(text=f"Lote {lote} · {pv['concepto'].get()}")
            )

            # Retícula compacta: el campo y su etiqueta viven en la misma celda.
            # Evita filas vacías producidas por etiquetas y entradas separadas.
            def campo_partida(contenedor, etiqueta, clave, fila, columna, ancho):
                celda = ctk.CTkFrame(contenedor, fg_color="transparent")
                celda.grid(row=fila, column=columna, columnspan=ancho,
                           sticky="ew", padx=3, pady=(0, 2))
                ctk.CTkLabel(
                    celda, text=etiqueta, font=("Montserrat", 9),
                    text_color=TEXT_SECONDARY, anchor="w", height=15,
                ).pack(fill="x")
                variable = vars_item[clave]
                ent = AxiaEntry(celda, textvariable=variable, height=25,
                                font=("Montserrat", 10))
                ent.pack(fill="x")
                if clave in {"precio_lista", "costo", "precio_venta", "precio_unitario", "importe"}:
                    aplicar_mascara_numerica(ent, variable, MONEY)
                elif clave in {"cantidad", "utilidad_pct"}:
                    aplicar_mascara_numerica(ent, variable, NUMBER)
                # Se mantienen las mismas reglas de solo lectura anteriores.
                if clave in {"unidad_tipo", "cantidad", "concepto", "costo", "precio_venta", "precio_unitario", "importe"} and not (servicio and clave == "importe"):
                    ent.configure(state="disabled")
                else:
                    estado["editables"].append(ent)
                return ent

            if servicio:
                principales = [
                    ("Unidad / Tipo", "unidad_tipo", 1, 0, 3),
                    ("Cantidad", "cantidad", 1, 3, 2),
                    ("Modelo", "modelo", 1, 5, 4),
                    ("Marca", "marca", 1, 9, 3),
                    ("P. Unitario", "precio_unitario", 1, 12, 3),
                    ("Importe", "importe", 1, 15, 3),
                    ("Concepto", "concepto", 2, 0, 20),
                ]
                secundarios = [
                    ("Proveedor", "proveedor", 0, 0, 5),
                    ("SKU", "sku", 0, 5, 4),
                    ("P. Lista", "precio_lista", 0, 9, 3),
                    ("Costo", "costo", 0, 12, 3),
                    ("Utilidad %", "utilidad_pct", 0, 15, 3),
                    ("P. Venta", "precio_venta", 0, 18, 3),
                    ("Observaciones", "observaciones", 1, 0, 24),
                ]
            else:
                principales = [
                    ("Unidad / Tipo", "unidad_tipo", 1, 0, 3),
                    ("Cantidad", "cantidad", 1, 3, 2),
                    ("Modelo", "modelo", 1, 5, 4),
                    ("Marca", "marca", 1, 9, 3),
                    ("Costo", "costo", 1, 12, 3),
                    ("P. Venta", "precio_venta", 1, 15, 3),
                    ("Importe", "importe", 1, 18, 3),
                    ("Concepto", "concepto", 2, 0, 20),
                ]
                secundarios = [
                    ("Proveedor", "proveedor", 0, 0, 5),
                    ("SKU", "sku", 0, 5, 4),
                    ("P. Lista", "precio_lista", 0, 9, 3),
                    ("Utilidad %", "utilidad_pct", 0, 12, 3),
                    ("P. Unitario", "precio_unitario", 0, 15, 3),
                    ("Observaciones", "observaciones", 0, 18, 6),
                ]

            fila_boton = 2
            columna_boton = 20
            ancho_boton = 4

            for etiqueta, clave, fila, columna, ancho in principales:
                campo_partida(card, etiqueta, clave, fila, columna, ancho)

            zona_detalles = ctk.CTkFrame(card, fg_color="#F4F7FB", corner_radius=8)
            zona_detalles.grid(row=3, column=0, columnspan=24, sticky="ew",
                              padx=4, pady=(1, 3))
            for col_detalle in range(24):
                zona_detalles.grid_columnconfigure(col_detalle, weight=1,
                                                     uniform="detalle_partida")
            for etiqueta, clave, fila, col, span in secundarios:
                campo_partida(zona_detalles, etiqueta, clave, fila, col, span)

            # El ocultamiento no elimina widgets ni variables, solo la retícula.
            zona_detalles.grid_remove()
            detalles_abiertos = {"valor": False}

            def alternar_detalles(panel=zona_detalles, estado_panel=detalles_abiertos,
                                 boton_ref=None):
                estado_panel["valor"] = not estado_panel["valor"]
                if estado_panel["valor"]:
                    panel.grid()
                    if boton_ref is not None:
                        boton_ref.configure(text="▲ Ocultar detalles")
                else:
                    panel.grid_remove()
                    if boton_ref is not None:
                        boton_ref.configure(text="▼ Más detalles")

            boton_detalles = ctk.CTkButton(
                card, text="▼ Más detalles", height=27, corner_radius=8,
                fg_color="#E7EFF8", hover_color="#DAE7F5", text_color="#1F4E79",
                font=("Montserrat", 10, "bold"),
            )
            boton_detalles.configure(command=lambda panel=zona_detalles,
                                    visual=detalles_abiertos, boton=boton_detalles:
                                    alternar_detalles(panel, visual, boton))
            boton_detalles.grid(row=fila_boton, column=columna_boton,
                                columnspan=ancho_boton, sticky="ew",
                                padx=4, pady=(15, 2))

            if servicio:
                # El importe lo introduce Ventas sin porcentajes ni costos.
                # Sincronizamos campos internos para que el Preview muestre
                # un precio unitario coherente incluso antes de guardar.
                lock_servicio = {"x": False}
                def calc_servicio(*_, pv=vars_item, lk=lock_servicio):
                    if lk["x"]:
                        return
                    importe = _num(pv["importe"].get())
                    cantidad = _num(pv["cantidad"].get()) or 1.0
                    unitario = round(importe / cantidad, 2)
                    lk["x"] = True
                    try:
                        pv["precio_lista"].set(f"{importe:.2f}")
                        pv["costo"].set("0.00")
                        pv["utilidad_pct"].set("0")
                        pv["precio_venta"].set(f"{unitario:.2f}")
                        pv["precio_unitario"].set(f"{unitario:.2f}")
                    finally:
                        lk["x"] = False
                    recalcular()
                vars_item["importe"].trace_add("write", calc_servicio)
                calc_servicio()

            if not servicio:
                # Costo = P.Lista * Utilidad%; P.Venta = Lista + Costo;
                # P.Unitario = P.Venta; Importe = P.Unitario * Cantidad.
                lock = {"x": False}
                def calc_comercial(*_, pv=vars_item, lk=lock):
                    if lk["x"]:
                        return
                    try:
                        lista = _num(pv["precio_lista"].get())
                        utilidad = _num(pv["utilidad_pct"].get())
                        cantidad = _num(pv["cantidad"].get())
                    except (TypeError, ValueError):
                        recalcular()
                        return
                    costo = round(lista * utilidad / 100.0, 2)
                    venta = round(lista + costo, 2)
                    importe = round(venta * cantidad, 2)
                    lk["x"] = True
                    try:
                        pv["costo"].set(f"{costo:.2f}")
                        pv["precio_venta"].set(f"{venta:.2f}")
                        pv["precio_unitario"].set(f"{venta:.2f}")
                        pv["importe"].set(f"{importe:.2f}")
                    finally:
                        lk["x"] = False
                    recalcular()
                vars_item["precio_lista"].trace_add("write", calc_comercial)
                vars_item["utilidad_pct"].trace_add("write", calc_comercial)
                vars_item["cantidad"].trace_add("write", calc_comercial)
                calc_comercial()

            vars_item["importe"].trace_add("write", recalcular)
            for _var in vars_item.values():
                _var.trace_add("write", lambda *_: actualizar_estado_botones())
            estado["partida_vars"].append(vars_item)

        # Estado visual y permisos de edición. Una cotización guardada se abre en
        # consulta; "Modificar" recarga desde Supabase y habilita sólo los campos
        # que Ventas podía editar durante la generación original.
        for widget in estado["editables"]:
            try:
                widget.configure(state="normal" if estado["modo_edicion"] else "disabled")
            except Exception:
                pass
        actualizar_estado_botones()
        if finalizada:
            lbl_detalle.configure(text=f"{cot.get('cot_folio')} · En compra X Cotización. El registro quedó bloqueado para conservar lo enviado a Compras.", text_color="#15803D")
        elif cot:
            lbl_detalle.configure(text=f"{cot.get('cot_folio')} · Cotización guardada. Usa Modificar para habilitar cambios o Finalizar para enviarla a Dirección General.")
        recalcular()

    def collect():
        base = dict(estado["cotizacion"] or {})
        reg = estado["registro"] or {}
        base.update({k:v.get().strip() for k,v in estado["vars"].items()})
        base.update({
            "id_cotizacion": (estado["cotizacion"] or {}).get("id_cotizacion"),
            "id_levantamiento": reg.get("id_levantamiento"), "id_cliente": reg.get("id_cliente"), "id_sucursal": reg.get("id_sucursal"),
        })
        parts=[]
        for i,pv in enumerate(estado["partida_vars"],1):
            item={k:v.get().strip() for k,v in pv.items()}; item["lote"]=str(i); parts.append(item)
        return base,parts

    def guardar():
        if not estado["registro"]: return
        valida, motivo = validar_captura_completa()
        if not valida:
            messagebox.showwarning("Cotización incompleta", motivo)
            actualizar_estado_botones()
            return
        datos,parts=collect()
        usuario_nombre=str((usuario or {}).get("usuario") or "Ventas")
        btn_guardar.configure(state="disabled")
        def ok(cot):
            estado["cotizacion"] = cot
            if "cot_folio" in estado["vars"]:
                estado["vars"]["cot_folio"].set(str(cot.get("cot_folio") or ""))
            estado["modo_edicion"] = False
            for widget in estado["editables"]:
                try:
                    widget.configure(state="disabled")
                except Exception:
                    pass
            actualizar_estado_botones()
            lbl_detalle.configure(text=f"{cot.get('cot_folio')} · Cotización guardada. Usa Modificar para habilitar cambios o Finalizar para enviarla a Dirección General.")
            recalcular()
            refrescar()
            messagebox.showinfo("Cotización guardada",f"Cotización {cot.get('cot_folio')} guardada correctamente.\n\nTotal: ${float(cot.get('cot_total') or 0):,.2f} MXN")
        run_async(parent.winfo_toplevel(), lambda: guardar_cotizacion_comercial(datos,parts,usuario_nombre), ok,
                  lambda e:(actualizar_estado_botones(),messagebox.showerror("No fue posible guardar",str(e))))

    def modificar():
        reg = estado.get("registro")
        cot = estado.get("cotizacion") or {}
        if not reg or not cot.get("id_cotizacion"):
            messagebox.showinfo("Cotización pendiente", "Primero guarda la cotización para poder utilizar Modificar.")
            return
        if str(cot.get("cot_estatus") or ESTATUS_BORRADOR).strip().upper() != ESTATUS_BORRADOR:
            messagebox.showwarning("Cotización bloqueada", "Esta cotización fue enviada a Dirección General o Compras; no puede modificarse desde Ventas.")
            return
        # Se vuelve a consultar la cotización desde Supabase mediante render() y
        # sólo entonces se habilitan los mismos campos disponibles al generarla.
        render(reg, forzar_edicion=True)
        lbl_detalle.configure(text=f"{estado['cotizacion'].get('cot_folio')} · Modo modificación activo. Guarda los cambios antes de finalizar.", text_color=TEXT_SECONDARY)

    def finalizar():
        cot = estado.get("cotizacion") or {}
        if not cot.get("id_cotizacion"):
            messagebox.showwarning("Cotización sin guardar", "Primero guarda la cotización para asignar su folio COT-XXXXX.")
            return
        if estado.get("modo_edicion"):
            messagebox.showwarning("Cambios pendientes", "Guarda los cambios de la cotización antes de finalizarla.")
            return
        valida, motivo = validar_captura_completa()
        if not valida:
            messagebox.showwarning("Cotización incompleta", motivo)
            actualizar_estado_botones()
            return
        folio = str(cot.get("cot_folio") or "").strip()
        if str(cot.get("cot_estatus") or ESTATUS_BORRADOR).strip().upper() != ESTATUS_BORRADOR:
            messagebox.showinfo("Cotización enviada", f"{folio} ya salió del estado BORRADOR.")
            return
        if not messagebox.askyesno(
            "Finalizar cotización",
            f"¿Confirmas finalizar {folio} y enviarla a Dirección General?\n\n"
            "Esta acción NO genera una Orden de Trabajo y bloqueará la cotización para evitar cambios posteriores desde Ventas.",
        ):
            return
        usuario_nombre = str((usuario or {}).get("usuario") or "Ventas")
        btn_finalizar.configure(state="disabled")
        def ok_finalizada(actualizada):
            estado["cotizacion"] = actualizada
            estado["modo_edicion"] = False
            actualizar_estado_botones()
            lbl_detalle.configure(text=f"{folio} · Pendiente de autorización por DG.", text_color="#15803D")
            refrescar()
            messagebox.showinfo(
                "Cotización enviada a Dirección General",
                f"{folio} quedó pendiente de autorización por Dirección General.\n\nCompras no puede procesarla hasta obtener esa autorización.",
            )
        run_async(
            parent.winfo_toplevel(),
            lambda: finalizar_cotizacion_para_compras(cot, usuario_nombre),
            ok_finalizada,
            lambda e: (actualizar_estado_botones(), messagebox.showerror("No fue posible finalizar", str(e))),
        )

    def pdf():
        if not estado.get("registro"):
            messagebox.showinfo("Selecciona un levantamiento", "Carga primero un levantamiento para generar la vista previa.")
            return
        valida, motivo = validar_captura_completa()
        if not valida:
            messagebox.showwarning("Cotización incompleta", motivo)
            actualizar_estado_botones()
            return

        # El Preview trabaja con lo que está actualmente capturado en pantalla;
        # no obliga a guardar ni consume un folio COT-XXXXX.
        datos, parts = collect()
        preview = dict(datos)
        preview["cot_folio"] = str((estado.get("cotizacion") or {}).get("cot_folio") or "").strip()
        if not preview["cot_folio"] or preview["cot_folio"] == "SE ASIGNA AL GUARDAR":
            preview["cot_folio"] = "COT-BORRADOR"

        subtotal = 0.0
        partidas_pdf = []
        for i, item in enumerate(parts, 1):
            row = dict(item)
            cantidad = _num(row.get("cantidad")) or 1.0
            precio_unitario = _num(row.get("precio_unitario"))
            importe = _num(row.get("importe"))
            if importe == 0 and precio_unitario > 0:
                importe = round(cantidad * precio_unitario, 2)
                row["importe"] = f"{importe:.2f}"
            subtotal += importe
            row["lote"] = str(row.get("lote") or i)
            partidas_pdf.append(row)

        descuento_pct = _num(preview.get("cot_descuento_pct"))
        iva_pct = _num(preview.get("cot_iva_pct"))
        descuento = round(subtotal * descuento_pct / 100.0, 2)
        subtotal_desc = round(subtotal - descuento, 2)
        iva = round(subtotal_desc * iva_pct / 100.0, 2)
        total = round(subtotal_desc + iva, 2)
        preview.update({
            "cot_partidas_json": partidas_pdf,
            "cot_subtotal": round(subtotal, 2),
            "cot_descuento": descuento,
            "cot_subtotal_descuento": subtotal_desc,
            "cot_iva": iva,
            "cot_total": total,
        })

        try:
            opciones = solicitar_campos_pdf(parent)
            if opciones is None:
                return
            AxiaPdfEngine.render_cotizacion(preview, abrir=True, campos_visibles=opciones)
        except Exception as e:
            logger.exception("Error al generar Preview PDF de cotización")
            messagebox.showerror("Preview PDF", str(e))

    def cargar_seleccion():
        reg = tabla.selected_payload()
        if not reg:
            messagebox.showinfo("Selecciona un levantamiento", "Selecciona primero un levantamiento de la tabla.")
            return
        lbl_titulo.configure(text=f"{_texto(reg,'lev_folio')} · {_texto(reg,'lev_cliente')}")
        lbl_detalle.configure(text="Cotización comercial ligada al levantamiento preautorizado.")
        render(reg)
        mostrar_bandejas(False)

    def cargar_cotizacion_seleccionada(origen="borrador"):
        cot = (tabla_aut if origen == "autorizada" else tabla_cot).selected_payload()
        if not cot:
            messagebox.showinfo("Selecciona una cotización", "Selecciona primero una cotización COT-XXXXX de la tabla.")
            return

        def tarea():
            reg = obtener_levantamiento_de_cotizacion(cot)
            if not reg:
                raise ValueError(f"No fue posible localizar el levantamiento origen de {cot.get('cot_folio') or 'la cotización'}.")
            return reg

        def ok(reg):
            lbl_titulo.configure(text=f"{_texto(cot,'cot_folio')} · {_texto(cot,'cot_cliente')}")
            if origen == "autorizada":
                lbl_detalle.configure(text=f"{_texto(cot,'cot_folio')} · Estado: {_texto(cot,'cot_estatus')} (solo consulta).")
            else:
                lbl_detalle.configure(text=f"{_texto(cot,'cot_folio')} · Cotización guardada sin autorizar. Usa Modificar para habilitar cambios.")
            render(reg)
            mostrar_bandejas(False)

        run_async(parent.winfo_toplevel(), tarea, ok,
                  lambda e: messagebox.showerror("No fue posible abrir la cotización", str(e)))

    def refrescar():
        lbl_lista.configure(text="Consultando levantamientos...")
        lbl_cotizaciones.configure(text="Consultando cotizaciones realizadas...")
        lbl_autorizadas.configure(text="Consultando cotizaciones en DG / Compras...")

        def valores_cot(r):
            return (_texto(r,"cot_folio"), _texto(r,"lev_folio"),
                    _texto(r,"cot_cliente"), _texto(r,"cot_fecha"))

        def pintar_lev(regs):
            registros_cache[:] = list(regs or [])
            lbl_lista.configure(text=f"Levantamientos Preautorizados ({len(registros_cache)})")
            tabla.set_rows(
                registros_cache,
                value_factory=lambda r:(
                    _texto(r,"lev_folio"), _texto(r,"lev_cliente"),
                    " / ".join(filter(None,[_texto(r,"lev_tipo"),_texto(r,"lev_modalidad_operativa")])),
                    _texto(r,"lev_fecha_programada"),
                ),
            )
            if not registros_cache:
                lbl_detalle.configure(text="No hay levantamientos preautorizados pendientes de cotización.")

        def pintar_cot(regs):
            cotizaciones_cache[:] = list(regs or [])
            lbl_cotizaciones.configure(text=f"Cotizaciones Realizadas ({len(cotizaciones_cache)})")
            tabla_cot.set_rows(cotizaciones_cache, value_factory=valores_cot)

        def pintar_aut(regs):
            autorizadas_cache[:] = list(regs or [])
            lbl_autorizadas.configure(text=f"En DG / Compras ({len(autorizadas_cache)})")
            tabla_aut.set_rows(autorizadas_cache, value_factory=valores_cot)

        run_async(parent.winfo_toplevel(), obtener_levantamientos_para_cotizar, pintar_lev,
                  lambda e: messagebox.showerror("No fue posible consultar levantamientos", str(e)))
        run_async(parent.winfo_toplevel(), obtener_cotizaciones_pendientes_compras, pintar_cot,
                  lambda e: messagebox.showerror("No fue posible consultar cotizaciones", str(e)))
        run_async(parent.winfo_toplevel(), obtener_cotizaciones_seguimiento_dg, pintar_aut,
                  lambda e: messagebox.showerror("No fue posible consultar cotizaciones autorizadas", str(e)))

    ctk.CTkButton(
        bandeja, text="Cargar levantamiento seleccionado", image=icono_votar, compound="left",
        height=36, width=180, corner_radius=10, font=BUTTON_FONT,
        fg_color="#2563EB", hover_color="#1D4ED8", text_color=WHITE,
        border_width=0, command=cargar_seleccion,
    ).grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 7))
    ctk.CTkButton(
        bandeja_cot, text="Abrir cotización modificable", image=icono_abrir, compound="left",
        height=36, width=180, corner_radius=10, font=BUTTON_FONT,
        fg_color="#2563EB", hover_color="#1D4ED8", text_color=WHITE,
        border_width=0, command=lambda: cargar_cotizacion_seleccionada("borrador"),
    ).grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 7))
    ctk.CTkButton(
        bandeja_aut, text="Consultar cotización autorizada", image=icono_abrir, compound="left",
        height=36, width=180, corner_radius=10, font=BUTTON_FONT,
        fg_color="#2563EB", hover_color="#1D4ED8", text_color=WHITE,
        border_width=0, command=lambda: cargar_cotizacion_seleccionada("autorizada"),
    ).grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 7))

    btn_guardar.configure(command=guardar); btn_pdf.configure(command=pdf); btn_modificar.configure(command=modificar); btn_finalizar.configure(command=finalizar)
    refrescar()
