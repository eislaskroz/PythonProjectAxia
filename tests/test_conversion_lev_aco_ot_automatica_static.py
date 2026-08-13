from pathlib import Path


def read(path):
    return Path(path).read_text(encoding='utf-8')


def test_conversion_garantiza_aco_antes_de_ot():
    src = read('services/ordenes_trabajo_service.py')
    block = src[src.index('def convertir_levantamiento_a_trabajo'):src.index('def buscar_ordenes_trabajo_por_aco')]
    pos_aco = block.index('crear_aco_desde_levantamiento')
    pos_ot = block.index('resultado = crear_orden_trabajo(payload)')
    assert pos_aco < pos_ot
    assert '"id_aco": id_aco' in src
    assert '"ot_aco_numero": numero_aco' in src


def test_levantamiento_se_vincula_al_aco_antes_de_crear_ot():
    src = read('services/ordenes_trabajo_service.py')
    assert '{"id_aco": id_aco, "lev_aco_numero": numero_aco}' in src
    assert 'La Orden de Trabajo no se creó para evitar perder trazabilidad.' in src


def test_reintento_evitar_aco_duplicado():
    src = read('services/ordenes_trabajo_service.py')
    acos = read('services/acos_service.py')
    assert 'buscar_aco_generado_por_levantamiento' in src
    assert 'def buscar_aco_generado_por_levantamiento' in acos


def test_ui_explica_aco_automatico():
    src = read('views/orden_servicio_conversion_view.py')
    assert 'AXIA lo generará automáticamente en este momento' in src
    assert 'ACO generado automáticamente' in src
