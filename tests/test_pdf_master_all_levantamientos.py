import json
from pathlib import Path

import pytest

from services.levantamiento_seguridad_pdf import generar_pdf_levantamiento_maestro
from services.axia_pdf_artifacts import PDF_RENDERER_VERSION


def base(tipo, modalidad='Instalación', detalle=None):
    return {
        'lev_folio': 'LEV-TEST',
        'lev_tipo_levantamiento': tipo,
        'lev_modalidad_operativa': modalidad,
        'lev_cliente': 'CLIENTE DEMO',
        'lev_contacto': 'CONTACTO DEMO',
        'lev_correo': 'demo@axia.mx',
        'lev_telefono': '5555555555',
        'lev_direccion': 'DIRECCIÓN DEMO',
        'lev_tecnico': 'TÉCNICO DEMO',
        'lev_supervisor': 'SUPERVISOR DEMO',
        'lev_fecha_programada': '2026-08-11',
        'lev_observaciones': 'Descripción detallada del servicio con información suficiente para validar el formato.',
        'lev_detalle_tecnico_json': json.dumps(detalle or {}, ensure_ascii=False),
    }


CASES = [
    base('Seguridad y Monitoreo', 'Instalación', {
        'tipo_levantamiento':'Seguridad y Monitoreo','modalidad_operativa':'Instalación',
        'infraestructura_existente': {'existe_infraestructura':'No','tipo_infraestructura_existente':'No aplica','estado_general':'No aplica'},
        'rack_gabinete_energia': {'rack_requerido':'Sí','tipo_rack':'12U','gabinete_requerido':'Sí','tipo_gabinete':'Exterior','ups_requerida':'Sí','tipo_ups':'1500 VA','contacto_regulado':'Sí','detalle_contacto_regulado':'2','tierra_fisica':'Sí','detalle_tierra_fisica':'Nueva'},
        'acceso_alturas_riesgos': {'escalera_andamio':'Sí','altura_trabajo':'4 m','riesgo_instalacion':'Medio'},
        'datos_tecnicos_cctv': {'cantidad_camaras':'12','tipo_camaras':'IP','dias_trabajo':'3','personas_considerar':'2','ubicacion_nvr_dvr':'Site','punto_red':'Site','punto_energia':'Site'},
        'canalizacion_materiales':[{'categoria':'Tubo','tipo':'Pared delgada (EMT)','tamano_calibre_especificacion':'3/4 in','cantidad':'50','unidad':'m'}],
    }),
    base('Seguridad y Monitoreo', 'Reparación', {
        'tipo_levantamiento':'Seguridad y Monitoreo','modalidad_operativa':'Reparación','elemento_a_reparar':'Cámaras',
        'ubicacion_estado_sintomas': {'ubicacion_equipos':'Acceso 1','acceso_equipos':'Fácil','estado':'Sin imagen','horario_falla':'Intermitente'},
        'alimentacion_energia': {'voltaje_correcto':'Sí','amperaje_suficiente':'Sí'},
        'equipos_danados':[{'tipo':'Cámara','marca':'Axis','modelo':'M1','serie':'ABC'}],
    }),
    base('Seguridad y Monitoreo', 'Mantenimiento', {'tipo_levantamiento':'Seguridad y Monitoreo','modalidad_operativa':'Mantenimiento','mantenimiento':{'descripcion_detallada_servicio':'Mantenimiento preventivo general.'}}),
    base('Aires Acondicionados', detalle={'necesidad_inicial':{'necesidad':'Sistema nuevo','cantidad_equipos':'2'},'condiciones_sitio':{'dimensiones_area':'10x10 m'},'preparativos_riesgos':{'dias_trabajo':'2','personas_trabajo':'2'}}),
    base('Redes Voz y Datos', detalle={'necesidad_alcance':{'necesidad':'Instalación nueva','tipo_servicio':'Datos','cantidad_nodos_datos':'24'},'estimacion_recursos':{'dias_trabajo':'4','personas_trabajo':'3'},'canalizacion_materiales':[{'categoria':'Cable','tipo':'UTP Cat6','tamano_calibre_especificacion':'Cat6','cantidad':'800','unidad':'m'}]}),
    base('Plantas de Energía', detalle={'necesidad_respaldo':{'necesidad':'Nueva planta','tipo_planta':'Diésel'},'instalacion_pruebas_entrega':{'dias_trabajo':'5','personas_trabajo':'4'}}),
    base('Electricidad', detalle={'necesidad_alcance':{'necesidad':'Alimentador principal','tipo_servicio':'Alimentador principal'},'seguridad_operacion':{'altura_trabajo':'3 m'},'instalacion_pruebas_entrega':{'dias_trabajo':'2','personas_trabajo':'2'},'canalizacion_materiales':[{'categoria':'Cable','tipo':'THHN / THWN','tamano_calibre_especificacion':'12 AWG','cantidad':'200','unidad':'m'}]}),
    base('Control de Accesos', detalle={'secciones':{'necesidad_inicial_y_alcance':{'necesidad':'Instalación nueva','cantidad_accesos':'3'},'estimación_de_recursos':{'dias_trabajo':'2','personas_trabajo':'2'}},'canalizacion_materiales':[{'categoria':'Tubo','tipo':'PVC','tamano_calibre_especificacion':'1 in','cantidad':'30','unidad':'m'}]}),
    base('Enlaces Inalámbricos', detalle={'secciones':{'necesidad_inicial_y_alcance':{'necesidad':'Enlace punto a punto','distancia':'1.5 km'},'estimación_de_recursos':{'dias_trabajo':'1','personas_trabajo':'2'}},'canalizacion_materiales':[{'categoria':'Cable','tipo':'UTP Cat6 exterior','cantidad':'80','unidad':'m'}]}),
    base('Tecnología, Equipos y Periféricos', detalle={'secciones':{'tipo_de_solicitud_y_alcance':{'accion_ti':'Suministro','cantidad_equipos':'4'},'instalación_configuración_pruebas_y_entrega':{'dias_trabajo':'1','personas_trabajo':'1'}},'equipos_principales':[{'familia':'Laptop','subfamilia':'Empresarial','cantidad':'4','marca':'Dell','modelo':'Latitude','caracteristicas':'16 GB RAM'}]}),
    base('Paneles Solares', detalle={'secciones':{'necesidad_inicial_y_consumo':{'necesidad':'Sistema nuevo','consumo_mensual':'850 kWh'},'instalación_pruebas_y_entrega':{'dias_trabajo':'3','personas_trabajo':'4'}},'equipos_principales':[{'familia':'Panel','subfamilia':'Monocristalino','cantidad':'12','marca':'Demo','modelo':'550W','caracteristicas':'550 W'}]}),
]


@pytest.mark.parametrize('idx,registro', enumerate(CASES))
def test_master_pdf_all_types(tmp_path, idx, registro):
    out = tmp_path / f'case_{idx}.pdf'
    result = generar_pdf_levantamiento_maestro(registro, ruta_salida=out, abrir=False)
    assert Path(result).is_file()
    assert Path(result).stat().st_size > 1000


def test_renderer_version_migrated_all_levantamientos():
    assert PDF_RENDERER_VERSION >= 11


def test_seguridad_reparacion_ignora_bloques_historicos_no_visibles(tmp_path):
    registro = base('Seguridad y Monitoreo', 'Reparación', {
        'tipo_levantamiento': 'Seguridad y Monitoreo',
        'modalidad_operativa': 'Reparación',
        'elemento_a_reparar': 'Cámaras',
        'ubicacion_estado_sintomas': {
            'ubicacion_equipos': 'Acceso principal',
            'acceso_equipos': 'Fácil acceso',
            'estado': 'Sin imagen',
        },
        # Datos heredados de versiones anteriores. Ya no existen en el formulario
        # actual y por lo tanto tampoco deben imprimirse en el PDF.
        'alimentacion_energia': {'voltaje_correcto': 'Sí'},
        'conectividad_transmision_video': {'tipo_cableado': 'UTP'},
        'configuracion_grabador': {'disco_operativo': 'Sí'},
        'equipos_danados': [{'tipo':'Cámara','marca':'Axis','modelo':'M1','serie':'ABC'}],
        'descripcion_general_fallas': 'Cámara sin imagen.',
    })
    out = tmp_path / 'seguridad_reparacion.pdf'
    generar_pdf_levantamiento_maestro(registro, ruta_salida=out, abrir=False)

    from pypdf import PdfReader
    texto = '\n'.join((page.extract_text() or '') for page in PdfReader(str(out)).pages)
    assert 'ALIMENTACIÓN Y ENERGÍA' not in texto.upper()
    assert 'CONECTIVIDAD Y TRANSMISIÓN DE VIDEO' not in texto.upper()
    assert 'CONFIGURACIÓN Y GRABADOR' not in texto.upper()
    assert 'UBICACIÓN, ACCESO, ESTADO Y SÍNTOMAS' in texto.upper()
    assert 'INFORMACIÓN DE EQUIPOS DAÑADOS' in texto.upper()


def test_renderer_version_seguridad_reparacion_actualizada():
    assert PDF_RENDERER_VERSION >= 13


def test_seguridad_reparacion_y_mantenimiento_no_imprimen_canalizacion(tmp_path):
    from pypdf import PdfReader
    for modalidad in ('Reparación', 'Mantenimiento'):
        detalle = {
            'tipo_levantamiento': 'Seguridad y Monitoreo',
            'modalidad_operativa': modalidad,
            'canalizacion_materiales': [
                {'categoria':'Tubo','tipo':'PVC pesado','tamano_calibre_especificacion':'1 in','cantidad':'30','unidad':'m'}
            ],
        }
        if modalidad == 'Reparación':
            detalle.update({
                'elemento_a_reparar':'Infraestructura',
                'ubicacion_estado_sintomas': {'descripcion_infraestructura':'Canaleta dañada.'},
                'descripcion_general_fallas':'Reparar infraestructura existente.',
            })
        else:
            detalle.update({
                'acceso_alturas_riesgos': {'escalera_andamio':'Sí','altura_trabajo':'4 m','riesgo_instalacion':'Medio'},
                'mantenimiento': {'descripcion_detallada_servicio':'Mantenimiento preventivo.'},
            })
        reg = base('Seguridad y Monitoreo', modalidad, detalle)
        out = tmp_path / f'seg_{modalidad}.pdf'
        generar_pdf_levantamiento_maestro(reg, ruta_salida=out, abrir=False)
        texto = '\n'.join((page.extract_text() or '') for page in PdfReader(str(out)).pages).upper()
        assert 'CANALIZACIÓN, CABLEADO Y MATERIALES' not in texto
        if modalidad == 'Mantenimiento':
            assert 'ACCESO, ALTURAS Y RIESGOS' in texto
            assert '4 M' in texto


def test_renderer_version_seguridad_modalidades_y_redes():
    assert PDF_RENDERER_VERSION >= 14
