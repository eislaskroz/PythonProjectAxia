"""Comprobaciones previas a staging/producción sin modificar datos."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.deployment import load_deployment_config
from core.environment import cargar_entorno
from security.data_encryption import validar_configuracion_cifrado

cargar_entorno()


def main() -> int:
    errors: list[str] = []
    try:
        config = load_deployment_config()
        print(f"Ambiente: {config.environment}")
        print(f"Supabase project ref: {config.project_ref}")
    except Exception as exc:
        errors.append(str(exc))
        config = None
    try:
        validar_configuracion_cifrado()
        print("Cifrado: OK")
    except Exception as exc:
        errors.append(f"Cifrado: {exc}")
    if os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        errors.append("SUPABASE_SERVICE_ROLE_KEY no puede existir en el cliente.")
    if os.getenv("AXIA_AUTO_PROVISION_DEV_KEY", "0") == "1" and config and config.environment != "development":
        errors.append("AXIA_AUTO_PROVISION_DEV_KEY debe estar desactivado fuera de desarrollo.")
    try:
        from supabase_config import supabase, TABLA_USUARIOS
        result = supabase.table(TABLA_USUARIOS).select("id_usuario,usu_nickname,usu_tipo").limit(1).execute()
        print(f"Conectividad Supabase: OK ({len(result.data or [])} fila de prueba)")
    except Exception as exc:
        errors.append(f"Conectividad Supabase: {exc}")
    if errors:
        print("\nPREFLIGHT: FALLÓ")
        for error in errors:
            print(f"- {error}")
        return 1
    print("\nPREFLIGHT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
