from pathlib import Path


def read(path):
    return Path(path).read_text(encoding="utf-8")


def test_selector_incluye_general():
    src = read("views/tipo_levantamiento_view.py")
    assert '"nombre": "General"' in src


def test_formulario_general_declarativo_y_catalogos():
    defs = read("views/levantamientos/form_definitions.py")
    assert '"General": {' in defs
    assert 'detalle_levantamiento' in defs

    equipos = read("services/equipos_catalogo_service.py")
    materiales = read("services/materiales_catalogo_service.py")
    assert '"General": [' in equipos
    assert '"General": [' in materiales


def test_validacion_y_pdf_general_conservan_detalle():
    src = read("views/levantamiento_view.py")
    pdf = read("services/levantamiento_seguridad_pdf.py")
    assert 'falta("Detalle de levantamiento"' in src
    assert 'detalle["resumen_servicio"] = detalle["detalle_levantamiento"]' in src
    assert 'str(modalidad).strip().casefold() != str(tipo).strip().casefold()' in pdf
