"""Sesión AXIA compatible con FIELD para borradores privados.

Se emite durante el login normal y se conserva únicamente en RAM.
No almacena contraseñas, JWT ni llaves de servicio en disco.
"""
from __future__ import annotations

import time
import requests

_TOKEN: str | None = None
_USUARIO: str | None = None
_EXPIRA: int = 0


def solicitar_sesion(nickname: str, password: str, expected_user_id: object) -> tuple[str, int]:
    """Utiliza la Edge Function existente mobile-auth, sin solicitar segundo login."""
    from supabase_config import SUPABASE_URL, SUPABASE_KEY
    response = requests.post(
        f"{SUPABASE_URL.rstrip('/')}/functions/v1/mobile-auth",
        json={"nickname": nickname, "password": password, "deviceName": "AXIA DESKTOP", "appVersion": "borradores"},
        headers={"apikey": SUPABASE_KEY, "content-type": "application/json"},
        timeout=(6, 12), allow_redirects=False,
    )
    response.raise_for_status()
    body = response.json()
    data = body.get("data") if isinstance(body, dict) and body.get("ok") else None
    if not isinstance(data, dict) or str(data.get("id_usuario")) != str(expected_user_id):
        raise PermissionError("La sesión compartida no coincide con la cuenta de AXIA DESKTOP")
    token, expires = str(data.get("accessToken") or ""), int(data.get("expiresAtEpochSeconds") or 0)
    if not token or expires <= time.time():
        raise PermissionError("No se obtuvo una sesión compartida válida")
    return token, expires


def establecer_sesion(token: str | None, usuario_id: object, expira: int = 0) -> None:
    global _TOKEN, _USUARIO, _EXPIRA
    _TOKEN = token or None
    _USUARIO = str(usuario_id) if token else None
    _EXPIRA = int(expira) if token else 0


def obtener_sesion(usuario_id: object) -> str | None:
    if _USUARIO == str(usuario_id) and _TOKEN and _EXPIRA > time.time() + 30:
        return _TOKEN
    return None


def cerrar_sesion() -> None:
    establecer_sesion(None, None)
