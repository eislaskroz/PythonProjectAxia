"""Módulo comercial de cotizaciones formales para Ventas."""
from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox, filedialog

from app_context import obtener_usuario_actual
from core.background_tasks import run_async
from core.logger import configurar_logger
from security.permissions import puede_cotizar_levantamientos
from services.cotizaciones_service import (
    obtener_levantamientos_para_cotizar,
    obtener_cotizaciones_pendientes_compras,
    obtener_levantamiento_de_cotizacion,
    cargar_cotizacion,
    datos_generales_cotizacion,
    construir_partidas_comerciales,
    guardar_cotizacion_comercial,
    finalizar_cotizacion_para_compras,
    ESTATUS_BORRADOR,
    ESTATUS_EN_COMPRA,
)
from services.axia_pdf_engine import AxiaPdfEngine
from services.usuarios_service import obtener_nombres_usuarios_por_tipos, obtener_usuarios_por_tipos
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY, BUTTON_HOVER
from ui.fonts import TITLE_MD, TEXT_MD, TEXT_SM, BUTTON_FONT
from ui.native_table import NativeTreeTable

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

    root = ctk.CTkFrame(parent, fg_color="transparent")
    root.pack(fill="both", expand=True, padx=14, pady=(4, 12))
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)

    superior = ctk.CTkFrame(root, fg_color="transparent")
    superior.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    superior.grid_columnconfigure(0, weight=1, uniform="top")
    superior.grid_columnconfigure(1, weight=1, uniform="top")

    # FIX30: las dos bandejas superiores representan los dos caminos de Ventas:
    # a la izquierda, cotizaciones COT-XXXXX ya guardadas pero todavía editables;
    # a la derecha, levantamientos preautorizados que aún pueden generar cotización.
    bandeja_cot = ctk.CTkFrame(superior, fg_color=WHITE, corner_radius=16)
    bandeja_cot.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    bandeja_cot.grid_columnconfigure(0, weight=1)
    lbl_cotizaciones = ctk.CTkLabel(
        bandeja_cot, text="Cotizaciones realizadas · Pendientes de Compras",
        font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w"
    )
    lbl_cotizaciones.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))
    tabla_cot = NativeTreeTable(
        bandeja_cot,
        columns=(("folio","Cotización",130),("levantamiento","Levantamiento",130),
                 ("cliente","Cliente",210),("fecha","Fecha",115)),
        height=3,
    )
    tabla_cot.grid(row=1, column=0, sticky="ew", padx=10, pady=(0,6))

    bandeja = ctk.CTkFrame(superior, fg_color=WHITE, corner_radius=16)
    bandeja.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    bandeja.grid_columnconfigure(0, weight=1)
    lbl_lista = ctk.CTkLabel(bandeja, text="Levantamientos preautorizados", font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w")
    lbl_lista.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))
    tabla = NativeTreeTable(bandeja, columns=(("folio","Folio",135),("cliente","Cliente",210),("tipo","Tipo",210),("fecha","Fecha",125)), height=3)
    tabla.grid(row=1, column=0, sticky="ew", padx=10, pady=(0,6))

    detalle_card = ctk.CTkFrame(root, fg_color=WHITE, corner_radius=16)
    detalle_card.grid(row=1, column=0, sticky="nsew"); detalle_card.grid_columnconfigure(0, weight=1); detalle_card.grid_rowconfigure(1, weight=1)
    info = ctk.CTkFrame(detalle_card, fg_color="transparent")
    info.grid(row=0, column=0, sticky="ew", padx=14, pady=(8,3)); info.grid_columnconfigure(0, weight=1)
    lbl_titulo = ctk.CTkLabel(info, text="Selecciona un levantamiento", font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w")
    lbl_titulo.grid(row=0, column=0, sticky="ew")
    lbl_detalle = ctk.CTkLabel(info, text="La cotización se guardará en una tabla propia con folio COT-XXXXX.", font=TEXT_SM, text_color=TEXT_SECONDARY, anchor="w")
    lbl_detalle.grid(row=1, column=0, sticky="ew", pady=(2,0))

    scroll = ctk.CTkScrollableFrame(detalle_card, fg_color="#F8FAFC", corner_radius=12)
    scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=5)
    for col in range(4): scroll.grid_columnconfigure(col, weight=1)

    acciones = ctk.CTkFrame(detalle_card, fg_color="transparent")
    acciones.grid(row=2, column=0, sticky="ew", padx=14, pady=(4,10)); acciones.grid_columnconfigure(0, weight=1)
    lbl_total = ctk.CTkLabel(acciones, text="Total: $0.00 MXN", font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="e")
    lbl_total.grid(row=0, column=0, sticky="e", padx=(0,10))
    btn_pdf = ctk.CTkButton(acciones, text="👁 PDF Cotización (Preview)", width=170, fg_color="#334155", hover_color=BUTTON_HOVER,
                            font=BUTTON_FONT, state="disabled")
    btn_pdf.grid(row=0, column=1, padx=(0,8))
    btn_modificar = ctk.CTkButton(acciones, text="✎ Modificar cotización", width=165, fg_color="#0F766E", hover_color=BUTTON_HOVER,
                                  font=BUTTON_FONT, state="disabled")
    btn_modificar.grid(row=0, column=2, padx=(0,8))
    btn_guardar = ctk.CTkButton(acciones, text="💾 Guardar cotización", width=175, fg_color=SECONDARY, hover_color=BUTTON_HOVER,
                                font=BUTTON_FONT, state="disabled")
    btn_guardar.grid(row=0, column=3, padx=(0,8))
    btn_finalizar = ctk.CTkButton(acciones, text="✓ Finalizar cotización", width=170, fg_color="#15803D", hover_color=BUTTON_HOVER,
                                  font=BUTTON_FONT, state="disabled")
    btn_finalizar.grid(row=0, column=4)
    lbl_validacion = ctk.CTkLabel(acciones, text="Carga un levantamiento para iniciar la cotización.",
                                  font=TEXT_SM, text_color=TEXT_SECONDARY, anchor="e")
    lbl_validacion.grid(row=1, column=0, columnspan=5, sticky="e", pady=(4,0))

    def limpiar():
        for w in scroll.winfo_children(): w.destroy()
        estado["vars"] = {}; estado["partidas"] = []; estado["partida_vars"] = []; estado["cotizacion"] = {}; estado["editables"] = []
        estado["modo_edicion"] = False
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
        ctk.CTkLabel(parent_frame, text=label, font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w").grid(
            row=row*2, column=col, columnspan=colspan, sticky="ew", padx=5, pady=(4,1))
        var = ctk.StringVar(value=str(value or "")); estado["vars"][key] = var
        ent = ctk.CTkEntry(parent_frame, textvariable=var, height=32)
        ent.grid(row=row*2+1, column=col, columnspan=colspan, sticky="ew", padx=5, pady=(0,4))
        if readonly:
            ent.configure(state="disabled")
        else:
            estado["editables"].append(ent)
        var.trace_add("write", lambda *_: actualizar_estado_botones())
        return var

    def add_select(parent_frame, row, col, label, key, values, value="", colspan=1):
        ctk.CTkLabel(parent_frame, text=label, font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w").grid(
            row=row*2, column=col, columnspan=colspan, sticky="ew", padx=5, pady=(4,1))
        opciones = [str(x).strip() for x in (values or []) if str(x).strip()]
        actual = str(value or "").strip()
        if actual not in opciones:
            actual = opciones[0] if opciones else ""
        var = ctk.StringVar(value=actual); estado["vars"][key] = var
        menu = ctk.CTkOptionMenu(parent_frame, variable=var, values=opciones or ["SIN JEFES DE OPERACIONES REGISTRADOS"], height=32)
        menu.grid(row=row*2+1, column=col, columnspan=colspan, sticky="ew", padx=5, pady=(0,4))
        if not opciones:
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
        finalizada = str(cot.get("cot_estatus") or ESTATUS_BORRADOR).strip().upper() == ESTATUS_EN_COMPRA if cot else False
        modo = bool(estado.get("modo_edicion"))
        btn_pdf.configure(state="normal" if valida else "disabled")
        btn_guardar.configure(state="normal" if (modo and valida and not finalizada) else "disabled")
        btn_modificar.configure(state="normal" if (cot and not finalizada and not modo) else "disabled")
        btn_finalizar.configure(state="normal" if (cot and valida and not finalizada and not modo) else "disabled")
        if finalizada:
            lbl_validacion.configure(text="Cotización finalizada y enviada a Compras.", text_color="#15803D")
        elif not valida:
            lbl_validacion.configure(text=f"Pendiente: {mensaje}", text_color="#B45309")
        elif cot and not modo:
            lbl_validacion.configure(text="Cotización completa. Usa Modificar para editar o Finalizar para enviarla a Compras.", text_color="#15803D")
        else:
            lbl_validacion.configure(text="Cotización completa. Preview y Guardar están habilitados.", text_color="#15803D")

    def render(registro, forzar_edicion=False):
        limpiar(); estado["registro"] = registro
        cot = cargar_cotizacion(registro)
        base = datos_generales_cotizacion(registro, usuario)
        if cot:
            base.update({k:v for k,v in cot.items() if v is not None})
        estado["cotizacion"] = dict(cot)
        estatus = str(cot.get("cot_estatus") or ESTATUS_BORRADOR).strip().upper() if cot else ESTATUS_BORRADOR
        finalizada = bool(cot) and estatus == ESTATUS_EN_COMPRA
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
        for c in range(5): general.grid_columnconfigure(c, weight=1)

        # Distribución compacta de cinco columnas según el flujo comercial.
        add_field(general,0,0,"No. Cotización","cot_folio",base.get("cot_folio"),True)
        add_field(general,0,1,"Fecha de Cotización","cot_fecha",base.get("cot_fecha"),True)
        add_field(general,0,2,"No. Levantamiento","lev_folio",base.get("lev_folio"),True)
        add_field(general,0,3,"Cliente","cot_cliente",base.get("cot_cliente"),True)
        add_field(general,0,4,"Contacto","cot_contacto",base.get("cot_contacto"),True)

        add_field(general,1,0,"Sucursal","cot_sucursal",base.get("cot_sucursal"),True,2)
        add_field(general,1,2,"Asunto","cot_asunto",base.get("cot_asunto"),True,2)
        # El usuario tipo 6 queda asociado automáticamente como ESI. El administrador
        # puede elegir una Ejecutiva de Ventas real (tipo 6) para pruebas/gestión; al
        # seleccionarla se cargan automáticamente su correo corporativo y teléfono.
        tipo_actual = int((usuario or {}).get("usu_tipo") or 0)
        ventas_catalogo = obtener_usuarios_por_tipos([6]) if tipo_actual == 1 else []
        ventas_por_etiqueta = {str(u.get("etiqueta") or "").strip(): u for u in ventas_catalogo}
        if tipo_actual == 1 and ventas_catalogo:
            esi_actual = str(base.get("cot_esi") or "").strip()
            opciones_esi = list(ventas_por_etiqueta)
            if esi_actual and esi_actual not in opciones_esi and estado.get("cotizacion"):
                opciones_esi.insert(0, esi_actual)
            add_select(general,1,4,"ESI / Ejecutiva de Ventas","cot_esi",opciones_esi,esi_actual)
        else:
            add_field(general,1,4,"ESI / Ejecutiva de Ventas","cot_esi",base.get("cot_esi"),True)

        add_field(general,2,0,"Correo ESI","cot_esi_correo",base.get("cot_esi_correo"),True)
        add_field(general,2,1,"Teléfono ESI","cot_esi_telefono",base.get("cot_esi_telefono"),True)
        if tipo_actual == 1 and ventas_catalogo:
            def _sincronizar_esi(*_):
                elegido = str(estado["vars"]["cot_esi"].get() or "").strip()
                reg_esi = ventas_por_etiqueta.get(elegido) or {}
                if reg_esi:
                    estado["vars"]["cot_esi_correo"].set(str(reg_esi.get("usu_correo") or "").strip())
                    estado["vars"]["cot_esi_telefono"].set(str(reg_esi.get("usu_telefono") or "").strip())
                actualizar_estado_botones()
            estado["vars"]["cot_esi"].trace_add("write", _sincronizar_esi)
            if not estado.get("cotizacion"):
                _sincronizar_esi()

        jefes_operaciones = obtener_nombres_usuarios_por_tipos([2])
        add_select(general,2,2,"Jefe de Operaciones","cot_jefe_operaciones",jefes_operaciones,base.get("cot_jefe_operaciones"),2)
        add_field(general,2,4,"Supervisor","cot_supervisor",base.get("cot_supervisor"),True)

        add_field(general,3,0,"Días","cot_dias",base.get("cot_dias"),True)
        add_field(general,3,1,"Personas","cot_personas",base.get("cot_personas"),True)
        add_field(general,3,2,"Plan de Pagos","cot_plan_pagos",base.get("cot_plan_pagos"),False,2)

        add_field(general,4,0,"Vigencia de Cotización","cot_vigencia",base.get("cot_vigencia"))
        vd=add_field(general,4,1,"Descuento %","cot_descuento_pct",base.get("cot_descuento_pct",0))
        vi=add_field(general,4,2,"IVA %","cot_iva_pct",base.get("cot_iva_pct",16))
        vd.trace_add("write", recalcular); vi.trace_add("write", recalcular)

        ctk.CTkLabel(scroll, text="Partidas comerciales", font=TITLE_MD, text_color=TEXT_PRIMARY, anchor="w").grid(
            row=2, column=0, columnspan=4, sticky="ew", padx=6, pady=(4,2))
        partidas = construir_partidas_comerciales(registro, cot)
        estado["partidas"] = partidas
        cont = ctk.CTkFrame(scroll, fg_color="transparent")
        cont.grid(row=3, column=0, columnspan=4, sticky="ew")
        cont.grid_columnconfigure(0, weight=1)

        for i,item in enumerate(partidas):
            card = ctk.CTkFrame(cont, fg_color=WHITE, corner_radius=10)
            card.grid(row=i, column=0, sticky="ew", padx=4, pady=4)
            for c in range(6): card.grid_columnconfigure(c, weight=1)
            ctk.CTkLabel(card, text=f"Lote {item.get('lote',i+1)} · {item.get('concepto','')}", font=("Montserrat",11,"bold"),
                         text_color=TEXT_PRIMARY, anchor="w", wraplength=1100).grid(row=0,column=0,columnspan=6,sticky="ew",padx=8,pady=(6,2))
            vars_item={}
            fields=[
                ("Unidad / Tipo","unidad_tipo",1,0,1),("Cantidad","cantidad",1,1,1),("Proveedor","proveedor",1,2,1),
                ("Modelo","modelo",1,3,1),("SKU","sku",1,4,1),("Marca","marca",1,5,1),
                ("Concepto","concepto",3,0,2),("P. Lista","precio_lista",3,2,1),("Costo","costo",3,3,1),
                ("Utilidad %","utilidad_pct",3,4,1),("P. Venta","precio_venta",3,5,1),
                ("P. Unitario","precio_unitario",5,0,1),("Importe","importe",5,1,1),("Observaciones","observaciones",5,2,4),
            ]
            for lab,key,r,c,span in fields:
                ctk.CTkLabel(card,text=lab,font=("Montserrat",9,"bold"),text_color=TEXT_SECONDARY,anchor="w").grid(row=r,column=c,columnspan=span,sticky="ew",padx=5,pady=(2,0))
                var=ctk.StringVar(value=str(item.get(key) if item.get(key) not in (None,"") else "")); vars_item[key]=var
                ent = ctk.CTkEntry(card,textvariable=var,height=29)
                ent.grid(row=r+1,column=c,columnspan=span,sticky="ew",padx=5,pady=(0,5))
                if key in {"unidad_tipo", "cantidad", "concepto", "costo", "precio_venta", "precio_unitario", "importe"}:
                    # Unidad/Cantidad/Concepto vienen del levantamiento.
                    # Costo/P.Venta/P.Unitario/Importe son resultados comerciales calculados.
                    ent.configure(state="disabled")
                else:
                    estado["editables"].append(ent)

            # FIX25: Ventas captura únicamente P. Lista y Utilidad %.
            # COSTO       = P. LISTA * (UTILIDAD / 100)
            # P. VENTA    = P. LISTA + COSTO
            # P. UNITARIO = P. VENTA
            # IMPORTE     = P. UNITARIO * CANTIDAD
            lock={"x":False}
            def calc_comercial(*_, pv=vars_item, lk=lock):
                if lk["x"]:
                    return
                try:
                    lista=float(str(pv["precio_lista"].get()).replace(",","") or 0)
                    utilidad=float(str(pv["utilidad_pct"].get()).replace("%","").replace(",","") or 0)
                    cantidad=float(str(pv["cantidad"].get()).replace(",","") or 0)
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

            vars_item["precio_lista"].trace_add("write",calc_comercial)
            vars_item["utilidad_pct"].trace_add("write",calc_comercial)
            vars_item["cantidad"].trace_add("write",calc_comercial)
            vars_item["importe"].trace_add("write",recalcular)
            for _var in vars_item.values():
                _var.trace_add("write", lambda *_: actualizar_estado_botones())
            calc_comercial()
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
            lbl_detalle.configure(text=f"{cot.get('cot_folio')} · Cotización guardada. Usa Modificar para habilitar cambios o Finalizar para enviarla a Compras.")
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
            lbl_detalle.configure(text=f"{cot.get('cot_folio')} · Cotización guardada. Usa Modificar para habilitar cambios o Finalizar para enviarla a Compras.")
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
        if str(cot.get("cot_estatus") or ESTATUS_BORRADOR).strip().upper() == ESTATUS_EN_COMPRA:
            messagebox.showwarning("Cotización en Compras", "Esta cotización ya fue finalizada y enviada a Compras; no puede modificarse desde Ventas.")
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
        if str(cot.get("cot_estatus") or ESTATUS_BORRADOR).strip().upper() == ESTATUS_EN_COMPRA:
            messagebox.showinfo("Cotización finalizada", f"{folio} ya se encuentra En compra X Cotización.")
            return
        if not messagebox.askyesno(
            "Finalizar cotización",
            f"¿Confirmas finalizar {folio} y enviarla a Compras?\n\n"
            "Esta acción NO genera una Orden de Trabajo y bloqueará la cotización para evitar cambios posteriores desde Ventas.",
        ):
            return
        usuario_nombre = str((usuario or {}).get("usuario") or "Ventas")
        btn_finalizar.configure(state="disabled")
        def ok_finalizada(actualizada):
            estado["cotizacion"] = actualizada
            estado["modo_edicion"] = False
            actualizar_estado_botones()
            lbl_detalle.configure(text=f"{folio} · En compra X Cotización. Pendiente de atención por Compras.", text_color="#15803D")
            refrescar()
            messagebox.showinfo(
                "Cotización enviada a Compras",
                f"{folio} quedó con estado: En compra X Cotización.\n\nNo se generó ninguna Orden de Trabajo.",
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
            AxiaPdfEngine.render_cotizacion(preview, abrir=True)
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

    def cargar_cotizacion_seleccionada():
        cot = tabla_cot.selected_payload()
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
            lbl_detalle.configure(text=f"{_texto(cot,'cot_folio')} · Cotización guardada pendiente de Compras. Usa Modificar para habilitar cambios.")
            render(reg)

        run_async(parent.winfo_toplevel(), tarea, ok,
                  lambda e: messagebox.showerror("No fue posible abrir la cotización", str(e)))

    def refrescar():
        lbl_lista.configure(text="Consultando levantamientos preautorizados...")
        lbl_cotizaciones.configure(text="Consultando cotizaciones pendientes...")

        resultados = {"lev": None, "cot": None}

        def pintar_lev(regs):
            registros_cache[:] = list(regs or [])
            lbl_lista.configure(text=f"Levantamientos preautorizados ({len(registros_cache)})")
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
            lbl_cotizaciones.configure(text=f"Cotizaciones realizadas · Pendientes de Compras ({len(cotizaciones_cache)})")
            tabla_cot.set_rows(
                cotizaciones_cache,
                value_factory=lambda r:(
                    _texto(r,"cot_folio"), _texto(r,"lev_folio"), _texto(r,"cot_cliente"), _texto(r,"cot_fecha"),
                ),
            )

        run_async(parent.winfo_toplevel(), obtener_levantamientos_para_cotizar, pintar_lev,
                  lambda e:messagebox.showerror("No fue posible consultar levantamientos",str(e)))
        run_async(parent.winfo_toplevel(), obtener_cotizaciones_pendientes_compras, pintar_cot,
                  lambda e:messagebox.showerror("No fue posible consultar cotizaciones",str(e)))

    ctk.CTkButton(
        bandeja_cot, text="✎ Abrir cotización seleccionada", height=38, font=BUTTON_FONT,
        fg_color="#0F766E", hover_color=BUTTON_HOVER, command=cargar_cotizacion_seleccionada
    ).grid(row=2,column=0,sticky="ew",padx=10,pady=(0,8))
    ctk.CTkButton(
        bandeja,text="📥 Cargar levantamiento seleccionado",height=38,font=BUTTON_FONT,command=cargar_seleccion
    ).grid(row=2,column=0,sticky="ew",padx=10,pady=(0,8))
    btn_guardar.configure(command=guardar); btn_pdf.configure(command=pdf); btn_modificar.configure(command=modificar); btn_finalizar.configure(command=finalizar)
    refrescar()
