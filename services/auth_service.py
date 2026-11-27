from core.logger import configurar_logger

logger = configurar_logger(__name__)




import platform
import os
import socket
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import requests



def formatear_coordenada_7_decimales(valor):
    try:
        numero = Decimal(str(valor).strip())
        return format(numero.quantize(Decimal("0.0000001"), rounding=ROUND_HALF_UP), "f")
    except (InvalidOperation, ValueError, TypeError, AttributeError):
        return "No disponible"





def obtener_geolocalizacion():
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
        logger.warning("No fue posible obtener geolocalización.", exc_info=True)

    return {
        "latitud": "No disponible",
        "longitud": "No disponible",
        "ciudad": "No disponible",
        "region": "No disponible",
        "pais": "No disponible"
    }





def obtener_contexto_login():
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





class ErrorAutenticacion(RuntimeError):
    pass


def validar_login(nickname, password, contexto=None):
    from core.version import APP_VERSION
    from supabase_config import SUPABASE_URL, SUPABASE_KEY
    import time

    if not SUPABASE_URL.startswith("https://"):
        raise ErrorAutenticacion("La autenticación requiere HTTPS.")
    contexto = contexto or {}
    try:
        respuesta = requests.post(
            f"{SUPABASE_URL.rstrip('/')}/functions/v1/desktop-auth",
            json={"nickname": nickname.strip(), "password": password,
                  "deviceName": contexto.get("nombre_equipo", "AXIA DESKTOP"),
                  "appVersion": APP_VERSION, "ubicacion": contexto.get("ubicacion", {})},
            headers={"apikey": SUPABASE_KEY, "content-type": "application/json"},
            timeout=(6, 20), allow_redirects=False,
        )
    except requests.RequestException:
        raise ErrorAutenticacion("No fue posible contactar al servidor de autenticación.") from None
    try:
        body = respuesta.json()
    except ValueError:
        raise ErrorAutenticacion("Respuesta de autenticación no válida.") from None
    if not isinstance(body, dict):
        raise ErrorAutenticacion("Respuesta de autenticación no válida.")
    if respuesta.status_code == 401 and body.get("ok") is False:
        return None
    if respuesta.status_code == 429:
        raise ErrorAutenticacion("Demasiados intentos. Intenta nuevamente en unos minutos.")
    if respuesta.status_code != 200 or body.get("ok") is not True:
        raise ErrorAutenticacion("El servidor no pudo confirmar el acceso.")
    data = body.get("data")
    if not isinstance(data, dict):
        raise ErrorAutenticacion("Sesión de AXIA no válida.")
    try:
        uid = data["id_usuario"]
        rol = data["usu_tipo"]
        expira = data["expiresAtEpochSeconds"]
        token = data["accessToken"]
        if (type(uid) is not int or uid <= 0 or type(rol) is not int or rol not in range(1, 11)
                or type(expira) is not int or expira <= time.time() + 30
                or not isinstance(token, str) or token.count(".") != 2
                or not isinstance(data["usu_nickname"], str)
                or data["usu_nickname"].casefold() != nickname.strip().casefold()):
            raise ValueError
        usuario = {k: data[k] for k in ("id_usuario", "usu_nombre", "usu_apellido", "usu_nickname", "usu_tipo")}
    except (KeyError, TypeError, ValueError):
        raise ErrorAutenticacion("Sesión de AXIA no válida.") from None
    return usuario, token, expira


def cambiar_password_usuario(nickname, rfc, nueva_password):
    logger.warning("Intento de recuperación heredada bloqueado para usuario %r", nickname)
    return False, (
        "Por seguridad, el cambio de contraseña sin sesión fue deshabilitado. "
        "Solicita a un administrador que restablezca tu acceso y cambia la contraseña al ingresar."
    )