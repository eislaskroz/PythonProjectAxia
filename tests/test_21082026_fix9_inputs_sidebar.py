from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_campos_cuadrados_globales():
    txt = (ROOT / "ui" / "theme_manager.py").read_text(encoding="utf-8")
    assert "_aplicar_campos_cuadrados" in txt
    assert 'kwargs["corner_radius"] = 0' in txt

def test_sidebar_tiene_especialidades_y_obra_civil():
    txt = (ROOT / "ui" / "app_sidebar.py").read_text(encoding="utf-8")
    esperados = [
        "Seguridad y Monitoreo", "Redes Voz y Datos", "Control de Accesos",
        "Enlaces Inalámbricos", "Tecnología, Equipos y Periféricos", "Electricidad",
        "Paneles Solares", "Plantas de Energía", "Aires Acondicionados", "Obra Civil",
    ]
    for tipo in esperados:
        assert tipo in txt
    assert "actualizar_sidebar_especialidad" in txt

def test_assets_sidebar_presentes():
    for p in (ROOT / "assets").glob("fondo_*.png"):
        assert p.stat().st_size > 0
    assert len(list((ROOT / "assets").glob("fondo_*.png"))) == 11
