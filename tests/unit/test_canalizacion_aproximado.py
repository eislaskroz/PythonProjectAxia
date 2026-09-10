from views.levantamientos.canalizacion_aproximado import (
    texto_aproximado_canalizacion,
    unidad_forzada_canalizacion,
)


def test_tubo_siempre_usa_piezas_y_calcula_tres_metros_por_pieza():
    assert unidad_forzada_canalizacion("Tubo", "Metro(s)") == "Pieza(s)"
    assert texto_aproximado_canalizacion("Tubo", "4", "Pieza(s)") == "12 metros"
    assert texto_aproximado_canalizacion("Tubo", "1,5", "Pieza(s)") == "4.5 metros"


def test_otras_partidas_reflejan_cantidad_y_unidad():
    assert texto_aproximado_canalizacion("Cable", "25", "Metro(s)") == "25 Metro(s)"
    assert texto_aproximado_canalizacion("Cople", "6", "Pieza(s)") == "6 Pieza(s)"


def test_cantidad_vacia_o_invalida_no_inventa_metros():
    assert texto_aproximado_canalizacion("Tubo", "", "Pieza(s)") == "—"
    assert texto_aproximado_canalizacion("Tubo", "abc", "Pieza(s)") == "—"
