from services.levantamiento_compat import normalizar_registro_levantamiento


def test_infiere_tipo_desde_codigo_mobile():
    row = {"lev_tipo": 2, "creado_por": "AXIA FIELD", "lev_detalle_tecnico_json": {"rvd_necesidad": "Instalación nueva"}}
    out = normalizar_registro_levantamiento(row)
    assert out["lev_tipo_levantamiento"] == "Redes Voz y Datos"
    assert out["lev_detalle_tecnico_json"]["tipo_levantamiento"] == "Redes Voz y Datos"


def test_aliases_mobile_permiten_restaurar_campos_desktop():
    row = {"lev_tipo": 6, "lev_detalle_tecnico_json": {"ele_area": "SITE", "ele_prueba_voltaje": "Sí"}}
    detail = normalizar_registro_levantamiento(row)["lev_detalle_tecnico_json"]
    compat = detail["compatibilidad_axia_field"]
    assert compat["area_trabajo"] == "SITE"
    assert compat["medicion_voltaje"] == "Sí"


def test_declarativo_mobile_se_convierte_a_secciones():
    row = {"lev_tipo": 3, "lev_detalle_tecnico_json": {"necesidad": "Instalación nueva", "tipo_control": "Peatonal"}}
    detail = normalizar_registro_levantamiento(row)["lev_detalle_tecnico_json"]
    assert detail["tipo_levantamiento"] == "Control de Accesos"
    assert detail.get("secciones")
