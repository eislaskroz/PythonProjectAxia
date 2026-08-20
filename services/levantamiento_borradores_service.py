"""Borradores locales temporales de levantamientos.

Los borradores se guardan por usuario en AppData/local del equipo. No se envían a
Supabase hasta que el usuario pulsa Guardar en el formulario.
"""
from __future__ import annotations

import json
import os

from security.data_encryption import cifrar_valor, descifrar_valor
from datetime import datetime
from pathlib import Path


def _base_dir() -> Path:
    raiz = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home())
    ruta = Path(raiz) / "AXIA" / "borradores"
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def _usuario_id(usuario: dict | None) -> str:
    usuario = usuario or {}
    valor = usuario.get("id_usuario") or usuario.get("usuario") or "desconocido"
    seguro = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(valor))
    return seguro or "desconocido"


def ruta_borrador(usuario: dict | None) -> Path:
    return _base_dir() / f"levantamiento_{_usuario_id(usuario)}.json"


def guardar_borrador(usuario: dict | None, tipo_levantamiento: str, datos: dict) -> Path:
    ruta = ruta_borrador(usuario)
    payload = {
        "version": 1,
        "guardado_en": datetime.now().isoformat(timespec="seconds"),
        "tipo_levantamiento": str(tipo_levantamiento or ""),
        "datos": datos or {},
    }
    temporal = ruta.with_suffix(".tmp")
    contenido = json.dumps(payload, ensure_ascii=False)
    temporal.write_text(cifrar_valor(contenido), encoding="utf-8")
    temporal.replace(ruta)
    return ruta


def cargar_borrador(usuario: dict | None) -> dict | None:
    ruta = ruta_borrador(usuario)
    if not ruta.exists():
        return None
    try:
        contenido = ruta.read_text(encoding="utf-8")
        datos = json.loads(descifrar_valor(contenido))
        return datos if isinstance(datos, dict) else None
    except Exception:
        return None


def eliminar_borrador(usuario: dict | None) -> bool:
    ruta = ruta_borrador(usuario)
    try:
        if ruta.exists():
            ruta.unlink()
        return True
    except Exception:
        return False
