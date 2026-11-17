def _primero_con_datos(*valores):
    for valor in valores:
        texto = str(valor or "").strip()
        if texto:
            return texto
    return ""


def datos_contacto_aco(cliente=None, sucursal=None, contacto=None):
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