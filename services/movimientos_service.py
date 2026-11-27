import socket

from app_context import obtener_usuario_actual
from core.logger import configurar_logger
from services.desktop_audit_write import registrar_evento

logger = configurar_logger(__name__)
COLUMNAS_MOVIMIENTOS = "id_usuario,fecha_hora,usuario,modulo,accion,descripcion,equipo,ip_local,registro_afectado,latitud,longitud,ciudad,region,pais"


def obtener_equipo_local():
    try:
        return socket.gethostname()
    except OSError:
        return "DESCONOCIDO"


def obtener_ip_local():
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "DESCONOCIDA"


def registrar_movimiento(id_usuario=None, usuario="DESCONOCIDO", modulo="GENERAL", accion="SIN_ACCION", descripcion="Movimiento sin descripción", registro_afectado=None, latitud=None, longitud=None, ciudad=None, region=None, pais=None):
    actor = obtener_usuario_actual()
    identidad = actor.get("id_usuario")
    if identidad is None or (id_usuario is not None and str(id_usuario) != str(identidad)):
        return False
    ubicacion = actor.get("ubicacion") or {}
    datos = {"modulo": modulo, "accion": accion, "descripcion": descripcion, "registro_afectado": registro_afectado, "equipo": obtener_equipo_local(), "ip_local": obtener_ip_local()}
    for campo, valor in (("latitud", latitud), ("longitud", longitud), ("ciudad", ciudad), ("region", region), ("pais", pais)):
        datos[campo] = ubicacion.get(campo) if valor is None else valor
    try:
        return registrar_evento(identidad, datos)
    except Exception:
        logger.warning("No se pudo confirmar el movimiento de auditoría.")
        return False


def registrar_movimiento_seguro(
    modulo="GENERAL",
    accion="SIN_ACCION",
    descripcion="Movimiento sin descripción",
    registro_afectado=None,
):

    try:
        return registrar_movimiento(
            modulo=modulo,
            accion=accion,
            descripcion=descripcion,
            registro_afectado=str(registro_afectado) if registro_afectado is not None else None,
        )
    except Exception:
        logger.exception("Error no controlado en registrar_movimiento_seguro.")
        return False




def obtener_bitacora_movimientos():
    from services.desktop_secure_reads import listar
    registros = listar("desktop-audit", "movimientos", 1000)
    registrar_movimiento(modulo="AUDITORIA", accion="CONSULTAR", descripcion="Consulta de bitácora de movimientos", registro_afectado=f"Total consultado: {len(registros)}")
    return registros






def obtener_movimientos_usuario_actual(limite=300):
    from services.desktop_secure_reads import listar
    return listar("desktop-audit", "mis_movimientos", limite)




def obtener_estadisticas_movimientos():
    try:
        movimientos = obtener_bitacora_movimientos()

        total = len(movimientos)
        usuarios = len(set(m["usuario"] for m in movimientos if m.get("usuario")))
        modulos = len(set(m["modulo"] for m in movimientos if m.get("modulo")))

        return total, usuarios, modulos

    except Exception as error:
        logger.exception("Error al obtener estadísticas de movimientos.")
        return 0, 0, 0




def _coincide_movimiento(movimiento, termino):

    termino = str(termino or "").lower().strip()
    if not termino:
        return False

    campos = [
        "fecha_hora",
        "usuario",
        "modulo",
        "accion",
        "descripcion",
        "registro_afectado",
        "equipo",
        "ip_local",
        "latitud",
        "longitud",
        "ciudad",
        "region",
        "pais",
    ]

    return any(
        termino in str(movimiento.get(campo, "") or "").lower()
        for campo in campos
    )





def buscar_movimientos(termino="", limite=200):
    from services.desktop_secure_reads import listar
    if not str(termino or "").strip():
        return []
    registros = listar("desktop-audit", "movimientos", max(limite, 500))
    return [m for m in registros if _coincide_movimiento(m, termino)][:limite]





def buscar_movimientos_usuario_actual(termino="", limite=100):
    if not str(termino or "").strip():
        return []
    registros = obtener_movimientos_usuario_actual(max(limite, 300))
    return [m for m in registros if _coincide_movimiento(m, termino)][:limite]
