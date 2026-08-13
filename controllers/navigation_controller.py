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
from tkinter import messagebox

from app_context import obtener_usuario_actual
from security.permissions import (
    puede_administrar_clientes,
    puede_administrar_usuarios,
    puede_consultar_procesos,
    puede_convertir_levantamiento_a_orden,
    puede_entrar_inicio_aco,
    puede_generar_levantamiento,
    puede_generar_bitacora,
    puede_ver_auditoria,
    puede_ver_reportes,
    puede_ver_bitacoras_operativas,
)

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

    def _verificar_permiso(self, validador, mensaje):
        """Aplica defensa en profundidad antes de cargar una vista."""
        usuario = obtener_usuario_actual()
        if validador(usuario):
            return True
        logger.warning(
            "Acceso denegado a vista para usuario=%s usu_tipo=%s",
            usuario.get("usuario"),
            usuario.get("usu_tipo"),
        )
        messagebox.showerror("Acceso denegado", mensaje)
        return False

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

        if not puede_entrar_inicio_aco(obtener_usuario_actual()):
            self.mostrar_selector_levantamiento()
            return

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

        if not self._verificar_permiso(
            puede_generar_levantamiento,
            "Tu nivel de usuario no tiene permiso para agregar levantamientos.",
        ):
            return

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
        No genera registros nuevos; la creación del levantamiento se realiza desde su flujo de captura.
        """

        if not self._verificar_permiso(
            puede_consultar_procesos,
            "Tu nivel de usuario no tiene permiso para consultar esta sección.",
        ):
            return


        self._registrar_vista("mostrar_admin_levantamientos")
        logger.info("Cargando vista administrativa: Levantamientos")
        self.limpiar_contenido()
        if puede_convertir_levantamiento_a_orden(obtener_usuario_actual()):
            self.cambiar_titulo(
                "Levantamientos",
                "Busca, edita y convierte levantamientos aceptados en órdenes de trabajo."
            )
            from views.orden_servicio_conversion_view import mostrar_conversion_orden_servicio
            mostrar_conversion_orden_servicio(parent=self.content, app=self.app)
            return

        self.cambiar_titulo(
            "Levantamientos",
            "Busca y consulta levantamientos registrados."
        )
        from views.admin_procesos_view import mostrar_admin_procesos
        from services.levantamientos_service import obtener_levantamientos, buscar_levantamiento_por_folio, buscar_levantamientos

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
                "buscar": buscar_levantamientos,
                "buscar_por_folio": buscar_levantamiento_por_folio,
            }
        )

    def mostrar_admin_ordenes_servicio(self):
        """Administra Órdenes de Servicio y permite cerrar la OT de origen."""
        if not self._verificar_permiso(
            puede_consultar_procesos,
            "Tu nivel de usuario no tiene permiso para consultar esta sección.",
        ):
            return

        self._registrar_vista("mostrar_admin_ordenes_servicio")
        logger.info("Cargando vista administrativa: Órdenes de Servicio")
        self.limpiar_contenido()
        self.cambiar_titulo(
            "Órdenes de Servicio",
            "Etapa final del flujo: revisa la OS y finaliza la Orden de Trabajo cuando el servicio esté al 100%.",
        )
        from views.admin_operational_editor_view import mostrar_admin_operational_editor
        from services.ordenes_servicio_service import (
            obtener_ordenes_servicio, buscar_ordenes_servicio,
            actualizar_orden_servicio, finalizar_servicio_desde_os,
        )
        from tkinter import messagebox

        pdf_config = {
            "titulo": "Órdenes de Servicio", "prefijo": "OS", "campo_folio": "os_folio",
            "campos_aco": ["os_aco_numero"], "campos_cliente": ["os_cliente"],
            "campos_estatus": ["os_estatus"], "campos_fecha": ["os_fecha", "fecha_registro"],
            "campos_descripcion": ["os_descripcion", "os_actividades"],
        }

        def finalizar_ot(record, status, refresh):
            if not puede_convertir_levantamiento_a_orden(obtener_usuario_actual()):
                messagebox.showerror("Acceso denegado", "Solo el personal Administrativo puede finalizar el servicio desde la Orden de Servicio.")
                return
            if int(record.get("os_estatus") or 0) == 3:
                messagebox.showinfo("Servicio finalizado", "La Orden de Servicio seleccionada ya se encuentra finalizada.")
                return
            folio_ot = str(record.get("os_folio_ot") or "").strip()
            if not messagebox.askyesno(
                "Finalizar servicio",
                f"¿Confirmas que el servicio llegó al 100% y deseas finalizar {folio_ot or 'la OT asociada'}?",
            ):
                return
            try:
                resultado = finalizar_servicio_desde_os(record, obtener_usuario_actual())
            except Exception as exc:
                messagebox.showerror("No se pudo finalizar", str(exc))
                return
            if resultado:
                status.configure(text="Servicio finalizado correctamente al 100%.", text_color="#15803D")
                messagebox.showinfo("Servicio finalizado", f"{folio_ot or 'La Orden de Trabajo'} quedó finalizada correctamente.")
                refresh()

        mostrar_admin_operational_editor(
            parent=self.content, app=self.app,
            config={
                "titulo": "Órdenes de Servicio", "titulo_singular": "Orden de Servicio", "articulo": "una", "prefijo": "OS",
                "subtitulo": "Busca una OS, revisa sus datos y finaliza la OT de origen únicamente cuando el servicio esté al 100%.",
                "campo_folio": "os_folio", "campos_aco": ["os_aco_numero"], "campos_cliente": ["os_cliente"],
                "campos_estatus": ["os_estatus"], "campos_fecha": ["os_fecha", "fecha_registro"],
                "obtener_todos": obtener_ordenes_servicio, "buscar": buscar_ordenes_servicio,
                "actualizar": actualizar_orden_servicio, "id_field": "id_orden",
                "pdf_config": pdf_config, "pdf_text": "👁 PDF Orden de Servicio",
                "accion_text": "✓ Finalizar OT", "accion": finalizar_ot,
                "campos": [
                    {"key":"os_folio","label":"Folio OS","readonly":True},
                    {"key":"os_folio_ot","label":"OT de origen","readonly":True},
                    {"key":"os_folio_bitacora","label":"Bitácora asociada","readonly":True},
                    {"key":"os_aco_numero","label":"ACO"}, {"key":"os_fecha","label":"Fecha"},
                    {"key":"os_cliente","label":"Cliente"}, {"key":"os_contacto","label":"Contacto"},
                    {"key":"os_sucursal","label":"Sucursal / ubicación"}, {"key":"os_supervisor","label":"Supervisor"},
                    {"key":"os_tecnico","label":"Técnico"}, {"key":"os_estatus","label":"Estatus","integer":True,"readonly":True},
                    {"key":"os_descripcion","label":"Descripción","kind":"textbox","height":110},
                    {"key":"os_actividades","label":"Actividades / cierre","kind":"textbox","height":110},
                    {"key":"os_observaciones","label":"Observaciones","kind":"textbox","height":95},
                ],
            },
        )

    def mostrar_admin_ordenes_trabajo(self):
        """
        Carga la administración/consulta de órdenes de trabajo.
        """

        if not self._verificar_permiso(
            puede_consultar_procesos,
            "Tu nivel de usuario no tiene permiso para consultar esta sección.",
        ):
            return


        self._registrar_vista("mostrar_admin_ordenes_trabajo")
        logger.info("Cargando vista administrativa: Órdenes de Trabajo")
        self.limpiar_contenido()
        self.cambiar_titulo(
            "Órdenes de Trabajo",
            "Busca y consulta órdenes de trabajo registradas."
        )
        from views.admin_operational_editor_view import mostrar_admin_operational_editor
        from services.ordenes_trabajo_service import (
            obtener_ordenes_trabajo, buscar_orden_trabajo_por_folio, buscar_ordenes_trabajo, actualizar_orden_trabajo
        )
        from services.ordenes_servicio_service import convertir_orden_trabajo_a_servicio

        pdf_config_ot = {
            "titulo": "Órdenes de Trabajo", "prefijo": "OT", "campo_folio": "ot_folio",
            "campos_aco": ["ot_aco_numero", "aco_numero"],
            "campos_cliente": ["ot_cliente", "aco_cliente", "cliente"],
            "campos_estatus": ["ot_estatus", "estatus"],
            "campos_fecha": ["ot_fecha", "fecha_registro", "created_at"],
            "campos_descripcion": ["ot_descripcion", "ot_asunto", "descripcion"],
        }

        def convertir_ot_a_os(record, status, refresh):
            if not puede_convertir_levantamiento_a_orden(obtener_usuario_actual()):
                messagebox.showerror("Acceso denegado", "Solo el personal Administrativo puede convertir una OT en Orden de Servicio.")
                return
            try:
                resultado = convertir_orden_trabajo_a_servicio(record, obtener_usuario_actual())
            except Exception as exc:
                messagebox.showerror("No se pudo convertir", str(exc))
                return
            folio = resultado[0].get("os_folio", "OS") if resultado else "OS"
            status.configure(text=f"Orden de Servicio creada: {folio}", text_color="#15803D")
            messagebox.showinfo("Orden de Servicio creada", f"La Orden de Trabajo se convirtió correctamente en {folio}.")
            refresh()

        mostrar_admin_operational_editor(
            parent=self.content, app=self.app,
            config={
                "titulo": "Órdenes de Trabajo", "titulo_singular": "Orden de Trabajo", "articulo": "una", "prefijo": "OT",
                "subtitulo": "Busca una OT, revísala y conviértela en Orden de Servicio cuando su Bitácora asociada haya llegado al 100%.",
                "campo_folio": "ot_folio", "campos_aco": ["ot_aco_numero"], "campos_cliente": ["ot_cliente"],
                "campos_estatus": ["ot_estatus"], "campos_fecha": ["ot_fecha", "fecha_registro", "created_at"],
                "obtener_todos": obtener_ordenes_trabajo, "buscar": buscar_ordenes_trabajo,
                "actualizar": actualizar_orden_trabajo, "id_field": "ot_id",
                "pdf_config": pdf_config_ot, "pdf_text": "👁 PDF Orden de Trabajo",
                "accion_text": "✓ Convertir a OS", "accion": convertir_ot_a_os,
                "campos": [
                    {"key":"ot_folio","label":"Folio OT","readonly":True},
                    {"key":"ot_folio_levantamiento","label":"Levantamiento origen","readonly":True},
                    {"key":"ot_aco_numero","label":"ACO"}, {"key":"ot_fecha","label":"Fecha"},
                    {"key":"ot_cliente","label":"Cliente"}, {"key":"ot_contacto","label":"Contacto"},
                    {"key":"ot_sucursal","label":"Sucursal / ubicación"}, {"key":"ot_supervisor","label":"Supervisor"},
                    {"key":"ot_esi","label":"ESI / responsable"}, {"key":"ot_numero_dias","label":"Número de días"},
                    {"key":"ot_numero_personas","label":"Número de personas"}, {"key":"ot_asunto","label":"Asunto"},
                    {"key":"ot_estatus","label":"Estatus","integer":True,"readonly":True},
                    {"key":"ot_descripcion","label":"Descripción operativa","kind":"textbox","height":105},
                    {"key":"ot_partidas_json","label":"Partidas / conceptos JSON","kind":"textbox","height":170,"json":True},
                ],
            }
        )

    def mostrar_admin_bitacoras(self):
        """
        Carga la administración/consulta de bitácoras operativas.
        """

        if not self._verificar_permiso(
            puede_ver_bitacoras_operativas,
            "Tu nivel de usuario no tiene permiso para consultar Bitácoras Operativas.",
        ):
            return


        self._registrar_vista("mostrar_admin_bitacoras")
        logger.info("Cargando vista administrativa: Bitácoras Operativas")
        self.limpiar_contenido()
        self.cambiar_titulo(
            "Bitácoras Operativas",
            "Busca y consulta bitácoras operativas registradas."
        )
        from views.admin_operational_editor_view import mostrar_admin_operational_editor
        from services.bitacoras_service import obtener_bitacoras, buscar_bitacoras, actualizar_bitacora
        from tkinter import messagebox

        pdf_config_bit = {
            "titulo": "Bitácoras Operativas", "prefijo": "BIT", "campo_folio": "bit_folio",
            "campos_aco": ["bit_aco_numero", "aco_numero"],
            "campos_cliente": ["bit_cliente", "aco_cliente", "cliente"],
            "campos_estatus": ["bit_estatus", "estatus"],
            "campos_fecha": ["bit_fecha", "fecha_registro", "created_at"],
            "campos_descripcion": ["bit_descripcion", "bit_avance", "descripcion"],
        }

        from services.ordenes_trabajo_service import buscar_ordenes_trabajo_por_aco
        from services.bitacoras_service import asignar_bitacora_a_ot

        def asignar_a_ot(record, status, refresh):
            if record.get("bit_ot_folio"):
                messagebox.showinfo("Bitácora asignada", f"Esta Bitácora ya está ligada a {record.get('bit_ot_folio')}.")
                return
            numero_aco = str(record.get("bit_aco_numero") or "").strip()
            if not numero_aco:
                messagebox.showwarning("ACO requerido", "La Bitácora no tiene ACO asociado y no es posible localizar su OT.")
                return
            ordenes = buscar_ordenes_trabajo_por_aco(numero_aco)
            candidatas = [o for o in ordenes if int(o.get("ot_estatus") or 0) != 3]
            if not candidatas:
                messagebox.showwarning("OT no encontrada", f"No existe una Orden de Trabajo abierta para el ACO {numero_aco}.")
                return
            # La OT más reciente y abierta del mismo ACO es la relación operativa vigente.
            ot = candidatas[0]
            if not messagebox.askyesno("Asignar a OT", f"¿Ligar {record.get('bit_folio')} con {ot.get('ot_folio')}?"):
                return
            try:
                resultado = asignar_bitacora_a_ot(record.get("id_bitacora"), ot)
            except Exception as exc:
                messagebox.showerror("No se pudo asignar", str(exc))
                return
            if resultado:
                record["ot_id"] = ot.get("ot_id")
                record["bit_ot_folio"] = ot.get("ot_folio")
                status.configure(text=f"Bitácora asignada a {ot.get('ot_folio')}.", text_color="#15803D")
                messagebox.showinfo("Bitácora asignada", f"La Bitácora quedó ligada automáticamente a {ot.get('ot_folio')}.")
                refresh()

        mostrar_admin_operational_editor(
            parent=self.content, app=self.app,
            config={
                "titulo": "Bitácoras Operativas", "titulo_singular": "Bitácora Operativa", "articulo": "una", "prefijo": "BIT",
                "subtitulo": "Busca una Bitácora, revisa sus datos y asígnala a la Orden de Trabajo correspondiente.",
                "campo_folio": "bit_folio", "campos_aco": ["bit_aco_numero"], "campos_cliente": ["bit_cliente"],
                "campos_estatus": ["bit_estatus"], "campos_fecha": ["bit_fecha", "fecha_registro"],
                "obtener_todos": obtener_bitacoras, "buscar": buscar_bitacoras,
                "actualizar": actualizar_bitacora, "id_field": "id_bitacora",
                "pdf_config": pdf_config_bit, "pdf_text": "👁 PDF Bitácora",
                "accion_text": "✓ Asignar a OT", "accion": asignar_a_ot,
                "campos": [
                    {"key":"bit_folio","label":"Folio Bitácora","readonly":True},
                    {"key":"bit_ot_folio","label":"Orden de Trabajo asignada","readonly":True},
                    {"key":"bit_aco_numero","label":"ACO"}, {"key":"bit_fecha","label":"Fecha"},
                    {"key":"bit_cliente","label":"Cliente"}, {"key":"bit_direccion_sucursal","label":"Dirección / sucursal"},
                    {"key":"bit_encargado_proyecto_axia","label":"Encargado del proyecto AXIA"}, {"key":"bit_tecnico_sitio","label":"Técnico en sitio"},
                    {"key":"bit_hora_llegada","label":"Hora de llegada"}, {"key":"bit_hora_salida","label":"Hora de salida"},
                    {"key":"bit_estatus","label":"Estatus","integer":True,"readonly":True}, {"key":"bit_porcentaje_avance","label":"Porcentaje de avance","integer":True},
                    {"key":"bit_observaciones","label":"Observaciones","kind":"textbox","height":95},
                    {"key":"bit_descripcion","label":"Descripción","kind":"textbox","height":110},
                ],
            }
        )


    def mostrar_admin_obras_civiles(self):
        """
        Carga la administración/consulta de obras civiles.
        """

        if not self._verificar_permiso(
            puede_consultar_procesos,
            "Tu nivel de usuario no tiene permiso para consultar esta sección.",
        ):
            return


        self._registrar_vista("mostrar_admin_obras_civiles")
        logger.info("Cargando vista administrativa: Obras Civiles")
        self.limpiar_contenido()
        self.cambiar_titulo(
            "Obras Civiles",
            "Busca y consulta proyectos ejecutivos de obra civil."
        )
        from views.admin_procesos_view import mostrar_admin_procesos
        from services.obras_civiles_service import obtener_obras_civiles, buscar_obra_civil_por_folio, buscar_obras_civiles

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
                "buscar": buscar_obras_civiles,
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

        if not self._verificar_permiso(
            puede_ver_reportes,
            "Tu nivel de usuario no tiene permiso para consultar reportes.",
        ):
            return


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

        if not self._verificar_permiso(
            puede_administrar_usuarios,
            "Tu nivel de usuario no tiene permiso para administrar usuarios.",
        ):
            return


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

        if not self._verificar_permiso(
            puede_administrar_clientes,
            "Tu nivel de usuario no tiene permiso para administrar clientes.",
        ):
            return


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
        Carga el formulario operativo para registrar una Bitácora de Avance.
        """

        if not self._verificar_permiso(
            puede_generar_bitacora,
            "Tu nivel de usuario no tiene permiso para registrar Bitácoras Operativas.",
        ):
            return

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

        if not self._verificar_permiso(
            puede_ver_auditoria,
            "La auditoría de accesos y movimientos está reservada al Administrador.",
        ):
            return


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
        card.pack(pady=25)
        card.pack_propagate(False)

        ctk.CTkLabel(
            card,
            text="Módulo en construcción",
            font=("Montserrat", 22, "bold"),
            text_color="#0F172A"
        ).pack(pady=(60, 5))

        ctk.CTkLabel(
            card,
            text="Esta sección todavía no está liberada. Las funciones operativas principales ya están disponibles desde el menú lateral.",
            font=("Montserrat", 12),
            text_color="#475569",
            wraplength=650
        ).pack()
