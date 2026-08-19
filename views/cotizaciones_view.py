"""Módulo comercial de cotizaciones de levantamientos para Ventas."""
from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

from app_context import obtener_usuario_actual
from core.background_tasks import run_async
from core.logger import configurar_logger
from security.permissions import puede_cotizar_levantamientos
from services.cotizaciones_service import (
    obtener_levantamientos_para_cotizar,
    partidas_cotizables,
    cargar_cotizacion,
    guardar_cotizacion_levantamiento,
)
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY, BUTTON_HOVER
from ui.fonts import TITLE_MD, TEXT_MD, TEXT_SM, BUTTON_FONT
from ui.native_table import NativeTreeTable

logger = configurar_logger(__name__)


def _texto(registro, clave):
    return str((registro or {}).get(clave) or "").strip()


def mostrar_cotizaciones(parent, app=None):
    usuario = obtener_usuario_actual()
    if not puede_cotizar_levantamientos(usuario):
        messagebox.showerror(
            "Acceso denegado",
            "Este módulo está disponible únicamente para Ventas (id=6) y Administrador.",
        )
        return

    for widget in parent.winfo_children():
        widget.destroy()

    seleccion = {
        "registro": None,
        "partidas": [],
        "entries": [],
        "servicio_concepto": None,
        "servicio_costo": None,
    }
    registros_cache = []

    root = ctk.CTkFrame(parent, fg_color="transparent")
    root.pack(fill="both", expand=True, padx=14, pady=(4, 12))
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)

    # ------------------------------------------------------------------
    # Franja superior: búsqueda a la izquierda y bandeja a la derecha.
    # ------------------------------------------------------------------
    superior = ctk.CTkFrame(root, fg_color="transparent")
    superior.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    superior.grid_columnconfigure(0, weight=1, uniform="top")
    superior.grid_columnconfigure(1, weight=1, uniform="top")

    cabecera = ctk.CTkFrame(superior, fg_color=WHITE, corner_radius=16)
    cabecera.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    cabecera.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        cabecera, text="Cotizaciones de levantamientos", font=TITLE_MD,
        text_color=TEXT_PRIMARY, anchor="w",
    ).grid(row=0, column=0, columnspan=3, sticky="ew", padx=14, pady=(10, 2))
    ctk.CTkLabel(
        cabecera,
        text=(
            "Ventas captura el costo de materiales, insumos, equipos y del servicio "
            "de los levantamientos preautorizados por Operaciones."
        ),
        font=TEXT_MD, text_color=TEXT_SECONDARY, anchor="w",
    ).grid(row=1, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 8))

    var_busqueda = ctk.StringVar()
    _normalizando_busqueda = {"activo": False}

    def _forzar_mayusculas_busqueda(*_):
        if _normalizando_busqueda["activo"]:
            return
        actual = var_busqueda.get()
        mayusculas = actual.upper()
        if actual == mayusculas:
            return
        _normalizando_busqueda["activo"] = True
        try:
            var_busqueda.set(mayusculas)
        finally:
            _normalizando_busqueda["activo"] = False

    var_busqueda.trace_add("write", _forzar_mayusculas_busqueda)
    entrada_busqueda = ctk.CTkEntry(
        cabecera, textvariable=var_busqueda, height=40,
        placeholder_text="BUSCAR POR FOLIO, CLIENTE, TIPO O MODALIDAD",
    )
    entrada_busqueda.grid(row=2, column=0, sticky="ew", padx=(14, 6), pady=(0, 10))

    # ------------------------------------------------------------------
    # Bandeja superior derecha: compacta y alineada con la búsqueda.
    # ------------------------------------------------------------------
    bandeja = ctk.CTkFrame(superior, fg_color=WHITE, corner_radius=16)
    bandeja.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    bandeja.grid_columnconfigure(0, weight=1)

    lbl_lista = ctk.CTkLabel(
        bandeja, text="Levantamientos preautorizados", font=TITLE_MD,
        text_color=TEXT_PRIMARY, anchor="w",
    )
    lbl_lista.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))

    tabla = NativeTreeTable(
        bandeja,
        columns=(("folio", "Folio", 135), ("cliente", "Cliente", 210),
                 ("tipo", "Tipo", 210), ("fecha", "Fecha", 125)),
        height=3,
    )
    tabla.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

    # ------------------------------------------------------------------
    # Detalle inferior: ocupa el resto de la pantalla.
    # ------------------------------------------------------------------
    detalle_card = ctk.CTkFrame(root, fg_color=WHITE, corner_radius=16)
    detalle_card.grid(row=1, column=0, sticky="nsew")
    detalle_card.grid_columnconfigure(0, weight=1)
    detalle_card.grid_rowconfigure(1, weight=1)

    info = ctk.CTkFrame(detalle_card, fg_color="transparent")
    info.grid(row=0, column=0, sticky="ew", padx=14, pady=(8, 3))
    info.grid_columnconfigure(0, weight=1)
    lbl_titulo = ctk.CTkLabel(
        info, text="Selecciona un levantamiento", font=TITLE_MD,
        text_color=TEXT_PRIMARY, anchor="w",
    )
    lbl_titulo.grid(row=0, column=0, sticky="ew")
    lbl_detalle = ctk.CTkLabel(
        info, text="Aquí aparecerán sus materiales, insumos, equipos y el costo del servicio.",
        font=TEXT_SM, text_color=TEXT_SECONDARY, anchor="w",
    )
    lbl_detalle.grid(row=1, column=0, sticky="ew", pady=(2, 0))

    scroll = ctk.CTkScrollableFrame(detalle_card, fg_color="#F8FAFC", corner_radius=12)
    scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=5)
    for col, weight in enumerate((0, 0, 0, 1, 0, 0)):
        scroll.grid_columnconfigure(col, weight=weight)

    acciones = ctk.CTkFrame(detalle_card, fg_color="transparent")
    acciones.grid(row=2, column=0, sticky="ew", padx=14, pady=(4, 10))
    acciones.grid_columnconfigure(0, weight=1)
    lbl_total = ctk.CTkLabel(
        acciones, text="Total cotizado: $0.00 MXN", font=TITLE_MD,
        text_color=TEXT_PRIMARY, anchor="e",
    )
    lbl_total.grid(row=0, column=0, sticky="e", padx=(0, 10))
    btn_guardar = ctk.CTkButton(
        acciones, text="💾 Guardar costos", width=190,
        fg_color=SECONDARY, hover_color=BUTTON_HOVER,
        font=BUTTON_FONT, state="disabled",
    )
    btn_guardar.grid(row=0, column=1, sticky="e")

    def limpiar_partidas():
        for w in scroll.winfo_children():
            w.destroy()
        seleccion["partidas"] = []
        seleccion["entries"] = []
        seleccion["servicio_concepto"] = None
        seleccion["servicio_costo"] = None
        lbl_total.configure(text="Total cotizado: $0.00 MXN")
        btn_guardar.configure(state="disabled")

    def recalcular_total(*_):
        total = 0.0
        for entry_info in seleccion["entries"]:
            texto = entry_info["var"].get().strip().replace(",", "")
            if not texto:
                continue
            try:
                valor = float(texto)
                if valor >= 0:
                    total += valor
            except ValueError:
                pass
        var_servicio = seleccion.get("servicio_costo")
        if var_servicio is not None:
            texto = var_servicio.get().strip().replace(",", "")
            if texto:
                try:
                    valor = float(texto)
                    if valor >= 0:
                        total += valor
                except ValueError:
                    pass
        lbl_total.configure(text=f"Total cotizado: ${total:,.2f} MXN")

    def render_partidas(registro):
        limpiar_partidas()
        partidas = partidas_cotizables(registro)
        seleccion["partidas"] = partidas
        cotizacion = cargar_cotizacion(registro)
        previas = cotizacion.get("partidas") if isinstance(cotizacion, dict) else []
        previas = previas if isinstance(previas, list) else []
        mapa_previas = {
            (str(x.get("partida") or ""), str(x.get("concepto") or "").strip().casefold()): x
            for x in previas if isinstance(x, dict)
        }

        # ----------------------------- Servicio -----------------------------
        servicio_previo = cotizacion.get("servicio") if isinstance(cotizacion, dict) else {}
        servicio_previo = servicio_previo if isinstance(servicio_previo, dict) else {}
        detalle = registro.get("lev_detalle_tecnico_json")
        especialidad = ""
        if isinstance(detalle, dict):
            especialidad = str(detalle.get("tipo_levantamiento") or "").strip()
        concepto_default = str(servicio_previo.get("concepto") or "").strip()
        if not concepto_default:
            base = especialidad or _texto(registro, "lev_tipo") or "levantamiento"
            concepto_default = f"Servicio de {base}"

        # Servicio: mantenemos únicamente los campos editables para ahorrar altura.
        ctk.CTkLabel(scroll, text="Concepto del servicio", font=TEXT_SM,
                     text_color=TEXT_PRIMARY, anchor="w").grid(row=0, column=0, columnspan=4, sticky="ew", padx=8, pady=(7, 2))
        ctk.CTkLabel(scroll, text="Costo total MXN", font=TEXT_SM,
                     text_color=TEXT_PRIMARY, anchor="w").grid(row=0, column=5, sticky="ew", padx=5, pady=(7, 2))

        var_servicio_concepto = ctk.StringVar(value=concepto_default)
        var_servicio_costo = ctk.StringVar(
            value=str(servicio_previo.get("costo_total"))
            if servicio_previo.get("costo_total") not in (None, "") else ""
        )
        var_servicio_costo.trace_add("write", recalcular_total)
        seleccion["servicio_concepto"] = var_servicio_concepto
        seleccion["servicio_costo"] = var_servicio_costo

        ctk.CTkEntry(
            scroll, textvariable=var_servicio_concepto, height=34,
            placeholder_text="DESCRIPCIÓN DEL SERVICIO",
        ).grid(row=1, column=0, columnspan=5, sticky="ew", padx=8, pady=(0, 7))
        ctk.CTkEntry(
            scroll, textvariable=var_servicio_costo, width=165, height=34,
            placeholder_text="0.00",
        ).grid(row=1, column=5, sticky="ew", padx=5, pady=(0, 7))

        ctk.CTkFrame(scroll, height=2, fg_color="#E2E8F0").grid(
            row=2, column=0, columnspan=6, sticky="ew", padx=6, pady=(0, 5)
        )

        headers = (
            "Partida", "Grupo", "Cant./Unidad", "Concepto / equipo",
            "Precio por pieza/unidad/metro", "Costo total MXN"
        )
        for c, text in enumerate(headers):
            ctk.CTkLabel(
                scroll, text=text, font=("Montserrat", 11, "bold"),
                text_color=TEXT_PRIMARY, anchor="w",
            ).grid(row=3, column=c, sticky="ew", padx=5, pady=(3, 7))

        if not partidas:
            ctk.CTkLabel(
                scroll,
                text="Este levantamiento no contiene materiales, insumos o equipos estructurados. Puedes cotizar únicamente el servicio.",
                font=TEXT_MD, text_color="#B45309", anchor="w",
            ).grid(row=4, column=0, columnspan=6, sticky="ew", padx=8, pady=12)
            btn_guardar.configure(state="normal")
            recalcular_total()
            return

        for i, item in enumerate(partidas, 1):
            row = i + 3
            concepto = str(item.get("concepto") or "")
            marca_modelo = " / ".join(filter(None, [
                str(item.get("marca") or "").strip(),
                str(item.get("modelo") or "").strip(),
            ]))
            if marca_modelo:
                concepto = f"{concepto}\n{marca_modelo}" if concepto else marca_modelo
            cant_unidad = " ".join(filter(None, [
                str(item.get("cantidad") or "").strip(),
                str(item.get("unidad") or "").strip(),
            ]))
            ctk.CTkLabel(scroll, text=str(item.get("partida") or i), font=TEXT_SM,
                         text_color=TEXT_PRIMARY, anchor="w").grid(row=row, column=0, sticky="nw", padx=5, pady=5)
            ctk.CTkLabel(scroll, text=str(item.get("grupo") or ""), font=TEXT_SM,
                         text_color=TEXT_PRIMARY, anchor="w").grid(row=row, column=1, sticky="nw", padx=5, pady=5)
            ctk.CTkLabel(scroll, text=cant_unidad, font=TEXT_SM,
                         text_color=TEXT_PRIMARY, anchor="w").grid(row=row, column=2, sticky="nw", padx=5, pady=5)
            ctk.CTkLabel(scroll, text=concepto, font=TEXT_SM, text_color=TEXT_PRIMARY,
                         anchor="w", justify="left", wraplength=760).grid(row=row, column=3, sticky="ew", padx=5, pady=5)
            previa = mapa_previas.get(
                (str(item.get("partida") or i), str(item.get("concepto") or "").strip().casefold()), {}
            )
            valor_previo = previa.get("costo_total", "") if isinstance(previa, dict) else ""
            precio_previo = previa.get("precio_unitario", "") if isinstance(previa, dict) else ""
            var_precio = ctk.StringVar(value=str(precio_previo) if precio_previo not in (None, "") else "")
            var_total = ctk.StringVar(value=str(valor_previo) if valor_previo not in (None, "") else "")

            actualizando_desde_precio = {"activo": False}

            def _recalcular_partida_desde_precio(*_, _item=item, _precio=var_precio, _total=var_total, _flag=actualizando_desde_precio):
                if _flag["activo"]:
                    return
                texto_precio = _precio.get().strip().replace(",", "")
                texto_cantidad = str(_item.get("cantidad") or "").strip().replace(",", "")
                if not texto_precio:
                    return
                try:
                    precio = float(texto_precio)
                    cantidad = float(texto_cantidad)
                except (TypeError, ValueError):
                    return
                if precio < 0 or cantidad < 0:
                    return
                _flag["activo"] = True
                try:
                    _total.set(f"{precio * cantidad:.2f}")
                finally:
                    _flag["activo"] = False
                recalcular_total()

            var_precio.trace_add("write", _recalcular_partida_desde_precio)
            var_total.trace_add("write", recalcular_total)
            ctk.CTkEntry(
                scroll, textvariable=var_precio, width=190, placeholder_text="0.00"
            ).grid(row=row, column=4, sticky="ew", padx=5, pady=5)
            ctk.CTkEntry(
                scroll, textvariable=var_total, width=165, placeholder_text="0.00"
            ).grid(row=row, column=5, sticky="ew", padx=5, pady=5)
            seleccion["entries"].append({
                "var": var_total, "precio_var": var_precio, "partida": item
            })

        btn_guardar.configure(state="normal")
        recalcular_total()

    def cargar_registro(registro):
        if not registro:
            return
        seleccion["registro"] = registro
        folio = _texto(registro, "lev_folio")
        cliente = _texto(registro, "lev_cliente")
        tipo = _texto(registro, "lev_tipo")
        detalle = registro.get("lev_detalle_tecnico_json")
        especialidad = ""
        if isinstance(detalle, dict):
            especialidad = str(detalle.get("tipo_levantamiento") or "").strip()
        elif isinstance(detalle, str):
            import json
            try:
                obj = json.loads(detalle) if detalle.strip() else {}
                especialidad = str(obj.get("tipo_levantamiento") or "").strip() if isinstance(obj, dict) else ""
            except Exception:
                pass
        lbl_titulo.configure(text=f"{folio} · {cliente}")
        lbl_detalle.configure(
            text=f"{especialidad or tipo} | Preautorizado por: {_texto(registro, 'lev_validado_por') or 'Operaciones'}"
        )
        render_partidas(registro)

    def cargar_seleccion():
        registro = tabla.selected_payload()
        if not registro:
            messagebox.showinfo("Selecciona un levantamiento", "Selecciona primero un levantamiento de la tabla.")
            return
        cargar_registro(registro)

    def filtrar_lista(*_):
        term = var_busqueda.get().strip().casefold()
        if not term:
            regs = list(registros_cache)
        else:
            regs = [r for r in registros_cache if term in " ".join([
                _texto(r, "lev_folio"), _texto(r, "lev_cliente"), _texto(r, "lev_tipo"),
                _texto(r, "lev_modalidad_operativa"),
            ]).casefold()]
        lbl_lista.configure(text=f"Levantamientos preautorizados ({len(regs)})")
        tabla.set_rows(regs, value_factory=lambda r: (
            _texto(r, "lev_folio"), _texto(r, "lev_cliente"),
            " / ".join(filter(None, [_texto(r, "lev_tipo"), _texto(r, "lev_modalidad_operativa")])),
            _texto(r, "lev_fecha_programada"),
        ))

    def refrescar():
        lbl_lista.configure(text="Consultando levantamientos preautorizados...")

        def ok(registros):
            registros_cache[:] = list(registros or [])
            filtrar_lista()
            if registros_cache:
                lbl_detalle.configure(text="Aquí aparecerán sus materiales, insumos, equipos y el costo del servicio.")
            else:
                lbl_detalle.configure(
                    text=(
                        "No hay levantamientos preautorizados en Supabase. "
                        "Los LEV validados antes de FIX10 no tenían aún la marca de preautorización; "
                        "valídalos una vez desde Levantamientos con el usuario autorizado (id=5)."
                    )
                )

        run_async(
            parent.winfo_toplevel(), obtener_levantamientos_para_cotizar, ok,
            lambda e: messagebox.showerror(
                "No fue posible abrir Cotizaciones",
                "Verifica que la migración de FIX10 ya fue ejecutada en Supabase.\n\n" + str(e),
            ),
        )

    def guardar_costos():
        registro = seleccion.get("registro")
        if not registro:
            return

        concepto_servicio = ""
        if seleccion.get("servicio_concepto") is not None:
            concepto_servicio = seleccion["servicio_concepto"].get().strip()
        if not concepto_servicio:
            messagebox.showwarning("Servicio pendiente", "Captura el concepto o descripción del servicio.")
            return

        valor_servicio = ""
        if seleccion.get("servicio_costo") is not None:
            valor_servicio = seleccion["servicio_costo"].get().strip().replace(",", "")
        if not valor_servicio:
            messagebox.showwarning("Servicio pendiente", "Captura el costo total del servicio antes de guardar.")
            return
        try:
            costo_servicio = float(valor_servicio)
        except ValueError:
            messagebox.showwarning("Costo inválido", "El costo del servicio debe ser un valor numérico.")
            return
        if costo_servicio < 0:
            messagebox.showwarning("Costo inválido", "El costo del servicio no puede ser negativo.")
            return

        partidas_guardar = []
        faltantes = []
        for info_entry in seleccion["entries"]:
            item = dict(info_entry["partida"])
            valor_precio = info_entry.get("precio_var").get().strip().replace(",", "") if info_entry.get("precio_var") is not None else ""
            valor = info_entry["var"].get().strip().replace(",", "")
            if not valor_precio or not valor:
                faltantes.append(str(item.get("partida") or "?"))
                continue
            try:
                precio_unitario = float(valor_precio)
                costo = float(valor)
            except ValueError:
                messagebox.showwarning(
                    "Costo inválido",
                    f"La partida {item.get('partida')} contiene un precio unitario o costo total no numérico."
                )
                return
            if precio_unitario < 0 or costo < 0:
                messagebox.showwarning("Costo inválido", "Los precios y costos no pueden ser negativos.")
                return
            item["precio_unitario"] = precio_unitario
            item["costo_total"] = costo
            partidas_guardar.append(item)

        if faltantes:
            messagebox.showwarning(
                "Costos pendientes",
                "Captura el precio unitario y el costo total de todas las partidas antes de guardar.\n\nPartidas pendientes: " + ", ".join(faltantes),
            )
            return

        total_materiales = sum(float(x.get("costo_total") or 0) for x in partidas_guardar)
        total_estimado = total_materiales + costo_servicio
        if not messagebox.askyesno(
            "Guardar cotización",
            (
                f"Se guardarán los costos de {_texto(registro, 'lev_folio')} en Supabase.\n\n"
                f"Materiales/equipos: ${total_materiales:,.2f} MXN\n"
                f"Servicio: ${costo_servicio:,.2f} MXN\n"
                f"TOTAL: ${total_estimado:,.2f} MXN\n\n¿Continuar?"
            ),
        ):
            return

        btn_guardar.configure(state="disabled")
        usuario_nombre = str(
            (usuario or {}).get("usuario") or (usuario or {}).get("usu_nickname") or "Ventas"
        )

        def ok(cotizacion):
            registro["lev_cotizacion_json"] = cotizacion
            btn_guardar.configure(state="normal")
            recalcular_total()
            messagebox.showinfo(
                "Cotización guardada",
                (
                    f"Los costos de {_texto(registro, 'lev_folio')} se guardaron correctamente.\n\n"
                    f"Total materiales/equipos: ${float(cotizacion.get('total_partidas') or 0):,.2f} MXN\n"
                    f"Servicio: ${float((cotizacion.get('servicio') or {}).get('costo_total') or 0):,.2f} MXN\n"
                    f"Total general: ${float(cotizacion.get('total_general') or 0):,.2f} MXN"
                ),
            )

        run_async(
            parent.winfo_toplevel(),
            lambda: guardar_cotizacion_levantamiento(
                registro,
                partidas_guardar,
                usuario_nombre,
                servicio={"concepto": concepto_servicio, "costo_total": costo_servicio},
            ),
            ok,
            lambda e: (
                btn_guardar.configure(state="normal"),
                messagebox.showerror("No fue posible guardar", str(e)),
            ),
        )

    ctk.CTkButton(
        cabecera, text="🔎 Buscar", width=125, height=40, fg_color=SECONDARY,
        hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=filtrar_lista,
    ).grid(row=2, column=1, padx=4, pady=(0, 10))
    ctk.CTkButton(
        cabecera, text="↻ Actualizar", width=125, height=40, fg_color="#334155",
        hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=refrescar,
    ).grid(row=2, column=2, padx=(0, 14), pady=(0, 10))
    entrada_busqueda.bind("<Return>", lambda _e: filtrar_lista())
    btn_guardar.configure(command=guardar_costos)

    ctk.CTkButton(
        bandeja, text="📥 Cargar seleccionado", height=38, font=BUTTON_FONT,
        command=cargar_seleccion,
    ).grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))

    refrescar()
