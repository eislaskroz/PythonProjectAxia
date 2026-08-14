from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_operador_abre_formulario_operativo_y_no_admin():
    src = read("ui/app_sidebar.py")
    assert 'if tipo_usuario == OPERADOR' in src
    assert 'callbacks["bitacora_avance"]' in src
    assert 'else callbacks["admin_bitacoras"]' in src


def test_formulario_bitacora_contiene_campos_del_formato_operativo():
    src = read("views/bitacora_avance_view.py")
    for texto in [
        "Folio de bitácora", "Fecha", "Número de ACO",
        "Dirección de la sucursal", "Nombre del Cliente",
        "Nombre del encargado del proyecto",
        "Hora de Llegada", "Hora de Salida", "Técnico en sitio",
        "Observaciones", "Descripción",
    ]:
        assert texto in src
