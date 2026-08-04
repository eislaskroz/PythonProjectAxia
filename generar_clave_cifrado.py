"""Genera o instala de forma segura la llave Fernet de AXIA.

Uso recomendado en desarrollo:
    python generar_clave_cifrado.py

El script crea o actualiza `.env` sin mostrar la llave en pantalla. Use
`--mostrar` únicamente cuando deba copiarla a un gestor de secretos.
"""
from __future__ import annotations

from core.logger import configurar_logger

logger = configurar_logger(__name__)

import argparse
import os
from pathlib import Path

from cryptography.fernet import Fernet


def actualizar_env(ruta: Path, clave: str) -> None:
    lineas = ruta.read_text(encoding="utf-8").splitlines() if ruta.exists() else []
    salida: list[str] = []
    encontrada = False
    for linea in lineas:
        if linea.strip().startswith("AXIA_DATA_KEY="):
            salida.append(f"AXIA_DATA_KEY={clave}")
            encontrada = True
        else:
            salida.append(linea)
    if not encontrada:
        if salida and salida[-1].strip():
            salida.append("")
        salida.append(f"AXIA_DATA_KEY={clave}")
    if not any(l.strip().startswith("AXIA_REQUIRE_ENCRYPTION=") for l in salida):
        salida.append("AXIA_REQUIRE_ENCRYPTION=1")
    ruta.write_text("\n".join(salida).rstrip() + "\n", encoding="utf-8")
    try:
        os.chmod(ruta, 0o600)
    except OSError:
        logger.debug("Excepción recuperable controlada.", exc_info=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mostrar", action="store_true", help="Muestra la llave para copiarla a un gestor seguro.")
    parser.add_argument("--forzar", action="store_true", help="Reemplaza una llave ya configurada (puede volver ilegibles datos existentes).")
    args = parser.parse_args()

    ruta = Path(__file__).resolve().parent / ".env"
    if ruta.exists() and "AXIA_DATA_KEY=" in ruta.read_text(encoding="utf-8") and not args.forzar:
        print(f"Ya existe AXIA_DATA_KEY en {ruta}. No se realizó ningún cambio.")
        return

    clave = Fernet.generate_key().decode("utf-8")
    actualizar_env(ruta, clave)
    print(f"Llave instalada correctamente en: {ruta}")
    print("Respalda el archivo en un lugar seguro. No lo subas a Git ni lo incluyas en el instalador.")
    if args.mostrar:
        print(f"AXIA_DATA_KEY={clave}")


if __name__ == "__main__":
    main()
