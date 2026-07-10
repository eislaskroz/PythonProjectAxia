"""
=========================================================
SERVICIO: aco_context_service.py
=========================================================

Normaliza la información de un ACO para que las vistas puedan
usar siempre las mismas llaves internas, aunque en la base de datos
los campos crezcan o cambien ligeramente de nombre.

Este servicio evita repetir lógica en levantamientos, órdenes de
servicio y bitácoras.
"""


def _primer_valor(datos, posibles_llaves):
    """
    Devuelve el primer valor encontrado dentro de un diccionario.

    PARÁMETROS:
        datos:
            Diccionario original del ACO.
        posibles_llaves:
            Lista de nombres de campo que podrían contener el dato.

    RETORNA:
        str:
            Valor encontrado o cadena vacía.
    """

    if not datos:
        return ""

    for llave in posibles_llaves:
        valor = datos.get(llave)
        if valor not in (None, ""):
            return str(valor)

    return ""


def normalizar_datos_aco(aco):
    """
    Convierte el diccionario del ACO en una estructura estándar.

    Esto permite que las vistas consuman siempre:
    - id_aco
    - aco_numero
    - cliente
    - contacto
    - telefono
    - correo
    - direccion
    - ubicacion
    - responsable

    Si hoy la tabla db_acos no tiene todos esos campos, simplemente
    regresará valores vacíos. Cuando se agreguen en Supabase, el
    formulario los tomará automáticamente si coinciden con alguna de
    las llaves contempladas.
    """

    aco = aco or {}

    return {
        "id_aco": aco.get("id_aco"),
        "id_cliente": aco.get("id_cliente"),
        "id_sucursal": aco.get("id_sucursal"),
        "id_contacto": aco.get("id_contacto"),
        "aco_numero": _primer_valor(aco, [
            "aco_numero",
            "numero_aco",
            "folio_aco"
        ]),
        "cliente": _primer_valor(aco, [
            "aco_cliente",
            "cliente",
            "nombre_cliente",
            "cli_razonsocial",
            "cli_nombre"
        ]),
        "contacto": _primer_valor(aco, [
            "aco_contacto",
            "contacto",
            "cliente_contacto",
            "contacto_nombre"
        ]),
        "telefono": _primer_valor(aco, [
            "aco_telefono",
            "telefono",
            "cliente_telefono",
            "contacto_telefono"
        ]),
        "correo": _primer_valor(aco, [
            "aco_correo",
            "correo",
            "email",
            "cliente_correo",
            "contacto_correo"
        ]),
        "direccion": _primer_valor(aco, [
            "aco_direccion",
            "direccion",
            "cliente_direccion",
            "direccion_servicio",
            "cli_direccion",
            "cli_calle"
        ]),
        "ubicacion": _primer_valor(aco, [
            "aco_ubicacion",
            "ubicacion",
            "referencia",
            "ubicacion_referencia"
        ]),
        "responsable": _primer_valor(aco, [
            "aco_responsable",
            "responsable",
            "tecnico_responsable"
        ]),
        "tipo_servicio": _primer_valor(aco, [
            "aco_tipo_servicio",
            "tipo_servicio",
            "servicio",
            "tipo"
        ]),
        "fecha_creacion": _primer_valor(aco, [
            "aco_fecha_creacion",
            "fecha_creacion",
            "created_at",
            "fecha_registro"
        ]),
        "sucursal": _primer_valor(aco, [
            "aco_sucursal",
            "sucursal",
            "nombre_sucursal",
            "cli_sucursal"
        ]),
        "jefe_operacion": _primer_valor(aco, [
            "aco_jefe_operacion",
            "jefe_operacion",
            "jefe_de_operacion",
            "responsable_operacion"
        ]),
        "supervisor": _primer_valor(aco, [
            "aco_supervisor",
            "supervisor",
            "supervisor_axia"
        ]),
        "esi": _primer_valor(aco, [
            "aco_esi",
            "esi",
            "especialista_esi"
        ])
    }