from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEV = (ROOT / 'views' / 'levantamiento_view.py').read_text(encoding='utf-8')
OBC = (ROOT / 'views' / 'obra_civil_view.py').read_text(encoding='utf-8')
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
PDF = (ROOT / 'services' / 'levantamiento_seguridad_pdf.py').read_text(encoding='utf-8')
SCHEMA = (ROOT / 'services' / 'levantamientos_schema.py').read_text(encoding='utf-8')
MIG = (ROOT / 'migrations' / '20260824_archivos_adjuntos_levantamientos.sql').read_text(encoding='utf-8')


def test_alturas_comun_en_especialidades_solicitadas():
    for nombre in ['Redes Voz y Datos','Control de Accesos','Enlaces Inalámbricos','Electricidad','Paneles Solares','Plantas de Energía','Aires Acondicionados']:
        assert f'"{nombre}"' in LEV
    assert 'TIPOS_CON_ACCESO_COMUN' in LEV
    assert 'Acceso, alturas y riesgos' in LEV
    assert 'Tipo de Sistema de Acceso Temporal' in LEV
    assert '"Escalera", "Andamio", "Plataforma"' in LEV
    assert '"Bajo", "Medio", "Alto", "Crítico"' in LEV
    assert 'Acceso, alturas y riesgos' in OBC


def test_titulos_sin_numeracion_visual():
    assert '_titulo_sin_numeracion' in LEV
    assert 'text=_titulo_sin_numeracion(titulo)' in LEV


def test_archivos_pdf_planos_comunes_y_persistencia():
    assert '¿Deseas agregar archivos PDF o planos?' in LEV
    assert 'lev_archivos_adjuntos_json' in LEV
    assert 'subir_archivos_levantamiento' in LEV
    assert 'lev_archivos_adjuntos_json' in SCHEMA
    assert 'lev_archivos_adjuntos_json' in MIG
    assert 'obc_archivos_adjuntos_json' in MIG
    assert '¿Deseas agregar archivos PDF o planos?' in OBC
    assert 'subir_archivos_obra_civil' in OBC
    assert '_append_archivos_adjuntos' in PDF


def test_autoguardado_periodico_y_cierre():
    assert '_instalar_autoguardado_borrador' in APP
    assert 'self.after(45000, ciclo)' in APP
    assert 'self.protocol("WM_DELETE_WINDOW", self.salir_aplicacion)' in APP
    assert 'self._guardar_borrador_actual()' in APP
    assert 'mostrar_obra_civil(borrador=datos)' in APP
