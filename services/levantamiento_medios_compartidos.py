"""Etapa 2C: cliente de transferencia verificada de evidencias AXIA.

No modifica borradores locales ni los sube automáticamente. Una ruta del otro
ordenador/teléfono jamás se considera portable. El token es el de la sesión AXIA.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import UUID

MAX_FILE = 8 * 1024 * 1024
MIMES = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
         '.webp': 'image/webp', '.pdf': 'application/pdf'}
BUCKET = 'axia-borradores-medios'


class EvidenciaNoTransferible(ValueError):
    pass


@dataclass(frozen=True)
class MediaRef:
    bucket: str
    path: str
    sha256: str
    size: int
    mime: str

    @classmethod
    def from_json(cls, data: dict, draft_id: str, user_id: int) -> 'MediaRef':
        if not isinstance(data, dict):
            raise EvidenciaNoTransferible('Referencia inexistente')
        try:
            UUID(str(draft_id))
        except ValueError as exc:
            raise EvidenciaNoTransferible('Identificador de borrador inválido') from exc
        ref = cls(str(data.get('bucket') or ''), str(data.get('path') or ''),
                  str(data.get('sha256') or ''), int(data.get('size') or 0),
                  str(data.get('mime') or ''))
        prefix = f'{user_id}/{draft_id}/'
        if ref.bucket != BUCKET or not ref.path.startswith(prefix):
            raise EvidenciaNoTransferible('Referencia no pertenece a este usuario/borrador')
        basename = ref.path[len(prefix):]
        if not re.fullmatch(r'[0-9a-fA-F-]{36}\.(jpg|png|webp|pdf)', basename):
            raise EvidenciaNoTransferible('Ruta de evidencia inválida')
        if not re.fullmatch(r'[0-9a-f]{64}', ref.sha256):
            raise EvidenciaNoTransferible('Huella digital inválida')
        if not 0 < ref.size <= MAX_FILE or ref.mime not in MIMES.values():
            raise EvidenciaNoTransferible('Tamaño o formato inválido')
        return ref


def _validate_signature(payload: bytes, mime: str) -> None:
    good = {
        'image/jpeg': payload.startswith(b'\xff\xd8\xff'),
        'image/png': payload.startswith(b'\x89PNG\r\n\x1a\n'),
        'image/webp': payload.startswith(b'RIFF') and payload[8:12] == b'WEBP',
        'application/pdf': payload.startswith(b'%PDF-'),
    }
    if not good.get(mime, False):
        raise EvidenciaNoTransferible('El contenido del archivo no coincide con el formato')


def leer_archivo_local(file_path: str | Path) -> tuple[bytes, str]:
    path = Path(file_path)
    mime = MIMES.get(path.suffix.lower())
    if not mime or not path.is_file() or path.is_symlink():
        raise EvidenciaNoTransferible('Archivo local inválido o formato no admitido')
    if path.stat().st_size > MAX_FILE:
        raise EvidenciaNoTransferible('El archivo excede el límite de 8 MB')
    payload = path.read_bytes()
    if not payload or len(payload) > MAX_FILE:
        raise EvidenciaNoTransferible('Archivo vacío o demasiado grande')
    _validate_signature(payload, mime)
    return payload, mime


class MediosCompartidos:
    def __init__(self, supabase_url: str, token_supplier: Callable[[], str], user_id: int):
        if not supabase_url.startswith('https://'):
            raise ValueError('Se requiere HTTPS')
        self.endpoint = supabase_url.rstrip('/') + '/functions/v1/axia-borradores-medios'
        self.token_supplier = token_supplier
        self.user_id = user_id

    def _headers(self, **extra: str) -> dict[str, str]:
        token = self.token_supplier()
        if not token:
            raise EvidenciaNoTransferible('La sesión AXIA no está disponible')
        return {'Authorization': 'Bearer ' + token, **extra}

    def subir(self, borrador_id: str, local_path: str | Path) -> MediaRef:
        UUID(borrador_id)
        payload, mime = leer_archivo_local(local_path)
        digest = hashlib.sha256(payload).hexdigest()
        req = Request(self.endpoint + '?' + urlencode({'borrador': borrador_id}),
                      data=payload, method='POST', headers=self._headers(
                          **{'Content-Type': mime, 'X-AXIA-SHA256': digest}))
        with urlopen(req, timeout=45) as response:
            result = json.loads(response.read().decode('utf-8'))
        if not result.get('ok'):
            raise EvidenciaNoTransferible('El servidor no confirmó la transferencia')
        ref = MediaRef.from_json(result['media'], borrador_id, self.user_id)
        if ref.sha256 != digest or ref.size != len(payload):
            raise EvidenciaNoTransferible('El servidor reportó una huella o tamaño incorrecto')
        return ref

    def bajar(self, borrador_id: str, ref: MediaRef) -> bytes:
        checked = MediaRef.from_json(vars(ref), borrador_id, self.user_id)
        url = self.endpoint + '?' + urlencode({'borrador': borrador_id, 'ruta': checked.path})
        with urlopen(Request(url, headers=self._headers()), timeout=45) as response:
            payload = response.read(MAX_FILE + 1)
        if len(payload) != checked.size or hashlib.sha256(payload).hexdigest() != checked.sha256:
            raise EvidenciaNoTransferible('La evidencia descargada no coincide con la original')
        _validate_signature(payload, checked.mime)
        return payload
