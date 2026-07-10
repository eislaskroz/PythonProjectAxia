"""Auditoría estática y no destructiva del proyecto AXIA.

Uso:
    python tools/auditar_proyecto.py

Genera ``docs/AUDITORIA_CONSOLIDACION.md`` con hallazgos verificables sobre:
- sintaxis Python;
- tablas y campos enviados a Supabase;
- formularios con vista previa y guardado automático de PDF;
- columnas JSON utilizadas;
- funciones duplicadas dentro de un mismo archivo;
- dependencias declaradas e importadas.
"""
from __future__ import annotations

import ast
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = DOCS / "AUDITORIA_CONSOLIDACION.md"
EXCLUDE = {".venv", "build", "dist", "__pycache__", ".git"}


def py_files() -> list[Path]:
    return sorted(
        p for p in ROOT.rglob("*.py")
        if not any(part in EXCLUDE for part in p.parts)
    )


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def dict_string_keys(tree: ast.AST) -> set[str]:
    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    keys.add(key.value)
    return keys


def duplicate_functions(tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.append(node.name)
    return sorted(name for name, count in Counter(names).items() if count > 1)


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    files = py_files()
    syntax_errors: list[str] = []
    duplicates: dict[str, list[str]] = {}
    json_columns: dict[str, set[str]] = defaultdict(set)
    pdf_preview: set[str] = set()
    pdf_save: set[str] = set()
    supabase_tables: set[str] = set()
    payload_keys: dict[str, set[str]] = defaultdict(set)
    todo_lines: list[str] = []

    table_pattern = re.compile(r"\.table\(\s*[\"']([^\"']+)[\"']\s*\)")
    json_key_pattern = re.compile(r"[\"']([A-Za-z0-9_]+_json)[\"']")

    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        text = source(path)
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError as exc:
            syntax_errors.append(f"{rel}:{exc.lineno}: {exc.msg}")
            continue

        dups = duplicate_functions(tree)
        if dups:
            duplicates[rel] = dups

        keys = dict_string_keys(tree)
        db_keys = {k for k in keys if re.match(r"^(lev|aco|cli|os|ot|bit|obc|usu|suc)_", k)}
        if db_keys:
            payload_keys[rel].update(db_keys)

        for col in json_key_pattern.findall(text):
            json_columns[rel].add(col)
        if "generar_pdf_preview(" in text:
            pdf_preview.add(rel)
        if "generar_pdf_archivo(" in text:
            pdf_save.add(rel)
        supabase_tables.update(table_pattern.findall(text))

        for no, line in enumerate(text.splitlines(), 1):
            if re.search(r"\b(TODO|FIXME|PENDIENTE)\b", line, re.I):
                todo_lines.append(f"{rel}:{no}: {line.strip()}")

    requirements = set()
    req_file = ROOT / "requirements.txt"
    if req_file.exists():
        requirements = {
            line.strip().split("==")[0].lower()
            for line in req_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

    lines = [
        "# Auditoría de consolidación AXIA",
        "",
        "> Auditoría estática generada automáticamente. No sustituye pruebas funcionales contra la instancia real de Supabase.",
        "",
        "## Resumen",
        "",
        f"- Archivos Python revisados: **{len(files)}**",
        f"- Errores de sintaxis: **{len(syntax_errors)}**",
        f"- Pantallas/módulos con vista previa PDF: **{len(pdf_preview)}**",
        f"- Pantallas/módulos con guardado automático PDF: **{len(pdf_save)}**",
        f"- Columnas JSON detectadas: **{sum(len(v) for v in json_columns.values())} referencias**",
        f"- Tablas Supabase detectadas de forma literal: **{len(supabase_tables)}**",
        "",
        "## Sintaxis",
        "",
    ]
    lines += (["- Sin errores de sintaxis detectados."] if not syntax_errors else [f"- ⚠️ {x}" for x in syntax_errors])

    lines += ["", "## Cobertura de PDF", "", "### Vista previa y guardado definitivo"]
    all_pdf = sorted(pdf_preview | pdf_save)
    for rel in all_pdf:
        lines.append(f"- `{rel}` — preview: {'sí' if rel in pdf_preview else 'no'}; guardado: {'sí' if rel in pdf_save else 'no'}")

    lines += ["", "## Columnas JSON utilizadas", ""]
    for rel, cols in sorted(json_columns.items()):
        lines.append(f"- `{rel}`: {', '.join(f'`{c}`' for c in sorted(cols))}")

    lines += ["", "## Campos de payload detectados por archivo", ""]
    for rel, keys in sorted(payload_keys.items()):
        lines.append(f"- `{rel}` ({len(keys)}): {', '.join(f'`{k}`' for k in sorted(keys))}")

    lines += ["", "## Tablas Supabase detectadas", ""]
    if supabase_tables:
        lines += [f"- `{name}`" for name in sorted(supabase_tables)]
    else:
        lines.append("- Las tablas se referencian mediante constantes; revisar `supabase_config.py`.")

    lines += ["", "## Funciones con nombres repetidos dentro de un archivo", ""]
    if duplicates:
        for rel, names in sorted(duplicates.items()):
            lines.append(f"- `{rel}`: {', '.join(f'`{n}`' for n in names)}")
        lines.append("")
        lines.append("> Nota: algunos nombres repetidos son funciones locales creadas deliberadamente en ramas distintas. Deben revisarse antes de refactorizar; no se eliminaron automáticamente.")
    else:
        lines.append("- No se detectaron nombres de función repetidos.")

    lines += ["", "## Marcadores TODO/FIXME/PENDIENTE", ""]
    lines += ([f"- `{x}`" for x in todo_lines[:100]] if todo_lines else ["- No se detectaron marcadores."])

    lines += ["", "## Dependencias declaradas", "", ", ".join(f"`{x}`" for x in sorted(requirements)) or "No disponible."]

    lines += [
        "",
        "## Alcance y siguiente validación obligatoria",
        "",
        "La auditoría confirma estructura y referencias en código, pero no puede conocer el esquema real de la base de datos sin conectarse a Supabase. Antes de producción se debe comparar cada campo de payload con las columnas reales y ejecutar pruebas de crear, consultar y editar por módulo.",
    ]

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Auditoría generada: {OUT.relative_to(ROOT)}")
    print(f"Errores de sintaxis: {len(syntax_errors)}")
    return 1 if syntax_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
