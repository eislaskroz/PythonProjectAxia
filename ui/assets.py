# =========================================================
# IMPORTACIÓN DE LIBRERÍAS
# =========================================================

# Manejo moderno y seguro de rutas del sistema
from pathlib import Path

# Librería para procesamiento de imágenes
from PIL import Image

# Framework visual utilizado en el sistema
import customtkinter as ctk

# =========================================================
# FUNCIÓN: cargar_logo_axia()
# =========================================================
def cargar_logo_axia(size=(210, 210)):
    """
    Carga el logotipo corporativo de AXIA
    desde la carpeta assets del proyecto.

    Esta función retorna una imagen compatible
    con CustomTkinter (CTkImage), permitiendo
    reutilizar el mismo logo en múltiples
    ventanas del sistema.

    -----------------------------------------------------
    PARÁMETROS:
    -----------------------------------------------------

    size : tuple(int, int)
        Tamaño deseado de la imagen.
        Formato:
            (ancho, alto)

        Ejemplo:
            (210, 210)

    -----------------------------------------------------
    RETORNA:
    -----------------------------------------------------

    ctk.CTkImage
        Imagen lista para utilizarse en Labels,
        Buttons o cualquier componente CTk.

    -----------------------------------------------------
    FUNCIONAMIENTO:
    -----------------------------------------------------

    1. Obtiene automáticamente la raíz del proyecto.
    2. Construye la ruta completa del logo.
    3. Abre la imagen utilizando Pillow.
    4. Convierte la imagen a formato CTkImage.
    5. Retorna el objeto listo para interfaz gráfica.

    -----------------------------------------------------
    EJEMPLO DE USO:
    -----------------------------------------------------

    logo = cargar_logo_axia(size=(240, 240))

    label_logo = ctk.CTkLabel(
        ventana,
        image=logo,
        text=""
    )

    -----------------------------------------------------
    """

    # =====================================================
    # OBTENER RUTA RAÍZ DEL PROYECTO
    # =====================================================

    # __file__:
    # Ruta actual de este archivo (assets.py)
    #
    # resolve():
    # Convierte la ruta a absoluta
    #
    # parent.parent:
    # Retrocede dos niveles para llegar
    # a la raíz principal del proyecto

    ruta_proyecto = Path(__file__).resolve().parent.parent

    # =====================================================
    # CONSTRUIR RUTA COMPLETA DEL LOGO
    # =====================================================

    # Ruta final esperada:
    #
    # Proyecto/
    # └── assets/
    #     └── LogoAxia-Full.png

    ruta_logo = ruta_proyecto / "assets" / "LogoAxia-Full.png"

    # =====================================================
    # CARGAR IMAGEN
    # =====================================================

    # Apertura del archivo PNG utilizando Pillow
    imagen = Image.open(ruta_logo)

    # =====================================================
    # RETORNAR IMAGEN COMPATIBLE CON CTK
    # =====================================================

    return ctk.CTkImage(
        light_image=imagen,
        dark_image=imagen,
        size=size
    )

# =========================================================
# FUNCIÓN: configurar_icono_ventana()
# =========================================================
def configurar_icono_ventana(ventana):
    """
    Configura el icono corporativo AXIA en la ventana.

    En Windows se recomienda utilizar archivo .ico
    mediante iconbitmap(), ya que iconphoto() con PNG
    puede no reflejarse correctamente en la barra superior.
    """

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