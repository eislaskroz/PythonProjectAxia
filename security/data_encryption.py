"""Cifrado reversible y obligatorio para datos sensibles de AXIA."""
from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from core.app_paths import PROJECT_ROOT, is_frozen, user_data_dir
from core.environment import cargar_entorno, es_entorno_desarrollo, invalidar_cache_entorno
from core.logger import configurar_logger

logger = configurar_logger(__name__)
PREFIX = "enc::"


class EncryptionConfigurationError(RuntimeError):
    """La aplicación no puede proteger datos sensibles de forma segura."""


def _es_obligatorio() -> bool:
    cargar_entorno()
    return os.getenv("AXIA_REQUIRE_ENCRYPTION", "1").strip().lower() not in {"0", "false", "no"}


def _ruta_env_aprovisionamiento() -> Path:
    """Devuelve una ruta persistente fuera del ejecutable empaquetado."""
    if not is_frozen():
        return PROJECT_ROOT / ".env"
    return user_data_dir() / ".env"


def _proteger_archivo(ruta: Path) -> None:
    """Aplica permisos restrictivos cuando el sistema operativo lo permite."""
    try:
        os.chmod(ruta, 0o600)
    except OSError:
        logger.warning("No fue posible ajustar permisos del archivo %s", ruta)


def _guardar_variable_env(ruta: Path, nombre: str, valor: str) -> None:
    """Agrega o reemplaza una variable sin imprimir su contenido en logs."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    lineas: list[str] = []
    if ruta.exists():
        lineas = ruta.read_text(encoding="utf-8").splitlines()

    prefijo = f"{nombre}="
    nuevas: list[str] = []
    reemplazada = False
    for linea in lineas:
        if linea.strip().startswith(prefijo):
            nuevas.append(f"{nombre}={valor}")
            reemplazada = True
        else:
            nuevas.append(linea)
    if not reemplazada:
        if nuevas and nuevas[-1].strip():
            nuevas.append("")
        nuevas.append(f"{nombre}={valor}")

    ruta.write_text("\n".join(nuevas).rstrip() + "\n", encoding="utf-8")
    _proteger_archivo(ruta)


def aprovisionar_clave_desarrollo() -> Path | None:
    """Genera una llave persistente solo en desarrollo local.

    En ejecutables/producción nunca se genera automáticamente: todas las
    instalaciones que compartan una misma base deben recibir exactamente la
    misma llave mediante un canal administrado y seguro.
    """
    cargar_entorno()
    if os.getenv("AXIA_DATA_KEY", "").strip():
        return None
    if is_frozen() or not es_entorno_desarrollo():
        return None
    if os.getenv("AXIA_AUTO_PROVISION_DEV_KEY", "1").strip().lower() in {"0", "false", "no"}:
        return None

    ruta = _ruta_env_aprovisionamiento()
    clave = Fernet.generate_key().decode("utf-8")
    _guardar_variable_env(ruta, "AXIA_DATA_KEY", clave)
    if not os.getenv("AXIA_REQUIRE_ENCRYPTION"):
        _guardar_variable_env(ruta, "AXIA_REQUIRE_ENCRYPTION", "1")

    # Disponible inmediatamente en este proceso sin exponer la clave.
    os.environ["AXIA_DATA_KEY"] = clave
    os.environ.setdefault("AXIA_REQUIRE_ENCRYPTION", "1")
    invalidar_cache_entorno()
    cargar_entorno()
    _obtener_fernet.cache_clear()

    huella = hashlib.sha256(clave.encode("utf-8")).hexdigest()[:12]
    logger.warning(
        "Se generó una llave de cifrado para desarrollo en %s (huella %s). "
        "Respalda la llave; perderla impide descifrar datos existentes.",
        ruta,
        huella,
    )
    return ruta


@lru_cache(maxsize=1)
def _obtener_fernet() -> Fernet | None:
    cargar_entorno()
    key = os.getenv("AXIA_DATA_KEY", "").strip()
    if not key:
        aprovisionar_clave_desarrollo()
        key = os.getenv("AXIA_DATA_KEY", "").strip()

    if not key:
        if _es_obligatorio():
            raise EncryptionConfigurationError(
                "AXIA_DATA_KEY no está configurada. AXIA bloqueó el acceso para evitar "
                "leer o guardar datos sensibles sin protección."
            )
        logger.warning("Cifrado desactivado explícitamente para entorno no productivo.")
        return None
    try:
        return Fernet(key.encode("utf-8"))
    except Exception as exc:
        raise EncryptionConfigurationError(
            "AXIA_DATA_KEY no es una llave Fernet válida. No se modificó ningún dato."
        ) from exc


def validar_configuracion_cifrado() -> Path | None:
    """Carga la configuración, aprovisiona desarrollo y valida Fernet."""
    ruta_generada = aprovisionar_clave_desarrollo()
    _obtener_fernet()
    return ruta_generada


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
