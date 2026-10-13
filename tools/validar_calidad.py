"""Puerta de calidad local para AXIA.

Bloquea errores de sintaxis y problemas de empaquetado; reporta patrones de
compatibilidad y manejo de errores como advertencias para revisión.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORADOS = {".git", ".idea", ".pytest_cache", ".tmp_merge", ".venv", "build", "dist", "release", "__pycache__"}


def archivos_python():
    for ruta in ROOT.rglob("*.py"):
        if not any(parte in IGNORADOS for parte in ruta.parts):
            yield ruta


def validar_excepciones_silenciosas() -> list[str]:
    errores: list[str] = []
    for ruta in archivos_python():
        try:
            arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
        except (OSError, SyntaxError):
            continue
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ExceptHandler) and len(nodo.body) == 1 and isinstance(nodo.body[0], ast.Pass):
                errores.append(f"{ruta.relative_to(ROOT)}:{nodo.lineno}: except silencioso")
    return errores


def validar_compilacion() -> list[str]:
    errores: list[str] = []
    for ruta in archivos_python():
        try:
            compile(ruta.read_bytes(), str(ruta), "exec")
        except (OSError, SyntaxError) as exc:
            linea = getattr(exc, "lineno", None)
            ubicacion = f":{linea}" if linea else ""
            errores.append(f"{ruta.relative_to(ROOT)}{ubicacion}: {exc}")
    return errores


def validar_empaquetado() -> list[str]:
    errores: list[str] = []
    spec = ROOT / "AXIA.spec"
    if not spec.exists():
        errores.append("Falta AXIA.spec")
    elif "('.env', '.')" in spec.read_text(encoding="utf-8") or '(".env", ".")' in spec.read_text(encoding="utf-8"):
        errores.append("AXIA.spec incluye .env")
    if (ROOT / "main.spec").exists():
        errores.append("main.spec duplica el proceso de compilación")
    return errores


def main() -> int:
    errores = validar_compilacion() + validar_empaquetado()
    advertencias = validar_excepciones_silenciosas()
    for archivo in archivos_python():
        if archivo == Path(__file__):
            continue
        texto = archivo.read_text(encoding="utf-8", errors="ignore")
        if '.select("*")' in texto or ".select('*')" in texto:
            advertencias.append(f"{archivo.relative_to(ROOT)}: consulta select(*)")

    if errores:
        print("PUERTA DE CALIDAD: FALLÓ")
        for error in errores:
            print(f"- {error}")
        return 1
    print("PUERTA DE CALIDAD: OK")
    print(f"Archivos Python revisados: {sum(1 for _ in archivos_python())}")
    if advertencias:
        print(f"Advertencias no bloqueantes: {len(advertencias)}")
        for advertencia in advertencias:
            print(f"- {advertencia}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
