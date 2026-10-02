from pathlib import Path
import customtkinter as ctk
from PIL import Image

ICON_DIR = Path(__file__).resolve().parent.parent / "assets" / "iconos"

def cargar_icono(nombre, size=(18,18), blanco=False):
    """Carga un icono sin derribar la app si el recurso falta o está dañado."""
    try:
        ruta = ICON_DIR / nombre
        if not ruta.exists():
            return None
        with Image.open(ruta) as src:
            img = src.convert("RGBA")
        if blanco:
            out = Image.new("RGBA", img.size, (255,255,255,0))
            out.putalpha(img.getchannel("A"))
            img = out
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    except Exception:
        return None
