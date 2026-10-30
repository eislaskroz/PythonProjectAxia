"""Adaptador del listado universal: unifica visualmente LEV/OBC, nunca mezcla sus tablas.

Las operaciones de Obra Civil se realizan exclusivamente por la Edge Function
con verificación de sesión; ningún UPDATE directo de db_obras_civiles se ejecuta.
"""
from __future__ import annotations

import json
from pathlib import Path


def _json(valor, default=None):
    if isinstance(valor, (dict, list)):
        return valor
    try:
        return json.loads(valor) if valor else ({} if default is None else default)
    except (TypeError, ValueError):
        return {} if default is None else default


def es_obra_civil(registro):
    return isinstance(registro, dict) and registro.get('_origen_tabla') == 'db_obras_civiles'


def transformar_obra_civil(obra):
    """Contrato visual de la ventana universal, sin fabricar ID de LEV."""
    original = dict(obra)
    ejecucion = _json(obra.get('obc_ejecucion_json'))
    general = ejecucion.get('_datos_generales_axia') or {}
    return {
        '_origen_tabla': 'db_obras_civiles', '_obc_original': original,
        'obc_id': obra.get('obc_id'), 'obc_folio': obra.get('obc_folio'),
        'lev_folio': str(obra.get('obc_folio') or ''),
        'lev_aco_numero': obra.get('obc_aco_numero') or '',
        'lev_cliente': obra.get('obc_cliente') or '',
        'lev_contacto': obra.get('obc_contacto') or '',
        'lev_correo': general.get('correo_encargado_sucursal') or '',
        'lev_telefono': general.get('telefono_encargado_sucursal') or '',
        'lev_direccion': obra.get('obc_direccion') or '',
        'lev_ubicacion': obra.get('obc_sucursal') or '',
        'lev_fecha_realizacion': obra.get('obc_fecha') or '',
        'lev_fecha_programada': obra.get('obc_fecha') or '',
        'lev_supervisor': obra.get('obc_supervisor') or '',
        'lev_tecnico': general.get('tecnico') or obra.get('obc_responsable_axia') or '',
        'lev_tipo': 'Obra Civil', 'lev_modalidad_operativa': 'Obra Civil',
        'lev_prioridad': '2',
        'lev_descripcion': obra.get('obc_nombre_proyecto') or '',
        'lev_requerimientos': obra.get('obc_tipo_giro') or '',
        'lev_observaciones': obra.get('obc_observaciones_iniciales') or '',
        'lev_detalle_tecnico_json': json.dumps(ejecucion, ensure_ascii=False),
        'lev_estatus': 'Validado' if obra.get('obc_validado_ventas') else 'Registrado',
        'lev_validado_ventas': bool(obra.get('obc_validado_ventas')),
        'fecha_registro': obra.get('fecha_registro') or '',
    }


def cambios_obra_civil_desde_formulario(registro, campos, descripcion, requerimientos, observaciones, detalle_texto):
    """Permite editar campos OBC disponibles sin pisar anexos, folio o claves."""
    if not es_obra_civil(registro):
        raise ValueError('No es un registro de Obra Civil.')
    original = registro['_obc_original']
    detalle = _json(detalle_texto)
    if not isinstance(detalle, dict):
        raise ValueError('El detalle técnico de Obra Civil debe ser un objeto JSON.')
    generales = dict(detalle.get('_datos_generales_axia') or {})
    generales.update({
        'tecnico': str(campos.get('lev_tecnico') or '').strip(),
        'telefono_encargado_sucursal': str(campos.get('lev_telefono') or '').strip(),
        'correo_encargado_sucursal': str(campos.get('lev_correo') or '').strip(),
    })
    detalle['_datos_generales_axia'] = generales
    datos = {
        'obc_cliente': str(campos.get('lev_cliente') or '').strip(),
        'obc_contacto': str(campos.get('lev_contacto') or '').strip(),
        'obc_direccion': str(campos.get('lev_direccion') or '').strip(),
        'obc_sucursal': str(campos.get('lev_ubicacion') or '').strip(),
        'obc_supervisor': str(campos.get('lev_supervisor') or '').strip(),
        'obc_fecha': str(campos.get('lev_fecha_realizacion') or '').strip(),
        'obc_nombre_proyecto': str(descripcion or '').strip(),
        'obc_tipo_giro': str(requerimientos or '').strip(),
        'obc_observaciones_iniciales': str(observaciones or '').strip(),
        'obc_ejecucion_json': json.dumps(detalle, ensure_ascii=False),
    }
    if not datos['obc_cliente'] or not datos['obc_nombre_proyecto']:
        raise ValueError('Cliente y Nombre del proyecto son obligatorios.')
    # Los ID vinculados a catálogos, folio y anexos no se tocan aquí.
    return datos


def generar_pdf_obra_civil_desde_registro(obra, *, ruta_salida=None, abrir=True):
    """Recrea el PDF estructurado a partir del registro persistido de Obra Civil."""
    from views.formato_helpers import generar_pdf_preview
    from services.axia_pdf_engine import AxiaPdfEngine
    ejecucion = _json(obra.get('obc_ejecucion_json'))
    general = ejecucion.get('_datos_generales_axia') or {}
    conceptos = ejecucion.get('_conceptos_obra') or []
    materiales = ejecucion.get('_materiales_miscelaneos') or []
    canalizacion = (ejecucion.get('_canalizacion_materiales') or {}).get('partidas') or []
    epp = (ejecucion.get('_epp') or {}).get('partidas') or []
    datos = {
        'Folio OBC': obra.get('obc_folio') or '', 'Fecha': obra.get('obc_fecha') or '',
        'ACO': obra.get('obc_aco_numero') or '',
        'Cliente': obra.get('obc_cliente') or '', 'Contacto': obra.get('obc_contacto') or '',
        'Sucursal': obra.get('obc_sucursal') or '', 'Dirección Fiscal': obra.get('obc_direccion') or '',
        'Teléfono': general.get('telefono_encargado_sucursal') or '',
        'Correo': general.get('correo_encargado_sucursal') or '',
        'Encargado de Proyecto': obra.get('obc_responsable_axia') or '',
        'Supervisor': obra.get('obc_supervisor') or '', 'Técnico': general.get('tecnico') or '',
        'Días de trabajo': obra.get('obc_dias_trabajo') or '',
        'Personas a considerar': obra.get('obc_personas_considerar') or '',
        'Tipo de giro': obra.get('obc_tipo_giro') or '',
        'Nombre del proyecto': obra.get('obc_nombre_proyecto') or '',
        'Superficie disponible': obra.get('obc_superficie_disponible') or '',
        'Superficie adecuada': obra.get('obc_superficie_adecuada') or '',
        'Planos arquitectónicos': obra.get('obc_planos_arquitectonicos') or '',
        'Requiere maquinaria': obra.get('obc_requiere_maquinaria') or '',
        'Permisos disponibles': obra.get('obc_permisos') or '',
        'Observaciones iniciales': obra.get('obc_observaciones_iniciales') or '',
        'Observaciones finales': obra.get('obc_observaciones_finales') or '',
        'Planos de acabados': obra.get('obc_planos_acabados') or '',
        'Generación de planos': obra.get('obc_generacion_planos') or '',
        'Etapa de acabados': obra.get('obc_etapa_acabados') or '',
        'Obra blanca': obra.get('obc_obra_blanca') or '',
        'Equipo de Protección Personal': '; '.join(str(p.get('epp') or '') for p in epp if isinstance(p, dict)),
        'Materiales misceláneos': '; '.join(str(p.get('material') or '') for p in materiales if isinstance(p, dict)),
        'Archivos PDF / planos': '; '.join(str(p.get('nombre') or '') for p in (_json(obra.get('obc_archivos_adjuntos_json'), []) or []) if isinstance(p, dict)),
    }
    # La evidencia ya subida permanece en Storage; no se simulan imágenes perdidas.
    # Las referencias de archivo se pueden listar sin requerir permiso de descarga.
    evidencia = _json(obra.get('obc_evidencias_json'), [])
    if evidencia:
        datos['Evidencias registradas'] = '; '.join(str(e.get('nombre') or e.get('storage_path') or '') for e in evidencia if isinstance(e, dict))
    def _filas(items, claves):
        return [{et: str(p.get(clave) or '') for et, clave in claves} for p in items if isinstance(p, dict)]
    secciones = [
        ('Ejecución', ['Actividad', 'Estado'], [{'Actividad': str(k), 'Estado': str(v)} for k, v in ejecucion.items() if not str(k).startswith('_')]),
        ('Conceptos de obra', ['Tipo','Partida','Unidad','Cantidad','Concepto'], _filas(conceptos, [('Tipo','tipo'),('Partida','partida'),('Unidad','unidad'),('Cantidad','cantidad'),('Concepto','concepto')])),
        ('Materiales misceláneos', ['Material','Cantidad','Unidad','Especificación'], _filas(materiales, [('Material','material'),('Cantidad','cantidad'),('Unidad','unidad'),('Especificación','especificacion')])),
        ('Canalización, cableado y materiales', ['Categoría','Tipo','Especificación','Cantidad','Unidad'], _filas(canalizacion, [('Categoría','categoria'),('Tipo','tipo'),('Especificación','especificacion'),('Cantidad','cantidad'),('Unidad','unidad')])),
    ]
    if ruta_salida is None:
        ruta_salida = AxiaPdfEngine._preview_path('Obra_Civil_' + str(obra.get('obc_folio') or 'OBC'))
    plano = _json(obra.get('obc_anotacion_plano_json'))
    if isinstance(plano, dict):
        datos['__anotacion_plano_base64'] = str(plano.get('imagen_base64') or '')
    # Recuperar imágenes desde el mismo bucket en que fueron subidas al guardar.
    # Si no pueden recuperarse, NO emitir un PDF que silenciosamente pierda evidencias.
    from tempfile import TemporaryDirectory
    from supabase_config import supabase
    from services.bitacora_evidencias_service import BUCKET
    with TemporaryDirectory(prefix='axia_obc_pdf_') as temporal:
        rutas = []
        for indice, evidencia in enumerate(evidencia or []):
            if not isinstance(evidencia, dict):
                continue
            path = str(evidencia.get('storage_path') or '').strip()
            if not path:
                continue
            extension = Path(path).suffix.lower()
            if extension not in ('.png', '.jpg', '.jpeg', '.webp'):
                continue
            destino = Path(temporal) / f'evidencia_{indice}{extension}'
            try:
                destino.write_bytes(supabase.storage.from_(BUCKET).download(path))
            except Exception as exc:
                raise RuntimeError(
                    'No fue posible recuperar una fotografía desde Supabase Storage. '
                    'No se generará un PDF incompleto; revisa los permisos del bucket.'
                ) from exc
            rutas.append(str(destino))
        datos['__evidencias_fotograficas'] = rutas
        return generar_pdf_preview('Obra Civil', datos, secciones_tabla=secciones,
                                   ruta_salida=Path(ruta_salida), abrir=abrir)
