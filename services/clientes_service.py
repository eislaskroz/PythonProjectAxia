"""
=========================================================
MÓDULO: services/clientes_service.py
DESCRIPCIÓN:
Servicio administrativo para buscar, crear y actualizar clientes.

Adaptado a la estructura real de db_clientes y con cifrado reversible
para datos sensibles.
=========================================================
"""

from core.logger import configurar_logger
from core.cache import ttl_cache, clear_cache
from supabase_config import supabase, TABLA_CLIENTES
from security.data_encryption import (
    cifrar_diccionario,
    descifrar_diccionario,
    descifrar_lista,
)

logger = configurar_logger(__name__)
from services.movimientos_service import registrar_movimiento_seguro


# Campos reales detectados en db_clientes.
CAMPOS_CLIENTE = [
    "cli_tipo",
    "cli_estatus",
    "cli_razonsocial",
    "cli_rfc",
    "cli_contacto",
    "cli_telefono",
    "cli_correo",
    "cli_calle",
    "cli_numero",
    "cli_colonia",
    "cli_municipio",
    "cli_estado",
    "cli_cp",
    "cli_notas",
]

# Campos que sí conviene cifrar porque contienen datos personales,
# fiscales, contacto o dirección.
CAMPOS_SENSIBLES_CLIENTE = [
    "cli_rfc",
    "cli_contacto",
    "cli_telefono",
    "cli_correo",
    "cli_calle",
    "cli_numero",
    "cli_colonia",
    "cli_municipio",
    "cli_estado",
    "cli_cp",
    "cli_notas",
]



def convertir_tipo_cliente_para_db(valor):
    """
    Convierte el tipo visual del formulario al smallint esperado por Supabase.

    db_clientes.cli_tipo espera un entero pequeño, por eso valores como
    "Cliente" deben transformarse antes de insertar/actualizar.
    """

    if valor is None:
        return 1

    if isinstance(valor, bool):
        return 1

    if isinstance(valor, int):
        return valor if valor > 0 else 1

    texto = str(valor).strip().lower()

    mapa = {
        "": 1,
        "cliente": 1,
        "proveedor": 2,
        "prospecto": 3,
        "interno": 4,
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4,
    }

    return mapa.get(texto, 1)


def convertir_tipo_cliente_para_ui(valor):
    """Convierte el smallint de Supabase a texto legible para el formulario."""

    if valor is None:
        return "Cliente"

    texto = str(valor).strip().lower()

    mapa = {
        "1": "Cliente",
        "2": "Proveedor",
        "3": "Prospecto",
        "4": "Interno",
        "cliente": "Cliente",
        "proveedor": "Proveedor",
        "prospecto": "Prospecto",
        "interno": "Interno",
    }

    return mapa.get(texto, str(valor).strip() or "Cliente")

def convertir_estatus_cliente_para_db(valor):
    """
    Convierte el estatus visual del formulario al tipo smallint de Supabase.

    db_clientes.cli_estatus espera un entero pequeño, por eso valores como
    "Activo" o "Inactivo" deben transformarse antes de insertar/actualizar.
    """

    if valor is None:
        return 1

    if isinstance(valor, bool):
        return 1 if valor else 0

    if isinstance(valor, int):
        return 1 if valor == 1 else 0

    texto = str(valor).strip().lower()

    if texto in ("", "activo", "activa", "alta", "habilitado", "habilitada", "vigente", "1", "true", "si", "sí"):
        return 1

    if texto in ("inactivo", "inactiva", "baja", "deshabilitado", "deshabilitada", "0", "false", "no"):
        return 0

    # Valor seguro por defecto: cliente activo.
    return 1


def convertir_estatus_cliente_para_ui(valor):
    """Convierte el smallint de Supabase a texto legible para el formulario."""

    if valor is None:
        return "Activo"

    if isinstance(valor, bool):
        return "Activo" if valor else "Inactivo"

    texto = str(valor).strip().lower()

    if texto in ("1", "activo", "activa", "alta", "habilitado", "habilitada", "vigente", "true", "si", "sí"):
        return "Activo"

    if texto in ("0", "inactivo", "inactiva", "baja", "deshabilitado", "deshabilitada", "false", "no"):
        return "Inactivo"

    return str(valor).strip() or "Activo"


def normalizar_cliente_para_ui(cliente):
    """Normaliza un registro leído de Supabase para mostrarlo en pantalla."""

    cliente = cliente or {}
    cliente["cli_tipo"] = convertir_tipo_cliente_para_ui(cliente.get("cli_tipo"))
    cliente["cli_estatus"] = convertir_estatus_cliente_para_ui(cliente.get("cli_estatus"))
    return cliente


def normalizar_lista_clientes_para_ui(clientes):
    """Normaliza una lista de clientes leídos de Supabase."""

    return [normalizar_cliente_para_ui(cliente) for cliente in (clientes or [])]


def construir_direccion_cliente(cliente):
    """
    Construye una dirección legible usando columnas separadas reales.
    """

    cliente = cliente or {}
    partes = []

    calle_numero = " ".join(
        str(cliente.get(campo, "") or "").strip()
        for campo in ("cli_calle", "cli_numero")
        if str(cliente.get(campo, "") or "").strip()
    )

    if calle_numero:
        partes.append(calle_numero)

    for campo in ("cli_colonia", "cli_municipio", "cli_estado", "cli_cp"):
        valor = str(cliente.get(campo, "") or "").strip()
        if valor:
            partes.append(valor)

    return ", ".join(partes)


def normalizar_cliente(datos):
    """
    Limpia y normaliza datos antes de enviar a Supabase.
    """

    normalizados = {}

    for campo in CAMPOS_CLIENTE:
        valor = datos.get(campo, "")
        normalizados[campo] = str(valor).strip() if valor is not None else ""

    normalizados["cli_rfc"] = normalizados.get("cli_rfc", "").upper()

    normalizados["cli_tipo"] = convertir_tipo_cliente_para_db(
        normalizados.get("cli_tipo")
    )

    normalizados["cli_estatus"] = convertir_estatus_cliente_para_db(
        normalizados.get("cli_estatus")
    )

    return normalizados


def _coincide_cliente(cliente, termino):
    """
    Filtro local sobre registros ya descifrados.

    Se usa porque los campos cifrados no se pueden buscar con ILIKE
    directamente en Supabase.
    """
    if not termino:
        return True

    termino = termino.lower().strip()
    campos_busqueda = [
        "cli_razonsocial",
        "cli_rfc",
        "cli_contacto",
        "cli_telefono",
        "cli_correo",
        "cli_municipio",
    ]

    return any(
        termino in str(cliente.get(campo, "") or "").lower()
        for campo in campos_busqueda
    )


@ttl_cache(ttl_seconds=120)
def buscar_clientes(termino="", limite=100):
    """
    Busca clientes por razón social, RFC, contacto, teléfono, correo o municipio.

    Nota técnica:
    Se consulta una ventana de registros y se filtra localmente después de
    descifrar, porque varios campos ya pueden estar cifrados.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_CLIENTES)
            .select("*")
            .limit(limite)
            .execute()
        )

        registros = normalizar_lista_clientes_para_ui(
            descifrar_lista(respuesta.data or [], CAMPOS_SENSIBLES_CLIENTE)
        )
        resultado = [
            cliente
            for cliente in registros
            if _coincide_cliente(cliente, termino)
        ]
        registrar_movimiento_seguro(
            modulo="CLIENTES",
            accion="BUSCAR",
            descripcion=f"Búsqueda administrativa de clientes: {termino or 'SIN FILTRO'}",
            registro_afectado=f"Resultados: {len(resultado)}",
        )
        return resultado

    except Exception:
        logger.exception("Error al buscar clientes.")
        return []


def crear_cliente(datos):
    """
    Crea un cliente nuevo en Supabase.
    """

    try:
        datos_guardar = normalizar_cliente(datos)

        if not datos_guardar.get("cli_razonsocial"):
            return False, "La razón social del cliente es obligatoria.", None

        datos_guardar = cifrar_diccionario(datos_guardar, CAMPOS_SENSIBLES_CLIENTE)

        respuesta = (
            supabase
            .table(TABLA_CLIENTES)
            .insert(datos_guardar)
            .execute()
        )

        if respuesta.data:
            clear_cache("services.clientes_service.buscar_clientes")
            cliente = normalizar_cliente_para_ui(
                descifrar_diccionario(respuesta.data[0], CAMPOS_SENSIBLES_CLIENTE)
            )
            registrar_movimiento_seguro(
                modulo="CLIENTES",
                accion="CREAR",
                descripcion="Alta administrativa de cliente",
                registro_afectado=cliente.get("id_cliente") or cliente.get("cli_razonsocial"),
            )
            return True, "Cliente registrado correctamente.", cliente

        return False, "No fue posible registrar el cliente.", None

    except Exception as error:
        logger.exception("Error al crear cliente.")
        return False, f"No fue posible registrar el cliente.\n\n{error}", None


def actualizar_cliente(id_cliente, datos):
    """
    Actualiza un cliente existente en Supabase.
    """

    try:
        if not id_cliente:
            return False, "Selecciona un cliente para modificar.", None

        datos_guardar = normalizar_cliente(datos)

        if not datos_guardar.get("cli_razonsocial"):
            return False, "La razón social del cliente es obligatoria.", None

        datos_guardar = cifrar_diccionario(datos_guardar, CAMPOS_SENSIBLES_CLIENTE)

        respuesta = (
            supabase
            .table(TABLA_CLIENTES)
            .update(datos_guardar)
            .eq("id_cliente", id_cliente)
            .execute()
        )

        if respuesta.data:
            clear_cache("services.clientes_service.buscar_clientes")
            cliente = normalizar_cliente_para_ui(
                descifrar_diccionario(respuesta.data[0], CAMPOS_SENSIBLES_CLIENTE)
            )
            registrar_movimiento_seguro(
                modulo="CLIENTES",
                accion="ACTUALIZAR",
                descripcion=f"Actualización administrativa de cliente ID: {id_cliente}",
                registro_afectado=id_cliente,
            )
            return True, "Cliente actualizado correctamente.", cliente

        return False, "No fue posible actualizar el cliente.", None

    except Exception as error:
        logger.exception("Error al actualizar cliente.")
        return False, f"No fue posible actualizar el cliente.\n\n{error}", None
