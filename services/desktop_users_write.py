import re
from urllib.parse import urlsplit

import requests


CAMPOS_CUENTA = frozenset({"usu_nombre", "usu_apellido", "usu_correo", "usu_depto", "usu_puesto", "usu_tipo"})


def guardar_cuenta(datos, clave_admin, seleccionado=None, activar=False):
    from app_context import obtener_usuario_actual
    from services.sesion_axia_compartida import obtener_sesion
    from supabase_config import SUPABASE_URL, SUPABASE_KEY

    actor = obtener_usuario_actual()
    if actor.get("usu_tipo") != 1:
        return False, "Administración de cuentas reservada al administrador.", None
    if not clave_admin:
        return False, "Confirma tu contraseña de administrador.", None
    token = obtener_sesion(actor.get("id_usuario"))
    if not token:
        return False, "Sesión inválida o vencida. Inicia sesión nuevamente.", None
    base = str(SUPABASE_URL).rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        return False, "Configuración HTTPS inválida.", None
    datos = dict(datos or {})
    nuevo = datos.get("usu_password") or None
    if nuevo is not None and (nuevo != datos.get("confirmar_password") or len(nuevo) < 10 or len(nuevo.encode("utf-8")) > 72 or not re.search(r"[A-Z]", nuevo) or not re.search(r"[a-z]", nuevo) or not re.search(r"[0-9]", nuevo) or not re.search(r"[^A-Za-z0-9]", nuevo) or re.search(r"[\x00-\x1f\x7f]", nuevo) or nuevo == clave_admin):
        return False, "La contraseña nueva no cumple los requisitos o no coincide con la confirmación.", None
    valores = {}
    try:
        for k in CAMPOS_CUENTA:
            if k in datos:
                valores[k] = int(datos[k]) if k == "usu_tipo" else str(datos[k] or "").strip()
        if "usu_tipo" in valores and not 2 <= valores["usu_tipo"] <= 10:
            return False, "El rol debe estar entre 2 y 10.", None
        for k in ("usu_nombre", "usu_apellido"):
            if k in valores and not valores[k]:
                return False, "Nombre y apellido son obligatorios.", None
        if seleccionado is None:
            if not nuevo or not {"usu_nombre", "usu_apellido", "usu_tipo"}.issubset(valores):
                return False, "Completa nombre, apellido, perfil y contraseña.", None
            valores["usu_nickname"] = str(datos.get("usu_nickname") or "").strip()
            if not re.fullmatch(r"[A-Za-z0-9._-]{3,40}", valores["usu_nickname"]):
                return False, "Nickname inválido (3 a 40 caracteres).", None
            objetivo, esperado = None, {}
        else:
            objetivo = int(seleccionado["id_usuario"])
            if objetivo == int(actor["id_usuario"]) or seleccionado.get("usu_tipo") == 1 or seleccionado.get("usu_activo") is not True or seleccionado.get("usu_fecha_baja") is not None:
                return False, "No se puede modificar esta cuenta desde Administración de Usuarios.", None
            if any(k not in seleccionado for k in ("usu_tipo", "usu_activo", "usu_acceso_habilitado", *valores)):
                return False, "Consulta nuevamente el usuario antes de guardar.", None
            valores = {k: v for k, v in valores.items() if v != (seleccionado[k] if k == "usu_tipo" else str(seleccionado[k] or "").strip())}
            esperado = {k: seleccionado[k] for k in {"usu_tipo", "usu_activo", "usu_acceso_habilitado", *valores}}
            if not valores and nuevo is None:
                return False, "No hay cambios para guardar.", None
            if activar and (nuevo is None or seleccionado["usu_acceso_habilitado"] is not False):
                return False, "La activación requiere una contraseña nueva y acceso pendiente.", None
    except (ValueError, TypeError, KeyError):
        return False, "Datos de cuenta inválidos.", None
    try:
        respuesta = requests.post(f"{base}/functions/v1/desktop-users-write", json={"accion": "crear" if objetivo is None else "actualizar", "id_usuario": objetivo, "datos": valores, "esperado": esperado, "passwordActual": clave_admin, "passwordNuevo": nuevo, "activar": bool(activar)}, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=(6, 40), allow_redirects=False)
        body = respuesta.json()
    except (requests.RequestException, ValueError):
        return False, "No se confirmó el cambio. Consulta la cuenta antes de reintentar.", None
    if not isinstance(body, dict):
        return False, "Respuesta inválida del servidor.", None
    data = body.get("data")
    if respuesta.status_code == 200 and body.get("ok") is True and isinstance(data, dict) and set(data) == {"id_usuario"} and type(data["id_usuario"]) is int and data["id_usuario"] > 0 and (objetivo is None or data["id_usuario"] == objetivo):
        return True, "Cuenta guardada y movimiento registrado.", data
    mensajes = {400: "Datos de cuenta inválidos.", 401: "Sesión inválida o vencida.", 403: "Contraseña administrativa incorrecta u operación no autorizada.", 404: "Cuenta no encontrada.", 409: "Nickname duplicado o cuenta modificada. Consulta nuevamente.", 429: "Demasiados intentos. Intenta más tarde."}
    mensaje = mensajes.get(respuesta.status_code, "No se confirmó la operación. Consulta antes de reintentar.")
    referencia = body.get("requestId")
    if isinstance(referencia, str) and re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", referencia):
        mensaje += f" Solicitud: {referencia}"
    return False, mensaje, None
