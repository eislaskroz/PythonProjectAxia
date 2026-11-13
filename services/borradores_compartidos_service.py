"""Cliente opcional para borradores AXIA en Supabase (etapa 1).

La fuente local sigue siendo la primaria. No se conecta ni sincroniza automáticamente
hasta disponer de sesión AXIA JWT y validación de equivalencia DESKTOP/FIELD.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import requests

MODULES = {"LEVANTAMIENTO", "BITACORA", "ORDEN_SERVICIO", "REPORTE_FOTOGRAFICO"}
SCHEMA = "axia.draft.v1"

class ErrorBorradoresCompartidos(RuntimeError):
    pass

class ConflictoBorrador(ErrorBorradoresCompartidos):
    pass


def sobre_desktop(tipo: str, datos: dict[str, Any]) -> dict[str, Any]:
    """Conserva TODAS las claves lev_*; no inventa conversiones ni copia fotos locales.

    No permitir restauración en FIELD sin un conversor validado: rutas de evidencia,
    estructura de detalles técnicos y estado de firma pueden ser incompatibles.
    """
    if not isinstance(datos, dict):
        raise ValueError("Se requiere un diccionario")
    return {
        "schema": SCHEMA,
        "module": "LEVANTAMIENTO",
        "source": "DESKTOP",
        "lift_type": str(tipo or ""),
        "common": {
            "client": str(datos.get("lev_cliente") or ""),
            "contact": str(datos.get("lev_contacto") or ""),
            "phone": str(datos.get("lev_telefono") or ""),
            "email": str(datos.get("lev_correo") or ""),
            "description": str(datos.get("lev_descripcion") or ""),
            "location": str(datos.get("lev_ubicacion") or ""),
        },
        "native": {"desktop": datos},
        "media_transfer_complete": False,
    }


def restaurar_desktop(sobre: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Fail closed si el borrador no es nativo; evita pérdida silenciosa."""
    if sobre.get("schema") != SCHEMA or sobre.get("module") != "LEVANTAMIENTO":
        raise ValueError("Versión o módulo de borrador incompatible")
    native = sobre.get("native")
    if sobre.get("source") != "DESKTOP" or not isinstance(native, dict) or not isinstance(native.get("desktop"), dict):
        raise ValueError("El borrador FIELD aún requiere conversión validada para DESKTOP")
    return str(sobre.get("lift_type") or ""), native["desktop"]


@dataclass(frozen=True)
class SesionBorradores:
    supabase_url: str
    anon_key: str
    axia_jwt: str

    def __post_init__(self):
        if not self.supabase_url.startswith("https://") or not self.anon_key or not self.axia_jwt:
            raise ValueError("Requiere HTTPS y sesión AXIA válida")

    def solicitar(self, accion: str, modulo: str, **campos: Any) -> dict[str, Any]:
        if modulo not in MODULES:
            raise ValueError("Módulo no admitido")
        response = requests.post(
            f"{self.supabase_url.rstrip('/')}/functions/v1/axia-borradores-compartidos",
            json={"accion": accion, "modulo": modulo, **campos},
            headers={"apikey": self.anon_key,
                     "Authorization": f"Bearer {self.axia_jwt}",
                     "content-type": "application/json"},
            timeout=(8, 25), allow_redirects=False,
        )
        try:
            body = response.json()
        except ValueError as exc:
            raise ErrorBorradoresCompartidos("Respuesta inválida del servidor") from exc
        if response.status_code == 409:
            raise ConflictoBorrador(str(body.get("error", "Conflicto")))
        if response.status_code >= 400 or not body.get("ok"):
            raise ErrorBorradoresCompartidos(str(body.get("error", "Error del servidor")))
        return body

    def listar(self, modulo: str = "LEVANTAMIENTO") -> list[dict]:
        return self.solicitar("listar", modulo).get("borradores", [])

    def guardar(self, clave: str, revision: int, origen: str, sobre: dict, modulo: str = "LEVANTAMIENTO") -> int:
        UUID(clave)
        result = self.solicitar("guardar", modulo, clave_cliente=clave, revision=revision,
                                origen=origen, datos=sobre)
        return int(result["revision"])

    def eliminar(self, clave: str, revision: int, modulo: str = "LEVANTAMIENTO") -> None:
        UUID(clave)
        self.solicitar("eliminar", modulo, clave_cliente=clave, revision=revision)


def nueva_clave() -> str:
    return str(uuid4())
