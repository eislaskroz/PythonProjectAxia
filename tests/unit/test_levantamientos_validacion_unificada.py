"""Regresión sin interfaz gráfica para los nueve formularios de AXIA.

Extrae la función realmente usada por la vista y la ejecuta con variables
simuladas. No requiere pantalla Windows, Tk ni conexión Supabase.
"""
from __future__ import annotations
import ast
import re
from pathlib import Path
import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'views' / 'levantamiento_view.py'
TEXT = SOURCE.read_text(encoding='utf-8-sig')
TREE = ast.parse(TEXT)


def extract(name):
    node = next(n for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef) and n.name == name)
    code = compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(SOURCE), 'exec')
    env = {}
    exec(code, env)
    return env[name]


class Var:
    def __init__(self, value='Dato'): self.value = value
    def get(self): return self.value
    def set(self, value): self.value = value


class Text:
    def __init__(self, value='Descripción real del servicio'): self.value = value
    def get(self, *args): return self.value


TIPOS = (
    'Seguridad y Monitoreo', 'Redes Voz y Datos', 'Control de Accesos',
    'Enlaces Inalámbricos', 'Electricidad', 'Paneles Solares',
    'Plantas de Energía', 'Aires Acondicionados',
    'Tecnología, Equipos y Periféricos',
)
TIPOS_CON_ACCESO = set(TIPOS) - {'Seguridad y Monitoreo', 'Tecnología, Equipos y Periféricos'}
TIPOS_CON_CANAL = set(TIPOS) - {'Tecnología, Equipos y Periféricos'}


def setup(tipo):
    body = ast.get_source_segment(TEXT, next(n for n in ast.walk(TREE)
                if isinstance(n, ast.FunctionDef) and n.name == 'campos_faltantes_preview'))
    referenced = set(re.findall(r'\bvar_[\w]+', body))
    env = {var: Var('Dato') for var in referenced}
    for flag in (
        'var_desea_notas_cliente', 'var_desea_anotacion_plano',
        'var_desea_evidencias', 'var_desea_archivos_adjuntos',
        'var_requiere_epp', 'var_trabajo_alturas_comun',
        'var_rack_requerido', 'var_gabinete_requerido',
        'var_ups_requerida', 'var_contacto_regulado',
        'var_tierra_fisica', 'var_escalera_requerida',
        'var_rvd_requiere_rack', 'var_rvd_requiere_gabinete',
        'var_rvd_ups', 'var_rvd_contacto_regulado',
        'var_rvd_tierra_fisica',
    ):
        env[flag] = Var('No')
    env.update({
        'tipo_levantamiento': tipo,
        'var_duracion_proyecto': Var('Un día'),
        'var_personas_considerar_general': Var('3'),
        'var_horas_estimadas_general': Var('8'),
        'var_infra_existe': Var('No'),
        'var_modalidad_levantamiento': Var('Instalación'),
        'var_rvd_tipo_servicio': Var('Datos'),
        'var_cctv_requiere_camaras': Var(''),  # Pregunta eliminada
        'txt_observaciones': Text(),
        'txt_descripcion': Text(),
        'txt_rep_infraestructura': Text(),
        'txt_rep_descripcion_fallas': Text(),
        'evidencias_levantamiento': [],
        'registro_editar': None,
        '_json_list': lambda value: value if isinstance(value, list) else [],
        '_total_archivos_adjuntos': lambda: 0,
        'obtener_epp_json': lambda: [{'epp':'Casco de seguridad','cantidad':'1'}],
        'epp_items': [],
        'equipos_danados_items': [],
        'pendientes_canalizacion_materiales': lambda: [],
        'TIPOS_CON_ACCESO_COMUN': TIPOS_CON_ACCESO,
        'TIPOS_LEVANTAMIENTO_ESPECIALIZADOS': set(TIPOS),
        'tipos_con_canalizacion': TIPOS_CON_CANAL,
    })
    env['vars_extra'] = {key: Var('Dato') for key in re.findall(r'vars_extra\["([^"]+)"\]',body)}
    # Mapping includes keys in list tuples used by the dynamic form.
    env['vars_extra'].update({key: Var('Dato') for key in (
        'cantidad_accesos','ubicacion_accesos','flujo_personas',
        'cantidad_lectores','usuarios_iniciales',
        'necesidad','sitio_origen','sitio_destino','distancia','ancho_banda',
        'linea_vista','altura_origen','altura_destino','obstrucciones',
        'acceso_azotea','frecuencia','tipo_equipo','cantidad_radios',
        'mastil_torre','proteccion_clima','punto_red_origen',
        'punto_red_destino','energia_origen','energia_destino',
        'metros_cable','proteccion_tierra',
    )})
    fn = extract('campos_faltantes_preview')
    fn.__globals__.update(env)
    return fn, env


@pytest.mark.parametrize('tipo', TIPOS)
def test_nueve_especialidades_pueden_validar_con_datos_visibles(tipo):
    fn, env = setup(tipo)
    assert fn() == [], f'{tipo}: {fn()}'


def test_unidad_de_validacion_coincide_con_faltantes():
    # No deben permanecer dos grupos de condiciones que se contradigan.
    fn = extract('formulario_preview_completo')
    fn.__globals__['campos_faltantes_preview'] = lambda: ['Nombre del servicio']
    assert not fn()
    fn.__globals__['campos_faltantes_preview'] = lambda: []
    assert fn()


def test_control_accesos_no_exige_campos_ocultos():
    fn, env = setup('Control de Accesos')
    env['vars_extra']['cantidad_lectores'].set('')
    env['vars_extra']['usuarios_iniciales'].set('')
    assert fn() == []


def test_seguridad_no_exige_respuesta_camaras_eliminada():
    fn, env = setup('Seguridad y Monitoreo')
    env['var_cctv_requiere_camaras'].set('')
    assert fn() == []
    env['var_cctv_punto_red'].set('')
    assert 'Punto de enlace de red' in fn()


def test_sin_altura_no_se_exigen_campos_dependientes():
    fn, env = setup('Electricidad')
    env['var_trabajo_alturas_comun'].set('No')
    env['var_altura_comun'].set('')
    env.setdefault('var_ele_altura_trabajo', Var('')).set('')
    assert fn() == []
    env['var_trabajo_alturas_comun'].set('Sí')
    assert 'Altura' in fn()


def test_epp_adicional_si_exige_partida_y_no_omite_cuatro_basicos():
    fn, env = setup('Paneles Solares')
    env['var_requiere_epp'].set('Sí')
    assert 'Agrega al menos un EPP adicional' in fn()
    env['epp_items'].append({'epp':Var('Guantes'), 'cantidad':Var('2')})
    assert fn() == []


def test_pendientes_condicionados_se_muestran_con_nombre():
    fn, env = setup('Redes Voz y Datos')
    fn.__globals__['pendientes_canalizacion_materiales'] = lambda: ['Material 1 (Tubo): falta tamaño']
    assert 'Material 1 (Tubo): falta tamaño' in fn()
    env['var_rvd_requiere_rack'].set('Sí')
    env['var_rvd_tipo_rack'].set('')
    assert 'Medida de Rack' in fn()


def test_seguimiento_en_tiempo_real_para_campos_dinamicos():
    assert 'var_cantidad_item, var_unidad_item' in TEXT
    assert 'var_horas_estimadas_general, var_requiere_canalizacion' in TEXT
    assert 'Ver campos pendientes' in TEXT
    assert '⚠ Aún existen campos obligatorios pendientes.' not in TEXT


def test_editar_no_exige_fotografias_ya_guardadas_en_supabase():
    fn, env = setup('Paneles Solares')
    env['var_desea_evidencias'].set('Sí')
    assert 'Evidencia fotográfica' in fn()
    fn.__globals__['registro_editar'] = {'lev_evidencias_json': [{'path':'foto_001.jpg'}]}
    assert fn() == []
