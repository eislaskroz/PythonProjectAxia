from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_roles_catalogos_usuarios():
    texto = (ROOT / "services" / "usuarios_service.py").read_text(encoding="utf-8")
    assert "obtener_nombres_usuarios_por_tipos([4]" in texto
    assert "obtener_nombres_usuarios_por_tipos([2, 3]" in texto
    assert "obtener_nombres_usuarios_por_tipos([3, 4]" in texto


def test_levantamientos_layout_fiscal_sucursal_encargado_roles():
    texto = (ROOT / "views" / "levantamiento_view.py").read_text(encoding="utf-8")
    assert '"Dirección Fiscal"' in texto
    assert '"Sucursal"' in texto
    assert '"Encargado de sucursal"' in texto
    assert '"Encargado de Proyecto"' in texto
    assert '"Técnico"' in texto
    assert 'var_direccion.set(construir_domicilio_sucursal' not in texto
    assert '"id_sucursal": seleccion_catalogo.get("id_sucursal")' in texto
    assert '"id_contacto": seleccion_catalogo.get("id_contacto")' in texto


def test_obra_civil_layout_y_roles():
    texto = (ROOT / "views" / "obra_civil_view.py").read_text(encoding="utf-8")
    assert '"Dirección Fiscal"' in texto
    assert 'option("Supervisor"' in texto
    assert 'option("Encargado de Proyecto"' in texto
    assert 'option("Técnico"' in texto
    assert 'var_direccion.set(construir_domicilio_sucursal' not in texto
