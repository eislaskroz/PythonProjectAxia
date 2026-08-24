from services.update_service import normalizar_url_actualizacion


def test_normaliza_protocolo_duplicado_reportado():
    assert normalizar_url_actualizacion(
        "https://http://www.axiacomunicaciones.com/sftwr//AXIA_Setup_2.02.2.exe"
    ) == "https://www.axiacomunicaciones.com/sftwr/AXIA_Setup_2.02.2.exe"


def test_agrega_https_a_www_y_limpia_ruta():
    assert normalizar_url_actualizacion(
        "www.axiacomunicaciones.com//sftwr//AXIA_Setup_2.02.2.exe"
    ) == "https://www.axiacomunicaciones.com/sftwr/AXIA_Setup_2.02.2.exe"


def test_rechaza_host_http_falso():
    import pytest
    with pytest.raises(ValueError):
        normalizar_url_actualizacion("https://http")
