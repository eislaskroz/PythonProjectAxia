"""
=========================================================
MÓDULO: security/data_encryption.py
DESCRIPCIÓN:
Cifrado reversible para datos sensibles de AXIA.

IMPORTANTE:
- Las contraseñas NO usan este módulo; siguen usando bcrypt.
- Este módulo es para datos que el sistema necesita volver a mostrar:
  teléfonos, correos, RFC, CURP, IMSS, INE, direcciones, notas, etc.
- Requiere la variable de entorno AXIA_DATA_KEY.

Cómo generar una llave:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Luego agregar en .env:
    AXIA_DATA_KEY=pega_aqui_la_llave_generada
=========================================================
"""

import os
from cryptography.fernet import Fernet, InvalidToken

from core.logger import configurar_logger

logger = configurar_logger(__name__)

PREFIX = "enc::"


def _obtener_fernet():
    """
    Retorna una instancia Fernet usando AXIA_DATA_KEY.

    Si no existe llave, se retorna None para NO romper operación.
    En ese caso el dato se guarda en claro y se registra advertencia.
    """
    key = os.getenv("AXIA_DATA_KEY", "").strip()

    if not key:
        logger.warning(
            "AXIA_DATA_KEY no está configurada. "
            "Los campos sensibles se conservarán sin cifrar hasta configurar la llave."
        )
        return None

    try:
        return Fernet(key.encode())
    except Exception:
        logger.exception("AXIA_DATA_KEY no es válida. Revisa el formato Fernet.")
        return None


def esta_cifrado(valor):
    """
    Indica si un texto ya tiene el prefijo de cifrado de AXIA.
    """
    return isinstance(valor, str) and valor.startswith(PREFIX)


def cifrar_valor(valor):
    """
    Cifra un valor de texto.

    No cifra:
    - None
    - cadenas vacías
    - valores que ya están cifrados
    - valores cuando AXIA_DATA_KEY no está configurada
    """
    if valor is None:
        return valor

    valor = str(valor)

    if not valor or esta_cifrado(valor):
        return valor

    fernet = _obtener_fernet()
    if not fernet:
        return valor

    token = fernet.encrypt(valor.encode("utf-8")).decode("utf-8")
    return f"{PREFIX}{token}"


def descifrar_valor(valor):
    """
    Descifra un valor si fue cifrado por AXIA.

    Si el dato no está cifrado o hay error de llave, devuelve el valor original
    para mantener compatibilidad con registros antiguos.
    """
    if not esta_cifrado(valor):
        return valor

    fernet = _obtener_fernet()
    if not fernet:
        return valor

    token = valor[len(PREFIX):]

    try:
        return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.exception("No fue posible descifrar un valor: llave incorrecta o dato corrupto.")
        return valor
    except Exception:
        logger.exception("Error inesperado al descifrar valor.")
        return valor


def cifrar_diccionario(datos, campos_sensibles):
    """
    Cifra solamente los campos indicados dentro de un diccionario.
    """
    resultado = dict(datos or {})

    for campo in campos_sensibles:
        if campo in resultado:
            resultado[campo] = cifrar_valor(resultado.get(campo))

    return resultado


def descifrar_diccionario(datos, campos_sensibles):
    """
    Descifra solamente los campos indicados dentro de un diccionario.
    """
    resultado = dict(datos or {})

    for campo in campos_sensibles:
        if campo in resultado:
            resultado[campo] = descifrar_valor(resultado.get(campo))

    return resultado


def descifrar_lista(registros, campos_sensibles):
    """
    Descifra una lista de diccionarios.
    """
    return [
        descifrar_diccionario(registro, campos_sensibles)
        for registro in (registros or [])
    ]
