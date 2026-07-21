"""Configuración compartida de pruebas AXIA."""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("AXIA_ENV", "test")
os.environ.setdefault("AXIA_AUTO_PROVISION_DEV_KEY", "0")
