"""Control centralizado de roles y permisos del sistema AXIA.

La base de datos almacena el nivel en ``db_usuarios.usu_tipo``:

1 = Administrador
2 = Jefe de Operaciones
3 = Supervisor
4 = Operador
5 = Administrativo
6 = Especial

Los permisos se validan tanto al construir la navegación como al abrir cada
vista sensible. Ocultar un botón no se considera una medida de seguridad por sí
sola.
"""

from __future__ import annotations

from typing import Any, Mapping

ADMINISTRADOR = 1
JEFE_OPERACIONES = 2
SUPERVISOR = 3
OPERADOR = 4
ADMINISTRATIVO = 5
ESPECIAL = 6

# Alias conservado para compatibilidad con módulos anteriores.
ADMIN = ADMINISTRADOR

NOMBRES_ROL = {
    ADMINISTRADOR: "Administrador",
    JEFE_OPERACIONES: "Jefe de Operaciones",
    SUPERVISOR: "Supervisor",
    OPERADOR: "Operador",
    ADMINISTRATIVO: "Administrativo",
    ESPECIAL: "Especial",
}

TIPOS_VALIDOS = frozenset(NOMBRES_ROL)

# Roles 5 y 6 quedan temporalmente alineados con Supervisor.
ROLES_SUPERVISION = frozenset({SUPERVISOR, ADMINISTRATIVO, ESPECIAL})
ROLES_GESTION_OPERATIVA = frozenset(
    {ADMINISTRADOR, JEFE_OPERACIONES, SUPERVISOR, ADMINISTRATIVO, ESPECIAL}
)
ROLES_TODOS = frozenset(TIPOS_VALIDOS)


def obtener_tipo_usuario(usuario_activo: Mapping[str, Any] | None) -> int | None:
    """Devuelve ``usu_tipo`` normalizado o ``None`` si es inválido."""
    if not usuario_activo:
        return None
    try:
        tipo = int(usuario_activo.get("usu_tipo"))
    except (TypeError, ValueError):
        return None
    return tipo if tipo in TIPOS_VALIDOS else None


def nombre_rol(tipo_o_usuario: int | Mapping[str, Any] | None) -> str:
    """Obtiene el nombre legible de un rol sin asumir valores inválidos."""
    if isinstance(tipo_o_usuario, Mapping):
        tipo = obtener_tipo_usuario(tipo_o_usuario)
    else:
        try:
            tipo = int(tipo_o_usuario) if tipo_o_usuario is not None else None
        except (TypeError, ValueError):
            tipo = None
    return NOMBRES_ROL.get(tipo, "Rol no válido")


def _es_rol(usuario_activo, *roles: int) -> bool:
    return obtener_tipo_usuario(usuario_activo) in roles


def es_superadmin(usuario_activo) -> bool:
    """Compatibilidad: el nivel máximo corresponde al Administrador."""
    return _es_rol(usuario_activo, ADMINISTRADOR)


def es_admin(usuario_activo) -> bool:
    """Indica si el usuario es Administrador (nivel 1)."""
    return _es_rol(usuario_activo, ADMINISTRADOR)


def puede_entrar_inicio_aco(usuario_activo) -> bool:
    """El Operador trabaja únicamente desde el flujo de levantamientos."""
    return obtener_tipo_usuario(usuario_activo) in ROLES_GESTION_OPERATIVA


def puede_crear_aco(usuario_activo) -> bool:
    return obtener_tipo_usuario(usuario_activo) in ROLES_GESTION_OPERATIVA


def puede_ver_clientes(usuario_activo) -> bool:
    """Administrador y Jefe de Operaciones administran clientes."""
    return _es_rol(usuario_activo, ADMINISTRADOR, JEFE_OPERACIONES)


def puede_administrar_clientes(usuario_activo) -> bool:
    return puede_ver_clientes(usuario_activo)


def puede_ver_dashboard(usuario_activo) -> bool:
    return obtener_tipo_usuario(usuario_activo) in ROLES_GESTION_OPERATIVA


def puede_administrar_usuarios(usuario_activo) -> bool:
    """Administrador y Jefe de Operaciones administran usuarios."""
    return _es_rol(usuario_activo, ADMINISTRADOR, JEFE_OPERACIONES)


def puede_ver_reportes(usuario_activo) -> bool:
    """Reportes operativos: todos salvo Operador."""
    return obtener_tipo_usuario(usuario_activo) in ROLES_GESTION_OPERATIVA


def puede_ver_auditoria(usuario_activo) -> bool:
    """Login y bitácora de movimientos: exclusivamente Administrador."""
    return _es_rol(usuario_activo, ADMINISTRADOR)


def puede_ver_reportes_login(usuario_activo) -> bool:
    return puede_ver_auditoria(usuario_activo)


def puede_ver_bitacora_movimientos(usuario_activo) -> bool:
    return puede_ver_auditoria(usuario_activo)


def puede_consultar_procesos(usuario_activo) -> bool:
    """Consulta administrativa de levantamientos, órdenes y bitácoras."""
    return obtener_tipo_usuario(usuario_activo) in ROLES_GESTION_OPERATIVA


def puede_generar_levantamiento(usuario_activo) -> bool:
    """Los seis roles pueden agregar levantamientos."""
    return obtener_tipo_usuario(usuario_activo) in ROLES_TODOS


def puede_generar_orden(usuario_activo) -> bool:
    """Todos salvo Operador pueden generar órdenes."""
    return obtener_tipo_usuario(usuario_activo) in ROLES_GESTION_OPERATIVA


def puede_generar_bitacora(usuario_activo) -> bool:
    """Todos salvo Operador pueden generar bitácoras operativas."""
    return obtener_tipo_usuario(usuario_activo) in ROLES_GESTION_OPERATIVA


def puede_editar_datos_aco_relacionados(usuario_activo) -> bool:
    """Edición de datos maestros: Administrador y Jefe de Operaciones."""
    return _es_rol(usuario_activo, ADMINISTRADOR, JEFE_OPERACIONES)


def matriz_permisos() -> dict[int, dict[str, bool]]:
    """Matriz serializable usada por documentación y pruebas."""
    return {
        tipo: {
            "inicio_aco": tipo in ROLES_GESTION_OPERATIVA,
            "crear_aco": tipo in ROLES_GESTION_OPERATIVA,
            "agregar_levantamiento": tipo in ROLES_TODOS,
            "consultar_procesos": tipo in ROLES_GESTION_OPERATIVA,
            "ordenes": tipo in ROLES_GESTION_OPERATIVA,
            "bitacoras_operativas": tipo in ROLES_GESTION_OPERATIVA,
            "reportes_operativos": tipo in ROLES_GESTION_OPERATIVA,
            "usuarios": tipo in {ADMINISTRADOR, JEFE_OPERACIONES},
            "clientes": tipo in {ADMINISTRADOR, JEFE_OPERACIONES},
            "auditoria_login_movimientos": tipo == ADMINISTRADOR,
        }
        for tipo in sorted(TIPOS_VALIDOS)
    }
