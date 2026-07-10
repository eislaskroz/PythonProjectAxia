import os
from dotenv import load_dotenv

from core.app_paths import candidate_env_files
from supabase import create_client

from core.logger import configurar_logger

logger = configurar_logger(__name__)

# =================================================
# CARGAR VARIABLES DE ENTORNO
# =================================================

ENV_CARGADO = None
for _env_path in candidate_env_files():
    if _env_path.is_file():
        load_dotenv(dotenv_path=_env_path, override=False)
        ENV_CARGADO = _env_path
        break

# Conserva compatibilidad con variables definidas por el sistema operativo.
if ENV_CARGADO is None:
    load_dotenv(override=False)

# =================================================
# VARIABLES SUPABASE
# =================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# =================================================
# CLIENTE SUPABASE
# =================================================

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error(
        "Faltan variables de entorno SUPABASE_URL o SUPABASE_KEY. "
        "Revisa el archivo .env."
    )
    raise RuntimeError(
        "Configuración incompleta de Supabase. "
        "Verifica SUPABASE_URL y SUPABASE_KEY en el archivo .env."
    )

try:
    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )
    logger.info("Cliente Supabase inicializado correctamente. Configuración: %s", ENV_CARGADO or "variables del sistema")
except Exception:
    logger.exception("No fue posible inicializar el cliente Supabase.")
    raise

# =================================================
# TABLAS DEL SISTEMA
# =================================================

TABLA_USUARIOS = "db_usuarios"
TABLA_CLIENTES = "db_clientes"
TABLA_ACOS = "db_acos"
TABLA_LEVANTAMIENTOS = "db_levantamientos"
TABLA_ORDENES_SERVICIO = "db_ordenes_servicio"
TABLA_BITACORAS = "db_bitacoras"
TABLA_BITACORA_LOGIN = "db_login"
TABLA_BITACORA_MOVIMIENTOS = "db_bitacora_mov"
TABLA_SUCURSALES = "db_clientes_sucursales"
TABLA_CONTACTOS_SUCURSAL = "db_clientes_sucursal_contactos"