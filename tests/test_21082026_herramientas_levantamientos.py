from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_catalogo_herramientas_cubre_especialidades_axia():
    from views.levantamientos.catalogo_herramientas import CATALOGO_HERRAMIENTAS
    esperadas = {
        'General', 'Electricidad', 'Seguridad y Monitoreo', 'Control de Accesos',
        'Redes de Voz y Datos', 'Enlaces Inalámbricos', 'Paneles Solares',
        'Plantas de Energía', 'Aires Acondicionados', 'Obra Civil',
        'Tecnología, Equipos y Periféricos',
    }
    assert esperadas.issubset(CATALOGO_HERRAMIENTAS)
    assert all(CATALOGO_HERRAMIENTAS[k] for k in esperadas)


def test_herramientas_se_guardan_en_detalle_tecnico_y_se_restauran():
    vista = (ROOT / 'views' / 'levantamiento_view.py').read_text(encoding='utf-8')
    assert 'text="🧰 Herramientas"' in vista
    assert 'detalle["herramientas"] = obtener_herramientas_json()' in vista
    assert 'detalle_tecnico["herramientas"] = obtener_herramientas_json()' in vista
    assert 'for fila in detalle.get("herramientas", [])' in vista


def test_notas_compactas_comparten_fila_con_fecha():
    vista = (ROOT / 'views' / 'levantamiento_view.py').read_text(encoding='utf-8')
    assert '_crear_contenedor_campo(4 + desplazamiento_filas, 1, colspan=4)' in vista
    assert 'txt_notas_generales = ctk.CTkTextbox(contenedor_notas, height=48' in vista
