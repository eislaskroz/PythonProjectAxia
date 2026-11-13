"""Transferencia privada de adjuntos de un borrador DESKTOP a AXIA FIELD.

El archivo original queda en la PC. Se transfieren únicamente archivos cuyo formato,
contenido, tamaño y hash hayan sido confirmados por la Edge Function.
"""
from __future__ import annotations

import base64
import binascii
import copy
import json
import tempfile
from pathlib import Path
from uuid import UUID

from services.levantamiento_medios_compartidos import MediosCompartidos, EvidenciaNoTransferible


def _json_object(data):
    if isinstance(data, dict):
        return data
    if isinstance(data, str) and data.strip():
        try:
            obj = json.loads(data)
            return obj if isinstance(obj, dict) else {}
        except ValueError:
            return {}
    return {}


def sanear_json_remoto(datos: dict) -> dict:
    """Elimina rutas de PC y anotaciones base64 del JSON transferible."""
    transportable = copy.deepcopy(datos)
    for key in ("__evidencias_locales", "__archivos_adjuntos_locales"):
        transportable[key] = []
    plano = _json_object(transportable.get("lev_anotacion_plano_json"))
    if plano:
        plano["imagen_base64"] = ""
        transportable["lev_anotacion_plano_json"] = json.dumps(plano, ensure_ascii=False)
    for key, value in list(transportable.items()):
        if key.startswith("__") and ("base64" in key or "locales" in key):
            transportable[key] = [] if isinstance(value, list) else ""
    return transportable


def preparar_medios_borrador(datos: dict, clave: str, cliente: MediosCompartidos) -> dict:
    """Devuelve un manifiesto y una copia transportable, sin tocar el respaldo local.

    Si algún archivo no se puede subir, falla explícitamente y no anuncia
    transferencia completa. No se aceptan rutas como referencias remotas.
    """
    UUID(str(clave))
    if not isinstance(datos, dict):
        raise ValueError("Borrador inválido")
    transportable = sanear_json_remoto(datos)
    manifest = []
    groups = (("fotografia", "__evidencias_locales"),
              ("anexo", "__archivos_adjuntos_locales"))
    for kind, key in groups:
        paths = datos.get(key) or []
        if not isinstance(paths, list):
            raise EvidenciaNoTransferible(f"Lista de {kind} inválida")
        for path in paths:
            if not isinstance(path, str) or not path.strip():
                raise EvidenciaNoTransferible(f"Ruta de {kind} inválida")
            ref = cliente.subir(str(clave), path)
            manifest.append({"kind": kind, "name": Path(path).name, "reference": vars(ref)})
        transportable[key] = []

    plano = _json_object(datos.get("lev_anotacion_plano_json"))
    encoded = str(plano.get("imagen_base64") or "").strip()
    if encoded:
        if encoded.startswith("data:"):
            encoded = encoded.partition(",")[2]
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise EvidenciaNoTransferible("Anotación tipo plano inválida") from exc
        if len(raw) > 8 * 1024 * 1024:
            raise EvidenciaNoTransferible("La anotación supera 8 MB")
        suffix = '.png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else '.jpg' if raw.startswith(b'\xff\xd8\xff') else None
        if not suffix:
            raise EvidenciaNoTransferible("Formato de anotación no transferible")
        with tempfile.TemporaryDirectory(prefix="axia_plano_") as directory:
            p = Path(directory) / f"anotacion{suffix}"
            p.write_bytes(raw)
            ref = cliente.subir(str(clave), p)
        manifest.append({"kind": "anotacion", "name": f"anotacion{suffix}", "reference": vars(ref)})
        plano["imagen_base64"] = ""
        transportable["lev_anotacion_plano_json"] = json.dumps(plano, ensure_ascii=False)
    # No se publican datos base64 ni rutas de la PC en el JSON remoto.
    for k, v in list(transportable.items()):
        if k.startswith("__") and ("base64" in k or "locales" in k):
            transportable[k] = [] if isinstance(v, list) else ""
    return {"media": manifest, "desktop": transportable, "media_transfer_complete": True}
