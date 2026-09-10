"""Máscaras visuales para cifras sin contaminar el valor persistido.

El valor que ve el usuario puede incluir moneda y separadores de miles, pero
``StringVar.get()`` siempre devuelve la representación numérica limpia. Así los
servicios, validaciones y payloads existentes continúan trabajando con números.
"""

from decimal import Decimal, InvalidOperation
import re
from types import MethodType


MONEY = "money"
NUMBER = "number"
INTEGER = "integer"


def limpiar_numero(value, integer=False):
    texto = str(value if value is not None else "").strip()
    if not texto:
        return ""
    texto = texto.replace("$", "").replace("%", "").replace(" ", "")
    texto = texto.replace(",", "")
    texto = re.sub(r"[^0-9.\-]", "", texto)
    if texto in {"", "-", ".", "-."}:
        return ""
    try:
        numero = Decimal(texto)
    except InvalidOperation:
        return ""
    if integer:
        return str(int(numero))
    resultado = format(numero, "f")
    if "." in resultado:
        resultado = resultado.rstrip("0").rstrip(".")
    return resultado


def formatear_numero(value, kind=NUMBER):
    limpio = limpiar_numero(value, integer=(kind == INTEGER))
    if not limpio:
        return ""
    numero = Decimal(limpio)
    if kind == INTEGER:
        return f"{numero:,.0f}"
    prefijo = "$" if kind == MONEY else ""
    return f"{prefijo}{numero:,.2f}"


def aplicar_mascara_numerica(entry, variable, kind=NUMBER):
    """Vincula una máscara; la UI se formatea y ``get`` entrega el dato limpio."""
    if getattr(variable, "_axia_numeric_mask", False):
        return entry

    get_tk = variable.get
    set_tk = variable.set
    actualizando = False

    def get_limpio(self):
        return limpiar_numero(get_tk(), integer=(kind == INTEGER))

    def set_formateado(self, value):
        nonlocal actualizando
        if actualizando:
            return set_tk(value)
        actualizando = True
        try:
            return set_tk(formatear_numero(value, kind) if str(value or "").strip() else "")
        finally:
            actualizando = False

    variable.get = MethodType(get_limpio, variable)
    variable.set = MethodType(set_formateado, variable)
    variable._axia_numeric_mask = True
    variable._axia_numeric_kind = kind

    def al_entrar(_event=None):
        set_tk(get_limpio(variable))

    def al_salir(_event=None):
        set_tk(formatear_numero(get_tk(), kind))

    entry.bind("<FocusIn>", al_entrar, add="+")
    entry.bind("<FocusOut>", al_salir, add="+")
    al_salir()
    return entry


def tipo_mascara_por_etiqueta(etiqueta):
    """Clasificación conservadora: sólo campos inequívocamente numéricos."""
    texto = str(etiqueta or "").casefold()
    if any(x in texto for x in ("precio", "costo", "importe", "subtotal", "total $", "monto")):
        return MONEY
    if any(x in texto for x in ("cantidad", "cuánt", "dias", "días", "personas", "horas", "metros", "porcentaje", "%")):
        return NUMBER
    return None
