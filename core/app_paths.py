"""Rutas de ejecución seguras para AXIA.

Centraliza rutas que deben funcionar tanto en desarrollo como en el ejecutable
creado con PyInstaller. Los archivos modificables nunca se escriben dentro de
``_internal`` ni en la carpeta temporal de un ejecutable empaquetado.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "AXIA"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def executable_dir() -> Path:
    """Carpeta donde vive AXIA.exe, o raíz del proyecto en desarrollo."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT


def user_data_dir() -> Path:
    """Carpeta persistente y escribible para datos locales de la aplicación."""
    if os.name == "nt":
        base = Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.getenv("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def documents_dir() -> Path:
    """Carpeta de documentos generados por AXIA."""
    path = Path.home() / "Documents" / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def candidate_env_files() -> list[Path]:
    """Orden de búsqueda del archivo .env sin empaquetarlo dentro del EXE."""
    candidates = [
        executable_dir() / ".env",
        user_data_dir() / ".env",
        PROJECT_ROOT / ".env",
    ]
    # Elimina duplicados conservando orden.
    return list(dict.fromkeys(p.resolve() for p in candidates))
