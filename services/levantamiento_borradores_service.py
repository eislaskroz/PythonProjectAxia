"""Borradores locales temporales de levantamientos.

Los borradores se guardan por usuario en AppData/local del equipo. No se envían a
Supabase hasta que el usuario pulsa Guardar en el formulario.
"""
from __future__ import annotations

import json
import os

from security.data_encryption import cifrar_valor, descifrar_valor
from datetime import datetime
from uuid import uuid4
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
    previo = cargar_borrador(usuario) or {}
    cloud = previo.get("sincronizacion") if isinstance(previo.get("sincronizacion"), dict) else {}
    cloud = {
        "clave_cliente": cloud.get("clave_cliente") or str(uuid4()),
        "revision": int(cloud.get("revision") or 0),
        "estado": "pendiente",
    }
    payload = {
        "version": 1,
        "sincronizacion": cloud,
        "guardado_en": datetime.now().isoformat(timespec="microseconds"),
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


def confirmar_sincronizacion(usuario: dict | None, clave_cliente: str, revision: int, guardado_en: str) -> bool:
    """Confirma la revision remota solo si la captura local no cambió durante la petición."""
    actual = cargar_borrador(usuario)
    if not actual:
        return False
    cloud = actual.get("sincronizacion") or {}
    if cloud.get("clave_cliente") != clave_cliente:
        return False
    # Se conserva la revisión devuelta por el servidor aun si el autoguardado
    # local avanzó durante la petición. En ese caso queda pendiente de
    # sincronizar la captura más reciente, evitando una colisión falsa en el
    # próximo intento por reutilizar la revisión anterior.
    misma_captura = actual.get("guardado_en") == guardado_en
    cloud.update({"revision": int(revision), "estado": "sincronizado" if misma_captura else "pendiente"})
    actual["sincronizacion"] = cloud
    ruta = ruta_borrador(usuario)
    temporal = ruta.with_suffix(".tmp")
    temporal.write_text(cifrar_valor(json.dumps(actual, ensure_ascii=False)), encoding="utf-8")
    temporal.replace(ruta)
    return misma_captura
