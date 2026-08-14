import re
"""
=========================================================
SERVICIO DE ACOS - AXIA
=========================================================

Este archivo pertenece a la capa de servicios de AXIA.

Responsabilidad principal:
- Contener lógica de negocio.
- Consultar y modificar datos en Supabase.
- Devolver resultados limpios a las vistas.

Regla de arquitectura:
Las vistas en `views/` no deben hablar directamente con Supabase.
Deben llamar funciones de esta capa `services/`.
"""

from datetime import datetime

from core.logger import configurar_logger
from core.error_reporting import register_error
from core.cache import ttl_cache, clear_cache

logger = configurar_logger(__name__)
from services.movimientos_service import registrar_movimiento_seguro
from services.search_service import buscar_parcial_supabase

# =====================================================
# NORMALIZACIÓN DE FECHAS
# =====================================================
def normalizar_fecha_supabase(valor):
    """
    Convierte una fecha capturada por el usuario al formato ISO
    que PostgreSQL/Supabase acepta de forma segura: YYYY-MM-DD.

    Formatos aceptados:
    - 28082026
    - 28/08/2026
    - 28-08-2026
    - 2026-08-28

    Si el campo viene vacío, retorna None para guardar NULL.
    Si el formato no es válido, lanza ValueError para evitar
    enviar una fecha incorrecta a Supabase.
    """

    if valor is None:
        return None

    valor = str(valor).strip()

    if not valor:
        return None

    formatos_permitidos = [
        "%d%m%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
    ]

    for formato in formatos_permitidos:
        try:
            return datetime.strptime(valor, formato).date().isoformat()
        except ValueError:
            continue

    raise ValueError(
        f"Formato de fecha inválido: {valor}. "
        "Usa DD/MM/AAAA o AAAA-MM-DD."
    )


def normalizar_fechas_aco(datos_aco):
    """
    Normaliza todas las fechas conocidas del diccionario de ACO
    antes de insertar o actualizar en Supabase.

    Esta función trabaja sobre una copia para no modificar el
    diccionario original recibido desde la vista.
    """

    datos_normalizados = dict(datos_aco or {})

    campos_fecha = [
        "aco_fecha_inicio",
        "aco_fecha_compromiso",
        "aco_fecha_creacion",
        "fecha_inicio",
        "fecha_compromiso",
        "fecha_creacion",
        "fecha_registro",
    ]

    for campo in campos_fecha:
        if campo in datos_normalizados:
            datos_normalizados[campo] = normalizar_fecha_supabase(
                datos_normalizados.get(campo)
            )

    return datos_normalizados


# =====================================================
# IMPORTACIÓN DE SUPABASE
# =====================================================

from supabase_config import supabase, TABLA_ACOS


# Columnas explícitas de db_acos usadas por la aplicación.
# Mantener esta lista sincronizada con migrations/validar_esquema_beta_095.sql.
COLUMNAS_ACOS = ",".join([
    "id_aco",
    "aco_numero",
    "aco_cliente",
    "aco_descripcion",
    "aco_observaciones",
    "aco_responsable",
    "aco_creado_por",
    "aco_fecha_inicio",
    "aco_fecha_compromiso",
    "aco_estatus",
    "id_cliente",
    "id_sucursal",
    "id_contacto",
    "fecha_registro",
])


def normalizar_numero_aco(valor):
    """Devuelve un folio ACO con un solo prefijo ``ACO-``.

    Protege la interfaz y las consultas contra datos históricos como
    ``ACO-ACO-AGO-2026-001`` sin alterar el resto del folio.
    """
    texto = str(valor or "").strip().upper()
    if not texto:
        return ""
    return re.sub(r"^(?:ACO-)+", "ACO-", texto)


def _normalizar_registro_aco(registro):
    if not registro:
        return registro
    limpio = dict(registro)
    limpio["aco_numero"] = normalizar_numero_aco(limpio.get("aco_numero"))
    return limpio


class AcoServiceError(RuntimeError):
    """Error de comunicación o consulta del servicio de ACOs."""



def enriquecer_aco_con_sucursal_contacto(aco):
    """Completa un ACO con datos operativos de sucursal/contacto si tiene IDs ligados."""
    if not aco:
        return aco
    aco = dict(aco)
    try:
        from services.sucursales_service import (
            obtener_sucursal_por_id,
            obtener_contacto_por_id,
            construir_domicilio_sucursal,
        )

        sucursal = obtener_sucursal_por_id(aco.get("id_sucursal"))
        contacto = obtener_contacto_por_id(aco.get("id_contacto"))

        if sucursal:
            aco.setdefault("aco_sucursal", sucursal.get("suc_nombre", ""))
            aco.setdefault("aco_direccion", construir_domicilio_sucursal(sucursal))
            aco.setdefault("aco_telefono", sucursal.get("suc_telefono", ""))
            aco.setdefault("aco_correo", sucursal.get("suc_correo", ""))

        if contacto:
            # El contacto operativo tiene prioridad sobre el contacto fiscal del cliente.
            aco["aco_contacto"] = contacto.get("con_nombre", "") or aco.get("aco_contacto", "")
            aco["aco_telefono"] = contacto.get("con_telefono", "") or aco.get("aco_telefono", "")
            aco["aco_correo"] = contacto.get("con_correo", "") or aco.get("aco_correo", "")

    except Exception:
        logger.exception("No fue posible enriquecer el ACO con sucursal/contacto.")
    return aco


# =====================================================
# FUNCIÓN: buscar_aco_por_numero()
# =====================================================
@ttl_cache(ttl_seconds=90)
def buscar_aco_por_numero(aco_numero):
    """
    Busca un ACO por su número interno.

    RETORNA:
        dict | None:
            Diccionario con la información del ACO
            si existe, o None si no se encuentra.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_ACOS)
            .select(COLUMNAS_ACOS)
            .eq("aco_numero", normalizar_numero_aco(aco_numero))
            .execute()
        )

        if respuesta.data:
            registrar_movimiento_seguro(
                modulo="ACOS",
                accion="BUSCAR",
                descripcion=f"Consulta de ACO por número: {aco_numero}",
                registro_afectado=aco_numero,
            )
            return enriquecer_aco_con_sucursal_contacto(_normalizar_registro_aco(respuesta.data[0]))

        registrar_movimiento_seguro(
            modulo="ACOS",
            accion="BUSCAR_SIN_RESULTADO",
            descripcion=f"Búsqueda de ACO sin resultado: {aco_numero}",
            registro_afectado=aco_numero,
        )
        return None

    except Exception as error:
        logger.exception("Error al buscar ACO %s.", aco_numero)
        raise AcoServiceError(
            "No fue posible consultar el ACO en Supabase. "
            "Revisa la conexión y la estructura de db_acos."
        ) from error


def buscar_aco_por_id(id_aco):
    """Busca un ACO por su ID principal.

    Se usa en flujos automáticos para reconstruir la relación cuando el
    levantamiento ya conserva ``id_aco`` pero no el folio visible.
    """
    if id_aco in (None, ""):
        return None
    try:
        respuesta = (
            supabase
            .table(TABLA_ACOS)
            .select(COLUMNAS_ACOS)
            .eq("id_aco", id_aco)
            .limit(1)
            .execute()
        )
        if respuesta.data:
            return enriquecer_aco_con_sucursal_contacto(
                _normalizar_registro_aco(respuesta.data[0])
            )
        return None
    except Exception as error:
        logger.exception("Error al buscar ACO por ID %s.", id_aco)
        raise AcoServiceError("No fue posible consultar el ACO por ID en Supabase.") from error



def buscar_aco_generado_por_levantamiento(folio_levantamiento):
    """Localiza un ACO automático por el folio LEV guardado en observaciones.

    Es una defensa de idempotencia: si Supabase alcanzó a crear el ACO pero una
    falla posterior impidió enlazar el levantamiento, un reintento reutiliza el
    mismo ACO en lugar de crear otro.
    """
    folio = str(folio_levantamiento or "").strip().upper()
    if not folio:
        return None
    patron = f"%Generado automáticamente al autorizar {folio}.%"
    try:
        respuesta = (
            supabase
            .table(TABLA_ACOS)
            .select(COLUMNAS_ACOS)
            .ilike("aco_observaciones", patron)
            .order("fecha_registro", desc=True)
            .limit(1)
            .execute()
        )
        if respuesta.data:
            return enriquecer_aco_con_sucursal_contacto(
                _normalizar_registro_aco(respuesta.data[0])
            )
        return None
    except Exception:
        logger.exception("No fue posible comprobar ACO automático previo para %s.", folio)
        return None

def crear_aco_desde_levantamiento(levantamiento, usuario_activo=None):
    """Crea el ACO operativo que nace al autorizar un levantamiento.

    Momento de negocio:
        El ACO se crea *justo al convertir* el levantamiento autorizado en
        Orden de Trabajo. Antes de ese momento el levantamiento puede existir
        sin ACO, porque todavía no representa un servicio autorizado.

    La función copia únicamente datos ya conocidos del levantamiento y deja a
    Supabase la asignación de ``aco_numero`` mediante su trigger vigente.
    """
    lev = dict(levantamiento or {})
    cliente = str(lev.get("lev_cliente") or "").strip()
    if not cliente:
        raise ValueError("No se puede generar el ACO automático sin cliente.")

    usuario = str(
        (usuario_activo or {}).get("usu_nickname")
        or (usuario_activo or {}).get("usuario")
        or (usuario_activo or {}).get("usu_usuario")
        or "AXIA"
    ).strip()
    responsable = str(
        lev.get("lev_supervisor")
        or lev.get("lev_tecnico")
        or usuario
    ).strip()
    observacion_lev = str(lev.get("lev_observaciones") or "").strip()
    folio_lev = str(lev.get("lev_folio") or "").strip().upper()
    nota_origen = f"Generado automáticamente al autorizar {folio_lev}." if folio_lev else "Generado automáticamente desde levantamiento autorizado."
    observaciones = nota_origen if not observacion_lev else f"{nota_origen}\n{observacion_lev}"

    tipo_levantamiento = str(
        lev.get("lev_tipo_nombre")
        or lev.get("lev_tipo_levantamiento")
        or lev.get("lev_tipo")
        or "Servicio autorizado"
    ).strip()
    descripcion_aco = (
        f"Servicio autorizado desde {folio_lev} - {tipo_levantamiento}"
        if folio_lev
        else f"Servicio autorizado desde levantamiento - {tipo_levantamiento}"
    )

    payload = {
        # aco_numero NO se envía: Supabase lo genera automáticamente.
        "id_cliente": lev.get("id_cliente"),
        "id_sucursal": lev.get("id_sucursal"),
        "id_contacto": lev.get("id_contacto"),
        "aco_cliente": cliente,
        # db_acos.aco_descripcion es NOT NULL. Aunque el formulario manual ya
        # no muestra este campo, el contrato de base de datos sigue exigiéndolo.
        "aco_descripcion": descripcion_aco,
        "aco_observaciones": observaciones,
        "aco_responsable": responsable,
        "aco_creado_por": usuario,
        "aco_fecha_inicio": lev.get("lev_fecha_programada") or lev.get("lev_fecha_realizacion") or None,
        "aco_fecha_compromiso": None,
        "aco_estatus": 1,
    }
    payload = {k: v for k, v in payload.items() if v not in (None, "")}
    # En el flujo automático necesitamos distinguir entre dos casos:
    # 1) el INSERT sí ocurrió pero PostgREST no devolvió representación; y
    # 2) el INSERT realmente falló.  Supabase puede devolver una lista vacía
    # aun cuando el trigger haya creado correctamente el folio, por ejemplo
    # cuando la política SELECT no permite retornar inmediatamente la fila.
    resultado = crear_aco(payload, propagar_error=True)
    if resultado:
        return resultado[0]

    # Confirmación posterior por la marca de origen que acabamos de guardar.
    # Esto evita reportar un falso negativo y, además, impide crear un ACO
    # duplicado si el usuario vuelve a pulsar Convertir.
    recuperado = buscar_aco_generado_por_levantamiento(folio_lev) if folio_lev else None
    if recuperado:
        return recuperado

    raise RuntimeError(
        "Supabase procesó la solicitud pero no fue posible recuperar el ACO recién creado. "
        "Revisa las políticas SELECT/INSERT de db_acos."
    )


# =====================================================
# FUNCIÓN: obtener_acos()
# =====================================================
@ttl_cache(ttl_seconds=60)
def obtener_acos(page=1, page_size=100):
    """
    Consulta todos los ACOs registrados.

    RETORNA:
        list:
            Lista de ACOs ordenados del más reciente al más antiguo.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_ACOS)
            .select(COLUMNAS_ACOS)
            .order("fecha_registro", desc=True)
            .range(*page_range(page, page_size))
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="ACOS",
            accion="CONSULTAR",
            descripcion="Consulta general de ACOs",
            registro_afectado=f"Total: {len(respuesta.data or [])}",
        )
        return [_normalizar_registro_aco(r) for r in (respuesta.data or [])]

    except Exception as error:
        logger.exception("Error al consultar ACOs.")
        return []


# =====================================================
# FUNCIÓN: crear_aco()
# =====================================================
def crear_aco(datos_aco, propagar_error=False):
    """Crea un nuevo ACO en Supabase.

    ``propagar_error`` se usa en operaciones transaccionales (LEV -> ACO -> OT)
    para no ocultar el detalle real de PostgREST detrás de un ``None``. La
    captura manual conserva el comportamiento histórico por compatibilidad.
    """

    try:
        # PostgreSQL requiere fechas en formato seguro ISO: YYYY-MM-DD.
        # La vista puede recibir DD/MM/AAAA, DD-MM-AAAA o DDMMAAAA,
        # por eso normalizamos aquí antes del insert.
        datos_aco = normalizar_fechas_aco(datos_aco)

        # Compatibilidad con el esquema vigente: aco_descripcion sigue siendo
        # NOT NULL en Supabase aunque el campo ya no se capture en pantalla.
        # En creación manual usamos cadena vacía; en creación automática se
        # genera una descripción de trazabilidad antes de llegar aquí.
        if datos_aco.get("aco_descripcion") is None:
            datos_aco["aco_descripcion"] = ""

        # Desde la migración 20260813 el folio ACO lo asigna Supabase mediante
        # trigger. Un valor vacío impediría que el trigger distinga claramente
        # entre un folio manual y uno automático, por eso nunca enviamos vacío.
        if not str(datos_aco.get("aco_numero", "") or "").strip():
            datos_aco.pop("aco_numero", None)

        respuesta = (
            supabase
            .table(TABLA_ACOS)
            .insert(datos_aco)
            .execute()
        )

        clear_cache("services.acos_service")

        registrar_movimiento_seguro(
            modulo="ACOS",
            accion="CREAR",
            descripcion="Creación de ACO",
            registro_afectado=datos_aco.get("aco_numero") or datos_aco.get("aco_folio") or respuesta.data,
        )
        return [_normalizar_registro_aco(r) for r in (respuesta.data or [])]

    except Exception as error:
        register_error(error, "Registrar ACO")
        logger.exception("Error al crear ACO.")
        if propagar_error:
            detalle = str(error)
            if "id_aco" in detalle and "23502" in detalle:
                raise RuntimeError(
                    "Supabase rechazó la creación del ACO porque db_acos.id_aco no tiene "
                    "autogeneración configurada. Ejecuta la migración "
                    "migrations/20260814_fix_db_acos_id_aco_sequence.sql. "
                    f"Detalle técnico: {error}"
                ) from error
            raise RuntimeError(f"Supabase rechazó la creación del ACO. Detalle técnico: {error}") from error
        return None


# =====================================================
# FUNCIÓN: actualizar_aco()
# =====================================================
def actualizar_aco(id_aco, datos_aco):
    """
    Actualiza la información de un ACO existente.

    PARÁMETROS:
        id_aco:
            Identificador principal del ACO.

        datos_aco:
            Diccionario con los campos a actualizar.

    RETORNA:
        list | None:
            Respuesta de Supabase si la actualización fue exitosa.
    """

    try:
        # También normalizamos fechas en actualizaciones para mantener
        # consistencia si después editamos fechas de un ACO existente.
        datos_aco = normalizar_fechas_aco(datos_aco)

        respuesta = (
            supabase
            .table(TABLA_ACOS)
            .update(datos_aco)
            .eq("id_aco", id_aco)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="ACOS",
            accion="ACTUALIZAR",
            descripcion=f"Actualización de ACO ID: {id_aco}",
            registro_afectado=id_aco,
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al actualizar ACO.")
        return None


# =====================================================
# FUNCIÓN: validar_aco_existente()
# =====================================================
def validar_aco_existente(aco_numero):
    """
    Valida si un ACO existe dentro de la base de datos.

    RETORNA:
        bool:
            True si existe.
            False si no existe.
    """

    return buscar_aco_por_numero(aco_numero) is not None

# Búsqueda parcial unificada
def buscar_acos(termino, limite=100):
    termino = normalizar_numero_aco(termino) if str(termino or "").strip().upper().startswith("ACO-") else termino
    resultados = buscar_parcial_supabase(
        supabase=supabase, tabla=TABLA_ACOS, columnas=COLUMNAS_ACOS, termino=termino,
        campos=('aco_numero', 'aco_cliente', 'aco_responsable', 'aco_sucursal', 'aco_estatus'), id_campos=('id_aco', 'aco_numero'), orden='fecha_registro', limite=limite,
    )
    resultados = [_normalizar_registro_aco(r) for r in resultados]
    registrar_movimiento_seguro(
        modulo='ACOS', accion="BUSCAR",
        descripcion=f"Búsqueda parcial: {str(termino).strip().upper()}",
        registro_afectado=f"Coincidencias: {len(resultados)}",
    )
    return resultados
