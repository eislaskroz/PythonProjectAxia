from pathlib import Path
from types import SimpleNamespace
import base64
import json
import pytest

from services.levantamiento_evidencias_borrador import preparar_medios_borrador, sanear_json_remoto

DRAFT = 'd0000000-0000-4000-8000-000000000001'

class Client:
    def __init__(self): self.sent = []
    def subir(self, draft, path):
        data = Path(path).read_bytes()
        self.sent.append((draft, data))
        return SimpleNamespace(bucket='axia-borradores-medios', path='20/'+draft+'/file.png', sha256='a'*64, size=len(data), mime='image/png')

def test_without_media():
    source={'lev_descripcion':'Prueba','__evidencias_locales':[]}
    result=preparar_medios_borrador(source,DRAFT,Client())
    assert result['media']==[] and result['desktop']['lev_descripcion']=='Prueba'
    assert source['__evidencias_locales']==[]

def test_two_files_and_annotation(tmp_path):
    data=b'\x89PNG\r\n\x1a\n'+b'xyz'
    p=tmp_path/'foto.png'; p.write_bytes(data)
    input_={'__evidencias_locales':[str(p)],'__archivos_adjuntos_locales':[],
            'lev_anotacion_plano_json':json.dumps({'habilitado':True,'imagen_base64':base64.b64encode(data).decode()})}
    client=Client()
    result=preparar_medios_borrador(input_,DRAFT,client)
    assert len(client.sent)==2 and len(result['media'])==2
    assert result['desktop']['__evidencias_locales']==[]
    assert json.loads(result['desktop']['lev_anotacion_plano_json'])['imagen_base64']==''
    assert input_['__evidencias_locales']==[str(p)]

def test_failed_transfer_leaves_original(tmp_path):
    path=tmp_path/'missing.png'
    source={'__evidencias_locales':[str(path)]}
    class Broken:
        def subir(self, draft, path): raise ValueError('missing')
    with pytest.raises(ValueError): preparar_medios_borrador(source,DRAFT,Broken())
    assert source['__evidencias_locales']==[str(path)]

def test_sanitize_pre_upload():
    data={'__evidencias_locales':['C:/sensitive.jpg'],
          'lev_anotacion_plano_json':json.dumps({'habilitado':True,'imagen_base64':'abcd'}),
          'lev_descripcion':'Prueba'}
    result=sanear_json_remoto(data)
    assert 'C:/' not in json.dumps(result) and 'abcd' not in json.dumps(result)
    assert data['__evidencias_locales'] == ['C:/sensitive.jpg']
