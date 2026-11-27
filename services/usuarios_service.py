from core.logger import configurar_logger
from core.error_reporting import register_error
from core.date_utils import normalizar_campos_fecha
from core.performance import page_range, TTLCache
from services.query_compat import execute_select_compatible

logger = configurar_logger(__name__)
from services.movimientos_service import registrar_movimiento_seguro




from supabase_config import supabase, TABLA_USUARIOS
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


def registrar_usuario(datos, clave_admin=None):
    from services.desktop_users_write import guardar_cuenta
    return guardar_cuenta(datos, clave_admin)


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
    from services.desktop_secure_reads import listar
    return listar("desktop-users", "listar", limite)


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
        from services.desktop_secure_reads import ConsultaSeguraError
        mensaje = str(error) if isinstance(error, ConsultaSeguraError) else "No fue posible consultar los usuarios."
        raise UsuarioServiceError(mensaje) from error


def crear_usuario_admin(datos, clave_admin):
    return registrar_usuario(datos, clave_admin)


def actualizar_usuario_admin(id_usuario, datos, seleccionado, clave_admin, activar=False):
    from services.desktop_users_write import guardar_cuenta
    if not seleccionado or str(id_usuario) != str(seleccionado.get("id_usuario")):
        return False, "Selecciona nuevamente un usuario.", None
    return guardar_cuenta(datos, clave_admin, seleccionado, activar)


def obtener_usuario_por_id(id_usuario):
    from app_context import obtener_usuario_actual
    from services.desktop_secure_reads import consultar, ConsultaSeguraError
    if not id_usuario:
        return None
    try:
        if str(id_usuario) == str(obtener_usuario_actual().get("id_usuario")):
            registro = consultar("desktop-users", "mi_perfil")
        else:
            registro = consultar("desktop-users", "detalle", id_usuario=int(id_usuario))
        if str(registro.get("id_usuario")) != str(id_usuario):
            raise ConsultaSeguraError("El perfil recibido no corresponde a la consulta.")
        return descifrar_diccionario(registro, CAMPOS_SENSIBLES_USUARIO)
    except Exception:
        logger.exception("Error al obtener perfil autorizado.")
        return None





def cambiar_password_usuario_actual(password_actual, password_nuevo, password_confirmacion):
    from services.desktop_password_change import cambiar_password
    return cambiar_password(password_actual, password_nuevo, password_confirmacion)


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