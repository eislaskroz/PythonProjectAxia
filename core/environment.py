from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from core.app_paths import candidate_env_files
from core.logger import configurar_logger

logger = configurar_logger(__name__)


@lru_cache(maxsize=1)
def cargar_entorno() -> Path | None:
    for ruta in candidate_env_files():
        if ruta.is_file():
            load_dotenv(dotenv_path=ruta, override=False)
            logger.info("Configuración de entorno cargada desde: %s", ruta)
            return ruta

    load_dotenv(override=False)
    logger.info("No se encontró archivo .env; se usarán variables del sistema.")
    return None


def es_entorno_desarrollo() -> bool:
    valor = os.getenv("AXIA_ENV", "development").strip().lower()
    return valor in {"dev", "development", "local", "test", "testing"}


def invalidar_cache_entorno() -> None:
    cargar_entorno.cache_clear()