from pathlib import Path


def test_contactos_sucursal_tiene_fallback_tolerante():
    text = Path("services/sucursales_service.py").read_text(encoding="utf-8")
    assert '.select("*")' in text
    assert 'if filas:' in text
    assert '"activo"' in text
    assert 'Error al consultar contactos de la sucursal incluso con fallback.' in text
