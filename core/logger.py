import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from core.app_paths import logs_dir


# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = logs_dir()

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
    logger = logging.getLogger(nombre)

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
    return configurar_logger(nombre)