# =========================================================
# IMPORTACIÓN DE LIBRERÍAS
# =========================================================
from pathlib import Path

# Librería para procesamiento de imágenes
from PIL import Image

# Framework visual utilizado en el sistema
import customtkinter as ctk

_BASE_LOGO_IMAGE = None

# =========================================================
# FUNCIÓN: cargar_logo_axia()
# =========================================================
def cargar_logo_axia(size=(210, 210)):
    # =====================================================
    # OBTENER RUTA RAÍZ DEL PROYECTO
    # =====================================================
    ruta_proyecto = Path(__file__).resolve().parent.parent

    # =====================================================
    # CONSTRUIR RUTA COMPLETA DEL LOGO
    # =====================================================
    ruta_logo = ruta_proyecto / "assets" / "Isologo-con-fondo-blanco.png"

    # =====================================================
    # CARGAR IMAGEN
    # =====================================================

    global _BASE_LOGO_IMAGE
    key = tuple(size)

    if _BASE_LOGO_IMAGE is None:
        with Image.open(ruta_logo) as source:
            _BASE_LOGO_IMAGE = source.convert("RGBA").copy()

    return ctk.CTkImage(
        light_image=_BASE_LOGO_IMAGE,
        dark_image=_BASE_LOGO_IMAGE,
        size=key
    )

# =========================================================
# FUNCIÓN: configurar_icono_ventana()
# =========================================================
def configurar_icono_ventana(ventana):
    # =====================================================
    # RUTA DEL ICONO CORPORATIVO
    # =====================================================

    ruta_proyecto = Path(__file__).resolve().parent.parent
    ruta_icono = ruta_proyecto / "assets" / "SoloAxia.ico"

    # =====================================================
    # ASIGNAR ICONO A LA VENTANA
    # =====================================================

    ventana.iconbitmap(str(ruta_icono))

# =========================================================
# FUNCIÓN: configurar_icono_app()
# =========================================================
def configurar_icono_app(app):
    ruta_proyecto = Path(__file__).resolve().parent.parent
    ruta_icono = ruta_proyecto / "assets" / "SoloAxia.ico"
    app.iconbitmap(str(ruta_icono))

# =========================================================
# FUNCIÓN: configurar_icono_menu()
# =========================================================
def configurar_icono_menu(menu):
    ruta_proyecto = Path(__file__).resolve().parent.parent
    ruta_icono = ruta_proyecto / "assets" / "SoloAxia.ico"
    menu.iconbitmap(str(ruta_icono))