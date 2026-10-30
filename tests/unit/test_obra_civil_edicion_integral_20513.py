"""Pruebas puras: la edición desbloqueada no afecta otras secciones ni JSON oculto."""
import json
from services.obra_civil_edicion import preparar_borrador_edicion, cambios_secciones, CAMPOS_POR_SECCION


def _obra():
    return dict(obc_id=7, obc_folio='OBC-0007', obc_cliente='Antiguo',
                obc_nombre_proyecto='Proyecto', obc_dias_trabajo=5,
                obc_evidencias_json='[{"storage_path":"archivo/imagen.jpg"}]',
                obc_archivos_adjuntos_json='[{"storage_path":"archivo/plano.pdf"}]',
                obc_ejecucion_json=json.dumps({
                    'Trazo y nivelación':'Terminado',
                    '_conceptos_obra':[{'tipo':'OTROS','concepto':'Prueba'}],
                    '_epp':{'requiere':'Sí','partidas':[]},
                    '_datos_generales_axia':{'supervisor':'A','tecnico':'T'},
                    '_metadatos_invisibles':{'id':'oculto'},
                }))


def test_abre_con_folio_y_listas_sin_perder_adjuntos():
    estado=preparar_borrador_edicion(_obra())['__obra_civil_borrador']
    assert estado['folio']=='OBC-0007'
    assert estado['obra_guardada']['id']==7
    assert len(estado['obra_guardada']['fotos'])==1
    assert len(estado['obra_guardada']['archivos'])==1
    assert estado['conceptos_obra'][0]['concepto']=='Prueba'
    assert estado['ejecucion']['Trazo y nivelación']=='Terminado'


def test_sin_modificar_no_envia_cambios_no_versiona():
    obra=_obra()
    base={'obc_cliente':'Antiguo','obc_ejecucion_json':obra['obc_ejecucion_json']}
    assert cambios_secciones(obra,base,dict(base),{'Datos generales','Conceptos de obra requeridos'})=={}


def test_solo_guarda_campo_de_seccion_desbloqueada():
    obra=_obra()
    base={'obc_cliente':'Antiguo','obc_nombre_proyecto':'Proyecto', 'obc_ejecucion_json':obra['obc_ejecucion_json']}
    actual={**base,'obc_cliente':'Nuevo', 'obc_nombre_proyecto':'Indebido'}
    assert cambios_secciones(obra,base,actual,{'Datos generales'}) == {'obc_cliente':'Nuevo'}


def test_preserva_claves_ocultas_json_y_separacion_secciones():
    obra=_obra()
    base=json.loads(obra['obc_ejecucion_json'])
    actual=json.loads(obra['obc_ejecucion_json'])
    actual['Trazo y nivelación']='En proceso'
    actual['_conceptos_obra']=[{'tipo':'OTROS','concepto':'NO AUTORIZADO'}]
    base_blob={'obc_ejecucion_json':json.dumps(base)}
    actual_blob={'obc_ejecucion_json':json.dumps(actual)}
    cambios=cambios_secciones(obra,base_blob,actual_blob,{'Ejecución'})
    assert set(cambios)=={'obc_ejecucion_json'}
    nuevo=json.loads(cambios['obc_ejecucion_json'])
    assert nuevo['Trazo y nivelación']=='En proceso'
    assert nuevo['_metadatos_invisibles']=={'id':'oculto'}
    assert nuevo['_conceptos_obra']==base['_conceptos_obra']


def test_catalogo_completo_secciones_formulario_original():
    assert len(CAMPOS_POR_SECCION)==13
    assert 'obc_anotacion_plano_json' in CAMPOS_POR_SECCION['Anotaciones tipo plano']
    assert '__adjuntos_nuevos_fotos' in CAMPOS_POR_SECCION['Evidencia fotográfica']
    assert '__adjuntos_nuevos_archivos' in CAMPOS_POR_SECCION['Archivos PDF o planos']


def test_sql_versionado_existe_y_no_inserta_obras():
    from pathlib import Path
    ruta=Path(__file__).resolve().parents[2]/'supabase/sql/AXIA_OBRA_CIVIL_EDICION_VERSIONADA_20513.sql'
    sql=ruta.read_text()
    assert 'FOR UPDATE' in sql
    assert 'nextval(' in sql
    assert 'axia_obc_historial_ediciones' in sql
    assert 'obc_id=$3 AND obc_folio=$4' in sql
    assert 'RETURN to_jsonb(v_actual)' in sql
    assert 'INSERT INTO public.db_obras_civiles' not in sql
