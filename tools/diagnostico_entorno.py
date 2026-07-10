"""Diagnóstico local de dependencias y configuración para soporte AXIA."""
from __future__ import annotations

import importlib.util
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.app_paths import candidate_env_files, documents_dir, logs_dir

MODULES = [
    "customtkinter", "supabase", "dotenv", "requests", "PIL", "bcrypt",
    "cryptography", "openpyxl", "reportlab", "qrcode",
]


def main() -> int:
    print("AXIA - Diagnóstico de entorno")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Sistema: {platform.platform()}")
    print(f"Ejecutable: {sys.executable}")
    print(f"Documentos: {documents_dir()}")
    print(f"Logs: {logs_dir()}")
    print("\nArchivo .env:")
    found = False
    for path in candidate_env_files():
        state = "ENCONTRADO" if path.is_file() else "no existe"
        print(f"- {path}: {state}")
        found = found or path.is_file()

    print("\nDependencias:")
    missing = []
    for module in MODULES:
        ok = importlib.util.find_spec(module) is not None
        print(f"- {module}: {'OK' if ok else 'FALTA'}")
        if not ok:
            missing.append(module)

    if not found:
        print("\nADVERTENCIA: no se encontró .env. Copia uno junto a AXIA.exe o en la carpeta de datos de usuario.")
    if missing:
        print("\nDependencias faltantes:", ", ".join(missing))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
