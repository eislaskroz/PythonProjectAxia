"""
=========================================================
SERVICIO DE BITÁCORA DE MOVIMIENTOS - AXIA
=========================================================

Este servicio concentra la auditoría general de movimientos del sistema.

Responsabilidades:
- Registrar acciones de usuarios.
- Consultar movimientos históricos.
- Calcular estadísticas de auditoría.

Regla de arquitectura:
La UI puede solicitar que se registre un movimiento, pero la lógica de
construcción del registro, IP, equipo y Supabase vive aquí.
"""

from core.logger import configurar_logger

logger = configurar_logger(__name__)

# =====================================================
# IMPORTACIÓN DE LIBRERÍAS
# =====================================================

# Librería para obtener información del equipo local
import socket

# =====================================================
# IMPORTACIÓN DE SUPABASE
# =====================================================

# Cliente Supabase centralizado del proyecto
from supabase_config import (
    supabase,
    TABLA_BITACORA_MOVIMIENTOS
)
from app_context import obtener_usuario_actual

# =====================================================
# FUNCIÓN: obtener_equipo_local()
# =====================================================
def obtener_equipo_local():
    """
    Obtiene el nombre del equipo donde se ejecuta el sistema.

    RETORNA:
        str:
            Nombre del equipo local.
    """

    try:
        return socket.gethostname()

    except Exception:
        logger.warning("No fue posible obtener el nombre del equipo.", exc_info=True)
        return "DESCONOCIDO"


# =====================================================
# FUNCIÓN: obtener_ip_local()
# =====================================================
def obtener_ip_local():
    """
    Obtiene la dirección IP local del equipo.

    RETORNA:
        str:
            Dirección IP local.
    """

    try:
        return socket.gethostbyname(socket.gethostname())

    except Exception:
        logger.warning("No fue posible obtener la IP local.", exc_info=True)
        return "DESCONOCIDA"


# =====================================================
# FUNCIÓN: registrar_movimiento()
# =====================================================
def registrar_movimiento(
    id_usuario=None,
    usuario="DESCONOCIDO",
    modulo="GENERAL",
    accion="SIN_ACCION",
    descripcion="Movimiento sin descripción",
    registro_afectado=None,
    ciudad=None,
    region=None,
    pais=None
):
    """
    Registra un movimiento del usuario en Supabase.

    PARÁMETROS:
        id_usuario:
            ID del usuario que realiza la acción.

        usuario:
            Nombre de usuario que realiza el movimiento.

        modulo:
            Módulo donde ocurrió la acción.
            Ejemplo:
                "Usuarios", "Login", "Bitácora", "Reportes"

        accion:
            Tipo de acción realizada.
            Ejemplo:
                "CREAR", "EDITAR", "ELIMINAR", "EXPORTAR", "CONSULTAR"

        descripcion:
            Descripción clara del movimiento realizado.

        registro_afectado:
            Información opcional del registro afectado.

        ciudad:
            Ciudad detectada del usuario.

        region:
            Región o estado detectado.

        pais:
            País detectado.

    RETORNA:
        bool:
            True si el movimiento fue registrado correctamente.
            False si ocurrió un error.
    """

    try:

        # =================================================
        # OBTENER USUARIO ACTIVO
        # =================================================
        usuario_activo = obtener_usuario_actual()

        if id_usuario is None:
            id_usuario = usuario_activo.get("id_usuario")

        if usuario == "DESCONOCIDO":
            usuario = usuario_activo.get("usuario", "DESCONOCIDO")

        # =================================================
        # DATOS A INSERTAR EN SUPABASE
        # =================================================

        datos = {
            "id_usuario": id_usuario,
            "usuario": usuario,
            "modulo": modulo,
            "accion": accion,
            "descripcion": descripcion,
            "registro_afectado": registro_afectado,
            "ip_local": obtener_ip_local(),
            "equipo": obtener_equipo_local(),
            "ciudad": ciudad,
            "region": region,
            "pais": pais
        }

        # =================================================
        # INSERTAR REGISTRO EN SUPABASE
        # =================================================

        supabase.table(TABLA_BITACORA_MOVIMIENTOS).insert(datos).execute()

        return True

    except Exception as error:
        logger.exception("Error al registrar movimiento.")
        return False


# =====================================================
# FUNCIÓN: registrar_movimiento_seguro()
# =====================================================
def registrar_movimiento_seguro(
    modulo="GENERAL",
    accion="SIN_ACCION",
    descripcion="Movimiento sin descripción",
    registro_afectado=None,
):
    """
    Wrapper simple para auditoría interna.

    Sirve para que todos los servicios registren movimientos sin tener
    que repetir usuario, equipo e IP. Nunca debe romper el flujo del
    sistema si la auditoría falla.
    """

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

# =====================================================
# FUNCIÓN: obtener_bitacora_movimientos()
# =====================================================
def obtener_bitacora_movimientos():
    """
    Consulta los movimientos registrados en Supabase.

    RETORNA:
        list:
            Lista de movimientos ordenados del más reciente al más antiguo.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_BITACORA_MOVIMIENTOS)
            .select("*")
            .order("fecha_hora", desc=True)
            .execute()
        )

        # Registramos la consulta de auditoría sin interrumpir si falla.
        try:
            registrar_movimiento(
                modulo="AUDITORIA",
                accion="CONSULTAR",
                descripcion="Consulta de bitácora de movimientos",
                registro_afectado=f"Total consultado: {len(respuesta.data or [])}",
            )
        except Exception:
            logger.warning("No fue posible auditar la consulta de movimientos.", exc_info=True)

        return respuesta.data

    except Exception as error:
        logger.exception("Error al consultar bitácora de movimientos.")
        return []



# =====================================================
# FUNCIÓN: obtener_movimientos_usuario_actual()
# =====================================================
def obtener_movimientos_usuario_actual(limite=300):
    """
    Consulta únicamente los movimientos del usuario en sesión.

    Esta función alimenta la bitácora personal. Es de solo consulta y no
    expone movimientos de otros usuarios a perfiles no administrativos.
    """

    try:
        usuario_activo = obtener_usuario_actual()
        id_usuario = usuario_activo.get("id_usuario")
        usuario = usuario_activo.get("usuario")

        consulta = supabase.table(TABLA_BITACORA_MOVIMIENTOS).select("*")

        if id_usuario:
            consulta = consulta.eq("id_usuario", id_usuario)
        elif usuario:
            consulta = consulta.eq("usuario", usuario)
        else:
            return []

        respuesta = consulta.order("fecha_hora", desc=True).limit(limite).execute()
        return respuesta.data or []

    except Exception:
        logger.exception("Error al consultar bitácora personal.")
        return []

# =====================================================
# FUNCIÓN: obtener_estadisticas_movimientos()
# =====================================================
def obtener_estadisticas_movimientos():
    """
    Obtiene estadísticas generales de movimientos.

    RETORNA:
        tuple:
            Total de movimientos, total de usuarios distintos
            y total de módulos registrados.
    """

    try:
        movimientos = obtener_bitacora_movimientos()

        total = len(movimientos)
        usuarios = len(set(m["usuario"] for m in movimientos if m.get("usuario")))
        modulos = len(set(m["modulo"] for m in movimientos if m.get("modulo")))

        return total, usuarios, modulos

    except Exception as error:
        logger.exception("Error al obtener estadísticas de movimientos.")
        return 0, 0, 0

# =====================================================
# FUNCIÓN: _coincide_movimiento()
# =====================================================
def _coincide_movimiento(movimiento, termino):
    """Filtro local tolerante sobre un movimiento."""

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
        "ciudad",
        "region",
        "pais",
    ]

    return any(
        termino in str(movimiento.get(campo, "") or "").lower()
        for campo in campos
    )


# =====================================================
# FUNCIÓN: buscar_movimientos()
# =====================================================
def buscar_movimientos(termino="", limite=200):
    """
    Busca movimientos administrativos bajo demanda.

    Nota de rendimiento:
    - No se consulta nada al abrir la vista.
    - Solo cuando el usuario busca, se trae una ventana reciente
      y se filtra localmente para evitar errores por tipos de dato
      en Supabase/PostgREST.
    """

    try:
        termino = str(termino or "").strip()
        if not termino:
            return []

        respuesta = (
            supabase
            .table(TABLA_BITACORA_MOVIMIENTOS)
            .select("*")
            .order("fecha_hora", desc=True)
            .limit(max(limite, 500))
            .execute()
        )

        registros = respuesta.data or []
        return [m for m in registros if _coincide_movimiento(m, termino)][:limite]

    except Exception:
        logger.exception("Error al buscar movimientos.")
        return []


# =====================================================
# FUNCIÓN: buscar_movimientos_usuario_actual()
# =====================================================
def buscar_movimientos_usuario_actual(termino="", limite=100):
    """
    Busca movimientos del usuario actual bajo demanda.
    """

    try:
        termino = str(termino or "").strip()
        if not termino:
            return []

        usuario_activo = obtener_usuario_actual()
        id_usuario = usuario_activo.get("id_usuario")
        usuario = usuario_activo.get("usuario")

        consulta = supabase.table(TABLA_BITACORA_MOVIMIENTOS).select("*")

        if id_usuario:
            consulta = consulta.eq("id_usuario", id_usuario)
        elif usuario:
            consulta = consulta.eq("usuario", usuario)
        else:
            return []

        respuesta = consulta.order("fecha_hora", desc=True).limit(max(limite, 300)).execute()
        registros = respuesta.data or []
        return [m for m in registros if _coincide_movimiento(m, termino)][:limite]

    except Exception:
        logger.exception("Error al buscar movimientos del usuario actual.")
        return []
