# =====================================================
# IMPORTACIÓN DE LIBRERÍAS
# =====================================================

import customtkinter as ctk
from ui.form_fields import AxiaEntry, AxiaTextbox
import os
from tkinter import messagebox

from ui.theme import aplicar_fuente_tk, aplicar_estilo_ventana
from utils import centrar_ventana

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
from ui.keyboard_navigation import install_keyboard_navigation
from ui.manual_scroll_policy import install_manual_scroll_only
from ui.responsive import install_responsive_shell

from ui.colors import (
    PRIMARY,
    PRIMARY_50,
    PRIMARY_500,
    SECONDARY,
    WHITE,
    CONTENT_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    SURFACE,
    SURFACE_SOFT,
    DIVIDER,
    RING,
    CARD_BORDER,
)
from ui.fonts import (
    FONT_FAMILY,
    TITLE_LG,
    TITLE_MD,
    TEXT_MD,
    TEXT_SM,
    TEXT_XS,
    BUTTON_FONT,
)
from core.version import APP_VERSION

# =====================================================
# IMPORTACIÓN DE LOGGER CENTRAL
# =====================================================

from core.logger import configurar_logger
from core.error_reporting import show_operation_error
from core.performance import mark, measure

logger = configurar_logger(__name__)


# =====================================================
# CLASE PRINCIPAL: AxiaApp
# =====================================================
class AxiaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        aplicar_estilo_ventana(self, min_width=1024, min_height=640)

        logger.info("Inicializando ventana principal AXIA.")
        self.logout_requested = False

        # =================================================
        # CONFIGURACIÓN GENERAL DE VENTANA
        # =================================================
        self.title("Sistema AXIA")
        configurar_icono_ventana(self)
        self.after(100, self.maximizar_ventana)
        self.resizable(True, True)
        self.minsize(1024, 640)
        self.configure(fg_color=CONTENT_BG)
        install_manual_scroll_only(self)
        install_keyboard_navigation(self)

        # =================================================
        # USUARIO ACTIVO
        # =================================================
        self.usuario_activo = obtener_usuario_actual()

        self._proveedor_borrador = None
        self._tipo_borrador = None
        self._ultimo_evento_usuario_ms = 0
        try:
            minutos = int(os.getenv("AXIA_IDLE_TIMEOUT_MINUTES", "20"))
        except (TypeError, ValueError):
            minutos = 20
        self._inactividad_ms = max(1, minutos) * 60 * 1000

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
        mark("app: shell principal construido")
        self.after_idle(self._cargar_vista_inicial)
        self.protocol("WM_DELETE_WINDOW", self.salir_aplicacion)
        self._instalar_control_inactividad()
        self._instalar_autoguardado_borrador()
        self.after(900, self._ofrecer_borrador_pendiente)
        self.after(1200, self._mostrar_estado_actualizacion_anterior)
        self.after(1800, self._comprobar_actualizacion_axia)

    def report_callback_exception(self, exc, value, traceback_obj):
        try:
            import tkinter as tk

            mensaje = str(value or "")
            es_widget_destruido = (
                isinstance(value, tk.TclError)
                and "invalid command name" in mensaje.lower()
                and (".!ctk" in mensaje.lower() or ".!label" in mensaje.lower())
            )
            if es_widget_destruido:
                return
        except Exception:
            pass

        show_operation_error(
            "Error inesperado de AXIA",
            "Ejecutar una acción de la interfaz",
            value,
            parent=self,
        )

    def _cargar_vista_inicial(self):
        with measure("app: vista inicial por rol"):
            from security.permissions import obtener_tipo_usuario, COMPRAS, ALMACEN, RECURSOS_HUMANOS
            tipo = obtener_tipo_usuario(self.usuario_activo)
            if tipo == COMPRAS:
                self.navigation.mostrar_compras()
            elif tipo == ALMACEN:
                self.navigation.mostrar_almacen()
            elif tipo == RECURSOS_HUMANOS:
                self.navigation.mostrar_usuarios()
            else:
                self.navigation.mostrar_inicio_aco()

    # =====================================================
    # MÉTODO: maximizar_ventana()
    # =====================================================
    def maximizar_ventana(self):
        try:
            self.state("zoomed")
        except Exception:
            logger.exception("No fue posible usar state('zoomed'). Se usará fullscreen.")
            self.attributes("-fullscreen", True)

    # =====================================================
    # MÉTODO: crear_layout_base()
    # =====================================================
    def crear_layout_base(self):
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

        self.main_area.grid_rowconfigure(0, weight=0)
        self.main_area.grid_rowconfigure(1, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        self.crear_header()
        self.crear_area_contenido()

    # =====================================================
    # MÉTODO: crear_header()
    # =====================================================
    def crear_header(self):
        self.header_outer = ctk.CTkFrame(
            self.main_area,
            fg_color=CONTENT_BG,
            corner_radius=0,
        )
        self.header_outer.grid(row=0, column=0, sticky="nsew", padx=14, pady=(8, 2))

        self.header = ctk.CTkFrame(
            self.header_outer,
            corner_radius=16,
            fg_color=SURFACE,
            border_width=1,
            border_color=CARD_BORDER,
        )
        self.header.pack(fill="both", expand=True, padx=0, pady=0)

        accent_strip = ctk.CTkFrame(
            self.header,
            height=3,
            corner_radius=4,
            fg_color=PRIMARY,
            border_width=0,
        )
        accent_strip.pack(fill="x", padx=16, pady=(8, 0))

        accent_dot = ctk.CTkFrame(
            accent_strip,
            width=4,
            height=4,
            corner_radius=100,
            fg_color=WHITE,
            border_width=0,
        )
        accent_dot.place(relx=0.5, rely=0.5, anchor="center")

        header_body = ctk.CTkFrame(self.header, fg_color="transparent")
        header_body.pack(fill="x", padx=18, pady=(6, 6))

        left_block = ctk.CTkFrame(header_body, fg_color="transparent")
        left_block.pack(side="right", fill="x", expand=True, padx=(14, 0))

        self.label_titulo = ctk.CTkLabel(
            left_block,
            text="Sistema AXIA",
            font=TITLE_LG,
            text_color=TEXT_PRIMARY,
            anchor="e",
            justify="right",
        )
        self.label_titulo.pack(side="right", anchor="e", padx=(0, 16))

        self.label_subtitulo = ctk.CTkLabel(
            left_block,
            text="Gestión operativa centralizada",
            font=TEXT_SM,
            text_color=TEXT_SECONDARY,
            anchor="e",
            justify="right",
        )
        right_block = ctk.CTkFrame(header_body, fg_color="transparent")
        right_block.pack(side="left", fill="x")
        self.header_controls_host = right_block

        status_card = ctk.CTkFrame(
            right_block,
            corner_radius=12,
            fg_color=PRIMARY_50,
            border_width=1,
            border_color=RING,
        )
        status_card.pack(side="left", pady=0)

        self.header_status_card = status_card

        status_row = ctk.CTkFrame(status_card, fg_color="transparent")
        status_row.pack(fill="x", padx=10, pady=4)

        status_dot = ctk.CTkFrame(
            status_row,
            width=8,
            height=8,
            corner_radius=100,
            fg_color=PRIMARY,
            border_width=0,
        )
        status_dot.pack(side="left", padx=(0, 6), pady=2)

        status_label = ctk.CTkLabel(
            status_row,
            text="Conectado a Supabase",
            text_color=PRIMARY,
            font=(FONT_FAMILY, 11),
            anchor="w",
        )
        status_label.pack(side="left", fill="x", expand=True)

        fecha_texto = self._fecha_hora_es()
        info_card = ctk.CTkFrame(
            right_block,
            corner_radius=12,
            fg_color=SURFACE_SOFT,
            border_width=1,
            border_color=DIVIDER,
        )
        info_card.pack(side="left", padx=(10, 0), pady=0)
        info_row = ctk.CTkFrame(info_card, fg_color="transparent")
        info_row.pack(fill="x", padx=10, pady=4)

        calendar_label = ctk.CTkLabel(
            info_row,
            text="📅  " + fecha_texto,
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 11),
            anchor="w",
        )
        calendar_label.pack(side="left", fill="x", expand=True)
        self.header_calendar_label = calendar_label
        self.after(30000, self._actualizar_reloj_header)

        version_tag = ctk.CTkLabel(
            info_row,
            text="v" + APP_VERSION,
            text_color=TEXT_MUTED,
            font=(FONT_FAMILY, 9),
        )
        version_tag.pack(side="right", padx=(15, 0))

    @staticmethod
    def _fecha_hora_es():
        from datetime import datetime
        now = datetime.now()
        dias = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
        meses = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
        return f"{dias[now.weekday()].capitalize()}, {now.day} de {meses[now.month - 1]} de {now.year} · {now:%H:%M}"

    def _actualizar_reloj_header(self):
        try:
            if self.header_calendar_label.winfo_exists():
                self.header_calendar_label.configure(text="📅  " + self._fecha_hora_es())
                self.after(30000, self._actualizar_reloj_header)
        except Exception:
            pass

    # =====================================================
    # MÉTODO: crear_area_contenido()
    # =====================================================
    def crear_area_contenido(self):
        self.content_outer = ctk.CTkFrame(
            self.main_area,
            fg_color=CONTENT_BG,
            corner_radius=0,
        )
        self.content_outer.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=14,
            pady=(0, 12),
        )
        self.content_outer.grid_rowconfigure(0, weight=1)
        self.content_outer.grid_columnconfigure(0, weight=1)

        self.content_card = ctk.CTkFrame(
            self.content_outer,
            corner_radius=16,
            fg_color=SURFACE,
            border_width=1,
            border_color=CARD_BORDER,
        )
        self.content_card.grid(row=0, column=0, sticky="nsew")
        self.content_card.grid_rowconfigure(0, weight=1)
        self.content_card.grid_columnconfigure(0, weight=1)

        self.content_inner = ctk.CTkFrame(
            self.content_card,
            fg_color="transparent",
            corner_radius=14,
        )
        self.content_inner.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        self.content_inner.grid_rowconfigure(0, weight=1)
        self.content_inner.grid_columnconfigure(0, weight=1)

        self.content = ctk.CTkFrame(
            self.content_inner,
            fg_color="transparent",
            corner_radius=12,
        )
        self.content.grid(row=0, column=0, sticky="nsew")

    # =====================================================
    # MÉTODO: crear_sidebar_principal()
    # =====================================================
    def crear_sidebar_principal(self):
        callbacks = {
            "inicio_aco": self.navigation.mostrar_inicio_aco,

            "levantamiento": self.navigation.mostrar_selector_levantamiento,
            "orden_servicio": self.navigation.mostrar_orden_servicio,
            "orden_trabajo": self.navigation.mostrar_orden_trabajo,
            "bitacora_avance": self.navigation.mostrar_bitacora_avance,

            "admin_levantamientos": self.navigation.mostrar_admin_levantamientos,
            "mis_levantamientos": lambda: self.navigation.mostrar_mis_documentos("levantamientos"),
            "mis_bitacoras": lambda: self.navigation.mostrar_mis_documentos("bitacoras"),
            "mis_ordenes_servicio": lambda: self.navigation.mostrar_mis_documentos("ordenes_servicio"),
            "cotizaciones": self.navigation.mostrar_cotizaciones,
            "compras": self.navigation.mostrar_compras,
            "autorizacion_dg": self.navigation.mostrar_autorizacion_cotizaciones_dg,
            "almacen": self.navigation.mostrar_almacen,
            "admin_ordenes_servicio": self.navigation.mostrar_admin_ordenes_servicio,
            "admin_ordenes_trabajo": self.navigation.mostrar_admin_ordenes_trabajo,
            "admin_bitacoras": self.navigation.mostrar_admin_bitacoras,
            "admin_obras_civiles": self.navigation.mostrar_admin_obras_civiles,

            "reportes": self.navigation.mostrar_reportes,
            "reportador_fotografico": self.navigation.mostrar_reportador_fotografico,
            "direccion_general": self.navigation.mostrar_direccion_general,
            "usuarios": self.navigation.mostrar_usuarios,
            "clientes": self.navigation.mostrar_clientes,
            "admin_registros": self.navigation.mostrar_admin_registros,
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
        install_responsive_shell(self, self.sidebar)
        self._sidebar_visible = True
        self._sidebar_toggle = ctk.CTkButton(
            self.header_controls_host, text="☰  Ocultar menú", width=150,
            command=self.alternar_sidebar, fg_color="#123C58",
            hover_color="#17648A", corner_radius=9,
        )
        self._sidebar_toggle.pack(
            side="left", before=self.header_status_card, padx=(0, 10), pady=0
        )

    def alternar_sidebar(self):
        self._sidebar_visible = not self._sidebar_visible
        if self._sidebar_visible:
            self.sidebar.grid(row=0, column=0, sticky="ns")
            self._sidebar_toggle.configure(text="☰  Ocultar menú")
        else:
            self.sidebar.grid_remove()
            self._sidebar_toggle.configure(text="☰  Mostrar menú")
        self.layout.update_idletasks()


    # =====================================================
    # MÉTODOS DE COMPATIBILIDAD TEMPORAL
    # =====================================================
    def _auditar_navegacion(self, destino):
        try:
            from services.movimientos_service import registrar_movimiento_seguro
            registrar_movimiento_seguro(
                modulo="NAVEGACION", accion="ABRIR_VISTA",
                descripcion=f"El usuario abrió la vista {destino}",
                registro_afectado=destino,
            )
        except Exception:
            pass

    def volver_atras(self):
        self._auditar_navegacion("VOLVER_ATRAS")
        self.navigation.volver_atras()

    def mostrar_vista_inicio_aco(self):
        self._auditar_navegacion("Inicio ACO")
        self.navigation.mostrar_inicio_aco()

    def mostrar_vista_inicio_aco_validado(self, aco=None):
        self._auditar_navegacion("Inicio ACO validado")
        self.navigation.mostrar_inicio_aco_validado(aco)

    def mostrar_vista_en_construccion(self):
        self._auditar_navegacion("En construcción")
        self.navigation.mostrar_en_construccion()

    def mostrar_vista_selector_levantamiento(self, aco=None):
        self._auditar_navegacion("Selector de Levantamiento")
        self.navigation.mostrar_selector_levantamiento(aco=aco)

    def mostrar_vista_levantamiento(self, aco=None, tipo_levantamiento=None):
        self._auditar_navegacion(f"Levantamiento: {tipo_levantamiento or 'Selector'}")
        if tipo_levantamiento is None:
            self.navigation.mostrar_selector_levantamiento(aco=aco)
        else:
            self.navigation.mostrar_levantamiento(aco=aco, tipo_levantamiento=tipo_levantamiento)

    def mostrar_vista_orden_servicio(self, aco=None):
        self._auditar_navegacion("Orden de Servicio")
        self.navigation.mostrar_orden_servicio(aco=aco)

    def mostrar_vista_orden_trabajo(self, aco=None):
        self._auditar_navegacion("Orden de Trabajo")
        self.navigation.mostrar_orden_trabajo(aco=aco)

    def mostrar_vista_reportes(self):
        self._auditar_navegacion("Reportes")
        self.navigation.mostrar_reportes()

    def mostrar_vista_admin_levantamientos(self):
        self._auditar_navegacion("Administración Levantamientos")
        self.navigation.mostrar_admin_levantamientos()

    def mostrar_vista_cotizaciones(self):
        self._auditar_navegacion("Cotizaciones")
        self.navigation.mostrar_cotizaciones()

    def mostrar_vista_admin_ordenes_servicio(self):
        self._auditar_navegacion("Administración Órdenes de Servicio")
        self.navigation.mostrar_admin_ordenes_servicio()

    def mostrar_vista_admin_ordenes_trabajo(self):
        self._auditar_navegacion("Administración Órdenes de Trabajo")
        self.navigation.mostrar_admin_ordenes_trabajo()

    def mostrar_vista_admin_bitacoras(self):
        self._auditar_navegacion("Administración Bitácoras")
        self.navigation.mostrar_admin_bitacoras()

    def mostrar_vista_usuarios(self):
        self._auditar_navegacion("Usuarios")
        self.navigation.mostrar_usuarios()

    def mostrar_vista_clientes(self):
        self._auditar_navegacion("Clientes")
        self.navigation.mostrar_clientes()

    def mostrar_vista_auditoria(self):
        self._auditar_navegacion("Auditoría")
        self.navigation.mostrar_auditoria()

    def mostrar_vista_bitacora_avance(self, aco=None):
        self._auditar_navegacion("Bitácora de Avance")
        self.navigation.mostrar_bitacora_avance(aco=aco)

    def mostrar_vista_obra_civil(self, aco=None):
        self._auditar_navegacion("Obra Civil")
        self.navigation.mostrar_obra_civil(aco=aco)

    def mostrar_vista_admin_obras_civiles(self):
        self._auditar_navegacion("Administración Obra Civil")
        self.navigation.mostrar_admin_obras_civiles()

    def mostrar_vista_mi_bitacora(self):
        self._auditar_navegacion("Mi Bitácora")
        self.navigation.mostrar_mi_usuario()

    def mostrar_vista_mi_usuario(self):
        self._auditar_navegacion("Mi Usuario")
        self.navigation.mostrar_mi_usuario()

    def registrar_proveedor_borrador_levantamiento(self, tipo_levantamiento, proveedor):
        self._tipo_borrador = str(tipo_levantamiento or "")
        self._proveedor_borrador = proveedor if callable(proveedor) else None

    def limpiar_proveedor_borrador_levantamiento(self):
        self._tipo_borrador = None
        self._proveedor_borrador = None

    def _guardar_borrador_actual(self):
        if not callable(self._proveedor_borrador):
            return False
        try:
            datos = self._proveedor_borrador() or {}
            significativos = any(str(datos.get(k) or "").strip() for k in (
                "lev_cliente", "lev_contacto", "lev_observaciones", "lev_descripcion",
                "lev_telefono", "lev_correo", "lev_ubicacion"
            ))
            if not significativos:
                detalle = str(datos.get("lev_detalle_tecnico_json") or "").strip()
                significativos = bool(detalle and detalle not in ("{}", "[]"))
            if not significativos:
                return False
            from services.levantamiento_borradores_service import guardar_borrador
            guardar_borrador(self.usuario_activo, self._tipo_borrador, datos)
            return True
        except Exception:
            logger.exception("No fue posible guardar el borrador temporal del levantamiento.")
            return False

    def _instalar_autoguardado_borrador(self):
        def ciclo():
            try:
                if self.winfo_exists():
                    self._guardar_borrador_actual()
                    self.after(45000, ciclo)
            except Exception:
                logger.debug("Autoguardado periódico omitido.", exc_info=True)
        self.after(45000, ciclo)

    def _instalar_control_inactividad(self):
        import time
        self._ultimo_evento_usuario_ms = int(time.monotonic() * 1000)

        def actividad(_event=None):
            self._ultimo_evento_usuario_ms = int(time.monotonic() * 1000)

        for secuencia in ("<KeyPress>", "<ButtonPress>", "<Motion>", "<MouseWheel>"):
            try:
                self.bind_all(secuencia, actividad, add="+")
            except Exception:
                pass

        def revisar():
            if not self.winfo_exists():
                return
            ahora = int(time.monotonic() * 1000)
            if ahora - self._ultimo_evento_usuario_ms >= self._inactividad_ms:
                guardado = self._guardar_borrador_actual()
                try:
                    from services.movimientos_service import registrar_movimiento_seguro
                    registrar_movimiento_seguro(
                        modulo="Login", accion="CIERRE_INACTIVIDAD",
                        descripcion="Sesión cerrada automáticamente por inactividad" + ("; borrador de levantamiento guardado" if guardado else ""),
                    )
                except Exception:
                    pass
                self.cerrar_sesion(motivo="inactividad", mostrar_aviso=True)
                return
            self.after(15000, revisar)

        self.after(15000, revisar)

    def _ofrecer_borrador_pendiente(self):
        try:
            from services.levantamiento_borradores_service import cargar_borrador, eliminar_borrador
            borrador = cargar_borrador(self.usuario_activo)
        except Exception:
            borrador = None
        if not borrador:
            return

        dialogo = ctk.CTkToplevel(self)
        dialogo.title("Levantamiento pendiente")
        dialogo.resizable(False, False)
        dialogo.transient(self)
        centrar_ventana(dialogo, 520, 260, padre=self)
        dialogo.grab_set()
        configurar_icono_ventana(dialogo)

        tipo = borrador.get("tipo_levantamiento") or "levantamiento"
        guardado = str(borrador.get("guardado_en") or "").replace("T", " ")
        ctk.CTkLabel(dialogo, text="Tienes un levantamiento pendiente", font=TITLE_LG, text_color=TEXT_PRIMARY).pack(pady=(24, 8))
        ctk.CTkLabel(dialogo, text=f"{tipo}\nÚltimo guardado temporal: {guardado}", font=TEXT_MD, text_color=TEXT_SECONDARY, justify="center").pack(pady=(0, 22))
        fila = ctk.CTkFrame(dialogo, fg_color="transparent")
        fila.pack(fill="x", padx=24, pady=8)

        def continuar():
            datos = borrador.get("datos") if isinstance(borrador.get("datos"), dict) else {}
            try:
                dialogo.grab_release(); dialogo.destroy()
            except Exception:
                pass
            if str(tipo).strip() == "Obra Civil":
                self.navigation.mostrar_obra_civil(borrador=datos)
            else:
                self.navigation.mostrar_levantamiento(tipo_levantamiento=tipo, borrador=datos)

        def despues():
            try:
                dialogo.grab_release(); dialogo.destroy()
            except Exception:
                pass

        def borrar():
            if not messagebox.askyesno("Borrar borrador", "¿Deseas eliminar definitivamente este levantamiento temporal?", parent=dialogo):
                return
            eliminar_borrador(self.usuario_activo)
            try:
                dialogo.grab_release(); dialogo.destroy()
            except Exception:
                pass

        ctk.CTkButton(fila, text="Continuar", command=continuar).pack(side="left", expand=True, fill="x", padx=4)
        ctk.CTkButton(fila, text="Guardar para después", command=despues, fg_color="#334155").pack(side="left", expand=True, fill="x", padx=4)
        ctk.CTkButton(fila, text="Borrar", command=borrar, fg_color="#DC2626", hover_color="#B91C1C").pack(side="left", expand=True, fill="x", padx=4)
        dialogo.protocol("WM_DELETE_WINDOW", despues)

    def _mostrar_estado_actualizacion_anterior(self):
        try:
            from services.update_service import consumir_estado_actualizacion
            estado = consumir_estado_actualizacion()
        except Exception:
            logger.exception("No fue posible leer el resultado de la actualización anterior.")
            return
        if not estado:
            return
        if estado.get("ok"):
            logger.info("Resultado de actualización anterior: %s", estado.get("message"))
            return
        mensaje = str(estado.get("message") or "La actualización no pudo completarse.")
        messagebox.showwarning(
            "Actualización de AXIA",
            "La actualización anterior no pudo completarse.\n\n" + mensaje +
            "\n\nPuedes seguir usando AXIA y volver a intentarlo más tarde.",
            parent=self,
        )

    def _comprobar_actualizacion_axia(self):
        try:
            from core.background_tasks import run_async
            from services.update_service import obtener_actualizacion_disponible
        except Exception:
            logger.exception("No fue posible cargar el servicio de actualizaciones.")
            return

        def mostrar(actualizacion):
            if actualizacion is None or not self.winfo_exists():
                return
            self._mostrar_dialogo_actualizacion(actualizacion)

        run_async(
            root=self,
            task=obtener_actualizacion_disponible,
            on_success=mostrar,
            on_error=lambda error: logger.warning(
                "Comprobación de actualización omitida: %s", error
            ),
        )

    def _mostrar_dialogo_actualizacion(self, actualizacion):
        from core.version import APP_VERSION

        dialogo = ctk.CTkToplevel(self)
        dialogo.title("Actualización de AXIA")
        dialogo.resizable(False, False)
        dialogo.transient(self)
        centrar_ventana(dialogo, 590, 420, padre=self)
        dialogo.grab_set()
        configurar_icono_ventana(dialogo)

        ctk.CTkLabel(
            dialogo,
            text="Actualización disponible",
            font=TITLE_LG,
            text_color=TEXT_PRIMARY,
        ).pack(pady=(24, 7))
        ctk.CTkLabel(
            dialogo,
            text=f"Versión instalada: {APP_VERSION}    →    Nueva versión: {actualizacion.version}",
            font=TEXT_MD,
            text_color=TEXT_SECONDARY,
        ).pack(pady=(0, 13))

        if actualizacion.obligatoria:
            ctk.CTkLabel(
                dialogo,
                text="Esta actualización es obligatoria para continuar utilizando AXIA.",
                font=TEXT_MD,
                text_color="#B91C1C",
            ).pack(pady=(0, 10))

        notas = actualizacion.notas or "Mejoras y correcciones de AXIA."
        caja = AxiaTextbox(dialogo, width=520, height=175, wrap="word")
        caja.pack(padx=30, pady=(0, 15))
        caja.insert("1.0", notas)
        caja.configure(state="disabled")

        estado = ctk.CTkLabel(
            dialogo,
            text="",
            font=TEXT_MD,
            text_color=TEXT_SECONDARY,
        )
        estado.pack(pady=(0, 7))

        fila = ctk.CTkFrame(dialogo, fg_color="transparent")
        fila.pack(fill="x", padx=32, pady=(0, 20))

        def cerrar_dialogo():
            try:
                dialogo.grab_release()
                dialogo.destroy()
            except Exception:
                logger.debug("El diálogo de actualización ya estaba cerrado.", exc_info=True)

        def descargar_e_instalar():
            from core.background_tasks import run_async
            from services.update_service import descargar_actualizacion, programar_instalacion

            btn_actualizar.configure(state="disabled")
            if btn_posponer is not None:
                btn_posponer.configure(state="disabled")
            estado.configure(text="Descargando y verificando actualización...")
            dialogo.configure(cursor="watch")

            def tarea():
                instalador = descargar_actualizacion(actualizacion)
                programar_instalacion(instalador)
                return instalador

            def listo(_instalador):
                estado.configure(text="Instalador iniciado. AXIA se cerrará y volverá a abrir al finalizar.")
                try:
                    dialogo.grab_release()
                except Exception:
                    logger.debug("No fue necesario liberar el diálogo de actualización.", exc_info=True)
                self.after(350, self.salir_aplicacion)

            def error_descarga(error):
                dialogo.configure(cursor="")
                btn_actualizar.configure(state="normal")
                if btn_posponer is not None:
                    btn_posponer.configure(state="normal")
                estado.configure(text="No fue posible preparar la actualización.")
                messagebox.showerror(
                    "Actualización de AXIA",
                    f"No fue posible descargar o verificar la actualización.\n\n{error}",
                    parent=dialogo,
                )

            run_async(
                root=dialogo,
                task=tarea,
                on_success=listo,
                on_error=error_descarga,
            )

        btn_actualizar = ctk.CTkButton(
            fila,
            text="Actualizar ahora",
            command=descargar_e_instalar,
            height=42,
        )
        btn_actualizar.pack(side="left", expand=True, fill="x", padx=5)

        btn_posponer = None
        if actualizacion.obligatoria:
            btn_posponer = ctk.CTkButton(
                fila,
                text="Salir de AXIA",
                fg_color="#475569",
                command=self.salir_aplicacion,
                height=42,
            )
            btn_posponer.pack(side="left", expand=True, fill="x", padx=5)
            dialogo.protocol("WM_DELETE_WINDOW", self.salir_aplicacion)
        else:
            btn_posponer = ctk.CTkButton(
                fila,
                text="Más tarde",
                fg_color="#475569",
                command=cerrar_dialogo,
                height=42,
            )
            btn_posponer.pack(side="left", expand=True, fill="x", padx=5)
            dialogo.protocol("WM_DELETE_WINDOW", cerrar_dialogo)

    def cerrar_sesion(self, motivo="manual", mostrar_aviso=False):
        try:
            from services.reportador_fotografico_service import cerrar_sesion as rf_cerrar
            rf_cerrar()
        except Exception:
            pass
        try:
            from services.sesion_axia_compartida import cerrar_sesion as borrar_sesion_cerrar
            borrar_sesion_cerrar()
        except Exception:
            pass
        from app_context import establecer_usuario_actual
        from services.movimientos_service import registrar_movimiento_seguro

        self.logout_requested = True
        if motivo != "inactividad":
            self._guardar_borrador_actual()

        try:
            registrar_movimiento_seguro(
                modulo="Login",
                accion="CERRAR_SESION",
                descripcion=("El usuario cerró sesión por inactividad" if motivo == "inactividad" else "El usuario cerró sesión manualmente")
            )
        except Exception:
            logger.exception("No fue posible registrar el cierre de sesión.")

        establecer_usuario_actual()

        try:
            self.destroy()
        except Exception:
            logger.exception("No fue posible cerrar la ventana principal al cerrar sesión.")

    def salir_aplicacion(self):
        try:
            from services.reportador_fotografico_service import cerrar_sesion as rf_cerrar
            rf_cerrar()
        except Exception:
            pass
        try:
            from services.sesion_axia_compartida import cerrar_sesion as borrar_sesion_cerrar
            borrar_sesion_cerrar()
        except Exception:
            pass
        self.logout_requested = False
        self._guardar_borrador_actual()
        try:
            self.destroy()
        except Exception:
            logger.exception("No fue posible cerrar la aplicación.")


# =====================================================
# FUNCIÓN: abrir_app()
# =====================================================
def abrir_app():
    app = AxiaApp()
    app.mainloop()
    return bool(getattr(app, "logout_requested", False))