from pathlib import Path

from services.levantamiento_compat import normalizar_registro_levantamiento
from services.levantamiento_seguridad_pdf import generar_pdf_levantamiento_maestro


def mobile_security_record():
    return {
        "lev_folio": "LEV-90001",
        "lev_tipo": 1,
        "lev_tipo_levantamiento": "Seguridad y Monitoreo",
        "lev_modalidad_operativa": "EXISTING_CLIENT",
        "lev_cliente": "CLIENTE FIELD",
        "lev_descripcion": "Instalación de cámaras IP.",
        "lev_observaciones": "Observación final.",
        "lev_detalle_tecnico_json": {
            "sec_work_type": "Instalación",
            "sec_infra_exists": "Sí", "sec_infra_type": "Canalización", "sec_infra_state": "Bueno",
            "sec_rack_required": "Sí", "sec_rack_size": "24U",
            "sec_height_work": "Sí", "sec_temp_access": "Escalera", "sec_height": "3", "sec_risk": "Bajo",
            "sec_camera_count": "20", "sec_camera_type": "IP", "sec_recorder_location": "SITE",
            "sec_network_point": "Rack", "sec_power_point": "Contacto regulado",
            "sec_equipment_count": "1", "sec_equipment_0_family": "Cámara", "sec_equipment_0_subfamily": "Domo",
            "sec_equipment_0_quantity": "20", "sec_equipment_0_brand": "Por definir", "sec_equipment_0_model": "IP",
            "sec_misc_count": "1", "sec_misc_0_material": "Conector RJ45", "sec_misc_0_quantity": "20",
            "sec_misc_0_unit": "Pieza(s)", "sec_misc_0_specification": "Cat6",
            "common_tools_count": "1", "common_tool_0_category": "Seguridad y Monitoreo",
            "common_tool_0_name": "Tester PoE", "common_tool_0_quantity": "1",
            "common_epp_required": "Sí", "common_epp_count": "1", "common_epp_0_name": "Casco de seguridad",
            "common_epp_0_quantity": "1", "common_epp_0_notes": "Clase E",
        },
    }


def test_mobile_flat_payload_is_rebuilt_for_desktop_pdf():
    out = normalizar_registro_levantamiento(mobile_security_record())
    detail = out["lev_detalle_tecnico_json"]
    assert out["lev_modalidad_operativa"] == "Instalación"
    assert detail["datos_tecnicos_cctv"]["cantidad_camaras"] == "20"
    assert detail["equipos_principales"][0]["familia"] == "Cámara"
    assert detail["materiales_miscelaneos"][0]["material"] == "Conector RJ45"
    assert detail["herramientas"][0]["herramienta"] == "Tester PoE"
    assert detail["epp"]["partidas"][0]["epp"] == "Casco de seguridad"


def test_mobile_security_uses_desktop_master_pdf(tmp_path):
    output = tmp_path / "field-security.pdf"
    generar_pdf_levantamiento_maestro(mobile_security_record(), ruta_salida=output, abrir=False)
    assert Path(output).is_file()
    from pypdf import PdfReader
    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(output)).pages)
    for expected in ("20", "Cámara", "Conector RJ45", "Tester PoE", "Casco de seguridad", "Instalación de cámaras IP"):
        assert expected.casefold() in text.casefold()
