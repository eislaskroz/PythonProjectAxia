"""Autoría de levantamientos AXIA DESKTOP.

Los nombres se originan en db_usuarios.usu_nombre y usu_apellido, cargados al
iniciar sesión, y se conservan como instantánea en el JSON técnico del LEV.
Nunca se atribuye un registro histórico al usuario que esté consultándolo.
"""
from __future__ import annotations

from collections.abc import Mapping, Callable
from typing import Any


def _limpio(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def autoria_desde_usuario(usuario: Mapping[str, Any] | None) -> dict[str, str]:
    """Instantánea del nombre y apellido autenticados para guardar en el LEV."""
    usuario = usuario or {}
    return {
        "usu_nombre": _limpio(usuario.get("nombre") or usuario.get("usu_nombre")),
        "usu_apellido": _limpio(usuario.get("apellido") or usuario.get("usu_apellido")),
    }


def nombre_elaborador(
    registro: Mapping[str, Any],
    detalle: Mapping[str, Any] | None,
    buscar_usuario: Callable[[str], Mapping[str, Any] | None] | None = None,
) -> str:
    """Devuelve el autor original, no el usuario que abre el PDF.

    Orden: instantánea persistida > consulta por nickname original en registros
    históricos > técnico guardado en el levantamiento como último recurso.
    """
    detalle = detalle or {}
    snapshot = detalle.get("elaborado_por")
    if isinstance(snapshot, Mapping):
        nombre = " ".join(filter(None, (
            _limpio(snapshot.get("usu_nombre")),
            _limpio(snapshot.get("usu_apellido")),
        )))
        if nombre:
            return nombre

    nickname = _limpio(registro.get("creado_por"))
    if nickname and buscar_usuario is not None:
        try:
            usuario = buscar_usuario(nickname) or {}
        except Exception:
            usuario = {}
        if isinstance(usuario, Mapping):
            datos = autoria_desde_usuario(usuario)
            nombre = " ".join(filter(None, (datos["usu_nombre"], datos["usu_apellido"])))
            if nombre:
                return nombre

    return _limpio(registro.get("lev_tecnico"))
