"""
=========================================================
MÓDULO: app_context.py
DESCRIPCIÓN:
Almacena información temporal del usuario activo
durante la ejecución del sistema AXIA.
=========================================================
"""

usuario_actual = {
    "id_usuario": None,
    "usuario": "DESCONOCIDO",
    "nombre": "",
    "apellido": "",
    "usu_tipo": 3,
    "rol": "TECNICO"
}


def obtener_rol_por_tipo(usu_tipo):
    """
    Convierte el tipo numérico de usuario a rol legible.
    """

    roles = {
        1: "ADMIN",
        2: "SUPERVISOR",
        3: "TECNICO",
        4: "CAPTURISTA",
        5: "CONSULTA"
    }

    return roles.get(usu_tipo, "TECNICO")


def establecer_usuario_actual(
    id_usuario=None,
    usuario="DESCONOCIDO",
    nombre="",
    apellido="",
    usu_tipo=3
):
    """
    Guarda en memoria los datos del usuario autenticado.
    """

    usuario_actual["id_usuario"] = id_usuario
    usuario_actual["usuario"] = usuario
    usuario_actual["nombre"] = nombre
    usuario_actual["apellido"] = apellido
    usuario_actual["usu_tipo"] = int(usu_tipo or 3)
    usuario_actual["rol"] = obtener_rol_por_tipo(int(usu_tipo or 3))


def obtener_usuario_actual():
    """
    Retorna la información del usuario activo.
    """

    return usuario_actual


def es_admin():
    """
    Indica si el usuario activo es administrador.
    """

    return usuario_actual.get("usu_tipo") == 1