from ui.font_runtime import ensure_poppins
ensure_poppins()
from ui.axia_dialogs import install_axia_dialogs
install_axia_dialogs()

# =====================================================
# IMPORTACIÓN DE LIBRERÍAS
# =====================================================
import customtkinter as ctk

from ui.theme import aplicar_tema_global

from core.logger import configurar_logger
from core.performance import mark, measure
from core.error_reporting import show_operation_error

logger = configurar_logger(__name__)

aplicar_tema_global()

# =====================================================
# FUNCIÓN PRINCIPAL DEL SISTEMA
# =====================================================
def main():

    # =============================================
    # ABRIR LOGIN DEL SISTEMA
    # =============================================

    from core.environment import cargar_entorno
    from core.deployment import DeploymentConfigurationError, load_deployment_config
    from security.data_encryption import (
        EncryptionConfigurationError,
        validar_configuracion_cifrado,
    )

    cargar_entorno()
    try:
        deployment = load_deployment_config()
        logger.info(
            "Ambiente AXIA validado: %s / Supabase %s",
            deployment.environment,
            deployment.project_ref,
        )
    except DeploymentConfigurationError as exc:
        logger.critical("Configuración de despliegue inválida: %s", exc)
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "AXIA · Configuración de ambiente",
                f"{exc}\n\nAXIA no continuará para evitar conectarse al ambiente equivocado.",
            )
        except Exception:
            logger.exception("No fue posible mostrar el aviso de ambiente.")
        return
    try:
        ruta_generada = validar_configuracion_cifrado()
        if ruta_generada:
            logger.warning(
                "Configuración de cifrado creada automáticamente para desarrollo en %s.",
                ruta_generada,
            )
    except EncryptionConfigurationError as exc:
        logger.critical("Configuración de cifrado inválida: %s", exc)
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "AXIA · Configuración de seguridad",
                f"{exc}\n\n"
                "Por seguridad, AXIA no continuará.\n\n"
                "En producción configura AXIA_DATA_KEY con la misma llave Fernet "
                "en todos los equipos autorizados.",
            )
        except Exception:
            logger.exception("No fue posible mostrar el aviso de configuración de cifrado.")
        return

    logger.info("Iniciando sistema AXIA.")
    mark("main: tema y bootstrap listos")

    with measure("importar login"):
        from login import abrir_login

    try:
        while True:
            with measure("sesión de login"):
                acceso_correcto = abrir_login()

            if not acceso_correcto:
                break

            with measure("importar aplicación principal"):
                from app import abrir_app
            with measure("sesión aplicación principal"):
                volver_a_login = abrir_app()

            if not volver_a_login:
                break

    except Exception as error:
        logger.exception("Error crítico al iniciar AXIA.")
        show_operation_error("Error crítico de AXIA", "Iniciar o ejecutar la aplicación", error)


# =====================================================
# PUNTO DE ENTRADA DEL PROGRAMA
# =====================================================
if __name__ == "__main__":

    main()