from __future__ import annotations

from app_context import obtener_usuario_actual
from services.desktop_historical_upload import carga_historica_activa
from services.evidence_image_format import validar_imagenes
from ui.pdf_progress import con_progreso_pdf, progreso_pdf


def recuperacion_disponible(record):
    return (carga_historica_activa() and str(obtener_usuario_actual().get('usu_tipo')) == '1'
            and str(record.get('id_bitacora')) == '26' and record.get('bit_folio') == 'BIT-00026'
            and record.get('bit_ot_folio') == 'OT-00011')


@con_progreso_pdf(titulo='Recuperando evidencias', ventana='AXIA · Recuperando evidencias')
def recuperar_bitacora(record, rutas):
    from supabase_config import supabase
    from services.bitacora_evidencias_service import subir_evidencias_bitacora
    if not recuperacion_disponible(record):
        raise RuntimeError('Recuperación no autorizada para este documento.')
    rutas = list(rutas or [])
    if len(rutas) != 1:
        raise ValueError('Selecciona exactamente una fotografía de prueba.')
    validar_imagenes(rutas)

    def seleccionar():
        rows = supabase.table('db_bitacoras').select('id_bitacora,bit_folio,bit_ot_folio,bit_fotos').eq('id_bitacora', 26).eq('bit_folio', 'BIT-00026').eq('bit_ot_folio', 'OT-00011').limit(2).execute().data
        if not isinstance(rows, list) or len(rows) != 1:
            raise RuntimeError('No se pudo verificar la Bitácora existente.')
        return rows[0]

    actual = seleccionar()
    if actual.get('bit_fotos') != []:
        raise RuntimeError('La Bitácora ya contiene evidencias; no se sobrescribirá.')
    fotos = subir_evidencias_bitacora('BIT-00026', rutas)
    if len(fotos) != 1 or not fotos[0].get('sha256'):
        raise RuntimeError('No se confirmó la carga de la fotografía.')
    progreso_pdf('Vinculando evidencia a la Bitácora…')
    try:
        supabase.table('db_bitacoras').update({'bit_fotos': fotos}).eq('id_bitacora', 26).eq('bit_folio', 'BIT-00026').eq('bit_ot_folio', 'OT-00011').eq('bit_fotos', '[]').execute()
    except Exception:
        pass
    if seleccionar().get('bit_fotos') != fotos:
        raise RuntimeError('No se confirmó la vinculación. Conserva el archivo original y verifica la Bitácora antes de reintentar.')
    return fotos
