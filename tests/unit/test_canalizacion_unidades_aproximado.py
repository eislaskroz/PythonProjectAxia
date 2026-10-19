"""Regresiones de unidades y conversiones visuales de canalización."""

from views.levantamientos.canalizacion_aproximado import (
    texto_aproximado_canalizacion,
    unidad_fija_canalizacion,
    unidad_forzada_canalizacion,
)


def test_categorias_con_unidad_fija_son_por_pieza():
    for categoria in ("Tubo", "Canaleta", "Patch cord", "Patchcord", " patch  cord "):
        assert unidad_fija_canalizacion(categoria)
        assert unidad_forzada_canalizacion(categoria, "Metro(s)") == "Pieza(s)"
        assert unidad_forzada_canalizacion(categoria, "") == "Pieza(s)"


def test_otras_categorias_conservan_sus_unidades():
    for categoria in ("Cable", "Cople", "Registro", "Conectores", "Patch panel"):
        assert not unidad_fija_canalizacion(categoria)
        assert unidad_forzada_canalizacion(categoria, "Metro(s)") == "Metro(s)"


def test_canaleta_piezas_a_metros():
    assert texto_aproximado_canalizacion("Canaleta", "15.00", "Pieza(s)") == "30 metros"
    assert texto_aproximado_canalizacion("Canaleta", "2,5", "Pieza(s)") == "5 metros"
    assert texto_aproximado_canalizacion("Canaleta", "1", "Metro(s)") == "2 metros"


def test_tubo_conserva_su_conversion_anterior():
    assert texto_aproximado_canalizacion("Tubo", "3", "Pieza(s)") == "9 metros"
    assert texto_aproximado_canalizacion("Tubo", "1.5", "Pieza(s)") == "4.5 metros"


def test_patchcord_por_piezas_sin_conversion_de_longitud():
    assert texto_aproximado_canalizacion("Patch cord", "4", "Metro(s)") == "4 Pieza(s)"
    assert texto_aproximado_canalizacion("Patchcord", "12", "") == "12 Pieza(s)"


def test_sin_cantidad_o_invalida_muestra_guion():
    for categoria in ("Tubo", "Canaleta", "Patch cord"):
        assert texto_aproximado_canalizacion(categoria, "", "Pieza(s)") == "—"
    assert texto_aproximado_canalizacion("Canaleta", "invalid", "Pieza(s)") == "—"


def test_conserva_conducta_otras_categorias():
    assert texto_aproximado_canalizacion("Cable", "20", "Metro(s)") == "20 Metro(s)"
