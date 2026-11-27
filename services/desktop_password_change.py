import re
from urllib.parse import urlsplit

import requests


def cambiar_password(password_actual, password_nuevo, password_confirmacion):
    from app_context import obtener_usuario_actual
    from services.sesion_axia_compartida import obtener_sesion
    from supabase_config import SUPABASE_URL, SUPABASE_KEY

    actual = str(password_actual or "")
    nuevo = str(password_nuevo or "")
    if not actual:
        return False, "Captura tu contraseña actual."
    if nuevo != str(password_confirmacion or ""):
        return False, "La nueva contraseña y la confirmación no coinciden."
    if len(actual.encode("utf-8")) > 72 or re.search(r"[\x00-\x1f\x7f]", actual):
        return False, "Contraseña actual inválida. Contacta a soporte si necesitas recuperar tu cuenta."
    if (len(nuevo) < 10 or len(nuevo.encode("utf-8")) > 72 or not re.search(r"[A-Z]", nuevo)
            or not re.search(r"[a-z]", nuevo) or not re.search(r"[0-9]", nuevo)
            or not re.search(r"[^A-Za-z0-9]", nuevo) or re.search(r"[\x00-\x1f\x7f]", nuevo)
            or nuevo == actual):
        return False, "Utiliza una contraseña distinta, de al menos 10 caracteres y máximo 72 bytes UTF-8, con mayúscula, minúscula, número y carácter especial."
    token = obtener_sesion(obtener_usuario_actual().get("id_usuario"))
    if not token:
        return False, "Sesión inválida o vencida. Inicia sesión nuevamente."
    base = str(SUPABASE_URL).rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        return False, "Configuración HTTPS inválida."
    try:
        respuesta = requests.post(
            f"{base}/functions/v1/desktop-password-change",
            json={"passwordActual": actual, "passwordNuevo": nuevo},
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=(6, 30), allow_redirects=False,
        )
        body = respuesta.json()
    except (requests.RequestException, ValueError):
        return False, "No se pudo confirmar el cambio. Verifica la conexión y prueba iniciar sesión con tu nueva contraseña antes de reintentar."
    if not isinstance(body, dict):
        return False, "Respuesta inválida. No se pudo confirmar el cambio."
    data = body.get("data")
    if respuesta.status_code == 200 and body.get("ok") is True and isinstance(data, dict) and data.get("cambiado") is True:
        return True, "Contraseña actualizada correctamente. Cierra sesión e ingresa con la nueva contraseña."
    mensajes = {400: "La contraseña no cumple los requisitos.", 401: "Sesión inválida o vencida. Inicia sesión nuevamente.",
                403: "La contraseña actual no es correcta.", 409: "La cuenta requiere revisión o cambió durante la solicitud. Inicia sesión nuevamente.",
                429: "Demasiados intentos. Intenta más tarde."}
    mensaje = mensajes.get(respuesta.status_code, "No se pudo confirmar el cambio. Verifica antes de reintentar.")
    referencia = body.get("requestId")
    if isinstance(referencia, str) and re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", referencia):
        mensaje += f" Solicitud: {referencia}"
    return False, mensaje
