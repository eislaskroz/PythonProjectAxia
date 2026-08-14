"""PDFs corporativos para Órdenes de Servicio y Órdenes de Trabajo.

Ambos documentos usan la plantilla fija de AXIA mediante ``formato_helpers``.
La vista previa y el archivo definitivo reciben exactamente el mismo contrato.
"""
from __future__ import annotations

import json
from views.formato_helpers import generar_pdf_preview, generar_pdf_archivo
from services.ordenes_trabajo_schema import extract_origin, visible_partidas, partidas_desde_detalle_levantamiento


def _json_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else ([parsed] if isinstance(parsed, dict) else [])
    except Exception:
        return []



def _dividir_texto_largo(valor, limite=180):
    """Divide textos largos sin cortar palabras para que una fila pueda paginarse.

    ReportLab no puede partir una sola fila de tabla entre páginas. Al dividir el
    concepto en filas de continuación, cada fragmento cabe dentro del marco y la
    tabla puede continuar normalmente en la página siguiente.
    """
    texto = str(valor or "").strip()
    if not texto:
        return [""]
    partes = []
    restante = texto
    while len(restante) > limite:
        corte = restante.rfind(" ", 0, limite)
        if corte < limite // 2:
            corte = limite
        partes.append(restante[:corte].strip())
        restante = restante[corte:].strip()
    if restante or not partes:
        partes.append(restante)
    return partes


def contrato_orden_servicio(registro):
    r = dict(registro or {})
    datos = {
        "Folio OS": r.get("os_folio", ""),
        "Fecha": r.get("os_fecha") or r.get("os_fecha_programada") or r.get("fecha_registro") or "",
        "Levantamiento origen": r.get("os_folio_levantamiento", ""),
        "ACO": r.get("os_aco_numero", ""),
        "Cliente": r.get("os_cliente", ""),
        "Sucursal": r.get("os_sucursal") or r.get("os_ubicacion", ""),
        "Domicilio": r.get("os_domicilio") or r.get("os_direccion", ""),
        "Encargado": r.get("os_encargado") or r.get("os_contacto", ""),
        "Solicitante": r.get("os_solicitante", ""),
        "Correo": r.get("os_correo", ""),
        "Celular": r.get("os_celular") or r.get("os_telefono", ""),
        "Tipo de Servicio": r.get("os_tipo_servicio", ""),
        "Supervisor": r.get("os_supervisor", ""),
        "Encargado Servicio": r.get("os_encargado_servicio", ""),
        "Técnicos": r.get("os_tecnicos") or r.get("os_tecnico", ""),
        "Descripción": r.get("os_descripcion", ""),
        "Actividades": r.get("os_actividades", ""),
        "Materiales": r.get("os_materiales", ""),
        "Observaciones": r.get("os_observaciones", ""),
        "Hora de llegada": r.get("os_hora_llegada", ""),
        "Hora de salida": r.get("os_hora_salida", ""),
        "Evaluación habilidades": r.get("os_eval_habilidades", ""),
        "Evaluación trato": r.get("os_eval_trato", ""),
        "Evaluación velocidad": r.get("os_eval_velocidad", ""),
        "Evaluación otro": r.get("os_eval_otro", ""),
        "Evidencia Fotográfica": r.get("os_fotos") or [],
    }
    equipos = []
    for item in _json_list(r.get("os_equipos_json")):
        equipos.append({
            "Equipo": item.get("equipo") or item.get("tipo_equipo") or item.get("Equipo", ""),
            "Número de Serie": item.get("numero_serie") or item.get("serie") or item.get("Número de Serie", ""),
            "Movimiento": item.get("movimiento") or item.get("Movimiento", ""),
            "Diagnóstico de la Falla": item.get("diagnostico_falla") or item.get("diagnostico") or item.get("Diagnóstico de la Falla", ""),
        })
    secciones = []
    if equipos:
        secciones.append(("Entrada / salida de equipos", ["Equipo", "Número de Serie", "Movimiento", "Diagnóstico de la Falla"], equipos))
    return datos, secciones


def preview_orden_servicio(registro):
    datos, secciones = contrato_orden_servicio(registro)
    return generar_pdf_preview(
        "Orden de Servicio",
        datos,
        secciones_tabla=secciones,
        firma_base64=(registro or {}).get("os_firma_cliente"),
        mostrar_firmas=True,
    )


def guardar_pdf_orden_servicio(registro):
    datos, secciones = contrato_orden_servicio(registro)
    return generar_pdf_archivo(
        "Orden de Servicio", datos,
        nombre_archivo=(registro or {}).get("os_folio") or "Orden_Servicio",
        subcarpeta="ordenes_servicio",
        secciones_tabla=secciones,
        firma_base64=(registro or {}).get("os_firma_cliente"),
        mostrar_firmas=True,
    )


def contrato_orden_trabajo(registro):
    r = dict(registro or {})
    datos = {
        "Folio OT": r.get("ot_folio", ""),
        "Fecha": r.get("ot_fecha") or r.get("ot_fecha_programada") or r.get("fecha_registro") or "",
        "Orden de Servicio origen": extract_origin(r.get("ot_partidas_json")),
        "ACO": r.get("ot_aco_numero", ""),
        "Cliente": r.get("ot_cliente", ""),
        "Contacto": r.get("ot_contacto", ""),
        "Sucursal": r.get("ot_sucursal", ""),
        "Jefe de Operación": r.get("ot_jefe_operacion", ""),
        "Supervisor": r.get("ot_supervisor", ""),
        "ESI": r.get("ot_esi", ""),
        "Técnico / responsable": r.get("ot_esi", ""),
        "Número de Días": r.get("ot_numero_dias", ""),
        "Número de Personas": r.get("ot_numero_personas", ""),
        "Asunto": r.get("ot_asunto") or r.get("ot_descripcion", ""),
        "Descripción": r.get("ot_descripcion", ""),
    }
    # Para OTs creadas desde un levantamiento, la tabla del PDF debe contener
    # materiales/equipos/consumibles reales, no el texto narrativo completo del LEV.
    # Las OTs antiguas pueden traer solo uno o dos renglones gigantes en
    # ot_partidas_json; intentamos reconstruir sus partidas desde el LEV origen.
    origen_rows = []
    folio_lev = str(r.get("ot_folio_levantamiento") or extract_origin(r.get("ot_partidas_json"), "lev") or "").strip().upper()
    if folio_lev:
        try:
            from services.levantamientos_service import buscar_levantamiento_por_folio
            lev = buscar_levantamiento_por_folio(folio_lev) or {}
            origen_rows = partidas_desde_detalle_levantamiento(lev.get("lev_detalle_tecnico_json"))
        except Exception:
            # El PDF debe seguir siendo generable aunque Supabase no esté disponible
            # temporalmente; en ese caso se usa la información ya guardada en la OT.
            origen_rows = []

    source_rows = origen_rows or visible_partidas(r.get("ot_partidas_json"))

    # Compatibilidad con OTs antiguas: versiones previas podían guardar el
    # resumen completo del levantamiento como una fila ``Servicio``. Esa fila
    # nunca debe aparecer en PARTIDAS / MATERIALES / EQUIPOS. Solo conservamos
    # renglones con forma de material/equipo/misceláneo real.
    def _es_partida_operativa(item):
        if not isinstance(item, dict):
            return False
        unidad = str(item.get("unidad") or item.get("Unidad") or "").strip().casefold()
        concepto = str(item.get("concepto") or item.get("Concepto") or "").strip()
        if unidad == "servicio":
            return False
        if concepto.startswith("--- LEVANTAMIENTO") or "Tipo de solicitud y alcance" in concepto:
            return False
        return bool(
            concepto and (
                item.get("cantidad") not in (None, "") or item.get("Cantidad") not in (None, "") or
                item.get("marca") not in (None, "") or item.get("Marca") not in (None, "") or
                item.get("modelo") not in (None, "") or item.get("Modelo") not in (None, "") or
                unidad
            )
        )

    source_rows = [item for item in source_rows if _es_partida_operativa(item)]
    partidas = []
    for item in source_rows:
        base = {
            "Partida": item.get("partida") or item.get("part.") or item.get("Partida", ""),
            "Unidad": item.get("unidad") or item.get("Unidad", ""),
            "Cantidad": item.get("cantidad") or item.get("Cantidad", ""),
            "Modelo": item.get("modelo") or item.get("Modelo", ""),
            "Marca": item.get("marca") or item.get("Marca", ""),
            "_Grupo": item.get("_grupo") or item.get("grupo") or item.get("Grupo") or ("Equipos" if (item.get("marca") or item.get("Marca") or item.get("modelo") or item.get("Modelo")) else "Materiales"),
        }
        fragmentos = _dividir_texto_largo(item.get("concepto") or item.get("Concepto", ""))
        for indice, fragmento in enumerate(fragmentos):
            fila = dict(base) if indice == 0 else {clave: "" for clave in base}
            fila["Concepto"] = fragmento
            partidas.append(fila)
    # El PDF de OT presenta tres tablas independientes para lectura operativa:
    # MATERIALES, EQUIPOS y MISCELÁNEOS / CONSUMIBLES.
    grupos = {"Materiales": [], "Equipos": [], "Misceláneos": []}
    for fila in partidas:
        grupo = str(fila.pop("_Grupo", "Materiales") or "Materiales").strip().casefold()
        if "equipo" in grupo:
            grupos["Equipos"].append(fila)
        elif "miscel" in grupo or "consum" in grupo:
            grupos["Misceláneos"].append(fila)
        else:
            grupos["Materiales"].append(fila)

    secciones = []
    headers = ["Partida", "Unidad", "Cantidad", "Modelo", "Marca", "Concepto"]
    if grupos["Materiales"]:
        secciones.append(("Materiales", headers, grupos["Materiales"]))
    if grupos["Equipos"]:
        secciones.append(("Equipos", headers, grupos["Equipos"]))
    if grupos["Misceláneos"]:
        secciones.append(("Misceláneos / consumibles", headers, grupos["Misceláneos"]))
    return datos, secciones


def preview_orden_trabajo(registro):
    datos, secciones = contrato_orden_trabajo(registro)
    return generar_pdf_preview("Orden de Trabajo", datos, secciones_tabla=secciones, mostrar_firmas=True)


def guardar_pdf_orden_trabajo(registro):
    datos, secciones = contrato_orden_trabajo(registro)
    return generar_pdf_archivo(
        "Orden de Trabajo", datos,
        nombre_archivo=(registro or {}).get("ot_folio") or "Orden_Trabajo",
        subcarpeta="ordenes_trabajo",
        secciones_tabla=secciones,
        mostrar_firmas=True,
    )
