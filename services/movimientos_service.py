from core.logger import configurar_logger

logger = configurar_logger(__name__)

COLUMNAS_MOVIMIENTOS = "id_usuario,fecha_hora,usuario,modulo,accion,descripcion,equipo,ip_local,registro_afectado,latitud,longitud,ciudad,region,pais"






import socket
import json
from datetime import datetime
from core.app_paths import user_data_dir






from supabase_config import (
    supabase,
    TABLA_BITACORA_MOVIMIENTOS
)
from app_context import obtener_usuario_actual




def obtener_equipo_local():
    try:
        return socket.gethostname()

    except Exception:
        logger.warning("No fue posible obtener el nombre del equipo.", exc_info=True)
        return "DESCONOCIDO"





def obtener_ip_local():
    try:
        return socket.gethostbyname(socket.gethostname())

    except Exception:
        logger.warning("No fue posible obtener la IP local.", exc_info=True)
        return "DESCONOCIDA"


def _guardar_movimiento_pendiente(datos):
    try:
        carpeta = user_data_dir() / "audit_pending"
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / "movimientos_pendientes.jsonl"
        payload = dict(datos)
        payload["pendiente_desde"] = datetime.now().isoformat()
        with ruta.open("a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    except Exception:
        logger.exception("No fue posible conservar localmente el movimiento pendiente.")





def registrar_movimiento(
    id_usuario=None,
    usuario="DESCONOCIDO",
    modulo="GENERAL",
    accion="SIN_ACCION",
    descripcion="Movimiento sin descripción",
    registro_afectado=None,
    latitud=None,
    longitud=None,
    ciudad=None,
    region=None,
    pais=None
):

    try:




        usuario_activo = obtener_usuario_actual()

        if id_usuario is None:
            id_usuario = usuario_activo.get("id_usuario")

        if usuario == "DESCONOCIDO":
            usuario = usuario_activo.get("usuario", "DESCONOCIDO")

        ubicacion = usuario_activo.get("ubicacion") or {}
        if latitud is None:
            latitud = ubicacion.get("latitud")
        if longitud is None:
            longitud = ubicacion.get("longitud")
        if ciudad is None:
            ciudad = ubicacion.get("ciudad")
        if region is None:
            region = ubicacion.get("region")
        if pais is None:
            pais = ubicacion.get("pais")





        datos = {
            "id_usuario": id_usuario,
            "usuario": usuario,
            "modulo": modulo,
            "accion": accion,
            "descripcion": descripcion,
            "registro_afectado": registro_afectado,
            "ip_local": obtener_ip_local(),
            "equipo": obtener_equipo_local(),
            "latitud": latitud,
            "longitud": longitud,
            "ciudad": ciudad,
            "region": region,
            "pais": pais
        }





        supabase.table(TABLA_BITACORA_MOVIMIENTOS).insert(datos).execute()

        return True

    except Exception as error:
        logger.exception("Error al registrar movimiento; se conservará en cola local.")
        try:
            _guardar_movimiento_pendiente(datos)
        except UnboundLocalError:
            logger.warning("No fue posible construir el movimiento para la cola local.", exc_info=True)
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
