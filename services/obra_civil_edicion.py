"""Adaptación del registro OBC al formulario real (sin inventar un editor JSON).

La edición conserva las claves JSON desconocidas y compara contra el contenido
que se pudo representar al abrir el formulario, no contra valores predeterminados.
"""
from __future__ import annotations

import json

# Solo columnas que la Edge Function acepta como editables.
CAMPOS_EDITABLES = frozenset({
    'obc_fecha','obc_cliente','obc_contacto','obc_sucursal','obc_direccion',
    'obc_responsable_axia','obc_supervisor','obc_dias_trabajo','obc_personas_considerar',
    'obc_tipo_giro','obc_nombre_proyecto','obc_superficie_disponible','obc_superficie_adecuada',
    'obc_planos_arquitectonicos','obc_requiere_maquinaria','obc_permisos',
    'obc_observaciones_iniciales','obc_ejecucion_json','obc_planos_acabados',
    'obc_generacion_planos','obc_etapa_acabados','obc_obra_blanca',
    'obc_observaciones_finales','obc_anotacion_plano_json',
})

# Corresponde a las secciones REALES de views/obra_civil_view.py.
CAMPOS_POR_SECCION = {
    'Datos generales': {'obc_ejecucion_json','obc_cliente','obc_contacto','obc_sucursal','obc_direccion','obc_responsable_axia','obc_supervisor'},
    'Recursos proyectados': {'obc_dias_trabajo','obc_personas_considerar','obc_fecha','obc_tipo_giro','obc_nombre_proyecto', 'obc_ejecucion_json'},
    'Planeación inicial': {'obc_superficie_disponible','obc_superficie_adecuada','obc_planos_arquitectonicos', 'obc_requiere_maquinaria','obc_permisos','obc_observaciones_iniciales'},
    'Ejecución': {'obc_ejecucion_json'},
    'Acabados': {'obc_planos_acabados','obc_generacion_planos','obc_etapa_acabados','obc_obra_blanca'},
    'Conceptos de obra requeridos': {'obc_ejecucion_json'},
    'Materiales misceláneos y consumibles': {'obc_ejecucion_json'},
    'Canalización, cableado y materiales': {'obc_ejecucion_json'},
    'Acceso, alturas y riesgos': {'obc_ejecucion_json'},
    'Evidencia fotográfica': {'__adjuntos_nuevos_fotos'},  # Se cargan primero a Storage.
    'Anotaciones tipo plano': {'obc_anotacion_plano_json'},
    'Archivos PDF o planos': {'__adjuntos_nuevos_archivos'},
    'Observaciones finales': {'obc_observaciones_finales'},
}

JSON_POR_SECCION = {
    'Datos generales': {'_datos_generales_axia'},
    'Recursos proyectados': {'_notas_cliente','_datos_generales_axia'},
    'Ejecución': {'Trazo y nivelación', 'Trámites generales para instalaciones',
        'Construcción obra negra', 'Instalación eléctrica', 'Agua', 'Drenaje',
        'Telefonía', 'Datos y redes'},
    'Conceptos de obra requeridos': {'_conceptos_obra'},
    'Materiales misceláneos y consumibles': {'_materiales_miscelaneos'},
    'Canalización, cableado y materiales': {'_canalizacion_materiales'},
    'Acceso, alturas y riesgos': {'_acceso_alturas_riesgos'},
}
# EPP pertenece a Recursos proyectados.
JSON_POR_SECCION['Recursos proyectados'].add('_epp')


def _dict_json(valor):
    if isinstance(valor, dict):
        return dict(valor)
    if isinstance(valor, str):
        try:
            dato=json.loads(valor)
            return dato if isinstance(dato,dict) else {}
        except (TypeError, ValueError):
            return {}
    return {}


def _list_json(valor):
    if isinstance(valor, list):
        return list(valor)
    if isinstance(valor, str):
        try:
            dato=json.loads(valor)
            return dato if isinstance(dato,list) else []
        except (TypeError, ValueError):
            return []
    return []


def preparar_borrador_edicion(obra):
    """Precarga TODOS los controles del formulario ya existente; no toca red/BD."""
    datos=_dict_json(obra.get('obc_ejecucion_json'))
    notas=datos.get('_notas_cliente') or {}
    axia=datos.get('_datos_generales_axia') or {}
    epp=datos.get('_epp') or {}
    alturas=datos.get('_acceso_alturas_riesgos') or {}
    canal=datos.get('_canalizacion_materiales') or {}
    anotacion=_dict_json(obra.get('obc_anotacion_plano_json'))
    evidencias=_list_json(obra.get('obc_evidencias_json'))
    archivos=_list_json(obra.get('obc_archivos_adjuntos_json'))
    cliente=str(obra.get('obc_cliente') or '')
    return {'__obra_civil_borrador': {
        'obra_guardada': {'id':obra.get('obc_id'), 'folio':obra.get('obc_folio'),
            'fotos':evidencias, 'archivos':archivos},
        'folio':obra.get('obc_folio'), 'fecha':obra.get('obc_fecha'),
        'aco':obra.get('obc_aco_numero'),'cliente':cliente,
        'contacto':obra.get('obc_contacto'),'sucursal':obra.get('obc_sucursal'),
        'encargado_sucursal':obra.get('obc_contacto'),
        'direccion':obra.get('obc_direccion'),'responsable':obra.get('obc_responsable_axia'),
        'supervisor':obra.get('obc_supervisor'),
        'telefono':axia.get('telefono_encargado_sucursal'),
        'correo':axia.get('correo_encargado_sucursal'),'tecnico':axia.get('tecnico'),
        'tipo_giro':obra.get('obc_tipo_giro'),'nombre_proyecto':obra.get('obc_nombre_proyecto'),
        'dias_trabajo':obra.get('obc_dias_trabajo'),'personas':obra.get('obc_personas_considerar'),
        'requiere_epp':epp.get('requiere','No'), 'epp_partidas':epp.get('partidas',[]),
        'superficie':obra.get('obc_superficie_disponible'),
        'superficie_ok':obra.get('obc_superficie_adecuada'),
        'planos_arq':obra.get('obc_planos_arquitectonicos'),
        'maquinaria':obra.get('obc_requiere_maquinaria'),'permisos':obra.get('obc_permisos'),
        'desea_notas_cliente':notas.get('desea_agregar','No'),'notas_cliente':notas.get('notas',''),
        'observaciones_iniciales':obra.get('obc_observaciones_iniciales'),
        'ejecucion':{k: v for k,v in datos.items() if k in JSON_POR_SECCION['Ejecución']},
        'planos_acabados':obra.get('obc_planos_acabados'),
        'generacion_planos':obra.get('obc_generacion_planos'),
        'etapa_acabados':obra.get('obc_etapa_acabados'),'obra_blanca':obra.get('obc_obra_blanca'),
        'conceptos_obra':datos.get('_conceptos_obra',[]),
        'materiales_miscelaneos':[{**r, 'requerido':'Sí'} for r in datos.get('_materiales_miscelaneos',[]) if isinstance(r,dict)],
        'canalizacion_partidas':canal.get('partidas',[]),
        'requiere_canalizacion':canal.get('requiere','Sí'),
        'trabajo_alturas':alturas.get('trabajo_alturas','No'),
        'sistema_acceso':alturas.get('sistema_acceso_temporal','Escalera'),
        'altura_trabajo':alturas.get('altura',''), 'riesgo':alturas.get('riesgo','Bajo'),
        'desea_evidencias':'Sí' if evidencias else 'No',
        'desea_archivos':'Sí' if archivos else 'No',
        'desea_anotacion':'Sí' if anotacion.get('habilitado') else 'No',
        'anotacion_base64':anotacion.get('imagen_base64',''),
        'observaciones_finales':obra.get('obc_observaciones_finales'),
    }}


def _fusionar_solo_modificados(original, base, nuevo):
    """Conservar propiedades JSON no representadas por el formulario original."""
    if isinstance(base, dict) and isinstance(nuevo, dict):
        salida=dict(original) if isinstance(original,dict) else {}
        for clave in base.keys() | nuevo.keys():
            if base.get(clave) != nuevo.get(clave):
                if clave not in nuevo:
                    salida.pop(clave,None)
                else:
                    salida[clave]=_fusionar_solo_modificados(salida.get(clave),base.get(clave),nuevo[clave])
        return salida
    if isinstance(base, list) and isinstance(nuevo, list) and isinstance(original, list):
        # Al corregir una cantidad no borrar IDs/referencias de otros conceptos.
        if len(base)==len(nuevo)==len(original):
            return [_fusionar_solo_modificados(o,b,n) if b!=n else o
                    for o,b,n in zip(original,base,nuevo)]
    return nuevo


def cambios_secciones(obra, datos_base, datos_actuales, secciones_habilitadas):
    """Envía únicamente campos modificados desde secciones desbloqueadas."""
    cambios={}
    base_json=_dict_json(datos_base.get('obc_ejecucion_json'))
    nuevo_json=_dict_json(datos_actuales.get('obc_ejecucion_json'))
    original_json=_dict_json(obra.get('obc_ejecucion_json'))
    final_json=dict(original_json)
    for nombre in secciones_habilitadas:
        for campo in CAMPOS_POR_SECCION.get(nombre, ()):
            if campo=='obc_ejecucion_json' or campo not in CAMPOS_EDITABLES:
                continue
            anterior=datos_base.get(campo)
            actual=datos_actuales.get(campo)
            if anterior != actual:
                cambios[campo]=actual
        for subclave in JSON_POR_SECCION.get(nombre, ()):
            if base_json.get(subclave)!=nuevo_json.get(subclave):
                final_json[subclave]=_fusionar_solo_modificados(
                    original_json.get(subclave),base_json.get(subclave),nuevo_json.get(subclave))
    if final_json != original_json:
        cambios['obc_ejecucion_json']=json.dumps(final_json,ensure_ascii=False)
    return cambios
