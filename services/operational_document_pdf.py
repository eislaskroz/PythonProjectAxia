"""PDFs corporativos para Órdenes de Servicio y Órdenes de Trabajo.

Ambos documentos usan la plantilla fija de AXIA mediante ``formato_helpers``.
La vista previa y el archivo definitivo reciben exactamente el mismo contrato.
"""
from __future__ import annotations

import json
from views.formato_helpers import generar_pdf_preview, generar_pdf_archivo
from services.ordenes_trabajo_schema import extract_origin, visible_partidas


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
    partidas = []
    for item in visible_partidas(r.get("ot_partidas_json")):
        base = {
            "Partida": item.get("partida") or item.get("part.") or item.get("Partida", ""),
            "Unidad": item.get("unidad") or item.get("Unidad", ""),
            "Cantidad": item.get("cantidad") or item.get("Cantidad", ""),
            "Modelo": item.get("modelo") or item.get("Modelo", ""),
            "Marca": item.get("marca") or item.get("Marca", ""),
        }
        fragmentos = _dividir_texto_largo(item.get("concepto") or item.get("Concepto", ""))
        for indice, fragmento in enumerate(fragmentos):
            fila = dict(base) if indice == 0 else {clave: "" for clave in base}
            fila["Concepto"] = fragmento
            partidas.append(fila)
    secciones = []
    if partidas:
        secciones.append(("Partidas / conceptos", ["Partida", "Unidad", "Cantidad", "Modelo", "Marca", "Concepto"], partidas))
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
