"""Contrato conservador para intercambio de levantamientos AXIA.

No conecta los formularios ni traslada archivos de evidencia. Nunca interpreta un
borrador de FIELD como si fuera automáticamente un formulario completo DESKTOP.
"""
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

SCHEMA = 'axia.draft.v1'
MODULE = 'LEVANTAMIENTO'
COMMON_TO_DESKTOP = {
    'client': 'lev_cliente', 'contact': 'lev_contacto', 'phone': 'lev_telefono',
    'email': 'lev_correo', 'description': 'lev_descripcion',
    'location': 'lev_ubicacion', 'address': 'lev_direccion',
    'branchAddress': 'lev_direccion_sucursal', 'priority': 'lev_prioridad',
    'observations': 'lev_observaciones', 'duration': 'lev_duracion_proyecto',
    'estimatedHours': 'lev_horas_estimadas', 'estimatedDays': 'lev_dias_trabajo',
    'estimatedPeople': 'lev_personas_considerar', 'clientNotes': 'lev_notas',
}

class IntercambioNoSeguro(ValueError):
    """Se necesita el conversor especializado o la transferencia de archivos."""


def _json_safe(data: dict[str, Any]) -> dict[str, Any]:
    # Copia profunda y comprueba que realmente podría viajar en JSON.
    return json.loads(json.dumps(data, ensure_ascii=False, allow_nan=False))


def desktop_a_sobre(tipo: str, datos: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(datos, dict):
        raise TypeError('Borrador DESKTOP inválido')
    clean = _json_safe(datos)
    # Las rutas locales no pueden utilizarse en el otro dispositivo.
    if clean.get('__evidencias_locales') or clean.get('__archivos_adjuntos_locales'):
        raise IntercambioNoSeguro('Primero se deben transferir las evidencias locales')
    if any(clean.get(k) for k in ('lev_anotacion_plano_json', 'lev_archivos_adjuntos_json', 'lev_evidencias_json')):
        for k in ('lev_anotacion_plano_json','lev_archivos_adjuntos_json','lev_evidencias_json'):
            value = clean.get(k)
            if not value: continue
            try: parsed = json.loads(value) if isinstance(value,str) else value
            except ValueError: raise IntercambioNoSeguro(f'Adjunto inválido en {k}')
            if parsed not in ([], {}, {'habilitado': False, 'imagen_base64': ''}):
                raise IntercambioNoSeguro(f'Existe contenido multimedia en {k}')
    return {
        'schema': SCHEMA, 'module': MODULE, 'source': 'DESKTOP',
        'lift_type': tipo, 'common': {
            common: str(clean.get(field) or '') for common,field in COMMON_TO_DESKTOP.items()
        },
        'native': {'desktop': clean},
        'media_transfer_complete': True,
    }


def field_a_vista_desktop(sobre: dict[str, Any]) -> dict[str, str]:
    """Vista de campos compartidos, NO restauración del formulario entero.

    Rechaza expresamente respuestas técnicas, evidencias y firmas hasta que sus
    transformaciones hayan sido validadas. No se descartan silenciosamente.
    """
    if not isinstance(sobre, dict) or sobre.get('schema') != SCHEMA or sobre.get('module') != MODULE:
        raise IntercambioNoSeguro('Esquema de borrador desconocido')
    if sobre.get('source') != 'FIELD':
        raise IntercambioNoSeguro('No es un borrador FIELD')
    native = sobre.get('native', {}).get('field')
    if not isinstance(native, dict):
        raise IntercambioNoSeguro('No se dispone del borrador nativo FIELD')
    if native.get('formValues') or native.get('evidences') or native.get('signatureData') or native.get('signedAt'):
        raise IntercambioNoSeguro('Contiene respuestas técnicas, evidencias o firmas sin conversor')
    common = sobre.get('common')
    if not isinstance(common, dict):
        raise IntercambioNoSeguro('Faltan los datos compartidos')
    return {column: str(common.get(name) or '') for name,column in COMMON_TO_DESKTOP.items()}


def restaurar_desktop_nativo(sobre: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if sobre.get('schema') != SCHEMA or sobre.get('module') != MODULE or sobre.get('source') != 'DESKTOP':
        raise IntercambioNoSeguro('No es un borrador nativo DESKTOP')
    native = sobre.get('native', {}).get('desktop')
    if not isinstance(native, dict):
        raise IntercambioNoSeguro('Falta la captura original')
    return str(sobre.get('lift_type') or ''), deepcopy(native)
