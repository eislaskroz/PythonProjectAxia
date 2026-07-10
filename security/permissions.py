"""
=========================================================
MÓDULO: permissions.py
DESCRIPCIÓN:
Control centralizado de permisos del sistema AXIA.

Aquí se define qué puede hacer cada tipo de usuario.
=========================================================
"""

ADMIN = 1
SUPERVISOR = 2
TECNICO = 3
CAPTURISTA = 4
CONSULTA = 5


def es_admin(usuario_activo):
    """
    Valida si el usuario activo es administrador.
    """

    return usuario_activo.get("usu_tipo") == ADMIN


def puede_crear_aco(usuario_activo):
    """
    Solo administración puede crear ACO.
    """

    return usuario_activo.get("usu_tipo") == ADMIN


def puede_ver_clientes(usuario_activo):
    """
    Solo administración puede ver clientes.
    """

    return usuario_activo.get("usu_tipo") == ADMIN


def puede_ver_dashboard(usuario_activo):
    """
    Solo administración puede ver dashboards y estadísticas.
    """

    return usuario_activo.get("usu_tipo") == ADMIN


def puede_administrar_usuarios(usuario_activo):
    """
    Solo administración puede crear, editar o consultar usuarios.
    """

    return usuario_activo.get("usu_tipo") == ADMIN


def puede_generar_levantamiento(usuario_activo):
    """
    Admin, supervisor y técnico pueden generar levantamientos.
    """

    return usuario_activo.get("usu_tipo") in [
        ADMIN,
        SUPERVISOR,
        TECNICO
    ]


def puede_generar_orden(usuario_activo):
    """
    Admin, supervisor y técnico pueden generar órdenes de servicio.
    """

    return usuario_activo.get("usu_tipo") in [
        ADMIN,
        SUPERVISOR,
        TECNICO
    ]


def puede_generar_bitacora(usuario_activo):
    """
    Admin, supervisor y técnico pueden generar bitácoras.
    """

    return usuario_activo.get("usu_tipo") in [
        ADMIN,
        SUPERVISOR,
        TECNICO
    ]


def puede_editar_datos_aco_relacionados(usuario_activo):
    """
    Define qué usuarios pueden editar datos heredados del ACO.

    Regla operativa actual:
    - Técnicos NO pueden modificar datos maestros del ACO.
    - Administradores y supervisores pueden hacerlo únicamente en
      pantallas administrativas futuras, no en los formularios técnicos.

    Esta función queda preparada para validaciones posteriores.
    """

    return usuario_activo.get("usu_tipo") in [
        ADMIN,
        SUPERVISOR
    ]
