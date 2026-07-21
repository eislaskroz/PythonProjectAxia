from pathlib import Path


def test_columnas_acos_esta_declarada_y_contiene_campos_clave():
    source = Path("services/acos_service.py").read_text(encoding="utf-8")
    assert "COLUMNAS_ACOS =" in source
    for campo in ("id_aco", "aco_numero", "aco_cliente", "aco_estatus"):
        assert f'"{campo}"' in source


def test_busqueda_aco_no_convierte_errores_tecnicos_en_no_encontrado():
    source = Path("services/acos_service.py").read_text(encoding="utf-8")
    inicio = source.index("def buscar_aco_por_numero")
    fin = source.index("def obtener_acos", inicio)
    bloque = source[inicio:fin]
    assert "raise AcoServiceError" in bloque
    assert 'logger.exception("Error al buscar ACO %s.", aco_numero)' in bloque
