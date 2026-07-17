"""Perfil rápido de importaciones AXIA.

Uso en PowerShell, desde el entorno virtual:
    python tools/perfil_rendimiento.py

No abre la interfaz. Mide los bloques principales que influyen en el arranque.
"""
from __future__ import annotations

import importlib
import time

MODULES = [
    "customtkinter",
    "ui.theme",
    "ui.assets",
    "login",
    "app",
    "controllers.navigation_controller",
    "services.auth_service",
    "views.levantamiento_view",
]

print("\nAXIA - PERFIL DE IMPORTACIONES\n" + "=" * 46)
for module_name in MODULES:
    start = time.perf_counter()
    try:
        importlib.import_module(module_name)
        status = "OK"
    except Exception as exc:  # diagnóstico, no oculta el error
        status = f"ERROR: {exc}"
    elapsed = (time.perf_counter() - start) * 1000
    print(f"{module_name:<38} {elapsed:>9.1f} ms  {status}")
