"""Regresión: abrazaderas para viga con tamaños exclusivos, sin alterar catálogos."""

from views.levantamientos.catalogos_canalizacion import (
    MEDIDAS_ABRAZADERA_PARA_VIGA,
    TAMANOS_TUBOS,
    TIPOS_ABRAZADERAS,
    especificaciones_por_categoria,
    normalizar_opciones_canalizacion,
)


def test_tipo_para_viga_en_catalogo_original():
    assert TIPOS_ABRAZADERAS[-1] == "Para Viga"
    assert len(TIPOS_ABRAZADERAS) == len(set(TIPOS_ABRAZADERAS))
    assert "Tipo Omega" in TIPOS_ABRAZADERAS


def test_medidas_exclusivas_para_viga():
    assert MEDIDAS_ABRAZADERA_PARA_VIGA == ['1" (25mm)', '3/4" (19mm)']
    assert especificaciones_por_categoria("Abrazadera", "Para Viga") == MEDIDAS_ABRAZADERA_PARA_VIGA


def test_otras_abrazaderas_conservan_medidas():
    assert especificaciones_por_categoria("Abrazadera", "Tipo Omega") == TAMANOS_TUBOS


def test_recalcular_cuando_cambia_de_tipo():
    tipo, tamano, opciones = normalizar_opciones_canalizacion(
        "Abrazadera", "Para Viga", '2" (51mm)', TIPOS_ABRAZADERAS
    )
    assert tipo == "Para Viga"
    assert tamano in MEDIDAS_ABRAZADERA_PARA_VIGA
    assert opciones == MEDIDAS_ABRAZADERA_PARA_VIGA


def test_tamano_valido_se_respeta():
    tipo, tamano, _ = normalizar_opciones_canalizacion(
        "Abrazadera", "Para Viga", '3/4" (19mm)', TIPOS_ABRAZADERAS
    )
    assert (tipo, tamano) == ("Para Viga", '3/4" (19mm)')
