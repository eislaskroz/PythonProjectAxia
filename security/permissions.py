from __future__ import annotations

from typing import Any, Mapping

ADMINISTRADOR = 1
JEFE_OPERACIONES = 2
SUPERVISOR = 3
OPERADOR = 4
ADMINISTRATIVO = 5
ESPECIAL = 6
COMPRAS = 7
ALMACEN = 8
DG_Y_CALIDAD = 9
RECURSOS_HUMANOS = 10

ADMIN = ADMINISTRADOR

NOMBRES_ROL = {
    ADMINISTRADOR: "Administrador",
    JEFE_OPERACIONES: "Jefe de Operaciones",
    SUPERVISOR: "Supervisor",
    OPERADOR: "Operador",
    ADMINISTRATIVO: "Administrativo",
    ESPECIAL: "Especial",
    COMPRAS: "Compras",
    ALMACEN: "Almacén",
    DG_Y_CALIDAD: "DG y Calidad",
    RECURSOS_HUMANOS: "Recursos Humanos",
}

TIPOS_VALIDOS = frozenset(NOMBRES_ROL)

ROLES_SUPERVISION = frozenset({SUPERVISOR, ADMINISTRATIVO, ESPECIAL})
ROLES_GESTION_OPERATIVA = frozenset(
    {ADMINISTRADOR, JEFE_OPERACIONES, SUPERVISOR, ADMINISTRATIVO, ESPECIAL}
)
ROLES_OPERATIVOS_LEGACY = frozenset({ADMINISTRADOR, JEFE_OPERACIONES, SUPERVISOR, OPERADOR, ADMINISTRATIVO, ESPECIAL})
ROLES_TODOS = ROLES_OPERATIVOS_LEGACY


def obtener_tipo_usuario(usuario_activo: Mapping[str, Any] | None) -> int | None:
    if not usuario_activo:
        return None
    try:
        tipo = int(usuario_activo.get("usu_tipo"))
    except (TypeError, ValueError):
        return None
    return tipo if tipo in TIPOS_VALIDOS else None


def nombre_rol(tipo_o_usuario: int | Mapping[str, Any] | None) -> str:
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
    return _es_rol(usuario_activo, ADMINISTRADOR)


def es_admin(usuario_activo) -> bool:
    return _es_rol(usuario_activo, ADMINISTRADOR)


def puede_entrar_inicio_aco(usuario_activo) -> bool:
    return obtener_tipo_usuario(usuario_activo) in ROLES_GESTION_OPERATIVA


def puede_crear_aco(usuario_activo) -> bool:
    return obtener_tipo_usuario(usuario_activo) in ROLES_GESTION_OPERATIVA


def puede_ver_clientes(usuario_activo) -> bool:
    return _es_rol(usuario_activo, ADMINISTRADOR, JEFE_OPERACIONES)


def puede_administrar_clientes(usuario_activo) -> bool:
    return puede_ver_clientes(usuario_activo)


def puede_ver_dashboard(usuario_activo) -> bool:
    return obtener_tipo_usuario(usuario_activo) in ROLES_GESTION_OPERATIVA


def puede_ver_usuarios(usuario_activo) -> bool:
    return _es_rol(usuario_activo, ADMINISTRADOR, JEFE_OPERACIONES, RECURSOS_HUMANOS)


def puede_editar_expedientes_rrhh(usuario_activo) -> bool:
    return _es_rol(usuario_activo, RECURSOS_HUMANOS)


def puede_administrar_usuarios(usuario_activo) -> bool:
    return _es_rol(usuario_activo, ADMINISTRADOR, JEFE_OPERACIONES)


def puede_ver_reportador_fotografico(usuario_activo) -> bool:
    return _es_rol(usuario_activo, ADMINISTRADOR, JEFE_OPERACIONES, SUPERVISOR, OPERADOR)


def puede_ver_reportes(usuario_activo) -> bool:
    return obtener_tipo_usuario(usuario_activo) in ROLES_GESTION_OPERATIVA

USUARIOS_DIRECCION_GENERAL = frozenset({39, 42, 43})


def puede_ver_direccion_general(usuario_activo) -> bool:
    tipo = obtener_tipo_usuario(usuario_activo)
    if tipo == ADMINISTRADOR:
        return True
    if tipo != DG_Y_CALIDAD or not usuario_activo:
        return False
    try:
        identificador = int(usuario_activo.get("id_usuario"))
    except (TypeError, ValueError):
        return False
    return identificador in USUARIOS_DIRECCION_GENERAL


def puede_administrar_registros(usuario_activo) -> bool:
    return es_admin(usuario_activo)


def puede_ver_auditoria(usuario_activo) -> bool:
    return _es_rol(usuario_activo, ADMINISTRADOR)


def puede_ver_reportes_login(usuario_activo) -> bool:
    return puede_ver_auditoria(usuario_activo)


def puede_ver_bitacora_movimientos(usuario_activo) -> bool:
    return puede_ver_auditoria(usuario_activo)


def puede_consultar_procesos(usuario_activo) -> bool:
    return obtener_tipo_usuario(usuario_activo) in ROLES_GESTION_OPERATIVA


def puede_generar_levantamiento(usuario_activo) -> bool:
    return obtener_tipo_usuario(usuario_activo) in ROLES_TODOS


def puede_modificar_levantamientos(usuario_activo) -> bool:
    return _es_rol(
        usuario_activo,
        ADMINISTRADOR,
        JEFE_OPERACIONES,
        SUPERVISOR,
        ADMINISTRATIVO,
    )

def puede_convertir_levantamiento_a_orden(usuario_activo) -> bool:
    return _es_rol(usuario_activo, ADMINISTRADOR, JEFE_OPERACIONES)


def puede_validar_levantamiento_ventas(usuario_activo) -> bool:
    return _es_rol(usuario_activo, ADMINISTRATIVO)


def puede_cotizar_levantamientos(usuario_activo) -> bool:
    return _es_rol(usuario_activo, ADMINISTRADOR, ESPECIAL)

def puede_autorizar_cotizacion_dg(usuario_activo) -> bool:
    return _es_rol(usuario_activo, ADMINISTRADOR, DG_Y_CALIDAD)


def puede_ver_compras(usuario_activo) -> bool:
    return _es_rol(usuario_activo, ADMINISTRADOR, COMPRAS)

def puede_convertir_cotizacion_a_orden(usuario_activo) -> bool:
    return _es_rol(usuario_activo, ADMINISTRADOR, COMPRAS)

def puede_ver_almacen(usuario_activo) -> bool:
    return _es_rol(usuario_activo, ADMINISTRADOR, ALMACEN)

def puede_avanzar_flujo_operativo(usuario_activo) -> bool:
    return _es_rol(usuario_activo, ADMINISTRADOR, ADMINISTRATIVO)

def puede_editar_ordenes_operativas(usuario_activo) -> bool:
    return _es_rol(usuario_activo, ADMINISTRADOR, JEFE_OPERACIONES, SUPERVISOR)


def puede_generar_orden(usuario_activo) -> bool:
    return obtener_tipo_usuario(usuario_activo) in ROLES_GESTION_OPERATIVA

def puede_generar_orden_servicio(usuario_activo) -> bool:
    return obtener_tipo_usuario(usuario_activo) in ROLES_TODOS


def puede_ver_bitacoras_operativas(usuario_activo) -> bool:
    return obtener_tipo_usuario(usuario_activo) in ROLES_TODOS


def puede_generar_bitacora(usuario_activo) -> bool:
    return puede_ver_bitacoras_operativas(usuario_activo)


def puede_editar_datos_aco_relacionados(usuario_activo) -> bool:
    return _es_rol(usuario_activo, ADMINISTRADOR, JEFE_OPERACIONES)


def matriz_permisos() -> dict[int, dict[str, bool]]:
    return {
        tipo: {
            "inicio_aco": tipo in ROLES_GESTION_OPERATIVA,
            "crear_aco": tipo in ROLES_GESTION_OPERATIVA,
            "agregar_levantamiento": tipo in ROLES_TODOS,
            "modificar_levantamientos": tipo in {
                ADMINISTRADOR, JEFE_OPERACIONES, SUPERVISOR, ADMINISTRATIVO
            },
            "consultar_procesos": tipo in ROLES_GESTION_OPERATIVA,
            "ordenes": tipo in ROLES_GESTION_OPERATIVA,
            "orden_servicio_operativa": tipo in ROLES_TODOS,
            "convertir_levantamiento_a_orden": tipo in {ADMINISTRADOR, JEFE_OPERACIONES},
            "cotizar_levantamientos": tipo in {ADMINISTRADOR, ESPECIAL},
            "compras": tipo in {ADMINISTRADOR, COMPRAS},
            "almacen": tipo in {ADMINISTRADOR, ALMACEN},
            "bitacoras_operativas": tipo in ROLES_TODOS,
            "reportes_operativos": tipo in ROLES_GESTION_OPERATIVA,
            "usuarios": tipo in {ADMINISTRADOR, JEFE_OPERACIONES, RECURSOS_HUMANOS},
            "administrar_cuentas": tipo in {ADMINISTRADOR, JEFE_OPERACIONES},
            "editar_expedientes_rrhh": tipo == RECURSOS_HUMANOS,
            "clientes": tipo in {ADMINISTRADOR, JEFE_OPERACIONES},
            "auditoria_login_movimientos": tipo == ADMINISTRADOR,
        }
        for tipo in sorted(TIPOS_VALIDOS)
    }