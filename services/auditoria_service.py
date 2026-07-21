"""Consultas centralizadas para la auditoría administrativa de AXIA.

Este módulo unifica dos fuentes distintas:
- ``db_bitacora_mov``: operaciones realizadas dentro del sistema.
- ``db_login``: intentos de acceso, correctos y fallidos.

Las consultas se ejecutan bajo demanda y se normalizan para que la interfaz
no dependa directamente de Supabase.
"""

from core.logger import configurar_logger
from supabase_config import supabase, TABLA_BITACORA_LOGIN, TABLA_BITACORA_MOVIMIENTOS

logger = configurar_logger(__name__)


def _texto(valor):
    return str(valor or "").strip().lower()


def _coincide(registro, termino, campos):
    termino = _texto(termino)
    if not termino:
        return True
    return any(termino in _texto(registro.get(campo)) for campo in campos)


def buscar_movimientos_auditoria(termino="", limite=200):
    """Obtiene movimientos recientes y aplica una búsqueda tolerante local."""
    try:
        ventana = max(int(limite or 200), 500)
        respuesta = (
            supabase.table(TABLA_BITACORA_MOVIMIENTOS)
            .select(
                "id_usuario,usuario,modulo,accion,descripcion,registro_afectado,"
                "ip_local,equipo,ciudad,region,pais,fecha_hora"
            )
            .order("fecha_hora", desc=True)
            .limit(ventana)
            .execute()
        )
        campos = (
            "fecha_hora", "usuario", "modulo", "accion", "descripcion",
            "registro_afectado", "ip_local", "equipo", "ciudad", "region", "pais",
        )
        return [r for r in (respuesta.data or []) if _coincide(r, termino, campos)][:limite]
    except Exception:
        logger.exception("Error al consultar movimientos para auditoría.")
        return []


def buscar_accesos_auditoria(termino="", limite=200):
    """Obtiene intentos de acceso recientes, incluidos accesos fallidos."""
    try:
        ventana = max(int(limite or 200), 500)
        respuesta = (
            supabase.table(TABLA_BITACORA_LOGIN)
            .select(
                "id_usuario,usu_nickname,fecha_hora,estatus,descripcion,direccion_ip,"
                "nombre_equipo,latitud,longitud,ciudad,region,pais"
            )
            .order("fecha_hora", desc=True)
            .limit(ventana)
            .execute()
        )
        campos = (
            "fecha_hora", "usu_nickname", "estatus", "descripcion", "direccion_ip",
            "nombre_equipo", "latitud", "longitud", "ciudad", "region", "pais",
        )
        return [r for r in (respuesta.data or []) if _coincide(r, termino, campos)][:limite]
    except Exception:
        logger.exception("Error al consultar accesos para auditoría.")
        return []


def resumen_registros(registros, tipo):
    """Calcula métricas rápidas sin generar consultas adicionales."""
    registros = registros or []
    if tipo == "accesos":
        usuarios = len({_texto(r.get("usu_nickname")) for r in registros if r.get("usu_nickname")})
        fallidos = sum(1 for r in registros if _texto(r.get("estatus")) not in {"correcto", "exitoso", "ok"})
        return len(registros), usuarios, fallidos

    usuarios = len({_texto(r.get("usuario")) for r in registros if r.get("usuario")})
    modulos = len({_texto(r.get("modulo")) for r in registros if r.get("modulo")})
    return len(registros), usuarios, modulos
