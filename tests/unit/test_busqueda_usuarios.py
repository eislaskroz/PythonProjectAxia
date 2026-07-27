import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _cargar_coincide_usuario():
    source = (ROOT / "services" / "usuarios_service.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(
        item for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == "_coincide_usuario"
    )
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {}
    exec(compile(module, "usuarios_service.py", "exec"), namespace)
    return namespace["_coincide_usuario"]


def test_busqueda_usuario_por_nickname_nombre_y_apellido():
    coincide = _cargar_coincide_usuario()
    usuario = {
        "usu_nickname": "ErickIslas",
        "usu_nombre": "Erick",
        "usu_apellido": "Islas",
        "usu_depto": "Tecnologías de la Información",
    }
    assert coincide(usuario, "erickislas")
    assert coincide(usuario, "ERICK")
    assert coincide(usuario, "islas")
    assert coincide(usuario, "tecnologías")
    assert not coincide(usuario, "sin-coincidencia")


def test_busqueda_usuario_ignora_espacios_y_mayusculas():
    coincide = _cargar_coincide_usuario()
    usuario = {"usu_nickname": "LuisMejia", "usu_nombre": "Luis", "usu_apellido": "Mejía"}
    assert coincide(usuario, "  LUISMEJIA  ")
