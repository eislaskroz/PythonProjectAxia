import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = {
    "services/clientes_service.py": "COLUMNAS_CLIENTES",
    "services/movimientos_service.py": "COLUMNAS_MOVIMIENTOS",
    "services/sucursales_service.py": "COLUMNAS_SUCURSALES",
    "services/usuarios_service.py": "COLUMNAS_USUARIOS",
}


def _constant(file_name: str, name: str) -> str:
    tree = ast.parse((ROOT / file_name).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"Falta {name} en {file_name}")


def test_contratos_de_columnas_criticos():
    for file_name, name in CONTRACTS.items():
        columns = _constant(file_name, name)
        values = [c.strip() for c in columns.split(",")]
        assert values and "*" not in values
        assert all(values)
        assert len(values) == len(set(values))
