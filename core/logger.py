"""
=========================================================
LOGGER CENTRAL - AXIA
=========================================================

Este módulo centraliza los logs del sistema.

Objetivo:
- Evitar prints sueltos en producción.
- Guardar errores técnicos en archivos locales.
- Mantener una salida clara para soporte y depuración.
- No exponer detalles técnicos innecesarios al usuario final.

Los logs se guardan en:
    logs/axia.log
    logs/axia_errors.log
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "axia.log"
ERROR_LOG_FILE = LOG_DIR / "axia_errors.log"

FORMATO_LOG = (
    "%(asctime)s | %(levelname)s | %(name)s | "
    "%(filename)s:%(lineno)d | %(message)s"
)

FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"


# =====================================================
# FUNCIÓN: configurar_logger()
# =====================================================
def configurar_logger(nombre="axia"):
    """
    Crea y configura un logger reutilizable.

    PARÁMETROS:
        nombre:
            Nombre lógico del logger. Normalmente se usa __name__.

    RETORNA:
        logging.Logger:
            Logger listo para registrar eventos.
    """

    logger = logging.getLogger(nombre)

    # Evita duplicar handlers cuando el módulo se importa varias veces.
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt=FORMATO_LOG,
        datefmt=FORMATO_FECHA
    )

    # =================================================
    # LOG GENERAL
    # =================================================
    # Guarda eventos informativos, advertencias y errores.
    general_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    general_handler.setLevel(logging.INFO)
    general_handler.setFormatter(formatter)

    # =================================================
    # LOG DE ERRORES
    # =================================================
    # Guarda únicamente errores y excepciones críticas.
    error_handler = RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    logger.addHandler(general_handler)
    logger.addHandler(error_handler)

    return logger


# =====================================================
# LOGGER GLOBAL DEL SISTEMA
# =====================================================

logger = configurar_logger("axia")


def get_logger(nombre="axia"):
    """
    Retorna un logger configurado para el módulo solicitado.

    Este alias evita inconsistencias entre módulos que llaman
    get_logger() y módulos que llaman configurar_logger().
    """

    return configurar_logger(nombre)
