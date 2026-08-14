from core.logger import configurar_logger

logger = configurar_logger(__name__)

# =====================================================
# SERVICIO DE AUTENTICACIÓN - AXIA
# =====================================================
"""
Este módulo concentra la lógica de negocio relacionada con autenticación.

La interfaz gráfica NO debería consultar directamente Supabase ni decidir
cómo se validan passwords. Ese trabajo pertenece a esta capa de servicios.

Responsabilidades:
- Validar credenciales.
- Migrar passwords heredados a bcrypt.
- Registrar bitácora de login.
- Cambiar contraseñas.
- Obtener información técnica del equipo para auditoría.
"""

import platform
import os
import socket
from datetime import datetime
import json
from core.app_paths import user_data_dir
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import requests

from supabase_config import supabase, TABLA_USUARIOS, TABLA_BITACORA_LOGIN
from security.passwords import verificar_password, requiere_migracion_a_bcrypt, generar_hash_password


def formatear_coordenada_7_decimales(valor):
    """Devuelve una coordenada con exactamente siete cifras decimales."""
    try:
        numero = Decimal(str(valor).strip())
        return format(numero.quantize(Decimal("0.0000001"), rounding=ROUND_HALF_UP), "f")
    except (InvalidOperation, ValueError, TypeError, AttributeError):
        return "No disponible"


# =====================================================
# FUNCIÓN: obtener_geolocalizacion()
# =====================================================
def obtener_geolocalizacion():
    """
    Obtiene una ubicación aproximada por IP pública.

    Retorna un diccionario con valores seguros aunque falle internet.
    Esta función no debe detener el login si la consulta externa falla.
    """

    if os.getenv("AXIA_ENABLE_IP_GEOLOCATION", "1").strip().lower() not in {"1", "true", "yes"}:
        return {"latitud": "No disponible", "longitud": "No disponible", "ciudad": "No disponible", "region": "No disponible", "pais": "No disponible"}

    try:
        respuesta = requests.get(
            "https://ipapi.co/json/",
            timeout=5
        )

        if respuesta.status_code == 200:
            datos = respuesta.json()

            return {
                "latitud": formatear_coordenada_7_decimales(datos.get("latitude")),
                "longitud": formatear_coordenada_7_decimales(datos.get("longitude")),
                "ciudad": datos.get("city", "No disponible"),
                "region": datos.get("region", "No disponible"),
                "pais": datos.get("country_name", "No disponible")
            }

    except Exception:
        # No bloqueamos el inicio de sesión por error de geolocalización.
        logger.warning("No fue posible obtener geolocalización.", exc_info=True)

    return {
        "latitud": "No disponible",
        "longitud": "No disponible",
        "ciudad": "No disponible",
        "region": "No disponible",
        "pais": "No disponible"
    }


# =====================================================
# FUNCIÓN: obtener_contexto_login()
# =====================================================
def obtener_contexto_login():
    """
    Obtiene datos técnicos del equipo para la bitácora de login.

    Retorna:
        dict:
            direccion_ip, nombre_equipo y ubicación aproximada.
    """

    nombre_equipo = platform.node()

    try:
        direccion_ip = socket.gethostbyname(
            socket.gethostname()
        )
    except Exception:
        logger.warning("No fue posible obtener la IP local para login.", exc_info=True)
        direccion_ip = "No disponible"

    return {
        "direccion_ip": direccion_ip,
        "nombre_equipo": nombre_equipo,
        "ubicacion": obtener_geolocalizacion()
    }


# =====================================================
# FUNCIÓN: validar_login()
# =====================================================
def validar_login(nickname, password):
    """
    Valida las credenciales del usuario contra Supabase.

    Soporta:
    - bcrypt actual.
    - SHA-256 heredado.
    - texto plano heredado, si existiera.

    Si el password heredado coincide, lo migra automáticamente a bcrypt.

    Retorna:
        dict | None:
            Datos del usuario si el acceso es correcto.
            None si las credenciales son inválidas o hay error.
    """

    try:
        nickname = nickname.strip()
        password = password.strip()

        respuesta = (
            supabase
            .table(TABLA_USUARIOS)
            .select(
                "id_usuario, usu_nombre, usu_apellido, "
                "usu_nickname, usu_tipo, usu_password"
            )
            .ilike("usu_nickname", nickname)
            .limit(1)
            .execute()
        )

        if not respuesta.data:
            return None

        usuario = respuesta.data[0]
        password_guardado = usuario.get("usu_password", "")

        if not verificar_password(password, password_guardado):
            return None

        if requiere_migracion_a_bcrypt(password_guardado):
            (
                supabase
                .table(TABLA_USUARIOS)
                .update({
                    "usu_password": generar_hash_password(password)
                })
                .eq("id_usuario", usuario.get("id_usuario"))
                .execute()
            )

        return usuario

    except Exception as error:
        logger.exception("Error al validar login.")
        return None


def _guardar_login_pendiente(datos):
    try:
        carpeta = user_data_dir() / "audit_pending"
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / "login_pendientes.jsonl"
        payload = dict(datos)
        payload["pendiente_desde"] = datetime.now().isoformat()
        with ruta.open("a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    except Exception:
        logger.exception("No fue posible conservar localmente el login pendiente.")


# =====================================================
# FUNCIÓN: registrar_bitacora_login()
# =====================================================
def registrar_bitacora_login(
    id_usuario,
    nickname,
    estatus,
    descripcion,
    direccion_ip,
    nombre_equipo,
    latitud="",
    longitud="",
    ciudad="",
    region="",
    pais=""
):
    """
    Registra intentos de inicio de sesión en Supabase.

    Esta función no lanza errores hacia la UI. Si falla la bitácora,
    el sistema lo informa por consola y permite que la app continúe.
    """

    try:
        datos = {
            "id_usuario": id_usuario,
            "usu_nickname": nickname,
            "fecha_hora": datetime.now().isoformat(),
            "estatus": estatus,
            "descripcion": descripcion,
            "direccion_ip": direccion_ip,
            "nombre_equipo": nombre_equipo,
            "latitud": formatear_coordenada_7_decimales(latitud),
            "longitud": formatear_coordenada_7_decimales(longitud),
            "ciudad": ciudad,
            "region": region,
            "pais": pais
        }

        supabase.table(TABLA_BITACORA_LOGIN).insert(datos).execute()

    except Exception as error:
        logger.exception("Error al registrar bitácora login; se conservará en cola local.")
        try:
            _guardar_login_pendiente(datos)
        except UnboundLocalError:
            logger.warning("No fue posible construir el evento de login para la cola local.", exc_info=True)


# =====================================================
# FUNCIÓN: cambiar_password_usuario()
# =====================================================
def cambiar_password_usuario(nickname, rfc, nueva_password):
    """Recuperación insegura retirada: nickname + RFC no acredita identidad."""
    logger.warning("Intento de recuperación heredada bloqueado para usuario %r", nickname)
    return False, (
        "Por seguridad, el cambio de contraseña sin sesión fue deshabilitado. "
        "Solicita a un administrador que restablezca tu acceso y cambia la contraseña al ingresar."
    )
