from core.logger import configurar_logger

logger = configurar_logger(__name__)
from services.movimientos_service import registrar_movimiento_seguro

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
import socket
from datetime import datetime

import requests

from supabase_config import supabase, TABLA_USUARIOS, TABLA_BITACORA_LOGIN
from security.passwords import verificar_password, requiere_migracion_a_bcrypt, generar_hash_password


# =====================================================
# FUNCIÓN: obtener_geolocalizacion()
# =====================================================
def obtener_geolocalizacion():
    """
    Obtiene una ubicación aproximada por IP pública.

    Retorna un diccionario con valores seguros aunque falle internet.
    Esta función no debe detener el login si la consulta externa falla.
    """

    try:
        respuesta = requests.get(
            "https://ipapi.co/json/",
            timeout=5
        )

        if respuesta.status_code == 200:
            datos = respuesta.json()

            return {
                "latitud": datos.get("latitude", "No disponible"),
                "longitud": datos.get("longitude", "No disponible"),
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

        registrar_movimiento_seguro(
            modulo="LOGIN",
            accion="LOGIN_VALIDADO",
            descripcion=f"Credenciales válidas para usuario: {nickname}",
            registro_afectado=usuario.get("id_usuario"),
        )
        return usuario

    except Exception as error:
        logger.exception("Error al validar login.")
        return None


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
            "latitud": latitud,
            "longitud": longitud,
            "ciudad": ciudad,
            "region": region,
            "pais": pais
        }

        supabase.table(TABLA_BITACORA_LOGIN).insert(datos).execute()

    except Exception as error:
        logger.exception("Error al registrar bitácora login.")


# =====================================================
# FUNCIÓN: cambiar_password_usuario()
# =====================================================
def cambiar_password_usuario(nickname, rfc, nueva_password):
    """
    Cambia la contraseña validando nickname + RFC.

    Nota importante:
    En usuarios creados desde la app, el RFC puede estar cifrado. Por eso
    esta función primero intenta validar por nickname y después compara RFC
    en claro o descifrado cuando sea posible.

    También evita bloquear usuarios: después de guardar el hash nuevo, lo
    vuelve a leer y verifica que funcione. Si no funciona, restaura el valor
    anterior.
    """

    try:
        from security.passwords import generar_hash_password, verificar_password
        from security.data_encryption import descifrar_valor

        nickname = str(nickname or "").strip()
        rfc = str(rfc or "").strip().upper()
        nueva_password = str(nueva_password or "")

        if not nickname or not rfc or not nueva_password:
            return False, "Usuario, RFC y nueva contraseña son obligatorios."

        respuesta_busqueda = (
            supabase
            .table(TABLA_USUARIOS)
            .select("id_usuario, usu_nickname, usu_rfc, usu_password")
            .ilike("usu_nickname", nickname)
            .limit(1)
            .execute()
        )

        if not respuesta_busqueda.data:
            return False, "No se encontró usuario con ese nickname"

        usuario = respuesta_busqueda.data[0]
        rfc_guardado = str(usuario.get("usu_rfc") or "").strip().upper()

        # RFC puede venir en claro o cifrado. Intentamos descifrar sin romper
        # compatibilidad con registros antiguos.
        rfc_descifrado = rfc_guardado
        try:
            valor_descifrado = descifrar_valor(rfc_guardado)
            if valor_descifrado:
                rfc_descifrado = str(valor_descifrado).strip().upper()
        except Exception:
            pass

        if rfc not in (rfc_guardado, rfc_descifrado):
            return False, "El RFC no corresponde al usuario indicado"

        id_usuario = usuario.get("id_usuario")
        password_anterior = usuario.get("usu_password") or ""
        nuevo_hash = generar_hash_password(nueva_password)

        if len(nuevo_hash) < 55:
            return False, "No fue posible generar un hash seguro para la contraseña."

        if not verificar_password(nueva_password, nuevo_hash):
            return False, "No fue posible validar el hash de la nueva contraseña."

        supabase.table(TABLA_USUARIOS).update({"usu_password": nuevo_hash}).eq("id_usuario", id_usuario).execute()

        verificacion = (
            supabase
            .table(TABLA_USUARIOS)
            .select("usu_password")
            .eq("id_usuario", id_usuario)
            .limit(1)
            .execute()
        )

        password_confirmado = ""
        if verificacion.data:
            password_confirmado = verificacion.data[0].get("usu_password") or ""

        if len(str(password_confirmado)) < 55:
            supabase.table(TABLA_USUARIOS).update({"usu_password": password_anterior}).eq("id_usuario", id_usuario).execute()
            return False, (
                "La base de datos no guardó completo el hash de contraseña. "
                "Ejecuta la migración para convertir usu_password a TEXT."
            )

        if not verificar_password(nueva_password, password_confirmado):
            supabase.table(TABLA_USUARIOS).update({"usu_password": password_anterior}).eq("id_usuario", id_usuario).execute()
            return False, (
                "La contraseña nueva no pudo verificarse después de guardarse. "
                "No se aplicó el cambio. Revisa que la columna usu_password "
                "permita guardar al menos 80 caracteres."
            )

        registrar_movimiento_seguro(
            modulo="USUARIOS",
            accion="CAMBIAR_PASSWORD",
            descripcion=f"Cambio de contraseña para usuario: {nickname}",
            registro_afectado=id_usuario,
        )
        return True, "La contraseña fue cambiada correctamente"

    except Exception:
        logger.exception("Error al cambiar contraseña.")
        return False, "Ocurrió un error al cambiar la contraseña"
