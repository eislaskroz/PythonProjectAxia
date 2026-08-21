from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "views" / "levantamiento_view.py").read_text(encoding="utf-8")
SCHEMA = (ROOT / "services" / "levantamientos_schema.py").read_text(encoding="utf-8")
MIG = (ROOT / "migrations" / "20260821_datos_generales_levantamientos.sql").read_text(encoding="utf-8")

def test_otros_y_direccion_sucursal():
    assert 'nombres_clientes.append("Otros")' in VIEW
    assert '"Dirección de Sucursal"' in VIEW
    assert 'construir_domicilio_sucursal(sucursal)' in VIEW
    assert 'activar_modo_cliente_otro' in VIEW

def test_asignaciones_axia_no_se_muestran_en_levantamiento():
    assert 'campo_option("Supervisor"' not in VIEW
    assert 'campo_option("Encargado de Proyecto"' not in VIEW
    assert 'campo_option("Técnico"' not in VIEW

def test_fecha_bloqueada_recursos_y_notas():
    assert '"Fecha de Levantamiento",\n        var_fecha_programada,\n        "DD/MM/AAAA",\n        state="disabled"' in VIEW
    assert '¿Proyecto de un día o varios días?' in VIEW
    assert 'Horas estimadas' in VIEW
    assert 'txt_notas_generales = ctk.CTkTextbox(contenedor_notas, height=48' in VIEW

def test_columnas_nuevas_contrato_y_migracion():
    for col in ("lev_direccion_sucursal", "lev_duracion_proyecto", "lev_horas_estimadas", "lev_notas"):
        assert f'"{col}"' in SCHEMA
        assert col in MIG
