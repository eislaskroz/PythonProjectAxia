"""Prepara fuentes suministradas por el equipo AXIA para el build local."""
from __future__ import annotations
from pathlib import Path
from zipfile import ZipFile
import sys

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ("Poppins-Regular.ttf", "Poppins-Medium.ttf", "Poppins-SemiBold.ttf", "Poppins-Bold.ttf", "Poppins-Italic.ttf", "Poppins-BoldItalic.ttf")
DEST = ROOT / "assets" / "fonts"

def prepare():
    archive = ROOT / "poppins.zip"
    if not archive.is_file():
        if all((DEST / name).is_file() for name in REQUIRED) and (DEST / "OFL.txt").is_file():
            return
        raise RuntimeError("Falta poppins.zip en la raíz de AXIA DESKTOP. Copia el ZIP original de Poppins junto a main.py y vuelve a compilar.")
    with ZipFile(archive) as z:
        files = {Path(name).name: name for name in z.namelist() if not name.endswith("/")}
        missing = set(REQUIRED + ("OFL.txt",)) - files.keys()
        if missing:
            raise RuntimeError("El ZIP de Poppins no tiene los archivos obligatorios: " + ", ".join(sorted(missing)))
        DEST.mkdir(parents=True, exist_ok=True)
        for filename in (*REQUIRED, "OFL.txt"):
            data = z.read(files[filename])
            if len(data) < 100 if filename.endswith(".ttf") else not data:
                raise RuntimeError("Archivo de fuente inválido: " + filename)
            (DEST / filename).write_bytes(data)
    print("Poppins preparada en assets/fonts (Regular, Medium, SemiBold, Bold e Italic).")

if __name__ == "__main__":
    try: prepare()
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
