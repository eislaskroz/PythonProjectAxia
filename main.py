# =====================================================
# IMPORTACIÓN DE LIBRERÍAS
# =====================================================

# Librería principal para interfaces gráficas modernas
# basada en Tkinter.
import customtkinter as ctk

from ui.theme import aplicar_tema_global

from core.logger import configurar_logger

logger = configurar_logger(__name__)


# =====================================================
# IMPORTACIÓN DE MÓDULOS DEL SISTEMA
# =====================================================

# Función que abre la ventana Login
from login import abrir_login
from app import abrir_app


# =====================================================
# CONFIGURACIÓN VISUAL GLOBAL
# =====================================================
"""
Estas configuraciones afectan TODA la aplicación.
Se ejecutan antes de abrir cualquier ventana.
"""

# Usa automáticamente:
# - modo claro
# - modo oscuro
# según el sistema operativo.
aplicar_tema_global()


# El tema global también fija colores, fuente y escala base.


# =====================================================
# FUNCIÓN PRINCIPAL DEL SISTEMA
# =====================================================
def main():

    """
    Función principal del programa.

    Se encarga de:

    1. Crear la tabla usuarios
       si todavía no existe.

    2. Crear el usuario administrador inicial.

    3. Abrir la ventana Login.
    """

    # =============================================
    # CREAR TABLA USUARIOS
    # =============================================

    """
    Si la tabla ya existe,
    SQLite simplemente la ignora.
    """

    # =============================================
    # CREAR USUARIO ADMINISTRADOR
    # =============================================

    """
    Usuario por defecto:

    Usuario:
        admin

    Contraseña:
        1234

    Si ya existe,
    no lo vuelve a crear.
    """

    # =============================================
    # ABRIR LOGIN DEL SISTEMA
    # =============================================

    logger.info("Iniciando sistema AXIA.")

    try:
        while True:
            acceso_correcto = abrir_login()

            # Si el usuario cerró el Login sin entrar, termina el programa.
            if not acceso_correcto:
                break

            # abrir_app() devuelve True cuando el usuario pulsa
            # Cerrar sesión, y False cuando pulsa Salir/cierra AXIA.
            volver_a_login = abrir_app()

            if not volver_a_login:
                break

    except Exception:
        logger.exception("Error crítico al iniciar AXIA.")
        raise


# =====================================================
# PUNTO DE ENTRADA DEL PROGRAMA
# =====================================================

"""
Esta validación verifica que:

- el archivo se ejecutó directamente,
- y no fue importado como módulo.

Si se ejecuta directamente:
    -> corre main()

Si se importa desde otro archivo:
    -> no ejecuta main()
"""

if __name__ == "__main__":

    main()