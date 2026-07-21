import pytest
from security.permissions import matriz_permisos

EXPECTED = {
    1: {"inicio_aco": True, "crear_aco": True, "agregar_levantamiento": True, "consultar_procesos": True, "ordenes": True, "bitacoras_operativas": True, "reportes_operativos": True, "usuarios": True, "clientes": True, "auditoria_login_movimientos": True},
    2: {"inicio_aco": True, "crear_aco": True, "agregar_levantamiento": True, "consultar_procesos": True, "ordenes": True, "bitacoras_operativas": True, "reportes_operativos": True, "usuarios": True, "clientes": True, "auditoria_login_movimientos": False},
    3: {"inicio_aco": True, "crear_aco": True, "agregar_levantamiento": True, "consultar_procesos": True, "ordenes": True, "bitacoras_operativas": True, "reportes_operativos": True, "usuarios": False, "clientes": False, "auditoria_login_movimientos": False},
    4: {"inicio_aco": False, "crear_aco": False, "agregar_levantamiento": True, "consultar_procesos": False, "ordenes": False, "bitacoras_operativas": False, "reportes_operativos": False, "usuarios": False, "clientes": False, "auditoria_login_movimientos": False},
    5: {"inicio_aco": True, "crear_aco": True, "agregar_levantamiento": True, "consultar_procesos": True, "ordenes": True, "bitacoras_operativas": True, "reportes_operativos": True, "usuarios": False, "clientes": False, "auditoria_login_movimientos": False},
    6: {"inicio_aco": True, "crear_aco": True, "agregar_levantamiento": True, "consultar_procesos": True, "ordenes": True, "bitacoras_operativas": True, "reportes_operativos": True, "usuarios": False, "clientes": False, "auditoria_login_movimientos": False},
}

@pytest.mark.parametrize("role", range(1, 7))
def test_matriz_completa_por_rol(role):
    assert matriz_permisos()[role] == EXPECTED[role]
