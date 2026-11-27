import hashlib
import io
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image
from services.evidence_image_format import preparar_imagen
from services import desktop_evidence_recovery as recovery
from services import desktop_historical_upload as upload


def test_webp_disguised_as_png(tmp_path):
    path = tmp_path / 'logo.png'
    Image.new('RGB', (30, 40), 'blue').save(path, format='WEBP')
    original = path.read_bytes()
    raw, name, ext, mime = preparar_imagen(path)
    assert (name, ext, mime) == ('logo.png', 'png', 'image/png')
    assert Image.open(io.BytesIO(raw)).format == 'PNG'
    assert path.read_bytes() == original
    assert preparar_imagen(path)[0] == raw


def test_valid_png_keeps_bytes(tmp_path):
    path = tmp_path / 'logo.png'
    Image.new('RGBA', (10, 10)).save(path)
    assert preparar_imagen(path)[0] == path.read_bytes()


def test_invalid_image(tmp_path):
    path = tmp_path / 'logo.png'
    path.write_bytes(b'not an image')
    with pytest.raises(ValueError):
        preparar_imagen(path)


def test_jpeg_with_extra_bytes(tmp_path):
    path = tmp_path / 'logo.jpg'
    Image.new('RGB', (10, 10)).save(path)
    path.write_bytes(path.read_bytes() + b'extra')
    raw, name, ext, mime = preparar_imagen(path)
    assert (name, ext, mime) == ('logo.png', 'png', 'image/png')
    assert raw.startswith(b'\x89PNG')


@pytest.fixture
def recovery_env(monkeypatch, tmp_path):
    path = tmp_path / 'logo.png'
    Image.new('RGB', (10, 10)).save(path)
    record = {'id_bitacora': 26, 'bit_folio': 'BIT-00026', 'bit_ot_folio': 'OT-00011', 'bit_fotos': []}
    state = dict(record)
    update = Mock()
    evidence = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'storage_path': 'example'}
    send = Mock(return_value=[evidence])
    monkeypatch.setattr(recovery, 'obtener_usuario_actual', lambda: {'usu_tipo': 1})
    monkeypatch.setenv('AXIA_HISTORICAL_EVIDENCE_SECURE', '1')
    monkeypatch.setitem(sys.modules, 'services.bitacora_evidencias_service', SimpleNamespace(subir_evidencias_bitacora=send))
    class Query:
        def __init__(self):
            self.payload = None
            self.filters = {}
        def select(self, *a): return self
        def update(self, payload):
            self.payload = payload
            return self
        def eq(self, key, value):
            self.filters[key] = value
            return self
        def limit(self, n): return self
        def execute(self):
            if self.payload is not None:
                update(self.payload, self.filters)
                if state['bit_fotos'] == [] and self.filters.get('bit_fotos') == '[]':
                    state.update(self.payload)
            return SimpleNamespace(data=[dict(state)])
    monkeypatch.setitem(sys.modules, 'supabase_config', SimpleNamespace(supabase=SimpleNamespace(table=lambda name: Query())))
    return record, state, path, send, update, evidence


def test_recovery_updates_only_photos(recovery_env):
    record, state, path, send, update, evidence = recovery_env
    assert recovery.recuperar_bitacora(record, [path]) == [evidence]
    update.assert_called_once_with({'bit_fotos': [evidence]}, {'id_bitacora': 26, 'bit_folio': 'BIT-00026', 'bit_ot_folio': 'OT-00011', 'bit_fotos': '[]'})
    assert state['bit_fotos'] == [evidence]


def test_recovery_refuses_existing_evidence(recovery_env):
    record, state, path, send, update, evidence = recovery_env
    state['bit_fotos'] = [evidence]
    with pytest.raises(RuntimeError, match='sobrescribirá'):
        recovery.recuperar_bitacora(record, [path])
    send.assert_not_called()
    update.assert_not_called()


def test_recovery_refuses_other_record(recovery_env):
    record, state, path, send, update, evidence = recovery_env
    record['id_bitacora'] = 25
    with pytest.raises(RuntimeError, match='no autorizada'):
        recovery.recuperar_bitacora(record, [path])
    send.assert_not_called()


def test_recovery_refuses_multiple_images(recovery_env):
    record, state, path, send, update, evidence = recovery_env
    with pytest.raises(ValueError, match='exactamente una'):
        recovery.recuperar_bitacora(record, [path, path])
    send.assert_not_called()
