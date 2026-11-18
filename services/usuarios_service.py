from core.logger import configurar_logger
from core.error_reporting import register_error
from core.date_utils import normalizar_campos_fecha
from core.performance import page_range, TTLCache
from services.query_compat import execute_select_compatible

logger = configurar_logger(__name__)
from services.movimientos_service import registrar_movimiento_seguro

# =====================================================
# SERVICIO DE USUARIOS - AXIA
# =====================================================
from supabase_config import supabase, TABLA_USUARIOS
from utils import encriptar_password
from security.permissions import OPERADOR, TIPOS_VALIDOS
from security.data_encryption import (
    cifrar_diccionario,
    descifrar_diccionario,
    descifrar_lista,
)


COLUMNAS_USUARIOS = "id_usuario,usu_nickname,usu_nombre,usu_apellido,usu_rfc,usu_curp,usu_imss,usu_ine,usu_fechanac,usu_telefono,usu_correo,usu_calle,usu_numero,usu_colonia,usu_municipio,usu_estado,usu_cp,usu_regimen,usu_depto,usu_puesto,usu_tipo,usu_auth_id,fecha_registro"

_catalogo_usuarios_cache = TTLCache(ttl_seconds=120)


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
    datos_normalizados = dict(datos or {})

    for campo in ("usu_rfc", "usu_curp", "usu_imss", "usu_ine"):
        datos_normalizados[campo] = str(datos_normalizados.get(campo, "") or "").upper()

    datos_normalizados["usu_correo"] = str(datos_normalizados.get("usu_correo", "") or "").strip().lower()

    return datos_normalizados


def validar_datos_usuario(datos):
    if not datos.get("usu_nickname"):
        return False, "El usuario es obligatorio."

    if not datos.get("usu_password"):
        return False, "La contraseña es obligatoria."

    if datos.get("usu_password") != datos.get("confirmar_password"):
        return False, "Las contraseñas no coinciden."

    from security.passwords import validar_fortaleza_password
    password_valida, mensaje_password = validar_fortaleza_password(datos.get("usu_password", ""))
    if not password_valida:
        return False, mensaje_password

    if not datos.get("usu_nombre"):
        return False, "El nombre es obligatorio."

    if not datos.get("usu_apellido"):
        return False, "El apellido es obligatorio."

    correo = str(datos.get("usu_correo", "") or "").strip()
    if correo and ("@" not in correo or "." not in correo.rsplit("@", 1)[-1]):
        return False, "El correo electrónico de empresa no tiene un formato válido."

    try:
        usu_tipo = int(datos.get("usu_tipo", OPERADOR))
    except (TypeError, ValueError):
        return False, "El tipo de usuario debe ser un número entre 1 y 10."

    if usu_tipo not in TIPOS_VALIDOS:
        return False, "El tipo de usuario debe estar entre 1 y 10."

    datos["usu_tipo"] = usu_tipo
    return True, "Datos válidos"


def existe_nickname(nickname):
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

        datos_guardar["usu_tipo"] = int(datos_guardar.get("usu_tipo", OPERADOR))

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
        report = register_error(error, "Registrar usuario")
        logger.exception("Error al registrar usuario.")
        return False, (
            "No fue posible registrar el usuario. "
            f"Motivo técnico: {report.technical_message} "
            f"Código: {report.incident_id}"
        ), None


def _coincide_usuario(usuario, termino):
    if not termino:
        return True

    termino = termino.lower().strip()
    campos = [
        "usu_nickname",
        "usu_nombre",
        "usu_apellido",
        "usu_rfc",
        "usu_telefono",
        "usu_correo",
        "usu_depto",
        "usu_puesto",
    ]

    return any(
        termino in str(usuario.get(campo, "") or "").lower()
        for campo in campos
    )


class UsuarioServiceError(RuntimeError):
    pass


def _obtener_usuarios_paginados(limite=500):
    limite = max(1, int(limite or 500))
    page_size = min(500, limite)
    registros = []
    page = 1

    while len(registros) < limite:
        start, end = page_range(page, page_size)
        respuesta = execute_select_compatible(
            supabase,
            TABLA_USUARIOS,
            COLUMNAS_USUARIOS,
            lambda query, start=start, end=end: query.order("id_usuario").range(start, end),
        )
        lote = list(respuesta.data or [])
        registros.extend(lote)
        if len(lote) < page_size:
            break
        page += 1

    return registros[:limite]


def buscar_usuarios(termino="", limite=500):
    try:
        termino = str(termino or "").strip()
        registros = _obtener_usuarios_paginados(limite=limite)
        registros = descifrar_lista(registros, CAMPOS_SENSIBLES_USUARIO)
        resultado = [usuario for usuario in registros if _coincide_usuario(usuario, termino)]
        resultado.sort(
            key=lambda usuario: (
                str(usuario.get("usu_nickname", "") or "").casefold(),
                str(usuario.get("usu_nombre", "") or "").casefold(),
                str(usuario.get("usu_apellido", "") or "").casefold(),
            )
        )
        registrar_movimiento_seguro(
            modulo="USUARIOS",
            accion="BUSCAR",
            descripcion=f"Búsqueda administrativa de usuarios: {termino or 'SIN FILTRO'}",
            registro_afectado=f"Resultados: {len(resultado)}",
        )
        return resultado
    except Exception as error:
        logger.exception("Error al buscar usuarios.")
        raise UsuarioServiceError(
            "No fue posible consultar los usuarios. Revisa la conexión y la estructura de db_usuarios."
        ) from error


def crear_usuario_admin(datos):
    return registrar_usuario(datos)


def actualizar_usuario_admin(id_usuario, datos):
    try:
        if not id_usuario:
            return False, "Selecciona un usuario para modificar.", None

        datos_guardar = normalizar_datos_usuario(dict(datos))
        datos_guardar.pop("confirmar_password", None)

        if "usu_tipo" in datos_guardar:
            try:
                datos_guardar["usu_tipo"] = int(datos_guardar["usu_tipo"])
            except (TypeError, ValueError):
                return False, "El tipo de usuario debe ser un número entre 1 y 10.", None
            if datos_guardar["usu_tipo"] not in TIPOS_VALIDOS:
                return False, "El tipo de usuario debe estar entre 1 y 10.", None

        password = datos_guardar.get("usu_password", "")
        if password:
            datos_guardar["usu_password"] = encriptar_password(password)
            datos_guardar["usu_acceso_habilitado"] = True
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
        report = register_error(error, "Actualizar usuario")
        logger.exception("Error al actualizar usuario.")
        return False, (
            "No fue posible actualizar el usuario. "
            f"Motivo técnico: {report.technical_message} "
            f"Código: {report.incident_id}"
        ), None

# =====================================================
# FUNCIÓN: obtener_usuario_por_id()
# =====================================================
def obtener_usuario_por_id(id_usuario):
    try:
        if not id_usuario:
            return None

        respuesta = execute_select_compatible(
            supabase,
            TABLA_USUARIOS,
            COLUMNAS_USUARIOS,
            lambda query: query.eq("id_usuario", id_usuario).limit(1),
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
    try:
        from app_context import obtener_usuario_actual
        from security.passwords import verificar_password, generar_hash_password, validar_fortaleza_password

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

        password_valida, mensaje_password = validar_fortaleza_password(password_nuevo)
        if not password_valida:
            return False, mensaje_password

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


def _nombre_mostrable_usuario(usuario):
    nombre = " ".join(
        parte.strip()
        for parte in (
            str(usuario.get("usu_nombre", "") or ""),
            str(usuario.get("usu_apellido", "") or ""),
        )
        if parte and parte.strip()
    ).strip()
    nickname = str(usuario.get("usu_nickname", "") or "").strip()
    return nombre or nickname


def obtener_usuarios_por_tipos(tipos, limite=500):
    cache_key = (tuple(sorted(int(x) for x in tipos)), int(limite))
    cached = _catalogo_usuarios_cache.get(cache_key)
    if cached is not None:
        return list(cached)
    try:
        tipos_validos = sorted({int(tipo) for tipo in tipos if int(tipo) in TIPOS_VALIDOS})
        if not tipos_validos:
            return []

        registros = []
        pagina = 1
        tamano_pagina = min(300, max(1, int(limite)))
        while len(registros) < limite:
            inicio = (pagina - 1) * tamano_pagina
            fin = min(inicio + tamano_pagina, limite) - 1
            respuesta = (
                supabase
                .table(TABLA_USUARIOS)
                .select("id_usuario,usu_nickname,usu_nombre,usu_apellido,usu_tipo,usu_correo,usu_telefono")
                .in_("usu_tipo", tipos_validos)
                .order("id_usuario")
                .range(inicio, fin)
                .execute()
            )
            lote = list(respuesta.data or [])
            registros.extend(lote)
            if len(lote) < (fin - inicio + 1):
                break
            pagina += 1

        registros_validos = []
        frecuencias = {}
        for registro in registros:
            nombre_base = _nombre_mostrable_usuario(registro)
            if not nombre_base:
                continue
            registros_validos.append((registro, nombre_base))
            clave = nombre_base.casefold()
            frecuencias[clave] = frecuencias.get(clave, 0) + 1

        usuarios = []
        for registro, nombre_base in registros_validos:
            etiqueta = nombre_base
            if frecuencias.get(nombre_base.casefold(), 0) > 1:
                nickname = str(registro.get("usu_nickname", "") or "").strip()
                etiqueta = f"{nombre_base} ({nickname})" if nickname else nombre_base
            usuarios.append({**registro, "etiqueta": etiqueta})

        return sorted(usuarios, key=lambda item: item["etiqueta"].casefold())
    except Exception:
        logger.exception("Error al obtener usuarios por tipo para formularios.")
        return []


def obtener_nombres_usuarios_por_tipos(tipos, limite=500):
    return [
        usuario["etiqueta"]
        for usuario in obtener_usuarios_por_tipos(tipos, limite=limite)
    ]


def obtener_tecnicos_responsables(limite=500):
    return obtener_nombres_usuarios_por_tipos([4], limite=limite)


def obtener_supervisores_formulario(limite=500):
    return obtener_nombres_usuarios_por_tipos([2, 3], limite=limite)


def obtener_encargados_proyecto_formulario(limite=500):
    return obtener_nombres_usuarios_por_tipos([3, 4], limite=limite)