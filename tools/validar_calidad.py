"""Puerta de calidad local para AXIA.

Valida sintaxis, secretos empaquetados, especificaciones duplicadas y bloques
``except`` que silencien errores mediante ``pass``.
"""
from __future__ import annotations

import ast
import compileall
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORADOS = {".venv", "build", "dist", "release", "__pycache__"}


def archivos_python():
    for ruta in ROOT.rglob("*.py"):
        if not any(parte in IGNORADOS for parte in ruta.parts):
            yield ruta


def validar_excepciones_silenciosas() -> list[str]:
    errores: list[str] = []
    for ruta in archivos_python():
        arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ExceptHandler) and len(nodo.body) == 1 and isinstance(nodo.body[0], ast.Pass):
                errores.append(f"{ruta.relative_to(ROOT)}:{nodo.lineno}: except silencioso")
    return errores


def validar_compilacion() -> list[str]:
    return [] if compileall.compile_dir(ROOT, quiet=1, force=True) else ["Falló compileall"]


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
    errores = validar_compilacion() + validar_excepciones_silenciosas() + validar_empaquetado()
    for archivo in ROOT.rglob("*.py"):
        if archivo == Path(__file__):
            continue
        texto = archivo.read_text(encoding="utf-8", errors="ignore")
        if '.select("*")' in texto or ".select('*')" in texto:
            errores.append(f"Consulta select(*) detectada: {archivo.relative_to(ROOT)}")

    if errores:
        print("PUERTA DE CALIDAD: FALLÓ")
        for error in errores:
            print(f"- {error}")
        return 1
    print("PUERTA DE CALIDAD: OK")
    print(f"Archivos Python revisados: {sum(1 for _ in archivos_python())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
