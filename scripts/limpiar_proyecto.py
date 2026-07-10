"""Limpieza segura del proyecto AXIA.

Elimina carpetas generadas por Python/PyInstaller sin tocar código fuente.
Ejecutar desde la raíz del proyecto:
    python scripts/limpiar_proyecto.py
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent
DIRS = ["__pycache__", ".pytest_cache", "build", "dist"]
SUFFIXES = [".pyc", ".pyo"]

for path in list(ROOT.rglob("*")):
    if path.is_dir() and path.name in DIRS:
        shutil.rmtree(path, ignore_errors=True)
        print(f"Eliminado: {path.relative_to(ROOT)}")
    elif path.is_file() and path.suffix in SUFFIXES:
        path.unlink(missing_ok=True)
        print(f"Eliminado: {path.relative_to(ROOT)}")
