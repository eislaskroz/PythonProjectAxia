"""Contexto temporal del usuario autenticado en AXIA."""

from security.permissions import NOMBRES_ROL, SUPERVISOR

usuario_actual = {
    "id_usuario": None,
    "usuario": "DESCONOCIDO",
    "nombre": "",
    "apellido": "",
    "usu_tipo": SUPERVISOR,
    "rol": NOMBRES_ROL[SUPERVISOR],
    "ubicacion": {"latitud": "No disponible", "longitud": "No disponible", "ciudad": "No disponible", "region": "No disponible", "pais": "No disponible"},
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
    ubicacion=None,
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
    if isinstance(ubicacion, dict):
        usuario_actual["ubicacion"] = {
            "latitud": ubicacion.get("latitud", "No disponible"),
            "longitud": ubicacion.get("longitud", "No disponible"),
            "ciudad": ubicacion.get("ciudad", "No disponible"),
            "region": ubicacion.get("region", "No disponible"),
            "pais": ubicacion.get("pais", "No disponible"),
        }


def obtener_usuario_actual():
    return usuario_actual


def es_admin():
    return usuario_actual.get("usu_tipo") == 1
