import pytest
from security.permissions import (
    matriz_permisos, nombre_rol, obtener_tipo_usuario,
    puede_administrar_usuarios, puede_generar_levantamiento,
    puede_ver_auditoria, puede_ver_clientes, puede_ver_bitacoras_operativas,
)

@pytest.mark.parametrize("tipo,nombre", [
    (1,"Administrador"),(2,"Jefe de Operaciones"),(3,"Supervisor"),
    (4,"Operador"),(5,"Administrativo"),(6,"Especial"),
])
def test_catalogo_roles(tipo, nombre):
    assert nombre_rol(tipo) == nombre
    assert obtener_tipo_usuario({"usu_tipo": str(tipo)}) == tipo

def test_matriz_de_permisos_acordada():
    matriz = matriz_permisos()
    assert all(matriz[t]["agregar_levantamiento"] for t in range(1, 7))
    assert puede_ver_auditoria({"usu_tipo": 1})
    assert not puede_ver_auditoria({"usu_tipo": 2})
    assert puede_administrar_usuarios({"usu_tipo": 2})
    assert not puede_administrar_usuarios({"usu_tipo": 3})
    assert puede_ver_clientes({"usu_tipo": 2})
    assert not puede_ver_clientes({"usu_tipo": 3})
    assert puede_generar_levantamiento({"usu_tipo": 4})
    assert puede_ver_bitacoras_operativas({"usu_tipo": 4})
    assert matriz[4]["bitacoras_operativas"] is True

def test_tipo_invalido_falla_cerrado():
    assert obtener_tipo_usuario({"usu_tipo": 99}) is None
    assert not puede_generar_levantamiento({"usu_tipo": 99})


def test_administrador_tiene_acceso_total_en_matriz():
    """El rol 1 es superusuario funcional: no debe quedar excluido de ninguna capacidad."""
    permisos_admin = matriz_permisos()[1]
    assert permisos_admin
    assert all(permisos_admin.values()), permisos_admin
