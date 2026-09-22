from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "services" / "acos_service.py").read_text(encoding="utf-8")


def test_contrato_completo_de_aco_automatico():
    assert "def buscar_aco_por_id" in SRC
    assert "def buscar_aco_generado_por_levantamiento" in SRC
    assert "def crear_aco_desde_levantamiento" in SRC


def test_reintento_usa_marca_unica_del_levantamiento():
    assert 'return f"[AXIA-LEV:{folio}]"' in SRC
    assert '.ilike("aco_observaciones", f"%{marca}%")' in SRC
    bloque = SRC[SRC.index("def crear_aco_desde_levantamiento"):]
    assert bloque.index("buscar_aco_generado_por_levantamiento") < bloque.index("resultado = crear_aco(datos)")


def test_aco_automatico_deja_folio_al_trigger():
    bloque = SRC[SRC.index("def crear_aco_desde_levantamiento"):]
    assert '"aco_numero":' not in bloque.split("resultado = crear_aco(datos)", 1)[0]
