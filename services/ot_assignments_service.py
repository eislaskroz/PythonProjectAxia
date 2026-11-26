import os
import re
import requests
from urllib.parse import urlsplit


def consultar_asignaciones(ot_id, action='list', expected=None, users=None):
    from app_context import obtener_usuario_actual
    from services.sesion_axia_compartida import obtener_sesion
    from supabase_config import SUPABASE_URL, SUPABASE_KEY
    actor = obtener_usuario_actual()
    token = obtener_sesion(actor.get('id_usuario'))
    grant = os.getenv('AXIA_DESKTOP_EVIDENCE_GRANT', '').strip()
    if not token or not re.fullmatch(r'[a-f0-9]{64}', grant):
        raise RuntimeError('Inicia sesión nuevamente y verifica la autorización corporativa con TI.')
    base = str(SUPABASE_URL).rstrip('/')
    if urlsplit(base).scheme != 'https':
        raise RuntimeError('Configuración HTTPS inválida.')
    payload = {'ot_id': int(ot_id), 'action': action}
    if action == 'save':
        payload.update(expected=expected, users=users)
    try:
        r = requests.post(base+'/functions/v1/desktop-ot-assignments', json=payload,
            headers={'Authorization': 'Bearer '+token, 'apikey': SUPABASE_KEY, 'X-AXIA-Desktop-Grant': grant},
            timeout=(6,20), allow_redirects=False)
        data = r.json()
    except (requests.RequestException, ValueError):
        raise RuntimeError('No se pudo confirmar la operación. Vuelve a consultar antes de reintentar.') from None
    if r.status_code != 200 or data.get('ok') is not True:
        messages = {401:'Sesión inválida.',403:'Sin autorización corporativa o de administrador.',404:'OT no encontrada.',409:'Conflicto o límite de consulta. Vuelve a abrir la ventana.',422:'OT cerrada o personal inválido.'}
        raise RuntimeError(messages.get(r.status_code, 'No fue posible procesar las asignaciones.'))
    return data
