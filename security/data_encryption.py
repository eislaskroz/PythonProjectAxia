"""Cifrado reversible y obligatorio para datos sensibles de AXIA."""
from __future__ import annotations

import os
from functools import lru_cache
from cryptography.fernet import Fernet, InvalidToken

from core.logger import configurar_logger

logger = configurar_logger(__name__)
PREFIX = "enc::"


class EncryptionConfigurationError(RuntimeError):
    """La aplicación no puede proteger datos sensibles de forma segura."""


def _es_obligatorio() -> bool:
    return os.getenv("AXIA_REQUIRE_ENCRYPTION", "1").strip().lower() not in {"0", "false", "no"}


@lru_cache(maxsize=1)
def _obtener_fernet() -> Fernet | None:
    key = os.getenv("AXIA_DATA_KEY", "").strip()
    if not key:
        if _es_obligatorio():
            raise EncryptionConfigurationError(
                "AXIA_DATA_KEY no está configurada. AXIA bloqueó el guardado de datos sensibles."
            )
        logger.warning("Cifrado desactivado explícitamente para entorno no productivo.")
        return None
    try:
        return Fernet(key.encode("utf-8"))
    except Exception as exc:
        raise EncryptionConfigurationError("AXIA_DATA_KEY no es una llave Fernet válida.") from exc


def validar_configuracion_cifrado() -> None:
    """Falla temprano cuando el cifrado obligatorio no está disponible."""
    _obtener_fernet()


def esta_cifrado(valor):
    return isinstance(valor, str) and valor.startswith(PREFIX)


def cifrar_valor(valor):
    if valor is None:
        return valor
    valor = str(valor)
    if not valor or esta_cifrado(valor):
        return valor
    fernet = _obtener_fernet()
    if fernet is None:
        return valor
    return f"{PREFIX}{fernet.encrypt(valor.encode('utf-8')).decode('utf-8')}"


def descifrar_valor(valor):
    if not esta_cifrado(valor):
        return valor
    fernet = _obtener_fernet()
    if fernet is None:
        return valor
    token = valor[len(PREFIX):]
    try:
        return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        logger.error("Dato cifrado ilegible: llave incorrecta o contenido corrupto.")
        raise EncryptionConfigurationError(
            "No fue posible descifrar información sensible. Verifica AXIA_DATA_KEY."
        ) from exc


def cifrar_diccionario(datos, campos_sensibles):
    resultado = dict(datos or {})
    for campo in campos_sensibles:
        if campo in resultado:
            resultado[campo] = cifrar_valor(resultado.get(campo))
    return resultado


def descifrar_diccionario(datos, campos_sensibles):
    resultado = dict(datos or {})
    for campo in campos_sensibles:
        if campo in resultado:
            resultado[campo] = descifrar_valor(resultado.get(campo))
    return resultado


def descifrar_lista(registros, campos_sensibles):
    return [descifrar_diccionario(r, campos_sensibles) for r in (registros or [])]
