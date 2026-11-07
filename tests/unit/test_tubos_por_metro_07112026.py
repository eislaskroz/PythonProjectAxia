"""Unidades y aproximados de tuberías flexibles, sin afectar las rígidas."""
from views.levantamientos.catalogos_canalizacion import TIPOS_TUBOS
from views.levantamientos.catalogos_materiales_jerarquicos import unidades_de_material
from views.levantamientos.canalizacion_aproximado import (
    tubo_por_metro, unidad_forzada_canalizacion, texto_aproximado_canalizacion,
)

FLEXIBLES = (
    'Helicoidal metálico / Flexible ZAPA',
    'Liquidtight /Licuatite',
    'Poliducto corrugado (Ligero)',
    'Vorrugado no metálico (ENT)',
)


def test_solo_cuatro_tubos_por_metro():
    for tipo in FLEXIBLES:
        assert tubo_por_metro('Tubo', tipo)
        assert unidades_de_material('Tubo', tipo) == ['Metro(s)']
        assert unidad_forzada_canalizacion('Tubo', 'Pieza(s)', tipo) == 'Metro(s)'
        assert texto_aproximado_canalizacion('Tubo', '15.00', 'Metro(s)', tipo) == '15 metros'
    for tipo in TIPOS_TUBOS:
        if tipo in FLEXIBLES:
            continue
        assert not tubo_por_metro('Tubo', tipo)
        assert unidades_de_material('Tubo', tipo) == ['Pieza(s)']
        assert unidad_forzada_canalizacion('Tubo', 'Metro(s)', tipo) == 'Pieza(s)'
        assert texto_aproximado_canalizacion('Tubo', '2', 'Pieza(s)', tipo) == '6 metros'


def test_otros_materiales_no_cambian():
    assert unidad_forzada_canalizacion('Canaleta', 'Metro(s)', 'Canaleta PVC') == 'Pieza(s)'
    assert texto_aproximado_canalizacion('Canaleta', '3', 'Pieza(s)', 'Canaleta PVC') == '6 metros'
    assert unidad_forzada_canalizacion('Cable', 'Metro(s)', 'UTP Cat6') == 'Metro(s)'


def test_cambio_de_tipo_corrige_unidad_y_no_multiplica_metros():
    assert unidad_forzada_canalizacion('Tubo', 'Metro(s)', 'Pared delgada (EMT)') == 'Pieza(s)'
    assert unidad_forzada_canalizacion('Tubo', 'Pieza(s)', FLEXIBLES[0]) == 'Metro(s)'
    assert texto_aproximado_canalizacion('Tubo', '0', 'Metro(s)', FLEXIBLES[1]) == '0 metros'
    assert texto_aproximado_canalizacion('Tubo', '', 'Metro(s)', FLEXIBLES[1]) == '—'
