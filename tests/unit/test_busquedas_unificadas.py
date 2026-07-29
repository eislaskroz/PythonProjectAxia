from pathlib import Path
from core.search_utils import normalizar_termino_busqueda


def test_normaliza_mayusculas_y_espacios():
    assert normalizar_termino_busqueda("  lev-  ") == "LEV-"


def test_servicios_exponen_busquedas_parciales():
    raiz = Path(__file__).resolve().parents[2]
    esperadas = {
        "levantamientos_service.py": "def buscar_levantamientos(",
        "acos_service.py": "def buscar_acos(",
        "ordenes_servicio_service.py": "def buscar_ordenes_servicio(",
        "ordenes_trabajo_service.py": "def buscar_ordenes_trabajo(",
        "bitacoras_service.py": "def buscar_bitacoras(",
        "obras_civiles_service.py": "def buscar_obras_civiles(",
    }
    for archivo, firma in esperadas.items():
        contenido = (raiz / "services" / archivo).read_text(encoding="utf-8")
        assert firma in contenido
