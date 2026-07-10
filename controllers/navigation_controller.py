"""
=========================================================
MÓDULO: controllers/navigation_controller.py
DESCRIPCIÓN:
Controlador central de navegación interna de AXIA.

OBJETIVO:
Evitar que app.py crezca demasiado.

Este archivo se encarga de:
- Limpiar el área dinámica de contenido.
- Cambiar títulos y subtítulos del encabezado.
- Cargar vistas internas del sistema.
- Mantener concentrada la lógica de navegación.

IMPORTANTE:
Las vistas siguen viviendo en views/.
Este controlador NO debe contener lógica de negocio.
Solo coordina qué vista se muestra y cuándo.
=========================================================
"""

# =====================================================
# IMPORTACIÓN DE LIBRERÍAS
# =====================================================

import customtkinter as ctk

# =====================================================
# IMPORTACIÓN DIFERIDA DE VISTAS Y SERVICIOS
# =====================================================
# Las vistas y servicios pesados se importan dentro de cada método.
# Esto reduce el tiempo de arranque y evita cargar pantallas que el usuario
# quizá no utilizará durante la sesión.

# =====================================================
# IMPORTACIÓN DE RECURSOS VISUALES
# =====================================================

from ui.colors import WHITE

# =====================================================
# IMPORTACIÓN DE LOGGER CENTRAL
# =====================================================

from core.logger import configurar_logger

logger = configurar_logger(__name__)


# =====================================================
# CLASE: NavigationController
# =====================================================
class NavigationController:
    """
    Controlador de navegación principal.

    Recibe referencias de la aplicación y del área visual
    donde se deben cargar las pantallas.

    Esto permite que app.py se mantenga limpio y que las
    nuevas pantallas se agreguen aquí, no directamente en
    la clase principal de la aplicación.
    """

    def __init__(self, app, content_frame, title_label, subtitle_label):
        """
        Inicializa el controlador de navegación.

        Args:
            app:
                Instancia principal de AxiaApp.
            content_frame:
                Frame donde se renderizan las vistas.
            title_label:
                Label del título superior.
            subtitle_label:
                Label del subtítulo superior.
        """

        self.app = app
        self.content = content_frame
        self.title_label = title_label
        self.subtitle_label = subtitle_label

        # Historial simple de navegación para el botón ATRÁS.
        self._historial = []
        self._vista_actual = None
        self._regresando = False

    # =================================================
    # HISTORIAL DE NAVEGACIÓN
    # =================================================
    def _registrar_vista(self, nombre_metodo, **kwargs):
        """Guarda la vista actual antes de cambiar de pantalla."""
        if self._vista_actual and not self._regresando:
            self._historial.append(self._vista_actual)
            if len(self._historial) > 25:
                self._historial = self._historial[-25:]
        self._vista_actual = (nombre_metodo, kwargs)

    def volver_atras(self):
        """Regresa a la pantalla anterior sin repetir pasos."""
        if not self._historial:
            self.mostrar_inicio_aco()
            return
        nombre_metodo, kwargs = self._historial.pop()
        metodo = getattr(self, nombre_metodo, None)
        if metodo is None:
            self.mostrar_inicio_aco()
            return
        self._regresando = True
        try:
            metodo(**kwargs)
        finally:
            self._regresando = False

    # =================================================
    # LIMPIEZA DE CONTENIDO
    # =================================================
    def limpiar_contenido(self):
        """
        Elimina todos los widgets del área dinámica.

        Se ejecuta antes de cargar una nueva vista para
        evitar que queden elementos visuales duplicados.
        """

        for widget in self.content.winfo_children():
            widget.destroy()

    # =================================================
    # ACTUALIZAR ENCABEZADO
    # =================================================
    def cambiar_titulo(self, titulo, subtitulo):
        """
        Cambia el título y subtítulo del encabezado.

        Args:
            titulo:
                Texto principal de la pantalla activa.
            subtitulo:
                Texto descriptivo de la pantalla activa.
        """

        self.title_label.configure(text=titulo)
        self.subtitle_label.configure(text=subtitulo)

    # =================================================
    # VISTA: INICIO ACO
    # =================================================
    def mostrar_inicio_aco(self):
        """
        Carga la pantalla inicial del flujo operativo ACO.
        """

        self._registrar_vista("mostrar_inicio_aco")
        logger.info("Cargando vista: Inicio ACO")
        self.limpiar_contenido()

        self.cambiar_titulo(
            "Inicio Operativo ACO",
            "Selecciona el flujo operativo con el que deseas trabajar."
        )

        from views.inicio_aco_view import mostrar_inicio_aco

        mostrar_inicio_aco(
            parent=self.content,
            app=self.app
        )


    def mostrar_inicio_aco_validado(self, aco):
        """Regresa a la pantalla de selección operativa manteniendo el ACO validado."""

        self._registrar_vista("mostrar_inicio_aco_validado", aco=aco)
        logger.info("Cargando vista: Inicio ACO con ACO validado")
        self.limpiar_contenido()

        self.cambiar_titulo(
            "Inicio Operativo ACO",
            "Selecciona el formulario operativo para el ACO validado."
        )

        from views.inicio_aco_view import mostrar_inicio_aco

        mostrar_inicio_aco(
            parent=self.content,
            app=self.app,
            aco_validado=aco
        )

    # =================================================
    # VISTA: LEVANTAMIENTO
    # =================================================
    def mostrar_selector_levantamiento(self, aco=None):
        """
        Carga la pantalla previa para seleccionar el tipo de levantamiento.
        """

        self._registrar_vista("mostrar_selector_levantamiento", aco=aco)
        logger.info("Cargando selector de tipo de levantamiento")
        self.limpiar_contenido()

        self.cambiar_titulo(
            "Nuevo Levantamiento",
            "Selecciona el tipo de levantamiento antes de capturar información técnica."
        )

        from views.tipo_levantamiento_view import mostrar_selector_tipo_levantamiento

        mostrar_selector_tipo_levantamiento(
            parent=self.content,
            app=self.app,
            aco=aco
        )

    def mostrar_levantamiento(self, aco=None, tipo_levantamiento=None):
        """
        Carga la vista para generar levantamientos.

        Args:
            aco:
                Registro ACO opcional que se puede enviar
                desde otra pantalla para continuar flujo.
            tipo_levantamiento:
                Tipo seleccionado en la pantalla previa. Ejemplo: Seguridad y Monitoreo.
        """

        self._registrar_vista("mostrar_levantamiento", aco=aco, tipo_levantamiento=tipo_levantamiento)
        logger.info("Cargando vista: Levantamiento")
        self.limpiar_contenido()

        titulo = "Levantamiento Seguridad y Monitoreo" if tipo_levantamiento == "Seguridad y Monitoreo" else "Generar Levantamiento"

        self.cambiar_titulo(
            titulo,
            "Captura la información inicial del servicio."
        )

        from views.levantamiento_view import mostrar_levantamiento

        mostrar_levantamiento(
            parent=self.content,
            app=self.app,
            aco=aco,
            tipo_levantamiento=tipo_levantamiento
        )

    # =================================================
    # VISTA: ORDEN DE SERVICIO
    # =================================================
    def mostrar_orden_servicio(self, aco=None):
        """
        Carga la vista para generar órdenes de servicio.
        """

        self._registrar_vista("mostrar_orden_servicio", aco=aco)
        logger.info("Cargando vista: Orden de Servicio")
        self.limpiar_contenido()

        self.cambiar_titulo(
            "Órdenes de Servicio",
            "Captura la información operativa de la orden."
        )

        from views.orden_servicio_view import mostrar_orden_servicio

        mostrar_orden_servicio(
            parent=self.content,
            app=self.app,
            aco=aco
        )


    # =================================================
    # VISTA: ORDEN DE TRABAJO
    # =================================================
    def mostrar_orden_trabajo(self, aco=None):
        """
        Carga la vista para generar órdenes de trabajo.
        """

        self._registrar_vista("mostrar_orden_trabajo", aco=aco)
        logger.info("Cargando vista: Orden de Trabajo")
        self.limpiar_contenido()

        self.cambiar_titulo(
            "Órdenes de Trabajo",
            "Captura la información operativa de la orden de trabajo."
        )

        from views.orden_trabajo_view import mostrar_orden_trabajo

        mostrar_orden_trabajo(
            parent=self.content,
            app=self.app,
            aco=aco
        )



    # =================================================
    # VISTA: OBRA CIVIL
    # =================================================
    def mostrar_obra_civil(self, aco=None):
        """
        Carga la vista para generar registros de obra civil / proyecto ejecutivo.
        """

        self._registrar_vista("mostrar_obra_civil", aco=aco)
        logger.info("Cargando vista: Obra Civil")
        self.limpiar_contenido()

        self.cambiar_titulo(
            "Obra Civil",
            "Captura el proceso ejecutivo de obra civil ligado al ACO."
        )

        from views.obra_civil_view import mostrar_obra_civil

        mostrar_obra_civil(
            parent=self.content,
            app=self.app,
            aco=aco
        )

    # =================================================
    # VISTAS ADMINISTRATIVAS DE PROCESOS
    # =================================================
    def mostrar_admin_levantamientos(self):
        """
        Carga la administración/consulta de levantamientos.
        No genera registros nuevos; la creación inicia desde Inicio ACO.
        """

        self._registrar_vista("mostrar_admin_levantamientos")
        logger.info("Cargando vista administrativa: Levantamientos")
        self.limpiar_contenido()
        self.cambiar_titulo(
            "Levantamientos",
            "Busca y consulta levantamientos registrados."
        )
        from views.admin_procesos_view import mostrar_admin_procesos
        from services.levantamientos_service import obtener_levantamientos, buscar_levantamiento_por_folio

        mostrar_admin_procesos(
            parent=self.content,
            app=self.app,
            configuracion={
                "titulo": "Levantamientos",
                "prefijo": "LEV",
                "campo_folio": "lev_folio",
                "campos_aco": ["lev_aco_numero", "aco_numero"],
                "campos_cliente": ["lev_cliente", "aco_cliente", "cliente"],
                "campos_estatus": ["lev_estatus", "estatus"],
                "campos_fecha": ["fecha_registro", "created_at"],
                "campos_descripcion": ["lev_descripcion", "lev_motivo", "descripcion"],
                "obtener_todos": obtener_levantamientos,
                "buscar_por_folio": buscar_levantamiento_por_folio,
            }
        )

    def mostrar_admin_ordenes_servicio(self):
        """
        Carga la administración/consulta de órdenes de servicio.
        """

        self._registrar_vista("mostrar_admin_ordenes_servicio")
        logger.info("Cargando vista administrativa: Órdenes de Servicio")
        self.limpiar_contenido()
        self.cambiar_titulo(
            "Órdenes de Servicio",
            "Busca y consulta órdenes de servicio registradas."
        )
        from views.admin_procesos_view import mostrar_admin_procesos
        from services.ordenes_servicio_service import obtener_ordenes_servicio, buscar_orden_por_folio

        mostrar_admin_procesos(
            parent=self.content,
            app=self.app,
            configuracion={
                "titulo": "Órdenes de Servicio",
                "prefijo": "OS",
                "campo_folio": "os_folio",
                "campos_aco": ["os_aco_numero", "aco_numero"],
                "campos_cliente": ["os_cliente", "aco_cliente", "cliente"],
                "campos_estatus": ["os_estatus", "estatus"],
                "campos_fecha": ["fecha_registro", "created_at"],
                "campos_descripcion": ["os_descripcion", "os_actividad", "descripcion"],
                "obtener_todos": obtener_ordenes_servicio,
                "buscar_por_folio": buscar_orden_por_folio,
            }
        )

    def mostrar_admin_ordenes_trabajo(self):
        """
        Carga la administración/consulta de órdenes de trabajo.
        """

        self._registrar_vista("mostrar_admin_ordenes_trabajo")
        logger.info("Cargando vista administrativa: Órdenes de Trabajo")
        self.limpiar_contenido()
        self.cambiar_titulo(
            "Órdenes de Trabajo",
            "Busca y consulta órdenes de trabajo registradas."
        )
        from views.admin_procesos_view import mostrar_admin_procesos
        from services.ordenes_trabajo_service import obtener_ordenes_trabajo, buscar_orden_trabajo_por_folio

        mostrar_admin_procesos(
            parent=self.content,
            app=self.app,
            configuracion={
                "titulo": "Órdenes de Trabajo",
                "prefijo": "OT",
                "campo_folio": "ot_folio",
                "campos_aco": ["ot_aco_numero", "aco_numero"],
                "campos_cliente": ["ot_cliente", "aco_cliente", "cliente"],
                "campos_estatus": ["ot_estatus", "estatus"],
                "campos_fecha": ["fecha_registro", "created_at"],
                "campos_descripcion": ["ot_descripcion", "ot_actividad", "descripcion"],
                "obtener_todos": obtener_ordenes_trabajo,
                "buscar_por_folio": buscar_orden_trabajo_por_folio,
            }
        )

    def mostrar_admin_bitacoras(self):
        """
        Carga la administración/consulta de bitácoras operativas.
        """

        self._registrar_vista("mostrar_admin_bitacoras")
        logger.info("Cargando vista administrativa: Bitácoras Operativas")
        self.limpiar_contenido()
        self.cambiar_titulo(
            "Bitácoras Operativas",
            "Busca y consulta bitácoras operativas registradas."
        )
        from views.admin_procesos_view import mostrar_admin_procesos
        from services.bitacoras_service import obtener_bitacoras, buscar_bitacora_por_folio

        mostrar_admin_procesos(
            parent=self.content,
            app=self.app,
            configuracion={
                "titulo": "Bitácoras Operativas",
                "prefijo": "BIT",
                "campo_folio": "bit_folio",
                "campos_aco": ["bit_aco_numero", "aco_numero"],
                "campos_cliente": ["bit_cliente", "aco_cliente", "cliente"],
                "campos_estatus": ["bit_estatus", "estatus"],
                "campos_fecha": ["fecha_registro", "created_at"],
                "campos_descripcion": ["bit_descripcion", "bit_avance", "descripcion"],
                "obtener_todos": obtener_bitacoras,
                "buscar_por_folio": buscar_bitacora_por_folio,
            }
        )


    def mostrar_admin_obras_civiles(self):
        """
        Carga la administración/consulta de obras civiles.
        """

        self._registrar_vista("mostrar_admin_obras_civiles")
        logger.info("Cargando vista administrativa: Obras Civiles")
        self.limpiar_contenido()
        self.cambiar_titulo(
            "Obras Civiles",
            "Busca y consulta proyectos ejecutivos de obra civil."
        )
        from views.admin_procesos_view import mostrar_admin_procesos
        from services.obras_civiles_service import obtener_obras_civiles, buscar_obra_civil_por_folio

        mostrar_admin_procesos(
            parent=self.content,
            app=self.app,
            configuracion={
                "titulo": "Obras Civiles",
                "prefijo": "OBC",
                "campo_folio": "obc_folio",
                "campos_aco": ["obc_aco_numero", "aco_numero"],
                "campos_cliente": ["obc_cliente", "aco_cliente", "cliente"],
                "campos_estatus": ["obc_estatus", "estatus"],
                "campos_fecha": ["obc_fecha", "fecha_registro", "created_at"],
                "campos_descripcion": ["obc_nombre_proyecto", "obc_observaciones_finales", "descripcion"],
                "obtener_todos": obtener_obras_civiles,
                "buscar_por_folio": buscar_obra_civil_por_folio,
            }
        )

    # =================================================
    # VISTA: REPORTES ADMINISTRATIVOS
    # =================================================
    def mostrar_reportes(self):
        """
        Carga la vista administrativa de reportes.
        """

        self._registrar_vista("mostrar_reportes")
        logger.info("Cargando vista: Reportes")
        self.limpiar_contenido()

        self.cambiar_titulo(
            "Reportes",
            "Consulta administrativa de reportes operativos."
        )

        from views.reportes_view import mostrar_reportes

        mostrar_reportes(
            parent=self.content,
            app=self.app
        )


    # =================================================
    # VISTA: ADMINISTRACIÓN DE USUARIOS
    # =================================================
    def mostrar_usuarios(self):
        """
        Carga la vista administrativa para buscar, crear y editar usuarios.
        """

        self._registrar_vista("mostrar_usuarios")
        logger.info("Cargando vista: Administración de Usuarios")
        self.limpiar_contenido()

        self.cambiar_titulo(
            "Usuarios",
            "Busca, actualiza o registra usuarios del sistema."
        )

        from views.usuarios_admin_view import mostrar_usuarios_admin

        mostrar_usuarios_admin(
            parent=self.content,
            app=self.app
        )

    # =================================================
    # VISTA: ADMINISTRACIÓN DE CLIENTES
    # =================================================
    def mostrar_clientes(self):
        """
        Carga la vista administrativa para buscar, crear y editar clientes.
        """

        self._registrar_vista("mostrar_clientes")
        logger.info("Cargando vista: Administración de Clientes")
        self.limpiar_contenido()

        self.cambiar_titulo(
            "Clientes",
            "Busca, actualiza o registra clientes."
        )

        from views.clientes_admin_view import mostrar_clientes_admin

        mostrar_clientes_admin(
            parent=self.content,
            app=self.app
        )

    # =================================================
    # VISTA: BITÁCORA DE AVANCE
    # =================================================
    def mostrar_bitacora_avance(self, aco=None):
        """
        Carga la vista de bitácoras operativas.
        """

        self._registrar_vista("mostrar_bitacora_avance", aco=aco)
        logger.info("Cargando vista: Bitácora Operativa")
        self.limpiar_contenido()

        self.cambiar_titulo(
            "Bitácora Operativa",
            "Registro de avances operativos del servicio."
        )

        from views.bitacora_avance_view import mostrar_bitacora_avance

        mostrar_bitacora_avance(
            parent=self.content,
            app=self.app,
            aco=aco
        )



    # =================================================
    # VISTA: MI USUARIO
    # =================================================
    def mostrar_mi_usuario(self):
        """Carga la vista personal del usuario en sesión."""

        self._registrar_vista("mostrar_mi_usuario")
        logger.info("Cargando vista: Mi Usuario")
        self.limpiar_contenido()

        self.cambiar_titulo(
            "Mi Usuario",
            "Consulta tus datos y cambia tu contraseña."
        )

        from views.mi_bitacora_view import mostrar_mi_usuario

        mostrar_mi_usuario(
            parent=self.content,
            app=self.app
        )

    def mostrar_mi_bitacora(self):
        """Compatibilidad temporal: redirige a Mi Usuario."""
        self.mostrar_mi_usuario()

    # =================================================
    # VISTA: AUDITORÍA ADMINISTRATIVA
    # =================================================
    def mostrar_auditoria(self):
        """
        Carga la vista administrativa de auditoría.
        """

        self._registrar_vista("mostrar_auditoria")
        logger.info("Cargando vista: Auditoría")
        self.limpiar_contenido()

        self.cambiar_titulo(
            "Auditoría",
            "Consulta de movimientos registrados en el sistema."
        )

        from views.auditoria_view import mostrar_auditoria

        mostrar_auditoria(
            parent=self.content,
            app=self.app
        )

    # =================================================
    # VISTA TEMPORAL: EN CONSTRUCCIÓN
    # =================================================
    def mostrar_en_construccion(self):
        """
        Muestra una pantalla temporal para módulos pendientes.

        Esta vista evita botones muertos y permite liberar
        nuevas secciones de forma progresiva.
        """

        self._registrar_vista("mostrar_en_construccion")
        logger.info("Cargando vista temporal: Módulo en construcción")
        self.limpiar_contenido()

        self.cambiar_titulo(
            "Módulo en construcción",
            "Esta sección será desarrollada en una siguiente etapa."
        )

        card = ctk.CTkFrame(
            self.content,
            width=900,
            height=420,
            fg_color=WHITE,
            corner_radius=18
        )
        card.pack(pady=50)
        card.pack_propagate(False)

        ctk.CTkLabel(
            card,
            text="Módulo en construcción",
            font=("Montserrat", 24, "bold"),
            text_color="#0F172A"
        ).pack(pady=(120, 10))

        ctk.CTkLabel(
            card,
            text="Esta sección todavía no está liberada. Las funciones operativas principales ya están disponibles desde el menú lateral.",
            font=("Montserrat", 14),
            text_color="#475569",
            wraplength=650
        ).pack()
