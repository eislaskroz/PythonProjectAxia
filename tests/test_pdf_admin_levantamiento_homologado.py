import json
from pathlib import Path

from services.levantamiento_seguridad_pdf import generar_pdf_levantamiento_maestro


def _registro_base():
    detalle = {
        "tipo_levantamiento": "Redes Voz y Datos",
        "modalidad_operativa": "Instalación",
        "secciones": {
            "necesidad_alcance": {"necesidad": "Instalación nueva", "tipo_servicio": "Datos"},
        },
        "equipos_principales": [],
        "materiales_miscelaneos": [],
        "canalizacion_materiales": [],
    }
    return {
        "lev_folio": "LEV-00006",
        "lev_cliente": "CLIENTE TEST",
        "lev_contacto": "CONTACTO",
        "lev_correo": "contacto@example.com",
        "lev_direccion": "DOMICILIO TEST",
        "lev_tecnico": "TECNICO",
        "lev_supervisor": "SUPERVISOR",
        "lev_fecha_programada": "2026-08-26",
        "lev_modalidad_operativa": "Instalación",
        "lev_descripcion": "Descripción",
        "lev_observaciones": "Observaciones",
        "lev_detalle_tecnico_json": json.dumps(detalle, ensure_ascii=False),
    }


def test_registro_supabase_sin_alias_de_tipo_usa_misma_especialidad(tmp_path):
    # Simula el registro recuperado por Administración: la tabla usa lev_tipo
    # como código y la especialidad real está en el detalle técnico.
    registro = _registro_base()
    registro["lev_tipo"] = 3
    out = tmp_path / "admin.pdf"
    generar_pdf_levantamiento_maestro(registro, ruta_salida=out, abrir=False)
    data = out.read_bytes()
    assert out.exists() and len(data) > 1000


def test_conversion_admin_previsualiza_levantamiento_con_motor_comun():
    source = Path("views/orden_servicio_conversion_view.py").read_text(encoding="utf-8")
    assert 'text="👁 PDF Levantamiento"' in source
    assert "generar_pdf_registro(" in source
    assert "preview_orden_servicio" not in source
