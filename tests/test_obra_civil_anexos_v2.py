import io
import sys
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock

import pytest
from PIL import Image
from services import obra_civil_anexos_v2 as svc
from services import desktop_historical_evidence as historical
from services.desktop_evidence_access import EvidenciaNoDisponible


@pytest.fixture
def captura(tmp_path):
    p=tmp_path/'logo.png'
    Image.new('RGB',(40,40),'blue').save(p,'WEBP')
    q=tmp_path/'plano.pdf'
    q.write_bytes(b'%PDF-1.7\nprueba\n%%EOF')
    return str(uuid4()),p,q


def test_normalizacion_e_identificadores(captura):
    solicitud,p,q=captura
    a=svc.preparar_archivos(solicitud,[p],[q])
    b=svc.preparar_archivos(solicitud,[p],[q])
    assert a==b
    assert a[0]['mime']=='image/png' and a[0]['raw'].startswith(b'\x89PNG')
    assert p.read_bytes().startswith(b'RIFF')
    assert a[1]['mime']=='application/pdf'
    assert a[0]['archivo']!=a[1]['archivo']
    assert svc.huella({'a':1},a)!=svc.huella({'a':2},b)


def test_rechaza_formato_y_manifiesto(captura):
    solicitud,p,q=captura
    with pytest.raises(ValueError): svc.preparar_archivos(solicitud,[p]*21,[])
    q.write_bytes(b'invalido')
    with pytest.raises(ValueError): svc.preparar_archivos(solicitud,[],[q])


def test_datos_limpios():
    assert svc.datos_limpios({'obc_fecha':'27/11/2026','obc_folio':'OBC-0001','creado_por':'x','obc_evidencias_json':'[]'})=={'obc_fecha':'2026-11-27'}


@pytest.mark.parametrize('operacion,completada,mal_ruta', [('ALTA',False,False),('EDICION',False,False),('REVISION_ESI',False,False),('ALTA',True,False),('ALTA',False,True)])
def test_sincronizar(captura,monkeypatch,operacion,completada,mal_ruta):
    solicitud,p,q=captura
    a=svc.preparar_archivos(solicitud,[p],[q]); folio=None if operacion=='ALTA' else 'OBC-0001'; autorizacion=str(uuid4()) if operacion=='REVISION_ESI' else None
    monkeypatch.setenv('AXIA_DESKTOP_EVIDENCE_GRANT','a'*64)
    monkeypatch.setitem(sys.modules,'supabase_config',SimpleNamespace(SUPABASE_URL='https://example.supabase.co',SUPABASE_KEY='anon'))
    monkeypatch.setitem(sys.modules,'services.sesion_axia_compartida',SimpleNamespace(obtener_sesion=lambda uid:'test'))
    llamados=[]
    def respond(url,**kw):
        b=kw['json']; accion=b['accion']; llamados.append(accion)
        assert b['solicitud']==solicitud and b['operacion']==operacion and kw['allow_redirects'] is False
        if accion=='abrir_sesion':
            assert b['folio']==folio and b['autorizacion']==autorizacion
            out=dict(solicitud=solicitud,operacion=operacion,id_usuario=2,estado='COMPLETADA' if completada else 'ABIERTA')
        elif accion in ('preparar_anexo','confirmar_anexo'):
            item=next(x for x in a if x['archivo']==b['archivo']); prefijo='obras-civiles' if item['clase']=='foto' else 'obras-civiles-archivos'; carpeta=('SOLICITUD-' if operacion=='ALTA' else 'EDICION-')+solicitud; ruta=f'{prefijo}/{carpeta}/{item["archivo"]}_archivo.{item["ext"]}'
            out=dict(subido=False,bucket=svc.BUCKET,ruta='incorrecta' if mal_ruta else ruta,token='signed') if accion=='preparar_anexo' else dict(estado='CONFIRMADA',archivo=item['archivo'],storage_path=ruta,sha256=item['sha256'],size_bytes=item['tamano'],mime_type=item['mime'])
        else:
            assert b['archivos']==[x['archivo'] for x in a]
            out=dict(solicitud=solicitud,obc_id='11',obc_folio='OBC-0011',total_anexos=2,alreadyCompleted=completada)
        return SimpleNamespace(status_code=200,json=lambda:dict(ok=True,resultado=out))
    put=Mock(return_value=SimpleNamespace(status_code=200)); monkeypatch.setattr(svc.requests,'post',respond);monkeypatch.setattr(svc.requests,'put',put)
    if mal_ruta:
        with pytest.raises(RuntimeError): svc.sincronizar(solicitud,2,operacion,{},a,folio,autorizacion)
        assert put.call_count==0 and 'finalizar' not in llamados
    else:
        r,fotos,planos=svc.sincronizar(solicitud,2,operacion,{},a,folio,autorizacion)
        assert r['alreadyCompleted']==completada and len(fotos)==len(planos)==1 and fotos[0]['url']==''
        assert put.call_count==(0 if completada else 2)
        assert llamados[-1]=='finalizar'


def test_rutas_obc(captura):
    solicitud,_,_=captura
    ruta=f'obras-civiles/SOLICITUD-{solicitud}/{uuid4()}_archivo.png'
    assert historical.ruta_historica({'bucket':svc.BUCKET,'storage_path':ruta},'OBC-0011','https://example.supabase.co')==ruta
    with pytest.raises(EvidenciaNoDisponible): historical.ruta_historica({'bucket':svc.BUCKET,'storage_path':ruta},'BIT-00011','https://example.supabase.co')
