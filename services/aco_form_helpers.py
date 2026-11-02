"""Autollenado del ACO a partir de los catálogos de cliente y sucursal.

Una sucursal/contacto puede no tener teléfono o correo propios aun cuando esos
campos sí existan en el registro maestro del cliente. Usamos el dato más
específico disponible sin alterar registros, ni inferir información inexistente.
"""


def _primero_con_datos(*valores):
    for valor in valores:
        texto = str(valor or "").strip()
        if texto:
            return texto
    return ""


def datos_contacto_aco(cliente=None, sucursal=None, contacto=None):
    """Prioridad: contacto de sucursal > sucursal > contacto del cliente.

    El nombre del contacto no se inventa. Si no hay contacto operativo,
    regresamos el principal registrado en db_clientes.
    """
    cliente = cliente or {}
    sucursal = sucursal or {}
    contacto = contacto or {}
    return {
        "nombre": _primero_con_datos(contacto.get("con_nombre"), cliente.get("cli_contacto")),
        "telefono": _primero_con_datos(
            contacto.get("con_telefono"), sucursal.get("suc_telefono"), cliente.get("cli_telefono")
        ),
        "correo": _primero_con_datos(
            contacto.get("con_correo"), sucursal.get("suc_correo"), cliente.get("cli_correo")
        ),
    }
