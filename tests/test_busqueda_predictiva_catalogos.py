from ui.native_combobox import _sorted_values, _filter_values, _exact_value


def test_busca_sin_acentos():
    values = ('Protección y Potencia', 'Conexiones y Uniones', 'Conductores y Canalización')
    assert _filter_values(values, 'proteccion') == ('Protección y Potencia',)


def test_busca_por_fragmento_y_prioriza_inicio():
    values = ('Tubo de PVC', 'Conduit metálico', 'Tubo Conduit')
    assert _filter_values(values, 'tubo') == ('Tubo de PVC', 'Tubo Conduit',)
    assert _filter_values(values, 'metali') == ('Conduit metálico',)


def test_no_fabrica_opciones_ajenas_al_catalogo():
    values = ('Apagador sencillo (1 vía)', 'Contacto dúplex')
    assert _exact_value(values, 'Apagador inventado') is None
    assert _exact_value(values, 'contacto duplex') == 'Contacto dúplex'


def test_mantiene_opciones_originales():
    values = ('Zeta', 'Árbol', 'Tubo')
    original = tuple(values)
    assert _sorted_values(values) == ('Árbol', 'Tubo', 'Zeta')
    assert values == original


def test_indicador_inicial_del_catalogo():
    values = ('Seleccione una opción', 'Contacto', 'Apagador')
    assert _sorted_values(values)[0] == 'Seleccione una opción'
