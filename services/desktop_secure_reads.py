from urllib.parse import urlsplit

import requests


class ConsultaSeguraError(RuntimeError):
    pass


def consultar(servicio, accion, **campos):
    from app_context import obtener_usuario_actual
    from services.sesion_axia_compartida import obtener_sesion
    from supabase_config import SUPABASE_URL, SUPABASE_KEY

    acciones = {"desktop-users": {"listar", "detalle", "mi_perfil"}, "desktop-audit": {"accesos", "movimientos", "mis_movimientos"}}
    if accion not in acciones.get(servicio, set()) or "accion" in campos:
        raise ConsultaSeguraError("Operación de consulta no admitida.")
    token = obtener_sesion(obtener_usuario_actual().get("id_usuario"))
    if not token:
        raise ConsultaSeguraError("Sesión vencida. Inicia sesión nuevamente.")
    base = str(SUPABASE_URL).rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        raise ConsultaSeguraError("Configuración HTTPS inválida.")
    try:
        respuesta = requests.post(f"{base}/functions/v1/{servicio}", json={"accion": accion, **campos}, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=(6, 25), allow_redirects=False)
        body = respuesta.json()
    except (requests.RequestException, ValueError):
        raise ConsultaSeguraError("No fue posible conectar con el servicio de consulta segura.") from None
    if not isinstance(body, dict):
        raise ConsultaSeguraError("Respuesta inválida del servidor.")
    if respuesta.status_code != 200 or body.get("ok") is not True:
        mensajes = {401: "Sesión inválida o vencida. Inicia sesión nuevamente.", 403: "Tu perfil no está autorizado para esta consulta.", 404: "Registro no encontrado."}
        mensaje = mensajes.get(respuesta.status_code, "No se pudo completar la consulta segura.")
        referencia = str(body.get("requestId") or "")
        if len(referencia) == 36 and all(c in "0123456789abcdef-" for c in referencia.lower()):
            mensaje += f" Solicitud: {referencia}"
        raise ConsultaSeguraError(mensaje)
    data = body.get("data")
    if accion in {"detalle", "mi_perfil"}:
        if not isinstance(data, dict) or "usu_password" in data:
            raise ConsultaSeguraError("Respuesta de perfil inválida.")
    elif not isinstance(data, list) or any(not isinstance(row, dict) or "usu_password" in row for row in data):
        raise ConsultaSeguraError("Respuesta de listado inválida.")
    return data


def listar(servicio, accion, limite):
    limite = max(0, min(int(limite), 100000))
    resultado = []
    while len(resultado) < limite:
        cantidad = min(200, limite - len(resultado))
        lote = consultar(servicio, accion, offset=len(resultado), limit=cantidad)
        if len(lote) > cantidad:
            raise ConsultaSeguraError("Paginación inválida del servidor.")
        resultado.extend(lote)
        if len(lote) < cantidad:
            break
    return resultado
