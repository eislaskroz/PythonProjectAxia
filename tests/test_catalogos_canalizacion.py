

def test_tipos_y_tamanos_de_tubos_estan_separados():
    from views.levantamientos.catalogos_canalizacion import TIPOS_TUBOS, TAMANOS_TUBOS
    assert TIPOS_TUBOS
    assert TAMANOS_TUBOS
    assert all("—" not in valor for valor in TIPOS_TUBOS)
    assert all('"' in valor for valor in TAMANOS_TUBOS)
