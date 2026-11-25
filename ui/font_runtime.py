"""Poppins privada de AXIA: disponible para las ventanas sin instalación global."""
from __future__ import annotations
import ctypes
import sys
from pathlib import Path

REQUIRED = ("Poppins-Regular.ttf", "Poppins-Medium.ttf", "Poppins-SemiBold.ttf", "Poppins-Bold.ttf", "Poppins-Italic.ttf", "Poppins-BoldItalic.ttf")
_registered = False

def fonts_dir() -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return root / "assets" / "fonts"

def ensure_poppins() -> Path:
    global _registered
    folder = fonts_dir()
    missing = [x for x in REQUIRED if not (folder / x).is_file()]
    if missing:
        raise RuntimeError("Poppins no está incluida en esta instalación AXIA (" + ", ".join(missing) + "). Reconstruye el instalador con poppins.zip.")
    if _registered:
        return folder
    if sys.platform == "win32":
        # FR_PRIVATE = 0x10: registra fuentes sólo dentro de este proceso.
        gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        add = gdi32.AddFontResourceExW
        add.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
        add.restype = ctypes.c_int
        for filename in REQUIRED:
            if add(str(folder / filename), 0x10, None) == 0:
                raise RuntimeError("Windows no pudo cargar Poppins desde el paquete AXIA: " + filename)
    _registered = True
    return folder
