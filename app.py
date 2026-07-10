"""
=========================================================
MÓDULO: app.py
DESCRIPCIÓN:
Ventana principal del sistema AXIA.

OBJETIVO DEL PASO 6:
Mantener este archivo ligero para evitar que se convierta
 en un archivo gigante difícil de mantener.

Ahora app.py se encarga solamente de:
- Crear la ventana principal.
- Crear el layout base.
- Crear encabezado y área de contenido.
- Conectar sidebar con NavigationController.

La navegación vive en:
controllers/navigation_controller.py

El sidebar vive en:
ui/app_sidebar.py
=========================================================
"""

# =====================================================
# IMPORTACIÓN DE LIBRERÍAS
# =====================================================

import customtkinter as ctk

from ui.theme import aplicar_fuente_tk, aplicar_estilo_ventana

# =====================================================
# IMPORTACIÓN DE CONTEXTO
# =====================================================

from app_context import obtener_usuario_actual

# =====================================================
# IMPORTACIÓN DE COMPONENTES Y CONTROLADORES
# =====================================================

from controllers.navigation_controller import NavigationController
from ui.app_sidebar import crear_app_sidebar

# =====================================================
# IMPORTACIÓN DE RECURSOS VISUALES
# =====================================================

from ui.assets import configurar_icono_ventana

from ui.colors import (
    CONTENT_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY
)

from ui.fonts import (
    TITLE_LG,
    TEXT_MD
)

# =====================================================
# IMPORTACIÓN DE LOGGER CENTRAL
# =====================================================

from core.logger import configurar_logger

logger = configurar_logger(__name__)


# =====================================================
# CLASE PRINCIPAL: AxiaApp
# =====================================================
class AxiaApp(ctk.CTk):
    """
    Clase principal del sistema AXIA.

    Esta clase representa la ventana principal y delega
    responsabilidades específicas a módulos especializados:

    - Sidebar: ui/app_sidebar.py
    - Navegación: controllers/navigation_controller.py
    - Vistas: views/
    - Servicios: services/
    """

    def __init__(self):
        """
        Inicializa la aplicación principal.
        """

        super().__init__()
        aplicar_estilo_ventana(self, min_width=1180, min_height=720)

        logger.info("Inicializando ventana principal AXIA.")

        # Indica a login.py si la ventana se cerró por "Cerrar sesión"
        # o por salida completa del sistema.
        self.logout_requested = False

        # =================================================
        # CONFIGURACIÓN GENERAL DE VENTANA
        # =================================================
        self.title("Sistema AXIA")
        configurar_icono_ventana(self)
        self.after(100, self.maximizar_ventana)
        self.resizable(True, True)
        self.minsize(1180, 720)
        self.configure(fg_color=CONTENT_BG)

        # =================================================
        # USUARIO ACTIVO
        # =================================================
        self.usuario_activo = obtener_usuario_actual()

        # =================================================
        # CREACIÓN DE LAYOUT BASE
        # =================================================
        self.crear_layout_base()
        self.crear_contenedor_principal()

        # =================================================
        # CONTROLADOR DE NAVEGACIÓN
        # =================================================
        self.navigation = NavigationController(
            app=self,
            content_frame=self.content,
            title_label=self.label_titulo,
            subtitle_label=self.label_subtitulo
        )

        # =================================================
        # SIDEBAR PRINCIPAL
        # =================================================
        self.crear_sidebar_principal()

        # =================================================
        # VISTA INICIAL
        # =================================================
        self.navigation.mostrar_inicio_aco()

    # =====================================================
    # MÉTODO: maximizar_ventana()
    # =====================================================
    def maximizar_ventana(self):
        """
        Ejecuta la aplicación en pantalla maximizada.

        Se intenta primero con state("zoomed"), que funciona en Windows.
        Si el sistema operativo no lo soporta, se usa fullscreen como
        respaldo controlado.
        """

        try:
            self.state("zoomed")
        except Exception:
            logger.exception("No fue posible usar state('zoomed'). Se usará fullscreen.")
            self.attributes("-fullscreen", True)

    # =====================================================
    # MÉTODO: crear_layout_base()
    # =====================================================
    def crear_layout_base(self):
        """
        Crea el layout general de dos columnas:

        columna 0:
            Sidebar fijo.
        columna 1:
            Área principal dinámica.
        """

        self.layout = ctk.CTkFrame(
            self,
            fg_color=CONTENT_BG,
            corner_radius=0
        )
        self.layout.pack(
            fill="both",
            expand=True
        )

        self.layout.grid_columnconfigure(0, weight=0)
        self.layout.grid_columnconfigure(1, weight=1)
        self.layout.grid_rowconfigure(0, weight=1)

    # =====================================================
    # MÉTODO: crear_contenedor_principal()
    # =====================================================
    def crear_contenedor_principal(self):
        """
        Crea el área derecha de la aplicación.

        Incluye:
        - Encabezado superior.
        - Frame dinámico donde se cargan las vistas.
        """

        self.main_area = ctk.CTkFrame(
            self.layout,
            fg_color=CONTENT_BG,
            corner_radius=0
        )
        self.main_area.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        # La zona superior de título/subtítulo se elimina para recuperar espacio útil.
        # Se conservan labels internos no visibles porque NavigationController los actualiza.
        self.main_area.grid_rowconfigure(0, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        self.crear_header()
        self.crear_area_contenido()

    # =====================================================
    # MÉTODO: crear_header()
    # =====================================================
    def crear_header(self):
        """
        Crea el encabezado superior de la aplicación.
        """

        self.header = ctk.CTkFrame(
            self.main_area,
            height=92,
            fg_color=CONTENT_BG,
            corner_radius=0
        )
        # No se muestra con grid: queda como contenedor lógico invisible.
        self.header.pack_propagate(False)

        self.label_titulo = ctk.CTkLabel(
            self.header,
            text="Sistema AXIA",
            font=TITLE_LG,
            text_color=TEXT_PRIMARY
        )
        self.label_titulo.pack(
            anchor="center",
            padx=35,
            pady=(18, 2)
        )

        self.label_subtitulo = ctk.CTkLabel(
            self.header,
            text="Gestión operativa centralizada",
            font=TEXT_MD,
            text_color=TEXT_SECONDARY
        )
        self.label_subtitulo.pack(
            anchor="center",
            padx=35
        )

    # =====================================================
    # MÉTODO: crear_area_contenido()
    # =====================================================
    def crear_area_contenido(self):
        """
        Crea el frame donde NavigationController cargará
        las vistas dinámicas.
        """

        self.content = ctk.CTkFrame(
            self.main_area,
            fg_color=CONTENT_BG,
            corner_radius=0
        )
        self.content.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

    # =====================================================
    # MÉTODO: crear_sidebar_principal()
    # =====================================================
    def crear_sidebar_principal(self):
        """
        Crea el menú lateral y conecta sus botones con
        el controlador de navegación.
        """

        callbacks = {
            "inicio_aco": self.navigation.mostrar_inicio_aco,

            # Flujo operativo real. Se usa desde Inicio ACO o para
            # usuarios no administradores cuando deben levantar un caso nuevo.
            "levantamiento": self.navigation.mostrar_selector_levantamiento,
            "orden_servicio": self.navigation.mostrar_orden_servicio,
            "orden_trabajo": self.navigation.mostrar_orden_trabajo,
            "bitacora_avance": self.navigation.mostrar_bitacora_avance,

            # Vistas administrativas/consulta. Para administradores, los
            # botones laterales de procesos abren búsqueda y administración,
            # no formularios de generación.
            "admin_levantamientos": self.navigation.mostrar_admin_levantamientos,
            "admin_ordenes_servicio": self.navigation.mostrar_admin_ordenes_servicio,
            "admin_ordenes_trabajo": self.navigation.mostrar_admin_ordenes_trabajo,
            "admin_bitacoras": self.navigation.mostrar_admin_bitacoras,
            "admin_obras_civiles": self.navigation.mostrar_admin_obras_civiles,

            "reportes": self.navigation.mostrar_reportes,
            "usuarios": self.navigation.mostrar_usuarios,
            "clientes": self.navigation.mostrar_clientes,
            "auditoria": self.navigation.mostrar_auditoria,
            "mi_usuario": self.navigation.mostrar_mi_usuario,
            "mi_bitacora": self.navigation.mostrar_mi_usuario,
            "en_construccion": self.navigation.mostrar_en_construccion,
            "obra_civil": self.navigation.mostrar_obra_civil
        }

        self.sidebar = crear_app_sidebar(
            parent=self.layout,
            usuario_activo=self.usuario_activo,
            callbacks=callbacks,
            on_exit=self.salir_aplicacion,
            on_logout=self.cerrar_sesion
        )

    # =====================================================
    # MÉTODOS DE COMPATIBILIDAD TEMPORAL
    # =====================================================
    # Algunas vistas existentes todavía llaman métodos
    # directamente sobre app. Estos wrappers mantienen
    # compatibilidad mientras se migra todo al controlador.

    def volver_atras(self):
        self.navigation.volver_atras()

    def mostrar_vista_inicio_aco(self):
        self.navigation.mostrar_inicio_aco()

    def mostrar_vista_inicio_aco_validado(self, aco=None):
        self.navigation.mostrar_inicio_aco_validado(aco)

    def mostrar_vista_en_construccion(self):
        self.navigation.mostrar_en_construccion()

    def mostrar_vista_selector_levantamiento(self, aco=None):
        self.navigation.mostrar_selector_levantamiento(aco=aco)

    def mostrar_vista_levantamiento(self, aco=None, tipo_levantamiento=None):
        # Si no llega tipo, primero se muestra el selector operativo.
        if tipo_levantamiento is None:
            self.navigation.mostrar_selector_levantamiento(aco=aco)
        else:
            self.navigation.mostrar_levantamiento(aco=aco, tipo_levantamiento=tipo_levantamiento)

    def mostrar_vista_orden_servicio(self, aco=None):
        self.navigation.mostrar_orden_servicio(aco=aco)

    def mostrar_vista_orden_trabajo(self, aco=None):
        self.navigation.mostrar_orden_trabajo(aco=aco)

    def mostrar_vista_reportes(self):
        self.navigation.mostrar_reportes()

    def mostrar_vista_admin_levantamientos(self):
        self.navigation.mostrar_admin_levantamientos()

    def mostrar_vista_admin_ordenes_servicio(self):
        self.navigation.mostrar_admin_ordenes_servicio()

    def mostrar_vista_admin_ordenes_trabajo(self):
        self.navigation.mostrar_admin_ordenes_trabajo()

    def mostrar_vista_admin_bitacoras(self):
        self.navigation.mostrar_admin_bitacoras()

    def mostrar_vista_usuarios(self):
        self.navigation.mostrar_usuarios()

    def mostrar_vista_clientes(self):
        self.navigation.mostrar_clientes()

    def mostrar_vista_auditoria(self):
        self.navigation.mostrar_auditoria()

    def mostrar_vista_bitacora_avance(self, aco=None):
        self.navigation.mostrar_bitacora_avance(aco=aco)

    def mostrar_vista_obra_civil(self, aco=None):
        self.navigation.mostrar_obra_civil(aco=aco)

    def mostrar_vista_admin_obras_civiles(self):
        self.navigation.mostrar_admin_obras_civiles()

    def mostrar_vista_mi_bitacora(self):
        self.navigation.mostrar_mi_usuario()

    def mostrar_vista_mi_usuario(self):
        self.navigation.mostrar_mi_usuario()

    def cerrar_sesion(self):
        """Cierra la sesión activa y solicita regresar al Login inicial.

        La ventana principal NO debe intentar abrir directamente login.py.
        Si lo hace desde un callback de Tkinter, puede destruir la ventana
        actual y quedarse sin crear el Login nuevo.

        Flujo correcto:
        1. Marcar logout_requested = True.
        2. Limpiar usuario activo.
        3. Destruir la ventana principal.
        4. login.py detecta la bandera y vuelve a abrir el Login.
        """
        from app_context import establecer_usuario_actual
        from services.movimientos_service import registrar_movimiento_seguro

        self.logout_requested = True

        try:
            registrar_movimiento_seguro(
                modulo="Login",
                accion="CERRAR_SESION",
                descripcion="El usuario cerró sesión manualmente"
            )
        except Exception:
            logger.exception("No fue posible registrar el cierre de sesión.")

        establecer_usuario_actual()

        try:
            self.destroy()
        except Exception:
            logger.exception("No fue posible cerrar la ventana principal al cerrar sesión.")

    def salir_aplicacion(self):
        """Cierra por completo el sistema AXIA."""
        self.logout_requested = False
        try:
            self.destroy()
        except Exception:
            logger.exception("No fue posible cerrar la aplicación.")


# =====================================================
# FUNCIÓN: abrir_app()
# =====================================================
def abrir_app():
    """
    Ejecuta la aplicación principal AXIA.

    Returns:
        bool: True si el usuario presionó "Cerrar sesión" y se debe
        volver al Login. False si eligió salir/cerrar la aplicación.
    """

    app = AxiaApp()
    app.mainloop()
    return bool(getattr(app, "logout_requested", False))
