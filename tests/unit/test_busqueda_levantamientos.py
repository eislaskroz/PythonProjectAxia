from core.search_utils import (
    coincide_en_campos,
    normalizar_termino_busqueda,
    puntaje_coincidencia,
)


CAMPOS = (
    "lev_folio",
    "lev_aco_numero",
    "lev_cliente",
    "lev_ubicacion",
    "lev_tecnico",
    "lev_supervisor",
    "lev_estatus",
    "lev_tipo",
)


def test_normaliza_busqueda_a_mayusculas_y_espacios():
    assert normalizar_termino_busqueda("  lev   0004 ") == "LEV 0004"


def test_coincidencia_parcial_por_folio_y_numero():
    registro = {"lev_folio": "LEV-0004", "lev_cliente": "AXIA COMUNICACIONES"}
    assert coincide_en_campos(registro, "lev", CAMPOS)
    assert coincide_en_campos(registro, "0004", CAMPOS)
    assert not coincide_en_campos(registro, "9999", CAMPOS)


def test_busqueda_ignora_acentos_y_mayusculas():
    registro = {"lev_cliente": "Ingeniería Eléctrica México"}
    assert coincide_en_campos(registro, "ingenieria", CAMPOS)
    assert coincide_en_campos(registro, "MÉXICO", CAMPOS)


def test_orden_prioriza_exacto_inicio_y_contenido():
    exacto = {"lev_folio": "LEV"}
    inicio = {"lev_folio": "LEV-0001"}
    contenido = {"lev_folio": "AX-LEV-0001"}
    assert puntaje_coincidencia(exacto, "LEV", CAMPOS) < puntaje_coincidencia(inicio, "LEV", CAMPOS)
    assert puntaje_coincidencia(inicio, "LEV", CAMPOS) < puntaje_coincidencia(contenido, "LEV", CAMPOS)
