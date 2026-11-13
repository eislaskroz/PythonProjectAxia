import hashlib
import pytest
from services.levantamiento_medios_compartidos import (
    MediaRef, EvidenciaNoTransferible, leer_archivo_local, BUCKET,
)

DRAFT = '123e4567-e89b-42d3-a456-426614174000'
FILE = '11111111-2222-4333-8444-555555555555.png'
BYTES = b'\x89PNG\r\n\x1a\n' + b'hello-world'


def test_media_valid_path_and_digest():
    item = dict(bucket=BUCKET, path=f'4/{DRAFT}/{FILE}', size=len(BYTES),
                sha256=hashlib.sha256(BYTES).hexdigest(), mime='image/png')
    assert MediaRef.from_json(item, DRAFT, 4).size == len(BYTES)


def test_media_cross_user_rejected():
    item = dict(bucket=BUCKET, path=f'4/{DRAFT}/{FILE}', size=len(BYTES),
                sha256=hashlib.sha256(BYTES).hexdigest(), mime='image/png')
    with pytest.raises(EvidenciaNoTransferible):
        MediaRef.from_json(item, DRAFT, 5)


def test_media_cross_draft_rejected():
    item = dict(bucket=BUCKET, path=f'4/{DRAFT}/{FILE}', size=len(BYTES),
                sha256=hashlib.sha256(BYTES).hexdigest(), mime='image/png')
    with pytest.raises(EvidenciaNoTransferible):
        MediaRef.from_json(item, '00000000-0000-4000-8000-000000000001', 4)


def test_local_signature_is_checked(tmp_path):
    bad = tmp_path / 'fake.png'
    bad.write_bytes(b'not a png')
    with pytest.raises(EvidenciaNoTransferible):
        leer_archivo_local(bad)


def test_local_good_png(tmp_path):
    good = tmp_path / 'image.png'
    good.write_bytes(BYTES)
    assert leer_archivo_local(good) == (BYTES, 'image/png')


def test_local_size_limit(tmp_path):
    big = tmp_path / 'huge.png'
    big.write_bytes(BYTES + b'0' * (8 * 1024 * 1024))
    with pytest.raises(EvidenciaNoTransferible):
        leer_archivo_local(big)
