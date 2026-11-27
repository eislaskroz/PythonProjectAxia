from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import quote, urlsplit
from uuid import UUID, uuid5

import requests
from core.date_utils import normalizar_campos_fecha
from services.evidence_image_format import preparar_imagen, EXTENSIONS
from ui.pdf_progress import con_progreso_pdf, progreso_pdf

BUCKET = 'bitacoras-evidencias'


def activo():
    return os.getenv('AXIA_OBC_ANEXOS_V2', '').strip() == '1'


def preparar_archivos(solicitud, fotos, planos):
    namespace = UUID(str(solicitud))
    entradas = [('foto', x) for x in fotos] + [('plano', x) for x in planos]
    if len(entradas) > 20:
        raise ValueError('El máximo es de 20 anexos por solicitud.')
    resultado = []
    for indice, (clase, ruta) in enumerate(entradas):
        p = Path(ruta)
        ext = p.suffix.lower()
        limite = 20 * 1024 * 1024 if clase == 'foto' else 30 * 1024 * 1024
        if clase == 'foto' or ext in EXTENSIONS:
            raw, nombre, extension, mime = preparar_imagen(p, max_bytes=limite)
            ext = 'jpg' if mime == 'image/jpeg' else extension
        else:
            with p.open('rb') as f:
                raw = f.read(limite + 1)
            nombre = p.name
            mime = {'.pdf':'application/pdf','.dwg':'image/vnd.dwg','.dxf':'image/vnd.dxf'}.get(ext)
            valido = (mime == 'application/pdf' and raw.startswith(b'%PDF-') or
                      mime == 'image/vnd.dwg' and re.match(rb'AC10[0-9]{2}',raw) or
                      mime == 'image/vnd.dxf' and (raw.startswith(b'AutoCAD Binary DXF') or re.match(rb'\s*0\s*SECTION\b',raw[:512],re.I)))
            if not valido:
                raise ValueError(f'{p.name}: formato técnico incompatible.')
            ext = ext.lstrip('.')
        if not 12 <= len(raw) <= limite or not 0 < len(nombre.strip()) <= 160 or re.search(r'[\x00-\x1f\x7f/\\]', nombre):
            raise ValueError(f'{p.name}: tamaño o nombre no permitido.')
        archivo = str(uuid5(namespace, f'{clase}:{indice}'))
        resultado.append(dict(archivo=archivo,clase=clase,nombre=nombre,mime=mime,tamano=len(raw),sha256=hashlib.sha256(raw).hexdigest(),ext=ext,raw=raw))
    return resultado


def datos_limpios(datos):
    return normalizar_campos_fecha({k:v for k,v in datos.items() if k not in {'obc_request_id','obc_folio','creado_por','obc_estatus','obc_evidencias_json','obc_archivos_adjuntos_json'}})


def huella(datos, anexos):
    contenido = [datos,[{k:v for k,v in a.items() if k!='raw'} for a in anexos]]
    return hashlib.sha256(json.dumps(contenido,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


@con_progreso_pdf(titulo='Guardando Obra Civil', ventana='AXIA · Cargando anexos')
def sincronizar(solicitud, usuario_id, operacion, datos, anexos, folio=None, autorizacion=None):
    from supabase_config import SUPABASE_URL, SUPABASE_KEY
    from services.sesion_axia_compartida import obtener_sesion
    solicitud = str(UUID(str(solicitud)))
    base = str(SUPABASE_URL).rstrip('/')
    u = urlsplit(base)
    token = obtener_sesion(usuario_id)
    grant = os.getenv('AXIA_DESKTOP_EVIDENCE_GRANT','').strip()
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.path or u.query or u.fragment:
        raise ValueError('Configuración HTTPS inválida.')
    if not token or not re.fullmatch(r'[a-f0-9]{64}',grant):
        raise PermissionError('Inicia sesión con autorización corporativa de evidencias.')
    headers = {'Authorization':f'Bearer {token}','apikey':str(SUPABASE_KEY),'X-AXIA-Desktop-Grant':grant,'Content-Type':'application/json'}
    def llamar(accion, **kwargs):
        try:
            r=requests.post(base+'/functions/v1/axia-obras-civiles-anexos-v2',headers=headers,json=dict(accion=accion,solicitud=solicitud,operacion=operacion,**kwargs),timeout=(10,150),allow_redirects=False)
            body=r.json()
        except (requests.RequestException,ValueError):
            raise RuntimeError('No se confirmó la operación. Conserva la solicitud y reintenta sin cambios.') from None
        if not isinstance(body,dict) or r.status_code!=200 or body.get('ok') is not True:
            b=body if isinstance(body,dict) else {}
            raise RuntimeError(f'HTTP {r.status_code}: {str(b.get("error") or "Operación no confirmada.")[:250]} {str(b.get("supportCode") or "")[:100]}')
        if not isinstance(body.get('resultado'),dict):
            raise RuntimeError('Respuesta de Obra Civil inválida.')
        return body['resultado']
    progreso_pdf('Abriendo sesión de anexos…')
    sesion=llamar('abrir_sesion',folio=folio,autorizacion=autorizacion)
    if sesion.get('solicitud')!=solicitud or sesion.get('operacion')!=operacion or str(sesion.get('id_usuario'))!=str(usuario_id) or sesion.get('estado') not in ('ABIERTA','COMPLETADA'):
        raise RuntimeError('La sesión no corresponde a la solicitud.')
    fotos, planos = [], []
    for i,a in enumerate(anexos,1):
        prefijo='obras-civiles' if a['clase']=='foto' else 'obras-civiles-archivos'
        carpeta=('SOLICITUD-' if operacion=='ALTA' else 'EDICION-')+solicitud
        ruta=f'{prefijo}/{carpeta}/{a["archivo"]}_archivo.{a["ext"]}'
        if sesion['estado']=='ABIERTA':
            progreso_pdf('Cargando y verificando anexos…',i-1,len(anexos))
            preparado=llamar('preparar_anexo',**{k:a[k] for k in ('archivo','clase','nombre','mime','tamano','sha256')})
            if preparado.get('subido') is False:
                firma=preparado.get('token')
                if preparado.get('bucket')!=BUCKET or preparado.get('ruta')!=ruta or not isinstance(firma,str) or not firma:
                    raise RuntimeError('Permiso de subida inválido.')
                try:
                    r=requests.put(base+'/storage/v1/object/upload/sign/'+BUCKET+'/'+quote(ruta,safe='/'),params={'token':firma},headers={'apikey':str(SUPABASE_KEY),'Content-Type':a['mime'],'x-upsert':'false'},data=a['raw'],timeout=(10,120),allow_redirects=False)
                except requests.RequestException:
                    raise RuntimeError('Carga no confirmada. Reintenta la misma solicitud.') from None
                if r.status_code not in (200,201):
                    raise RuntimeError(f'Storage respondió HTTP {r.status_code}. Reintenta sin modificar los anexos.')
                confirmado=llamar('confirmar_anexo',archivo=a['archivo'])
            elif preparado.get('subido') is True:
                confirmado=preparado.get('anexo')
            else:
                raise RuntimeError('Estado de carga inválido.')
            if not isinstance(confirmado,dict) or confirmado.get('estado')!='CONFIRMADA' or confirmado.get('archivo')!=a['archivo'] or confirmado.get('storage_path')!=ruta or confirmado.get('sha256')!=a['sha256'] or confirmado.get('size_bytes')!=a['tamano'] or confirmado.get('mime_type')!=a['mime']:
                raise RuntimeError('Integridad del anexo no confirmada.')
            progreso_pdf('Cargando y verificando anexos…',i,len(anexos))
        meta=dict(nombre=a['nombre'],bucket=BUCKET,storage_path=ruta,url='',mime=a['mime'],sha256=a['sha256'],size_bytes=a['tamano'],archivo=a['archivo'])
        (fotos if a['clase']=='foto' else planos).append(meta)
        if a['clase']=='plano':
            meta['tipo']='archivo_tecnico'
    progreso_pdf('Confirmando documento y anexos…')
    resultado=llamar('finalizar',datos=datos,archivos=[a['archivo'] for a in anexos])
    if resultado.get('solicitud')!=solicitud or not resultado.get('obc_id') or not re.fullmatch(r'OBC-[0-9]{4,}',str(resultado.get('obc_folio',''))) or resultado.get('total_anexos')!=len(anexos) or type(resultado.get('alreadyCompleted')) is not bool:
        raise RuntimeError('El servidor no confirmó el documento.')
    return resultado,fotos,planos
