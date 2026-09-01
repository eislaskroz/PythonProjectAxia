"""Compatibilidad de levantamientos entre AXIA Desktop y AXIA FIELD.

Normaliza registros históricos/móviles sin modificar Supabase. La salida conserva
las claves originales y agrega únicamente metadatos/aliases necesarios para que
Desktop pueda identificar el formulario, restaurar campos y usar AXIA PDF Engine.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any, Mapping

TIPO_POR_CODIGO = {
    1: "Seguridad y Monitoreo",
    2: "Redes Voz y Datos",
    3: "Control de Accesos",
    4: "Enlaces Inalámbricos",
    5: "Tecnología, Equipos y Periféricos",
    6: "Electricidad",
    7: "Paneles Solares",
    8: "Plantas de Energía",
    9: "Obra Civil",
    10: "Aires Acondicionados",
}

PREFIXES = ("sec_", "cctv_", "rvd_", "aa_", "pe_", "power_plant_", "ele_", "electric_", "control_", "wireless_", "technology_", "solar_", "obra_", "air_")
TYPE_PREFIXES = {
    "Seguridad y Monitoreo": ("sec_", "cctv_"),
    "Redes Voz y Datos": ("rvd_",),
    "Control de Accesos": ("control_",),
    "Enlaces Inalámbricos": ("wireless_",),
    "Tecnología, Equipos y Periféricos": ("technology_",),
    "Electricidad": ("electric_", "ele_"),
    "Paneles Solares": ("solar_",),
    "Plantas de Energía": ("power_plant_", "pe_"),
    "Obra Civil": ("obra_", "civil_"),
    "Aires Acondicionados": ("air_", "aa_"),
}
RESTORE_ALIAS = {
    "requiere_calculo":"requiere_calculo_termico", "marca_modelo":"marca_modelo_sugerido",
    "alimentacion_disponible":"alimentacion_electrica_disponible", "breaker_disponible":"breaker_proteccion_disponible",
    "perforaciones":"requiere_perforaciones", "ruta_tuberia":"ruta_tuberia_canaleta",
    "tuberia_cobre_m":"tuberia_cobre_metros", "cableado_m":"cableado_electrico_metros",
    "drenaje_m":"drenaje_metros", "canaleta_m":"canaleta_metros", "requiere_permiso":"requiere_permiso_sitio",
    "requiere_escalera":"requiere_escalera_andamio", "proteccion_area":"proteger_area",
    "limpieza_entrega":"entrega_limpia", "cantidad_nodos":"cantidad_nodos_datos",
    "cantidad_telefonia":"cantidad_puntos_voz", "acceso":"acceso_instalacion", "riesgo":"nivel_riesgo",
    "ubicacion_rack":"ubicacion_rack_gabinete", "detalle_contacto":"detalle_contacto_regulado",
    "detalle_tierra":"detalle_tierra_fisica", "capacidad":"capacidad_estimada",
    "maniobra":"requiere_maniobra_grua", "permisos":"requiere_permisos",
    "tanque":"tipo_tanque", "autonomia":"autonomia_estimada", "ruta_escape":"ruta_escape_gases",
    "protecciones":"protecciones_electricas", "entrega_manual":"entrega_manual_capacitacion",
    "area":"area_trabajo", "carga_estimacion":"carga_estimada", "desenergizar":"requiere_desenergizar",
    "prueba_voltaje":"medicion_voltaje", "etiquetado":"etiquetado_circuitos",
}


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return deepcopy(parsed) if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _slug_title(text: str) -> str:
    text = re.sub(r"^[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]*\d+\.\s*", "", str(text or "")).strip()
    return text.lower().replace(" ", "_").replace(",", "").replace("/", "_")


def _infer_tipo(registro: Mapping[str, Any], detalle: Mapping[str, Any]) -> str:
    direct = str(registro.get("lev_tipo_levantamiento") or detalle.get("tipo_levantamiento") or "").strip()
    if direct:
        return direct
    try:
        return TIPO_POR_CODIGO.get(int(registro.get("lev_tipo")), "")
    except Exception:
        return ""


def _add_mobile_aliases(detail: dict[str, Any]) -> None:
    compat: dict[str, Any] = {}
    for key, value in list(detail.items()):
        if isinstance(value, (dict, list, tuple)) or value in (None, ""):
            continue
        raw = str(key)
        stripped = raw
        for prefix in PREFIXES:
            if raw.startswith(prefix):
                stripped = raw[len(prefix):]
                break
        compat.setdefault(stripped, value)
        compat.setdefault(RESTORE_ALIAS.get(stripped, stripped), value)
    if compat:
        existing = detail.get("compatibilidad_axia_field")
        if isinstance(existing, dict):
            existing.update({k: v for k, v in compat.items() if k not in existing})
        else:
            detail["compatibilidad_axia_field"] = compat


def _build_declarative_sections(tipo: str, detail: dict[str, Any]) -> None:
    if isinstance(detail.get("secciones"), dict):
        return
    try:
        from views.levantamientos.form_definitions import FORMULARIOS_DETALLADOS_EXTRA
    except Exception:
        return
    form = FORMULARIOS_DETALLADOS_EXTRA.get(tipo)
    if not form:
        return
    sections: dict[str, dict[str, Any]] = {}
    for title, fields in form.get("secciones", []):
        values = {}
        for key, _kind, label, *_rest in fields:
            candidates = (key,) + tuple(f"{prefix}{key}" for prefix in TYPE_PREFIXES.get(tipo, ()))
            source_key = next((candidate for candidate in candidates if detail.get(candidate) not in (None, "")), None)
            if source_key:
                # Usar la etiqueta oficial como clave evita que el PDF tenga que
                # adivinar textos a partir de identificadores técnicos.
                values[label] = detail.get(source_key)
        if values:
            sections[_slug_title(title)] = values
    if sections:
        detail["secciones"] = sections


def _build_classic_sections(tipo: str, detail: dict[str, Any]) -> None:
    """Crea secciones legibles para PDF a partir del payload plano de FIELD.

    No reemplaza estructuras Desktop existentes; solo actúa si FIELD guardó un mapa plano.
    """
    if isinstance(detail.get("secciones"), dict):
        return
    flat = {k: v for k, v in detail.items() if not isinstance(v, (dict, list, tuple)) and v not in (None, "")}
    flat = {k: v for k, v in flat.items() if not str(k).startswith("datos_generales_") and k not in {"tipo_levantamiento", "modalidad_operativa"}}
    if not flat:
        return
    prefix = {
        "Seguridad y Monitoreo": ("sec_", "Datos técnicos Seguridad y Monitoreo"),
        "Redes Voz y Datos": ("rvd_", "Datos de Redes Voz y Datos"),
        "Aires Acondicionados": ("aa_", "Datos de Aires Acondicionados"),
        "Plantas de Energía": ("power_plant_", "Datos de Plantas de Energía"),
        "Electricidad": ("electric_", "Datos de Electricidad"),
    }.get(tipo)
    if not prefix:
        return
    pfx, title = prefix
    values = {}
    extra = {}
    for key, value in flat.items():
        if re.search(r"_(?:equipment|misc|damaged|material|tool|epp)_?\d+_", str(key)) or str(key).endswith("_count"):
            continue
        if str(key).startswith(pfx):
            values[str(key)[len(pfx):]] = value
        elif tipo == "Seguridad y Monitoreo" and key in {
            "modalidad", "infra_existe", "infra_tipo", "infra_estado", "infra_observaciones",
            "rack_requerido", "gabinete_requerido", "ups_requerida", "contacto_regulado",
            "tierra_fisica", "escalera_requerida", "altura_trabajo", "riesgo_instalacion",
        }:
            extra[key] = value
    sections = {}
    if tipo == "Seguridad y Monitoreo" and extra:
        infra = {k: v for k, v in extra.items() if k.startswith("infra_") or k == "modalidad"}
        energia = {k: v for k, v in extra.items() if k not in infra}
        if infra: sections["modalidad_e_infraestructura"] = infra
        if values: sections["datos_técnicos_cctv"] = values
        if energia: sections["rack_energía_y_seguridad"] = energia
    elif values:
        sections[_slug_title(title)] = values
    if sections:
        detail["secciones"] = sections


def _indexed_rows(detail: Mapping[str, Any], prefix: str, fields: tuple[str, ...]) -> list[dict[str, Any]]:
    """Reconstruye las filas repetibles que FIELD persiste como claves planas."""
    count_value = detail.get(f"{prefix}_count")
    if prefix == "common_tool":
        count_value = count_value or detail.get("common_tools_count")
    try:
        count = max(0, int(str(count_value))) if count_value not in (None, "") else -1
    except (TypeError, ValueError):
        count = -1
    if count < 0:
        indexes = [int(m.group(1)) for key in detail for m in [re.match(rf"^{re.escape(prefix)}_(\d+)_", str(key))] if m]
        count = max(indexes, default=-1) + 1
    rows: list[dict[str, Any]] = []
    for index in range(count):
        row = {field: detail.get(f"{prefix}_{index}_{field}") for field in fields}
        if any(value not in (None, "") for value in row.values()):
            rows.append(row)
    return rows


def _build_mobile_dynamic_rows(detail: dict[str, Any]) -> None:
    equipment: list[dict[str, Any]] = []
    materials: list[dict[str, Any]] = []
    for prefix in ("sec_equipment", "rvd_equipment", "control_equipment", "wireless_equipment", "technology_equipment", "electric_equipment", "solar_equipment", "power_plant_equipment", "air_equipment"):
        for row in _indexed_rows(detail, prefix, ("family", "subfamily", "quantity", "brand", "model", "features")):
            equipment.append({
                "familia": row.get("family"), "subfamilia": row.get("subfamily"),
                "cantidad": row.get("quantity"), "marca": row.get("brand"),
                "modelo": row.get("model"), "caracteristicas": row.get("features"),
            })
    if equipment and not detail.get("equipos_principales"):
        detail["equipos_principales"] = equipment

    for prefix in ("sec_misc", "rvd_misc", "control_misc", "wireless_misc", "technology_misc", "electric_misc", "solar_misc", "power_plant_misc", "air_misc", "civil_misc"):
        for row in _indexed_rows(detail, prefix, ("material", "quantity", "unit", "specification")):
            materials.append({
                "material": row.get("material"), "cantidad": row.get("quantity"),
                "unidad": row.get("unit"), "especificacion": row.get("specification"),
            })
    if materials and not detail.get("materiales_miscelaneos"):
        detail["materiales_miscelaneos"] = materials

    canal = []
    for row in _indexed_rows(detail, "common_material", ("category", "type", "size", "quantity", "unit")):
        canal.append({
            "categoria": row.get("category"), "tipo": row.get("type"),
            "tamano_calibre_especificacion": row.get("size"),
            "cantidad": row.get("quantity"), "unidad": row.get("unit"),
        })
    if canal and not detail.get("canalizacion_materiales"):
        detail["canalizacion_materiales"] = canal

    epp_rows = []
    for row in _indexed_rows(detail, "common_epp", ("name", "quantity", "notes")):
        epp_rows.append({"epp": row.get("name"), "cantidad": row.get("quantity"), "observaciones": row.get("notes")})
    if epp_rows and not detail.get("epp"):
        detail["epp"] = {"requiere": detail.get("common_epp_required") or "Sí", "partidas": epp_rows}

    tools = []
    for row in _indexed_rows(detail, "common_tool", ("category", "name", "quantity", "notes")):
        tools.append({"categoria": row.get("category"), "herramienta": row.get("name"), "cantidad": row.get("quantity"), "observaciones": row.get("notes")})
    if tools and not detail.get("herramientas"):
        detail["herramientas"] = tools

    damaged = []
    for row in _indexed_rows(detail, "sec_damaged", ("type", "brand", "model", "serial")):
        damaged.append({"tipo": row.get("type"), "marca": row.get("brand"), "modelo": row.get("model"), "serie": row.get("serial")})
    if damaged and not detail.get("equipos_danados"):
        detail["equipos_danados"] = damaged

    if not isinstance(detail.get("recursos_proyectados"), Mapping):
        resources = {
            "¿Proyecto de un día o varios días?": detail.get("common_project_duration"),
            "Horas estimadas": detail.get("common_estimated_hours"),
            "Días estimados": detail.get("common_estimated_days"),
            "Personas estimadas": detail.get("common_people"),
        }
        resources = {key: value for key, value in resources.items() if value not in (None, "")}
        if resources:
            detail["recursos_proyectados"] = resources


def _build_security_sections(detail: dict[str, Any]) -> None:
    """Convierte las claves `sec_*` al contrato histórico del PDF Desktop."""
    def block(mapping: Mapping[str, str]) -> dict[str, Any]:
        return {target: detail.get(source) for source, target in mapping.items() if detail.get(source) not in (None, "")}

    sections = {
        "infraestructura_existente": block({
            "sec_infra_exists": "existe_infraestructura",
            "sec_infra_type": "tipo_infraestructura_existente",
            "sec_infra_state": "estado_general",
        }),
        "rack_gabinete_energia": block({
            "sec_rack_required": "rack_requerido", "sec_rack_size": "tipo_rack",
            "sec_rack_vertical": "rack_organizadores_verticales", "sec_rack_horizontal": "rack_organizadores_horizontales",
            "sec_rack_trays": "rack_charolas", "sec_rack_pdu": "rack_pdu",
            "sec_cabinet_required": "gabinete_requerido", "sec_cabinet_type": "tipo_gabinete",
            "sec_ups_required": "ups_requerida", "sec_ups_type": "tipo_ups",
            "sec_regulated_required": "contacto_regulado", "sec_regulated_detail": "detalle_contacto_regulado",
            "sec_ground_required": "tierra_fisica", "sec_ground_detail": "detalle_tierra_fisica",
        }),
        "acceso_alturas_riesgos": block({
            "sec_height_work": "trabajo_alturas", "sec_temp_access": "sistema_acceso_temporal",
            "sec_height": "altura_trabajo", "sec_risk": "riesgo_instalacion",
        }),
        "datos_tecnicos_cctv": block({
            "sec_camera_count": "cantidad_camaras", "sec_camera_type": "tipo_camaras",
            "sec_recorder_location": "ubicacion_nvr_dvr", "sec_network_point": "punto_red",
            "sec_power_point": "punto_energia",
        }),
        "ubicacion_estado_sintomas": block({
            "sec_repair_location": "ubicacion_equipos", "sec_repair_access": "acceso_equipos",
            "sec_repair_state": "estado", "sec_repair_error": "codigo_error_dvr_nvr",
            "sec_repair_schedule": "horario_falla", "sec_repair_infrastructure": "descripcion_infraestructura",
        }),
    }
    for name, values in sections.items():
        if values and not isinstance(detail.get(name), Mapping):
            detail[name] = values
    if detail.get("sec_repair_target") and not detail.get("elemento_a_reparar"):
        detail["elemento_a_reparar"] = detail["sec_repair_target"]
    if detail.get("sec_repair_description") and not detail.get("descripcion_general_fallas"):
        detail["descripcion_general_fallas"] = detail["sec_repair_description"]
    if detail.get("sec_service_description") and not detail.get("mantenimiento"):
        detail["mantenimiento"] = {"descripcion_detallada_servicio": detail["sec_service_description"]}

    material_labels = {
        "sec_rack_vertical": ("Rack", "Organizadores verticales"),
        "sec_rack_horizontal": ("Rack", "Organizadores horizontales"),
        "sec_rack_trays": ("Rack", "Charolas"), "sec_rack_pdu": ("Rack", "PDU"),
        "sec_ground_bar": ("Tierra física", "Barra de cobre"),
        "sec_ground_insulators": ("Tierra física", "Aisladores de cobre"),
        "sec_ground_omega": ("Tierra física", "Abrazadera/Omega"),
        "sec_ground_rod": ("Tierra física", "Varilla de cobre"),
        "sec_ground_clamps": ("Tierra física", "Abrazaderas de cobre"),
        "sec_ground_cable": ("Tierra física", "Cable de cobre"),
        "sec_ground_screws": ("Tierra física", "Tornillos de cobre"),
        "sec_ground_chemical": ("Tierra física", "Químico"),
        "sec_ground_pipe": ("Tierra física", "Tubería"),
        "sec_ground_box": ("Tierra física", "Bote/Registro"),
    }
    rack_materials = []
    for key, (category, material) in material_labels.items():
        if detail.get(key) not in (None, ""):
            rack_materials.append({"categoria": category, "material": material, "cantidad": detail[key], "unidad": "Según captura", "especificacion": ""})
    if rack_materials and not detail.get("materiales_rack_tierra"):
        detail["materiales_rack_tierra"] = rack_materials


def normalizar_registro_levantamiento(registro: Mapping[str, Any] | None) -> dict[str, Any]:
    out = deepcopy(dict(registro or {}))
    detail = _json_dict(out.get("lev_detalle_tecnico_json"))
    tipo = _infer_tipo(out, detail)
    if tipo:
        out["lev_tipo_levantamiento"] = tipo
        detail.setdefault("tipo_levantamiento", tipo)

    # AXIA FIELD guarda modalidad como `modalidad` en algunos formularios.
    stored_modalidad = str(out.get("lev_modalidad_operativa") or "").strip()
    if stored_modalidad in {"NEW_CLIENT", "EXISTING_CLIENT", "EXISTING_ACO"}:
        stored_modalidad = ""
    modalidad = str(detail.get("sec_work_type") or detail.get("modalidad_operativa") or detail.get("modalidad") or stored_modalidad or "Instalación").strip()
    if modalidad:
        out["lev_modalidad_operativa"] = modalidad
        detail.setdefault("modalidad_operativa", modalidad)

    _add_mobile_aliases(detail)
    _build_mobile_dynamic_rows(detail)
    if tipo == "Seguridad y Monitoreo":
        _build_security_sections(detail)
    _build_declarative_sections(tipo, detail)
    _build_classic_sections(tipo, detail)
    out["lev_detalle_tecnico_json"] = detail
    return out
