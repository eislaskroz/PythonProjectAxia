"""Catálogo ZAPA compartido por Levantamientos y Obra Civil."""
from views.levantamientos.catalogos_canalizacion import (
    TIPOS_TUBOS, TIPOS_CONECTORES, TIPOS_CANALIZACION,
    especificaciones_por_categoria, normalizar_tipo_canalizacion, TAMANOS_TUBOS,
)


def test_tubo_zapa_en_catalogo_compartido():
    assert "Helicoidal metálico / Flexible ZAPA" in TIPOS_TUBOS
    assert "Helicoidal metálico / Flexible ZAPA" in TIPOS_CANALIZACION
    assert TIPOS_TUBOS.count("Helicoidal metálico / Flexible ZAPA") == 1


def test_conector_zapa_en_catalogo_compartido():
    assert "Conector de ZAPA" in TIPOS_CONECTORES
    assert TIPOS_CONECTORES.count("Conector de ZAPA") == 1


def test_los_tamanos_originales_siguen_disponibles():
    assert especificaciones_por_categoria("Tubo", "Helicoidal metálico / Flexible ZAPA") == TAMANOS_TUBOS
    assert especificaciones_por_categoria("Conectores", "Conector de ZAPA") == TAMANOS_TUBOS


def test_compatibilidad_de_helicoidal_historico():
    assert normalizar_tipo_canalizacion("Helicoidal metálico") == "Helicoidal metálico / Flexible ZAPA"
    assert normalizar_tipo_canalizacion("Helicoidal metálico / Flexible ZAPA") == "Helicoidal metálico / Flexible ZAPA"
