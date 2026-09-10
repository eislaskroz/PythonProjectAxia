from ui.numeric_masks import INTEGER, MONEY, NUMBER, formatear_numero, limpiar_numero


def test_formato_moneda():
    assert formatear_numero("1250000.5", MONEY) == "$1,250,000.50"


def test_formato_numero_general():
    assert formatear_numero("1250000.5", NUMBER) == "1,250,000.50"


def test_formato_entero():
    assert formatear_numero("1250000", INTEGER) == "1,250,000"


def test_limpieza_para_persistencia():
    assert limpiar_numero("$1,250,000.50") == "1250000.5"
    assert limpiar_numero("1,250,000.50") == "1250000.5"
    assert limpiar_numero("16%") == "16"


def test_vacio_permanece_vacio():
    assert formatear_numero("", MONEY) == ""
    assert limpiar_numero("") == ""
