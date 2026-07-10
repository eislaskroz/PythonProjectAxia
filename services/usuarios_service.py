from core.logger import configurar_logger
from core.date_utils import normalizar_campos_fecha

logger = configurar_logger(__name__)
from services.movimientos_service import registrar_movimiento_seguro

# =====================================================
# SERVICIO DE USUARIOS - AXIA
# =====================================================
"""
Este módulo concentra la lógica de negocio relacionada con usuarios.

Incluye:
- Registro administrativo.
- Búsqueda administrativa.
- Actualización administrativa.
- Bcrypt para contraseñas.
- Cifrado reversible de datos sensibles que sí deben mostrarse después.
"""

from supabase_config import supabase, TABLA_USUARIOS
from utils import encriptar_password
from security.data_encryption import (
    cifrar_diccionario,
    descifrar_diccionario,
    descifrar_lista,
)


CAMPOS_SENSIBLES_USUARIO = [
    "usu_rfc",
    "usu_curp",
    "usu_imss",
    "usu_ine",
    "usu_fechanac",
    "usu_telefono",
    "usu_calle",
    "usu_numero",
    "usu_colonia",
    "usu_municipio",
    "usu_estado",
    "usu_cp",
    "usu_regimen",
]


def normalizar_datos_usuario(datos):
    """
    Normaliza campos antes de validar o guardar.
    """

    datos_normalizados = dict(datos or {})

    for campo in ("usu_rfc", "usu_curp", "usu_imss", "usu_ine"):
        datos_normalizados[campo] = str(datos_normalizados.get(campo, "") or "").upper()

    return datos_normalizados


def validar_datos_usuario(datos):
    """
    Valida las reglas básicas para crear un usuario.
    """

    if not datos.get("usu_nickname"):
        return False, "El usuario es obligatorio."

    if not datos.get("usu_password"):
        return False, "La contraseña es obligatoria."

    if datos.get("usu_password") != datos.get("confirmar_password"):
        return False, "Las contraseñas no coinciden."

    if len(datos.get("usu_password", "")) < 4:
        return False, "La contraseña debe tener mínimo 4 caracteres."

    if not datos.get("usu_nombre"):
        return False, "El nombre es obligatorio."

    if not datos.get("usu_apellido"):
        return False, "El apellido es obligatorio."

    return True, "Datos válidos"


def existe_nickname(nickname):
    """
    Revisa si un nickname ya existe en Supabase.
    """

    respuesta = (
        supabase
        .table(TABLA_USUARIOS)
        .select("id_usuario")
        .eq("usu_nickname", nickname)
        .limit(1)
        .execute()
    )

    return bool(respuesta.data)


def registrar_usuario(datos):
    """
    Registra un usuario nuevo en Supabase.
    """

    try:
        datos = normalizar_datos_usuario(datos)

        valido, mensaje = validar_datos_usuario(datos)

        if not valido:
            return False, mensaje, None

        if existe_nickname(datos["usu_nickname"]):
            return False, "Ese nickname ya está registrado.", None

        datos_guardar = dict(datos)
        datos_guardar.pop("confirmar_password", None)

        datos_guardar["usu_password"] = encriptar_password(
            datos_guardar["usu_password"]
        )

        datos_guardar["usu_tipo"] = 3

        datos_guardar = cifrar_diccionario(datos_guardar, CAMPOS_SENSIBLES_USUARIO)

        respuesta = (
            supabase
            .table(TABLA_USUARIOS)
            .insert(datos_guardar)
            .execute()
        )

        if bool(respuesta.data):
            usuario = descifrar_diccionario(respuesta.data[0], CAMPOS_SENSIBLES_USUARIO)
            registrar_movimiento_seguro(
                modulo="USUARIOS",
                accion="CREAR",
                descripcion="Alta administrativa de usuario",
                registro_afectado=usuario.get("id_usuario") or usuario.get("usu_nickname"),
            )
            return True, "El usuario fue registrado correctamente.", usuario

        return False, "No fue posible registrar el usuario.", None

    except Exception as error:
        logger.exception("Error al registrar usuario.")
        return False, f"No fue posible registrar el usuario.\n\n{error}", None


def _coincide_usuario(usuario, termino):
    """
    Filtro local sobre registros descifrados.
    """
    if not termino:
        return True

    termino = termino.lower().strip()
    campos = [
        "usu_nickname",
        "usu_nombre",
        "usu_apellido",
        "usu_rfc",
        "usu_telefono",
        "usu_depto",
        "usu_puesto",
    ]

    return any(
        termino in str(usuario.get(campo, "") or "").lower()
        for campo in campos
    )


def buscar_usuarios(termino="", limite=100):
    """
    Busca usuarios para la vista administrativa.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_USUARIOS)
            .select("*")
            .limit(limite)
            .execute()
        )

        registros = descifrar_lista(respuesta.data or [], CAMPOS_SENSIBLES_USUARIO)
        resultado = [
            usuario
            for usuario in registros
            if _coincide_usuario(usuario, termino)
        ]
        registrar_movimiento_seguro(
            modulo="USUARIOS",
            accion="BUSCAR",
            descripcion=f"Búsqueda administrativa de usuarios: {termino or 'SIN FILTRO'}",
            registro_afectado=f"Resultados: {len(resultado)}",
        )
        return resultado

    except Exception:
        logger.exception("Error al buscar usuarios.")
        return []


def crear_usuario_admin(datos):
    """
    Crea un usuario desde la vista administrativa.
    """

    return registrar_usuario(datos)


def actualizar_usuario_admin(id_usuario, datos):
    """
    Actualiza datos básicos de un usuario existente.

    La contraseña solo se actualiza si se captura una nueva.
    """

    try:
        if not id_usuario:
            return False, "Selecciona un usuario para modificar.", None

        datos_guardar = normalizar_datos_usuario(dict(datos))
        datos_guardar.pop("confirmar_password", None)

        password = datos_guardar.get("usu_password", "")
        if password:
            datos_guardar["usu_password"] = encriptar_password(password)
        else:
            datos_guardar.pop("usu_password", None)

        datos_guardar = cifrar_diccionario(datos_guardar, CAMPOS_SENSIBLES_USUARIO)

        respuesta = (
            supabase
            .table(TABLA_USUARIOS)
            .update(datos_guardar)
            .eq("id_usuario", id_usuario)
            .execute()
        )

        if respuesta.data:
            usuario = descifrar_diccionario(respuesta.data[0], CAMPOS_SENSIBLES_USUARIO)
            registrar_movimiento_seguro(
                modulo="USUARIOS",
                accion="ACTUALIZAR",
                descripcion=f"Actualización administrativa de usuario ID: {id_usuario}",
                registro_afectado=id_usuario,
            )
            return True, "Usuario actualizado correctamente.", usuario

        return False, "No fue posible actualizar el usuario.", None

    except Exception as error:
        logger.exception("Error al actualizar usuario.")
        return False, f"No fue posible actualizar el usuario.\n\n{error}", None

# =====================================================
# FUNCIÓN: obtener_usuario_por_id()
# =====================================================
def obtener_usuario_por_id(id_usuario):
    """
    Obtiene un usuario por ID para la sección Mi Usuario.
    La contraseña nunca se devuelve a la vista.
    """

    try:
        if not id_usuario:
            return None

        respuesta = (
            supabase
            .table(TABLA_USUARIOS)
            .select("*")
            .eq("id_usuario", id_usuario)
            .limit(1)
            .execute()
        )

        if not respuesta.data:
            return None

        usuario = descifrar_diccionario(respuesta.data[0], CAMPOS_SENSIBLES_USUARIO)
        usuario.pop("usu_password", None)
        return usuario

    except Exception:
        logger.exception("Error al obtener usuario por ID.")
        return None


# =====================================================
# FUNCIÓN: cambiar_password_usuario_actual()
# =====================================================
def cambiar_password_usuario_actual(password_actual, password_nuevo, password_confirmacion):
    """
    Permite que el usuario en sesión cambie su propia contraseña.

    Medida anti-bloqueo:
    después de guardar el hash nuevo en Supabase, se vuelve a leer el campo
    y se valida contra la contraseña nueva. Si no coincide, se restaura el
    valor anterior para evitar que el usuario quede sin acceso.
    """

    try:
        from app_context import obtener_usuario_actual
        from security.passwords import verificar_password, generar_hash_password

        usuario_activo = obtener_usuario_actual()
        id_usuario = usuario_activo.get("id_usuario")

        if not id_usuario:
            return False, "No se encontró una sesión activa válida."

        password_actual = str(password_actual or "")
        password_nuevo = str(password_nuevo or "")
        password_confirmacion = str(password_confirmacion or "")

        if not password_actual:
            return False, "Captura tu contraseña actual."

        if not password_nuevo:
            return False, "Captura la nueva contraseña."

        if password_nuevo != password_confirmacion:
            return False, "La nueva contraseña y la confirmación no coinciden."

        if len(password_nuevo) < 4:
            return False, "La nueva contraseña debe tener mínimo 4 caracteres."

        respuesta = (
            supabase
            .table(TABLA_USUARIOS)
            .select("id_usuario, usu_password")
            .eq("id_usuario", id_usuario)
            .limit(1)
            .execute()
        )

        if not respuesta.data:
            return False, "No fue posible localizar tu usuario."

        password_anterior = respuesta.data[0].get("usu_password") or ""

        if not verificar_password(password_actual, password_anterior):
            return False, "La contraseña actual no es correcta."

        nuevo_hash = generar_hash_password(password_nuevo)

        if len(nuevo_hash) < 55:
            return False, "No fue posible generar un hash seguro para la contraseña."

        # Validación local antes de tocar Supabase.
        if not verificar_password(password_nuevo, nuevo_hash):
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

        if not verificar_password(password_nuevo, password_confirmado):
            # Restauramos el valor anterior para no bloquear al usuario.
            supabase.table(TABLA_USUARIOS).update({"usu_password": password_anterior}).eq("id_usuario", id_usuario).execute()
            return False, (
                "La contraseña nueva no pudo verificarse después de guardarse. "
                "No se aplicó el cambio. Revisa que la columna usu_password "
                "permita guardar al menos 80 caracteres."
            )

        registrar_movimiento_seguro(
            modulo="MI_USUARIO",
            accion="CAMBIAR_PASSWORD",
            descripcion="El usuario cambió su propia contraseña",
            registro_afectado=id_usuario,
        )

        return True, "Contraseña actualizada correctamente. Cierra sesión e ingresa con la nueva contraseña."

    except Exception as error:
        logger.exception("Error al cambiar contraseña del usuario actual.")
        return False, f"No fue posible cambiar la contraseña.\n\n{error}"
