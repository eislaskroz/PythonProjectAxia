"""Contexto temporal del usuario autenticado en AXIA."""

from security.permissions import NOMBRES_ROL, SUPERVISOR

usuario_actual = {
    "id_usuario": None,
    "usuario": "DESCONOCIDO",
    "nombre": "",
    "apellido": "",
    "usu_tipo": SUPERVISOR,
    "rol": NOMBRES_ROL[SUPERVISOR],
}


def obtener_rol_por_tipo(usu_tipo):
    """Convierte el nivel numérico en su nombre oficial."""
    try:
        tipo = int(usu_tipo)
    except (TypeError, ValueError):
        return "Rol no válido"
    return NOMBRES_ROL.get(tipo, "Rol no válido")


def establecer_usuario_actual(
    id_usuario=None,
    usuario="DESCONOCIDO",
    nombre="",
    apellido="",
    usu_tipo=SUPERVISOR,
):
    """Guarda en memoria los datos del usuario autenticado."""
    try:
        tipo = int(usu_tipo)
    except (TypeError, ValueError):
        tipo = SUPERVISOR

    # Un valor fuera del catálogo no obtiene permisos por defecto.
    if tipo not in NOMBRES_ROL:
        tipo = SUPERVISOR

    usuario_actual["id_usuario"] = id_usuario
    usuario_actual["usuario"] = usuario
    usuario_actual["nombre"] = nombre
    usuario_actual["apellido"] = apellido
    usuario_actual["usu_tipo"] = tipo
    usuario_actual["rol"] = obtener_rol_por_tipo(tipo)


def obtener_usuario_actual():
    return usuario_actual


def es_admin():
    return usuario_actual.get("usu_tipo") == 1
