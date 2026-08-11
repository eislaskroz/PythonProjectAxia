from core.error_reporting import show_operation_error
"""
=========================================================
MÓDULO: levantamiento_view.py
DESCRIPCIÓN:
Vista visual para generar levantamientos operativos AXIA.

Esta vista se carga dentro del área dinámica de app.py.
No abre ventanas nuevas.
=========================================================
"""

from core.logger import configurar_logger

logger = configurar_logger(__name__)

import json

import customtkinter as ctk
from tkinter import messagebox, ttk
from ui.native_combobox import NativeComboBox

from ui.colors import (
    PRIMARY,
    SECONDARY,
    WHITE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    BUTTON_HOVER
)

from ui.date_picker import abrir_selector_fecha, asociar_selector_fecha
from ui.fonts import (
    TITLE_MD,
    TEXT_MD,
    TEXT_SM,
    BUTTON_FONT
)

from app_context import obtener_usuario_actual
from services.movimientos_service import registrar_movimiento
from services.materiales_catalogo_service import obtener_materiales_por_especialidad, UNIDADES_MATERIAL
from services.equipos_catalogo_service import (
    MARCAS_COMUNES, obtener_nombres_familias, obtener_subfamilias,
    obtener_sugerencia_caracteristicas
)

from services.aco_context_service import normalizar_datos_aco
from services.acos_service import buscar_aco_por_numero
from services.clientes_service import buscar_clientes, construir_direccion_cliente
from services.levantamientos_service import crear_levantamiento
from services.usuarios_service import obtener_tecnicos_responsables, obtener_supervisores_formulario
from views.formato_helpers import generar_pdf_preview, generar_pdf_archivo, enfocar_inicio_formulario, ruta_documentos_axia
from services.pdf_registro_service import generar_pdf_registro

from security.permissions import puede_generar_levantamiento


# El catálogo maestro de materiales se carga desde services.materiales_catalogo_service.


from views.levantamientos.catalogos_canalizacion import (
    TIPOS_TUBOS,
    TAMANOS_TUBOS,
    TIPOS_COPLES,
    TIPOS_REGISTROS,
    TIPOS_CONECTORES,
    TIPOS_ABRAZADERAS,
    TIPOS_CABLE_ELECTRICO,
    CALIBRES_CABLE_ELECTRICO,
    TIPOS_CABLE_DATOS_CONTROL,
    TIPOS_CABLE_EXTERIOR,
    TIPOS_CANALIZACION,
)

from views.levantamientos.form_definitions import (
    FORMULARIOS_DETALLADOS_EXTRA,
    TIPOS_LEVANTAMIENTO_ESPECIALIZADOS,
)

# =====================================================
# FUNCIÓN: mostrar_levantamiento()
# =====================================================
def mostrar_levantamiento(parent, app, aco=None, tipo_levantamiento=None):
    """
    Muestra el formulario para generar un levantamiento.
    PARÁMETROS:
        parent:
            Frame dinámico principal.
        app:
            Instancia de AxiaApp.
        aco:
            Diccionario opcional con información del ACO validado.
        tipo_levantamiento:
            Tipo específico de levantamiento seleccionado previamente.
            Actualmente se libera formulario dedicado para Seguridad y Monitoreo.
    """

    usuario_activo = obtener_usuario_actual()

    if not puede_generar_levantamiento(usuario_activo):
        messagebox.showerror(
            "Acceso denegado",
            "No tienes permisos para generar levantamientos."
        )
        app.mostrar_vista_inicio_aco()
        return

    for widget in parent.winfo_children():
        widget.destroy()

    usuario_activo = obtener_usuario_actual()

    # =================================================
    # CONTENEDOR PRINCIPAL
    # =================================================

    contenedor = ctk.CTkFrame(
        parent,
        fg_color="transparent"
    )
    contenedor.pack(
        fill="both",
        expand=True,
        padx=9,
        pady=6
    )

    # El encabezado de la pantalla se muestra únicamente en app.py.
    # Se elimina el título interno para evitar textos duplicados y
    # aprovechar mejor el espacio vertical del formulario.

    # Card principal: queda reservado únicamente para la captura operativa.
    card = ctk.CTkScrollableFrame(
        contenedor,
        width=1280,
        height=520,
        fg_color=WHITE,
        corner_radius=22
    )

    # =================================================
    # VARIABLES
    # =================================================

    var_folio = ctk.StringVar(value="SE ASIGNA AL GUARDAR")
    var_cliente = ctk.StringVar()
    var_cliente_selector = ctk.StringVar()
    var_aco = ctk.StringVar()
    var_contacto = ctk.StringVar()
    var_telefono = ctk.StringVar()
    var_correo = ctk.StringVar()
    var_direccion = ctk.StringVar()
    var_ubicacion = ctk.StringVar()
    var_tecnico = ctk.StringVar()
    var_supervisor = ctk.StringVar()
    var_fecha_programada = ctk.StringVar()
    var_fecha_realizacion = ctk.StringVar()

    # Catálogos de asignación obtenidos directamente de db_usuarios.
    tecnicos_disponibles = obtener_tecnicos_responsables()
    supervisores_disponibles = obtener_supervisores_formulario()
    if tecnicos_disponibles and not var_tecnico.get().strip():
        var_tecnico.set(tecnicos_disponibles[0])
    if supervisores_disponibles and not var_supervisor.get().strip():
        var_supervisor.set(supervisores_disponibles[0])

    materiales_miscelaneos_items = []
    equipos_catalogo_items = []
    canalizacion_materiales_items = []

    # Campos dedicados del formulario Seguridad y Monitoreo.
    # Se guardan dentro de los campos descriptivos existentes para evitar
    # romper la estructura actual de Supabase mientras se valida el proceso.
    var_cctv_cantidad_camaras = ctk.StringVar()
    var_cctv_tipo_camaras = ctk.StringVar(value="IP")
    var_cctv_tipo_cableado = ctk.StringVar(value="UTP")
    var_cctv_dias_retencion = ctk.StringVar()
    var_cctv_personas_considerar = ctk.StringVar()
    var_cctv_ubicacion_nvr = ctk.StringVar()
    var_cctv_punto_red = ctk.StringVar()
    var_cctv_punto_energia = ctk.StringVar()
    var_cctv_altura_montaje = ctk.StringVar()
    var_cctv_distancia_aprox = ctk.StringVar()
    var_cctv_iluminacion = ctk.StringVar(value="Mixta")

    # Campos dedicados del formulario Aires Acondicionados.
    # El flujo va desde necesidad inicial, condiciones del sitio, equipo requerido,
    # infraestructura, instalación, entrega y pruebas finales.
    var_aa_necesidad = ctk.StringVar(value="Instalación nueva")
    var_aa_cantidad_equipos = ctk.StringVar()
    var_aa_area_climatizar = ctk.StringVar()
    var_aa_tipo_area = ctk.StringVar(value="Oficina")
    var_aa_horario_operacion = ctk.StringVar()
    var_aa_dimensiones_area = ctk.StringVar()
    var_aa_personas_area = ctk.StringVar()
    var_aa_equipos_calor = ctk.StringVar()
    var_aa_exposicion_solar = ctk.StringVar(value="Media")
    var_aa_requiere_calculo = ctk.StringVar(value="Sí")
    var_aa_tipo_equipo = ctk.StringVar(value="Mini split")
    var_aa_capacidad = ctk.StringVar()
    var_aa_voltaje = ctk.StringVar(value="220V")
    var_aa_refrigerante = ctk.StringVar(value="R410A")
    var_aa_marca_modelo = ctk.StringVar()
    var_aa_ubicacion_evaporadora = ctk.StringVar()
    var_aa_ubicacion_condensadora = ctk.StringVar()
    var_aa_distancia_unidades = ctk.StringVar()
    var_aa_altura_trabajo = ctk.StringVar()
    var_aa_acceso_instalacion = ctk.StringVar(value="Fácil acceso")
    var_aa_soporte_base = ctk.StringVar(value="Sí")
    var_aa_alimentacion_disponible = ctk.StringVar(value="No")
    var_aa_breaker_disponible = ctk.StringVar(value="No")
    var_aa_drenaje_disponible = ctk.StringVar(value="No")
    var_aa_perforaciones = ctk.StringVar(value="Sí")
    var_aa_ruta_tuberia = ctk.StringVar()
    var_aa_tuberia_cobre_m = ctk.StringVar()
    var_aa_cableado_m = ctk.StringVar()
    var_aa_drenaje_m = ctk.StringVar()
    var_aa_canaleta_m = ctk.StringVar()
    var_aa_bomba_drenaje = ctk.StringVar(value="No")
    var_aa_requiere_permiso = ctk.StringVar(value="No")
    var_aa_requiere_escalera = ctk.StringVar(value="No")
    var_aa_proteccion_area = ctk.StringVar(value="Sí")
    var_aa_dias_trabajo = ctk.StringVar()
    var_aa_personas_trabajo = ctk.StringVar()
    var_aa_prueba_vacio = ctk.StringVar(value="Sí")
    var_aa_prueba_fugas = ctk.StringVar(value="Sí")
    var_aa_prueba_electrica = ctk.StringVar(value="Sí")
    var_aa_prueba_enfriamiento = ctk.StringVar(value="Sí")
    var_aa_limpieza_entrega = ctk.StringVar(value="Sí")
    var_aa_capacitacion_usuario = ctk.StringVar(value="Sí")

    # Campos dedicados del formulario Redes de Voz y Datos.
    # El flujo va desde necesidad inicial, alcance, condiciones del sitio,
    # materiales, rack/energía, instalación, pruebas y entrega.
    var_rvd_necesidad = ctk.StringVar(value="Instalación nueva")
    var_rvd_tipo_servicio = ctk.StringVar(value="Datos")
    var_rvd_cantidad_nodos = ctk.StringVar()
    var_rvd_cantidad_telefonia = ctk.StringVar()
    var_rvd_area_instalacion = ctk.StringVar()
    var_rvd_horario_trabajo = ctk.StringVar()
    var_rvd_tipo_cable = ctk.StringVar(value="Cat6")
    var_rvd_tipo_canalizacion = ctk.StringVar(value="Canaleta")
    var_rvd_metros_cable = ctk.StringVar()
    var_rvd_metros_canalizacion = ctk.StringVar()
    var_rvd_patch_panel = ctk.StringVar(value="Sí")
    var_rvd_tipo_patch_panel = ctk.StringVar(value="24 puertos Cat6")
    var_rvd_cantidad_patch_panel = ctk.StringVar()
    var_rvd_tipo_jacks = ctk.StringVar(value="Cat6")
    var_rvd_jacks = ctk.StringVar()
    var_rvd_tipo_plugs = ctk.StringVar(value="Cat6")
    var_rvd_plugs = ctk.StringVar()
    var_rvd_tipo_faceplates = ctk.StringVar(value="1 puerto")
    var_rvd_faceplates = ctk.StringVar()
    var_rvd_tipo_patch_cords = ctk.StringVar(value="Cat6 - 1 m")
    var_rvd_patch_cords = ctk.StringVar()
    var_rvd_ubicacion_rack = ctk.StringVar()
    var_rvd_requiere_rack = ctk.StringVar(value="Sí")
    var_rvd_tipo_rack = ctk.StringVar()
    var_rvd_requiere_gabinete = ctk.StringVar(value="Sí")
    var_rvd_tipo_gabinete = ctk.StringVar()
    var_rvd_requiere_switch = ctk.StringVar(value="Sí")
    var_rvd_puertos_switch = ctk.StringVar()
    var_rvd_tipo_switch = ctk.StringVar()
    var_rvd_switch_poe = ctk.StringVar(value="Sí")
    var_rvd_ups = ctk.StringVar(value="Sí")
    var_rvd_detalle_ups = ctk.StringVar()
    var_rvd_contacto_regulado = ctk.StringVar(value="Sí")
    var_rvd_detalle_contacto = ctk.StringVar()
    var_rvd_tierra_fisica = ctk.StringVar(value="Sí")
    var_rvd_detalle_tierra = ctk.StringVar()
    var_rvd_altura_trabajo = ctk.StringVar()
    var_rvd_acceso = ctk.StringVar(value="Fácil acceso")
    var_rvd_permiso = ctk.StringVar(value="No")
    var_rvd_riesgo = ctk.StringVar(value="Bajo")
    var_rvd_dias_trabajo = ctk.StringVar()
    var_rvd_personas_trabajo = ctk.StringVar()

    # Campos dedicados del formulario Plantas de Energía.
    # Flujo: necesidad -> carga -> sitio -> combustible -> transferencia -> instalación, pruebas y entrega.
    var_pe_necesidad = ctk.StringVar(value="Instalación nueva")
    var_pe_tipo_planta = ctk.StringVar(value="Diésel")
    var_pe_capacidad = ctk.StringVar()
    var_pe_carga_respaldar = ctk.StringVar()
    var_pe_tiempo_respaldo = ctk.StringVar()
    var_pe_voltaje = ctk.StringVar(value="220V")
    var_pe_fases = ctk.StringVar(value="Trifásico")
    var_pe_tablero_respaldo = ctk.StringVar()
    var_pe_ubicacion_planta = ctk.StringVar()
    var_pe_base_cimentacion = ctk.StringVar(value="Por validar")
    var_pe_ventilacion = ctk.StringVar(value="Por validar")
    var_pe_ruido_restriccion = ctk.StringVar(value="No")
    var_pe_distancia_tablero = ctk.StringVar()
    var_pe_combustible = ctk.StringVar(value="Diésel")
    var_pe_tanque = ctk.StringVar(value="Integrado")
    var_pe_autonomia = ctk.StringVar()
    var_pe_ruta_escape = ctk.StringVar(value="Por validar")
    var_pe_transferencia = ctk.StringVar(value="Automática")
    var_pe_ats = ctk.StringVar(value="Sí")
    var_pe_protecciones = ctk.StringVar(value="Por validar")
    var_pe_tierra_fisica = ctk.StringVar(value="Por validar")
    var_pe_permisos = ctk.StringVar(value="No")
    var_pe_maniobra = ctk.StringVar(value="Sí")
    var_pe_prueba_arranque = ctk.StringVar(value="Sí")
    var_pe_prueba_transferencia = ctk.StringVar(value="Sí")
    var_pe_prueba_carga = ctk.StringVar(value="Sí")
    var_pe_entrega_manual = ctk.StringVar(value="Sí")
    var_pe_dias_trabajo = ctk.StringVar()
    var_pe_personas_trabajo = ctk.StringVar()

    # Campos dedicados del formulario Electricidad.
    # Flujo detallado: necesidad -> carga -> tablero -> canalización -> protecciones -> instalación, pruebas y entrega.
    var_ele_necesidad = ctk.StringVar(value="Instalación nueva")
    var_ele_area = ctk.StringVar()
    var_ele_tipo_servicio = ctk.StringVar(value="Contactos")
    var_ele_cantidad_puntos = ctk.StringVar()
    var_ele_carga_estimacion = ctk.StringVar()
    var_ele_voltaje = ctk.StringVar(value="127V")
    var_ele_fases = ctk.StringVar(value="Monofásico")
    var_ele_tablero_origen = ctk.StringVar()
    var_ele_capacidad_tablero = ctk.StringVar()
    var_ele_espacios_disponibles = ctk.StringVar(value="Por validar")
    var_ele_breaker_requerido = ctk.StringVar()
    var_ele_tipo_circuito = ctk.StringVar(value="Normal")
    var_ele_canalizacion = ctk.StringVar(value=TIPOS_CANALIZACION[0])
    var_ele_metros_canalizacion = ctk.StringVar()
    var_ele_metros_cable = ctk.StringVar()
    var_ele_calibre_cable = ctk.StringVar(value=CALIBRES_CABLE_ELECTRICO[0])
    # Infraestructura requerida homologada con los demás levantamientos.
    var_ele_tubos_tipo = ctk.StringVar(value=TIPOS_TUBOS[0])
    var_ele_tubos_tamano = ctk.StringVar(value=TAMANOS_TUBOS[0])
    var_ele_tubos_cantidad = ctk.StringVar()
    var_ele_coples_tipo = ctk.StringVar(value=TIPOS_COPLES[0])
    var_ele_coples_cantidad = ctk.StringVar()
    var_ele_registros_tipo = ctk.StringVar(value=TIPOS_REGISTROS[0])
    var_ele_registros_cantidad = ctk.StringVar()
    var_ele_conectores_tipo = ctk.StringVar(value=TIPOS_CONECTORES[0])
    var_ele_conectores_cantidad = ctk.StringVar()
    var_ele_abrazaderas_tipo = ctk.StringVar(value=TIPOS_ABRAZADERAS[0])
    var_ele_abrazaderas_cantidad = ctk.StringVar()
    var_ele_cable_tipo = ctk.StringVar(value=TIPOS_CABLE_ELECTRICO[0])
    var_ele_cable_cantidad = ctk.StringVar()
    var_ele_contactos = ctk.StringVar()
    var_ele_apagadores = ctk.StringVar()
    var_ele_luminarias = ctk.StringVar()
    var_ele_tierra_fisica = ctk.StringVar(value="Por validar")
    var_ele_neutro = ctk.StringVar(value="Por validar")
    var_ele_altura_trabajo = ctk.StringVar()
    var_ele_permiso = ctk.StringVar(value="No")
    var_ele_desenergizar = ctk.StringVar(value="Por validar")
    var_ele_riesgo = ctk.StringVar(value="Medio")
    var_ele_prueba_continuidad = ctk.StringVar(value="Sí")
    var_ele_prueba_polaridad = ctk.StringVar(value="Sí")
    var_ele_prueba_voltaje = ctk.StringVar(value="Sí")
    var_ele_etiquetado = ctk.StringVar(value="Sí")
    var_ele_entrega_diagrama = ctk.StringVar(value="No")
    var_ele_dias_trabajo = ctk.StringVar()
    var_ele_personas_trabajo = ctk.StringVar()

    # Variables dinámicas para formularios especializados adicionales
    # (Control de Accesos, Enlaces Inalámbricos y Paneles Solares).
    vars_extra = {}
    if tipo_levantamiento in FORMULARIOS_DETALLADOS_EXTRA:
        for _titulo_sec, _campos_sec in FORMULARIOS_DETALLADOS_EXTRA[tipo_levantamiento]["secciones"]:
            for _clave, _tipo_campo, _etiqueta, _opciones_placeholder, _default in _campos_sec:
                vars_extra[_clave] = ctk.StringVar(value=_default or "")

    # Infraestructura Seguridad y Monitoreo: estas variables permiten levantar información
    # previa a los datos técnicos. La sección se habilita dinámicamente
    # según la respuesta a: ¿Existe infraestructura?
    var_infra_existe = ctk.StringVar(value="Sí")
    var_infra_estado = ctk.StringVar(value="Bueno")
    var_infra_tipo_existente = ctk.StringVar(value="Canalización")
    var_infra_aprovechable_m = ctk.StringVar()
    var_infra_observaciones = ctk.StringVar()

    # Modalidad operativa del levantamiento Seguridad y Monitoreo.
    # Instalación conserva el formulario actual; Reparación muestra diagnóstico;
    # Mantenimiento queda preparado para próximas preguntas.
    var_modalidad_levantamiento = ctk.StringVar(value="Instalación")

    # Reparación: tipo de elemento, ubicación, estado y síntomas.
    var_rep_objetivo = ctk.StringVar(value="Cámaras")
    var_rep_ubicacion_equipos = ctk.StringVar()
    var_rep_descripcion_infraestructura = ctk.StringVar()
    var_rep_acceso_equipos = ctk.StringVar(value="Fácil acceso")
    var_rep_estado_camaras = ctk.StringVar(value="Apagadas")
    var_rep_codigo_error = ctk.StringVar(value="No")
    var_rep_horario_falla = ctk.StringVar(value="Día y noche")

    # Reparación: alimentación y energía.
    var_rep_voltaje_correcto = ctk.StringVar(value="Sí")
    var_rep_amperaje_suficiente = ctk.StringVar(value="Sí")
    var_rep_conectores_danados = ctk.StringVar(value="No")

    # Reparación: conectividad y transmisión de video.
    var_rep_tipo_cableado = ctk.StringVar(value="BalUns + UTP")
    var_rep_cable_danado = ctk.StringVar(value="No")
    var_rep_rj45_correcto = ctk.StringVar(value="No aplica")

    # Reparación: configuración y grabador.
    var_rep_disco_operativo = ctk.StringVar(value="Sí")
    var_rep_firmware_software = ctk.StringVar(value="No")
    var_rep_actualizacion_corte = ctk.StringVar(value="No")

    var_metros_pared_delgada = ctk.StringVar()
    var_metros_pvc = ctk.StringVar()
    var_metros_canaleta = ctk.StringVar()
    var_metros_charola = ctk.StringVar()
    var_metros_escalerilla = ctk.StringVar()
    var_metros_ducteria = ctk.StringVar()

    var_metros_utp_cat5e = ctk.StringVar()
    var_metros_utp_cat6 = ctk.StringVar()
    var_metros_utp_cat6a = ctk.StringVar()
    var_metros_fibra = ctk.StringVar()
    var_metros_coaxial = ctk.StringVar()

    # Infraestructura requerida en el orden operativo solicitado.
    var_infra_tubos_tipo = ctk.StringVar(value=TIPOS_TUBOS[0])
    var_infra_tubos_tamano = ctk.StringVar(value=TAMANOS_TUBOS[0])
    var_infra_tubos_cantidad = ctk.StringVar()
    var_infra_coples_tipo = ctk.StringVar(value=TIPOS_COPLES[0])
    var_infra_coples_cantidad = ctk.StringVar()
    var_infra_registros_tipo = ctk.StringVar(value=TIPOS_REGISTROS[0])
    var_infra_registros_cantidad = ctk.StringVar()
    var_infra_conectores_tipo = ctk.StringVar(value=TIPOS_CONECTORES[0])
    var_infra_conectores_cantidad = ctk.StringVar()
    var_infra_abrazaderas_tipo = ctk.StringVar(value=TIPOS_ABRAZADERAS[0])
    var_infra_abrazaderas_cantidad = ctk.StringVar()
    var_infra_cable_tipo = ctk.StringVar(value="UTP Cat6")
    var_infra_cable_cantidad = ctk.StringVar()

    var_plugs_rj45 = ctk.StringVar()
    var_jacks_rj45 = ctk.StringVar()
    var_keystone = ctk.StringVar()
    var_faceplate = ctk.StringVar()
    var_patchcord = ctk.StringVar()

    var_rack_requerido = ctk.StringVar(value="Sí")
    var_tipo_rack = ctk.StringVar()
    var_gabinete_requerido = ctk.StringVar(value="Sí")
    var_tipo_gabinete = ctk.StringVar()
    var_ru_requeridas = ctk.StringVar()
    var_ups_requerida = ctk.StringVar(value="Sí")
    var_tipo_ups = ctk.StringVar()
    var_contacto_regulado = ctk.StringVar(value="Sí")
    var_tipo_contacto_regulado = ctk.StringVar()
    var_tierra_fisica = ctk.StringVar(value="Sí")
    var_tipo_tierra_fisica = ctk.StringVar()

    var_escalera_requerida = ctk.StringVar(value="No")
    var_altura_trabajo = ctk.StringVar()
    var_riesgo_instalacion = ctk.StringVar(value="Bajo")

    var_tipo = ctk.StringVar(value="Seguridad" if tipo_levantamiento == "Seguridad y Monitoreo" else ("Infraestructura" if tipo_levantamiento in ("Aires Acondicionados", "Redes Voz y Datos", "Tecnología, Equipos y Periféricos") else "Técnico"))
    var_estatus = ctk.StringVar(value="Pendiente")
    var_prioridad = ctk.StringVar(value="Media")

    datos_aco = normalizar_datos_aco(aco)

    if aco:
        var_aco.set(datos_aco.get("aco_numero", ""))
        var_cliente.set(datos_aco.get("cliente", ""))
        var_contacto.set(datos_aco.get("contacto", ""))
        var_telefono.set(datos_aco.get("telefono", ""))
        var_correo.set(datos_aco.get("correo", ""))
        var_direccion.set(datos_aco.get("direccion", ""))
        var_ubicacion.set(datos_aco.get("ubicacion", ""))

    # =================================================
    # CLIENTES PARA LEVANTAMIENTO Seguridad y Monitoreo
    # =================================================
    # En Seguridad y Monitoreo el levantamiento ocurre antes de generar el ACO, por eso
    # NO se captura ACO. El técnico selecciona cliente desde db_clientes
    # para evitar duplicidad o errores de captura manual.
    clientes_disponibles = []
    clientes_por_nombre = {}

    if tipo_levantamiento in TIPOS_LEVANTAMIENTO_ESPECIALIZADOS and not aco:
        try:
            clientes_disponibles = buscar_clientes("", limite=500) or []
        except Exception:
            clientes_disponibles = []

        for cliente_db in clientes_disponibles:
            nombre_cliente = str(cliente_db.get("cli_razonsocial", "") or "").strip()
            if nombre_cliente:
                clientes_por_nombre[nombre_cliente] = cliente_db

        if clientes_por_nombre:
            primer_cliente = sorted(clientes_por_nombre.keys())[0]
            var_cliente_selector.set(primer_cliente)
            cliente_inicial = clientes_por_nombre[primer_cliente]
            var_cliente.set(primer_cliente)
            var_contacto.set(cliente_inicial.get("cli_contacto", "") or "")
            var_telefono.set(cliente_inicial.get("cli_telefono", "") or "")
            var_correo.set(cliente_inicial.get("cli_correo", "") or "")
            var_direccion.set(construir_direccion_cliente(cliente_inicial))

    entradas = {}

    def bloquear_datos_aco_autollenados():
        """Bloquea campos heredados del ACO para que no sean modificados."""
        for etiqueta in ("Cliente", "Contacto", "Teléfono", "Correo", "Dirección", "Ubicación / referencia", "Ubicación"):
            entry = entradas.get(etiqueta)
            if entry:
                entry.configure(state="disabled")

    def cargar_aco_desde_campo():
        """Busca el ACO capturado y autollena campos relacionados."""
        numero = var_aco.get().strip()
        if not numero:
            return
        registro_aco = buscar_aco_por_numero(numero)
        if not registro_aco:
            return
        datos = normalizar_datos_aco(registro_aco)
        var_cliente.set(datos.get("cliente", ""))
        var_contacto.set(datos.get("contacto", ""))
        var_telefono.set(datos.get("telefono", ""))
        var_correo.set(datos.get("correo", ""))
        var_direccion.set(datos.get("direccion", ""))
        var_ubicacion.set(datos.get("ubicacion", ""))
        bloquear_datos_aco_autollenados()

    def cargar_cliente_desde_selector(nombre_cliente=None):
        """Autollena datos del cliente seleccionado desde db_clientes y los bloquea."""
        nombre = (nombre_cliente or var_cliente_selector.get() or "").strip()
        cliente_db = clientes_por_nombre.get(nombre)
        if not cliente_db:
            return

        var_cliente.set(nombre)
        var_contacto.set(cliente_db.get("cli_contacto", "") or "")
        var_telefono.set(cliente_db.get("cli_telefono", "") or "")
        var_correo.set(cliente_db.get("cli_correo", "") or "")
        var_direccion.set(construir_direccion_cliente(cliente_db))
        var_ubicacion.set(cliente_db.get("cli_municipio", "") or "")


    # =================================================
    # HELPERS VISUALES
    # =================================================

    def crear_label(texto):
        ctk.CTkLabel(
            card,
            text=texto,
            font=TEXT_SM,
            text_color=TEXT_PRIMARY
        ).pack(
            anchor="w",
            padx=28,
            pady=(5, 2)
        )

    def crear_entry(variable, placeholder, state="normal"):
        ctk.CTkEntry(
            card,
            textvariable=variable,
            width=830,
            height=34,
            corner_radius=9,
            placeholder_text=placeholder,
            state=state
        ).pack(
            padx=28,
            pady=(0, 2)
        )



    def mostrar_panel_datos_aco():
        """
        Muestra la información del ACO en una ficha compacta de solo lectura.

        Objetivo del diseño:
        - Ocupar menos alto en pantalla.
        - Evitar scroll innecesario.
        - Mostrar datos maestros como resumen operativo, no como formulario editable.
        """

        panel_aco = ctk.CTkFrame(
            contenedor,
            fg_color="#F4F7FB",
            corner_radius=14,
            border_width=1,
            border_color="#DDE6F3"
        )
        panel_aco.pack(
            fill="x",
            padx=0,
            pady=(0, 4)
        )

        header_aco = ctk.CTkFrame(
            panel_aco,
            fg_color="transparent"
        )
        header_aco.grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=9,
            pady=(4, 2)
        )

        ctk.CTkLabel(
            header_aco,
            text="Información del ACO  🔒 Solo lectura",
            font=TEXT_SM,
            text_color=TEXT_PRIMARY
        ).pack(anchor="w")

        campos_aco = [
            ("ACO", datos_aco.get("aco_numero")),
            ("Cliente", datos_aco.get("cliente")),
            ("Contacto", datos_aco.get("contacto")),
            ("Teléfono", datos_aco.get("telefono")),
            ("Correo", datos_aco.get("correo")),
            ("Dirección", datos_aco.get("direccion")),
            ("Ubicación", datos_aco.get("ubicacion")),
            ("Tipo servicio", datos_aco.get("tipo_servicio")),
            ("Fecha creación", datos_aco.get("fecha_creacion")),
        ]

        for indice, (etiqueta, valor) in enumerate(campos_aco):
            fila = 1 + (indice // 3)
            columna = indice % 3

            item = ctk.CTkFrame(
                panel_aco,
                fg_color="transparent"
            )
            item.grid(
                row=fila,
                column=columna,
                sticky="ew",
                padx=9,
                pady=(1, 2)
            )

            ctk.CTkLabel(
                item,
                text=f"{etiqueta}: ",
                font=("Montserrat", 12, "bold"),
                text_color=TEXT_PRIMARY,
                anchor="w"
            ).pack(side="left", anchor="w")

            ctk.CTkLabel(
                item,
                text=valor or "No registrado",
                font=("Montserrat", 11),
                text_color=TEXT_SECONDARY,
                anchor="w",
                justify="left",
                wraplength=330
            ).pack(side="left", anchor="w", fill="x", expand=True)

        for columna in range(3):
            panel_aco.grid_columnconfigure(columna, weight=1, uniform="aco_compacto")

    def convertir_tipo(texto):
        return {
            "Técnico": 1,
            "Comercial": 2,
            "Infraestructura": 3,
            "Seguridad": 4,
            "Energía": 5,
            "Otro": 6
        }.get(texto, 1)

    def convertir_estatus(texto):
        return {
            "Pendiente": 1,
            "En proceso": 2,
            "Realizado": 3,
            "Cancelado": 4
        }.get(texto, 1)

    def convertir_prioridad(texto):
        return {
            "Baja": 1,
            "Media": 2,
            "Alta": 3,
            "Urgente": 4
        }.get(texto, 2)

    # =================================================
    # PANEL SUPERIOR DE ACO Y CARD DE CAPTURA
    # =================================================

    if aco:
        mostrar_panel_datos_aco()

    card.pack(
        side="top",
        fill="both",
        expand=True,
        pady=(0, 4)
    )


    # =================================================
    # CAMPOS EN TRES COLUMNAS
    # =================================================

    form_body = ctk.CTkFrame(
        card,
        fg_color="transparent"
    )
    # Bloque de datos generales compacto: no debe consumir más altura que
    # las demás secciones del levantamiento.
    form_body.pack(
        fill="x",
        expand=False,
        padx=12,
        pady=(7, 3)
    )

    # Cuadrícula principal en 4 columnas para aprovechar mejor el ancho.
    # La primera columna puede alojar campos cortos y las demás campos medianos/largos.
    for _col in range(5):
        form_body.grid_columnconfigure(_col, weight=1, uniform="form_cols")

    fila_actual = {"valor": 0}

    def _label_campo(parent_columna, texto):
        iconos = {
            "Folio": "🔢",
            "ACO": "📁",
            "Cliente": "🏢",
            "Contacto": "👤",
            "Teléfono": "☎️",
            "Correo": "✉️",
            "Dirección": "📍",
            "Ubicación": "🧭",
            "Tipo": "🧩",
            "Estatus": "📌",
            "Prioridad": "⚠️",
            "Técnico": "🛠️",
            "Supervisor": "👷",
            "Fecha": "📅",
            "Descripción": "📝",
            "Actividades": "✅",
            "Materiales": "📦",
            "Observaciones": "💬",
            "Porcentaje": "📊",
            "Requerimientos": "📋",
        }
        icono = next((valor for clave, valor in iconos.items() if texto.startswith(clave)), "•")

        ctk.CTkLabel(
            parent_columna,
            text=f"{icono} {texto}",
            font=TEXT_SM,
            text_color=TEXT_PRIMARY
        ).pack(
            anchor="w",
            pady=(0, 1)
        )

    def _crear_contenedor_campo(fila, columna, colspan=1):
        contenedor_campo = ctk.CTkFrame(
            form_body,
            fg_color="transparent"
        )
        izquierda = 0 if columna == 0 else 8
        derecha = 0 if (columna + colspan) >= 5 else 8
        contenedor_campo.grid(
            row=fila,
            column=columna,
            columnspan=colspan,
            sticky="ew",
            padx=(izquierda, derecha),
            pady=(0, 3)
        )
        contenedor_campo.grid_columnconfigure(0, weight=1)
        return contenedor_campo

    def campo_entry(texto, variable, placeholder, state="normal", columna=0, fila=None, colspan=1):
        """
        Crea un campo de texto dentro de una cuadrícula de tres columnas.
        Se usa para aprovechar mejor la pantalla maximizada.
        """

        if fila is None:
            fila = fila_actual["valor"]

        contenedor_campo = _crear_contenedor_campo(fila, columna, colspan=colspan)
        _label_campo(contenedor_campo, texto)

        entry = ctk.CTkEntry(
            contenedor_campo,
            textvariable=variable,
            height=34,
            corner_radius=9,
            placeholder_text=placeholder,
            state=state
        )

        # Campos de captura corta: ocupan menos ancho para evitar espacio muerto.
        # Se conservan en su columna para no romper el orden TAB ni el layout general.
        campos_compactos = {
            "Folio de levantamiento",
            "Teléfono",
            "Fecha programada",
        }
        if texto in campos_compactos:
            entry.configure(width=150)
            entry.pack(anchor="w", fill=None)
        elif texto == "Correo":
            entry.configure(width=310)
            entry.pack(anchor="w", fill=None)
        else:
            entry.pack(fill="x")

        entradas[texto] = entry

        if texto == "ACO relacionado":
            entry.bind("<FocusOut>", lambda _event: cargar_aco_desde_campo())
            entry.bind("<Return>", lambda _event: cargar_aco_desde_campo())

        if "fecha" in texto.lower() and state != "disabled":
            asociar_selector_fecha(entry, contenedor_campo, variable)

    def campo_option(texto, variable, values, columna=0, fila=None):
        """
        Crea un selector dentro de la cuadrícula de dos columnas.
        """

        if fila is None:
            fila = fila_actual["valor"]

        contenedor_campo = _crear_contenedor_campo(fila, columna)
        _label_campo(contenedor_campo, texto)

        NativeComboBox(
            contenedor_campo,
            variable=variable,
            values=values,
            height=34
        ).pack(
            fill="x"
        )

    def campo_cliente_selector(texto, variable, values, columna=0, fila=None, colspan=1):
        """Selector de cliente desde db_clientes para levantamientos Seguridad y Monitoreo."""
        if fila is None:
            fila = fila_actual["valor"]

        contenedor_campo = _crear_contenedor_campo(fila, columna, colspan=colspan)
        _label_campo(contenedor_campo, texto)

        option = NativeComboBox(
            contenedor_campo,
            variable=variable,
            values=values or ["Sin clientes registrados"],
            height=34,
            command=cargar_cliente_desde_selector
        )
        option.pack(fill="x")
        return option

    def campo_texto(texto, altura=90, fila=None):
        """
        Crea un campo de texto largo usando el ancho completo del formulario.
        """

        if fila is None:
            fila = fila_actual["valor"]

        contenedor_campo = _crear_contenedor_campo(fila, 0, colspan=5)
        _label_campo(contenedor_campo, texto)

        caja_texto = ctk.CTkTextbox(
            contenedor_campo,
            height=altura,
            corner_radius=10
        )
        caja_texto.pack(
            fill="x"
        )
        return caja_texto


    if tipo_levantamiento:
        badge_tipo = ctk.CTkFrame(form_body, fg_color="#EFF6FF", corner_radius=12)
        badge_tipo.grid(row=0, column=0, columnspan=5, sticky="ew", padx=0, pady=(0, 4))
        ctk.CTkLabel(
            badge_tipo,
            text=f"📌 Tipo seleccionado: {tipo_levantamiento}",
            font=("Montserrat", 12, "bold"),
            text_color=PRIMARY
        ).pack(anchor="w", padx=8, pady=3)
        desplazamiento_filas = 1
    else:
        desplazamiento_filas = 0

    # =================================================
    # CAMPOS BASE
    # =================================================
    # Regla especial Seguridad y Monitoreo:
    # - Este proceso inicia antes de generar ACO, por lo tanto NO se captura ACO.
    # - Cliente, contacto, teléfono y correo vienen desde db_clientes.
    # - Tipo de levantamiento y estatus no se muestran porque ya están definidos por flujo.

    es_cctv = tipo_levantamiento == "Seguridad y Monitoreo"
    es_aire = tipo_levantamiento == "Aires Acondicionados"
    es_redes = tipo_levantamiento == "Redes Voz y Datos"
    es_plantas = tipo_levantamiento == "Plantas de Energía"
    es_electricidad = tipo_levantamiento == "Electricidad"
    es_extra = tipo_levantamiento in FORMULARIOS_DETALLADOS_EXTRA
    es_especializado = tipo_levantamiento in TIPOS_LEVANTAMIENTO_ESPECIALIZADOS

    campo_entry(
        "Folio de levantamiento",
        var_folio,
        "Folio automático",
        state="disabled",
        columna=0,
        fila=0 + desplazamiento_filas
    )

    if es_especializado and not aco:
        nombres_clientes = sorted(clientes_por_nombre.keys())
        # Distribución compacta: folio/teléfono/fechas son cortos y no deben dejar huecos grandes.
        campo_cliente_selector(
            "Cliente",
            var_cliente_selector,
            nombres_clientes,
            columna=1,
            fila=0 + desplazamiento_filas
        )
        campo_entry("Contacto", var_contacto, "Autollenado desde cliente", state="disabled", columna=2, fila=0 + desplazamiento_filas)
        campo_entry("Teléfono", var_telefono, "Autollenado desde cliente", state="disabled", columna=3, fila=0 + desplazamiento_filas)
        campo_entry("Dirección", var_direccion, "Autollenado desde cliente", state="disabled", columna=0, fila=1 + desplazamiento_filas, colspan=5)
        fila_inicio_operativa = 2 + desplazamiento_filas

        if nombres_clientes:
            cargar_cliente_desde_selector(var_cliente_selector.get())

    elif not aco:
        # Cuando el levantamiento se genera sin ACO, no se muestra ni se solicita
        # ningún campo relacionado con ACO porque ese dato todavía no existe.
        campo_entry("Cliente", var_cliente, "Nombre del cliente", columna=1, fila=0 + desplazamiento_filas)
        campo_entry("Contacto", var_contacto, "Nombre de contacto", columna=2, fila=0 + desplazamiento_filas)
        campo_entry("Teléfono", var_telefono, "Teléfono de contacto", columna=3, fila=0 + desplazamiento_filas)
        campo_entry("Correo", var_correo, "Correo electrónico", columna=0, fila=1 + desplazamiento_filas)
        fila_inicio_operativa = 2 + desplazamiento_filas
    else:
        fila_inicio_operativa = 1 + desplazamiento_filas

    if not es_especializado:
        campo_option(
            "Tipo de levantamiento",
            var_tipo,
            ["Técnico", "Comercial", "Infraestructura", "Seguridad", "Energía", "Otro"],
            columna=0,
            fila=fila_inicio_operativa
        )

        campo_option(
            "Estatus",
            var_estatus,
            ["Pendiente", "En proceso", "Realizado", "Cancelado"],
            columna=1,
            fila=fila_inicio_operativa
        )

        campo_option(
            "Prioridad",
            var_prioridad,
            ["Baja", "Media", "Alta", "Urgente"],
            columna=2,
            fila=fila_inicio_operativa
        )
        fila_operativa = fila_inicio_operativa + 1
    else:
        # Para formularios especializados estos valores se asignan por sistema y no se exponen al técnico.
        var_tipo.set("Seguridad" if (es_cctv or tipo_levantamiento == "Control de Accesos") else ("Energía" if (es_plantas or es_electricidad or tipo_levantamiento == "Paneles Solares") else "Infraestructura"))
        var_estatus.set("Pendiente")
        fila_operativa = fila_inicio_operativa

    campo_option(
        "Técnico responsable",
        var_tecnico,
        tecnicos_disponibles or ["Sin operadores tipo 4 registrados"],
        columna=0,
        fila=fila_operativa
    )

    campo_option(
        "Supervisor",
        var_supervisor,
        supervisores_disponibles or ["Sin usuarios tipo 2 o 3 registrados"],
        columna=1,
        fila=fila_operativa
    )

    if es_especializado:
        campo_entry(
            "Correo",
            var_correo,
            "Correo electrónico",
            state="disabled" if not aco else "disabled",
            columna=2,
            fila=fila_operativa
        )
        fecha_col_programada = 3
    else:
        fecha_col_programada = 2

    campo_entry(
        "Fecha programada",
        var_fecha_programada,
        "YYYY-MM-DD",
        columna=fecha_col_programada,
        fila=fila_operativa
    )

    if not aco and not es_especializado:
        campo_entry("Dirección", var_direccion, "Dirección del servicio", columna=1, fila=fila_operativa + 1)
        campo_entry("Ubicación / referencia", var_ubicacion, "Referencia o ubicación específica", columna=2, fila=fila_operativa + 1)
        fila_textos = fila_operativa + 2
    else:
        fila_textos = fila_operativa + 1

    if tipo_levantamiento == "Seguridad y Monitoreo":
        # =============================================================
        # FORMULARIO Seguridad y Monitoreo ESPECIALIZADO
        # =============================================================
        # El levantamiento Seguridad y Monitoreo se divide en secciones operativas.
        # Primero se valida si existe infraestructura. Dependiendo de la
        # respuesta, se habilitan/deshabilitan bloques para evitar capturar
        # datos que no aplican.

        secciones_dinamicas = {}

        def crear_seccion(titulo, fila):
            """Crea un bloque visual compacto para agrupar campos relacionados.

            En Seguridad y Monitoreo muchas respuestas son valores cortos. Por eso las secciones
            usan hasta 5 columnas internas cuando aplica, reduciendo altura y
            aprovechando mejor la pantalla maximizada.
            """
            frame = ctk.CTkFrame(form_body, fg_color="#F8FAFC", corner_radius=14)
            frame.grid(row=fila, column=0, columnspan=5, sticky="ew", pady=(2, 5))
            for col in range(5):
                frame.grid_columnconfigure(col, weight=1, uniform="sec_cols")

            ctk.CTkLabel(
                frame,
                text=titulo,
                font=("Montserrat", 14, "bold"),
                text_color=TEXT_PRIMARY
            ).grid(row=0, column=0, columnspan=5, sticky="w", padx=7, pady=(5, 3))

            return frame

        def label_en(parent_frame, texto, fila, columna):
            ctk.CTkLabel(
                parent_frame,
                text=texto,
                font=TEXT_SM,
                text_color=TEXT_PRIMARY,
                anchor="w",
                justify="left",
                wraplength=260
            ).grid(row=fila, column=columna, sticky="w", padx=6, pady=(2, 1))

        def entry_en(parent_frame, texto, variable, placeholder, fila, columna):
            label_en(parent_frame, texto, fila * 2 + 1, columna)
            entry = ctk.CTkEntry(
                parent_frame,
                textvariable=variable,
                height=32,
                corner_radius=9,
                placeholder_text=placeholder
            )
            entry.grid(row=fila * 2 + 2, column=columna, sticky="ew", padx=6, pady=(0, 3))
            return entry

        def option_en(parent_frame, texto, variable, values, fila, columna, command=None, width=None):
            label_en(parent_frame, texto, fila * 2 + 1, columna)
            option = NativeComboBox(
                parent_frame,
                variable=variable,
                values=values,
                height=32,
                command=command,
                width=width
            )
            option.grid(row=fila * 2 + 2, column=columna, sticky="ew", padx=6, pady=(0, 3))
            return option

        def registrar_seccion(nombre, frame):
            secciones_dinamicas[nombre] = frame

        canalizacion_items = []
        cable_items = []

        TIPOS_CANALIZACION_LOCAL = TIPOS_CANALIZACION
        TIPOS_CABLE = TIPOS_CABLE_DATOS_CONTROL

        def agregar_fila_canalizacion(frame, coleccion):
            """Agrega una partida exclusiva de canalización."""
            indice = len(coleccion)
            fila_base = 3 + indice
            var_tipo = ctk.StringVar(value=TIPOS_CANALIZACION[0])
            var_metros = ctk.StringVar()

            fila = ctk.CTkFrame(frame, fg_color="transparent")
            fila.grid(row=fila_base, column=0, columnspan=2, sticky="ew", padx=5, pady=(1, 2))
            fila.grid_columnconfigure(0, weight=2)
            fila.grid_columnconfigure(1, weight=1)

            NativeComboBox(fila, variable=var_tipo, values=TIPOS_CANALIZACION, height=32).grid(row=0, column=0, sticky="ew", padx=(0, 3))
            ctk.CTkEntry(fila, textvariable=var_metros, height=32, corner_radius=9, placeholder_text="Metros").grid(row=0, column=1, sticky="ew", padx=(0, 3))

            def eliminar_fila():
                if len(coleccion) <= 1:
                    messagebox.showinfo("Información", "Debe quedar al menos una partida de canalización.")
                    return
                fila.destroy()
                coleccion[:] = [item for item in coleccion if item["frame"] is not fila]

            ctk.CTkButton(fila, text="Quitar", width=70, height=32, fg_color="#9CA3AF", command=eliminar_fila).grid(row=0, column=2, sticky="ew")
            coleccion.append({"frame": fila, "tipo": var_tipo, "metros": var_metros})

        def agregar_fila_cable(frame, coleccion):
            """Agrega una partida exclusiva de cable."""
            indice = len(coleccion)
            fila_base = 3 + indice
            var_tipo = ctk.StringVar(value=TIPOS_CABLE[0])
            var_metros = ctk.StringVar()

            fila = ctk.CTkFrame(frame, fg_color="transparent")
            fila.grid(row=fila_base, column=2, columnspan=3, sticky="ew", padx=5, pady=(1, 2))
            fila.grid_columnconfigure(0, weight=2)
            fila.grid_columnconfigure(1, weight=1)

            NativeComboBox(fila, variable=var_tipo, values=TIPOS_CABLE, height=32).grid(row=0, column=0, sticky="ew", padx=(0, 3))
            ctk.CTkEntry(fila, textvariable=var_metros, height=32, corner_radius=9, placeholder_text="Metros").grid(row=0, column=1, sticky="ew", padx=(0, 3))

            def eliminar_fila():
                if len(coleccion) <= 1:
                    messagebox.showinfo("Información", "Debe quedar al menos una partida de cable.")
                    return
                fila.destroy()
                coleccion[:] = [item for item in coleccion if item["frame"] is not fila]

            ctk.CTkButton(fila, text="Quitar", width=70, height=32, fg_color="#9CA3AF", command=eliminar_fila).grid(row=0, column=2, sticky="ew")
            coleccion.append({"frame": fila, "tipo": var_tipo, "metros": var_metros})

        def obtener_resumen_infraestructura(canalizaciones, cables):
            """Devuelve líneas limpias separando canalización y cable."""
            lineas = []
            lineas.append("Canalización requerida:")
            for idx, item in enumerate(canalizaciones, start=1):
                tipo = item["tipo"].get().strip() or "No definido"
                metros = item["metros"].get().strip() or "0"
                lineas.append(f"  Canalización {idx}: {tipo} - {metros} metros")
            lineas.append("Cable requerido:")
            for idx, item in enumerate(cables, start=1):
                tipo = item["tipo"].get().strip() or "No definido"
                metros = item["metros"].get().strip() or "0"
                lineas.append(f"  Cable {idx}: {tipo} - {metros} metros")
            return lineas or ["Sin datos capturados"]

        def configurar_estado_seccion(frame, habilitado=True):
            """
            Activa o bloquea widgets capturables dentro de una sección.
            Los labels permanecen visibles para que el técnico entienda
            qué datos aplican y cuáles no.
            """
            estado = "normal" if habilitado else "disabled"
            for widget in frame.winfo_children():
                try:
                    if isinstance(widget, (ctk.CTkEntry, NativeComboBox, ctk.CTkTextbox, ctk.CTkButton)):
                        widget.configure(state=estado)
                except Exception:
                    logger.debug("Excepción recuperable controlada.", exc_info=True)

        def actualizar_campos_infra_existente(_valor=None):
            """Si no existe infraestructura, bloquea los campos que no aplican."""
            habilitado = var_infra_existe.get() != "No"
            estado = "normal" if habilitado else "disabled"
            if not habilitado:
                var_infra_tipo_existente.set("")
                var_infra_estado.set("")
            for widget in (widget_infra_tipo_existente, widget_infra_estado):
                try:
                    widget.configure(state=estado)
                except Exception:
                    logger.debug("Excepción recuperable controlada.", exc_info=True)
            try:
                actualizar_estado_preview()
            except Exception:
                logger.debug("Excepción recuperable controlada.", exc_info=True)

        def actualizar_detalle_rack_energia(*_args):
            """Habilita el campo de tipo/detalle solo cuando el técnico marca Sí."""
            pares = [
                (var_rack_requerido, var_tipo_rack, widget_tipo_rack),
                (var_gabinete_requerido, var_tipo_gabinete, widget_tipo_gabinete),
                (var_ups_requerida, var_tipo_ups, widget_tipo_ups),
                (var_contacto_regulado, var_tipo_contacto_regulado, widget_tipo_contacto_regulado),
                (var_tierra_fisica, var_tipo_tierra_fisica, widget_tipo_tierra_fisica),
            ]
            for var_si_no, var_detalle, widget in pares:
                habilitado = var_si_no.get() == "Sí"
                if not habilitado:
                    var_detalle.set("")
                try:
                    widget.configure(state="normal" if habilitado else "disabled")
                except Exception:
                    logger.debug("Excepción recuperable controlada.", exc_info=True)
            try:
                actualizar_estado_preview()
            except Exception:
                logger.debug("Excepción recuperable controlada.", exc_info=True)

        def actualizar_secciones_infraestructura(_valor=None):
            """Muestra el subformulario correcto según Instalación/Reparación/Mantenimiento."""
            modalidad = var_modalidad_levantamiento.get()
            es_instalacion = modalidad == "Instalación"
            es_reparacion = modalidad == "Reparación"
            es_mantenimiento = modalidad == "Mantenimiento"
            valor = var_infra_existe.get()

            # Acceso/alturas/riesgos aplica tanto para instalación como para
            # mantenimiento. El resto de los bloques de infraestructura de CCTV
            # pertenecen únicamente al levantamiento de instalación.
            secciones_instalacion = [
                "existente",
                "rack_energia", "datos_cctv"
            ]
            secciones_reparacion = [
                "rep_selector", "rep_sintomas", "rep_infraestructura",
                "rep_energia", "rep_conectividad", "rep_grabador",
                "rep_equipos", "rep_descripcion"
            ]

            for nombre in secciones_instalacion:
                frame = secciones_dinamicas.get(nombre)
                if frame:
                    if es_instalacion:
                        frame.grid()
                    else:
                        frame.grid_remove()

            # Riesgos de acceso sí se evalúan durante mantenimiento, pero no
            # durante reparación (la reparación tiene su propio campo Acceso).
            frame_seguridad = secciones_dinamicas.get("seguridad")
            if frame_seguridad:
                if es_instalacion or es_mantenimiento:
                    frame_seguridad.grid()
                    configurar_estado_seccion(frame_seguridad, True)
                    actualizar_acceso_altura()
                else:
                    frame_seguridad.grid_remove()

            for nombre in secciones_reparacion:
                frame = secciones_dinamicas.get(nombre)
                if frame:
                    if es_reparacion:
                        frame.grid()
                    else:
                        frame.grid_remove()

            # La sección provisional de mantenimiento ya no se muestra.
            frame_mantenimiento = secciones_dinamicas.get("mantenimiento")
            if frame_mantenimiento:
                frame_mantenimiento.grid_remove()

            if es_instalacion:
                configurar_estado_seccion(secciones_dinamicas["existente"], True)
                configurar_estado_seccion(secciones_dinamicas["rack_energia"], valor in ("No", "Parcial"))
                configurar_estado_seccion(secciones_dinamicas["seguridad"], valor in ("No", "Parcial"))
                actualizar_campos_infra_existente()
                actualizar_detalle_rack_energia()
                actualizar_acceso_altura()
            elif es_reparacion:
                actualizar_formulario_reparacion()
            elif es_mantenimiento:
                actualizar_acceso_altura()

            try:
                actualizar_estado_preview()
            except Exception:
                logger.debug("Excepción recuperable controlada.", exc_info=True)

        # Tipo operativo del levantamiento: detona formularios dentro de la misma vista.
        seccion_tipo_operativo = crear_seccion("🧭 El levantamiento es para Instalación, Reparación o Mantenimiento", fila_textos)
        option_en(
            seccion_tipo_operativo,
            "Tipo de trabajo",
            var_modalidad_levantamiento,
            ["Instalación", "Reparación", "Mantenimiento"],
            fila=0,
            columna=0,
            command=actualizar_secciones_infraestructura
        )

        # Infraestructura del sitio / existente reutilizable en una sola sección.
        seccion_existente = crear_seccion("🏗️ Infraestructura del sitio / existente reutilizable", fila_textos + 1)
        registrar_seccion("existente", seccion_existente)
        option_en(
            seccion_existente,
            "¿Existe infraestructura para Seguridad y Monitoreo?",
            var_infra_existe,
            ["Sí", "Parcial", "No"],
            fila=0,
            columna=0,
            command=lambda valor: (actualizar_campos_infra_existente(valor), actualizar_secciones_infraestructura(valor))
        )
        widget_infra_tipo_existente = option_en(seccion_existente, "Tipo de infraestructura existente", var_infra_tipo_existente, ["Canalización", "Cableado", "Rack/Gabinete", "Red", "Energía", "Mixta"], 0, 1)
        widget_infra_estado = option_en(seccion_existente, "Estado general", var_infra_estado, ["Excelente", "Bueno", "Regular", "Malo"], 0, 2)
        ctk.CTkLabel(
            seccion_existente,
            text="Selecciona 'No' cuando se deba considerar infraestructura y materiales desde cero.",
            font=("Montserrat", 11),
            text_color=TEXT_SECONDARY,
            anchor="w",
            justify="left"
        ).grid(row=3, column=0, columnspan=5, sticky="w", padx=6, pady=(0, 2))

        # La captura de infraestructura requerida se realiza exclusivamente
        # mediante la sección dinámica común de canalización y materiales.

        # Consumibles de Conectividad
        seccion_conectividad = crear_seccion("🔌 Consumibles de Conectividad", fila_textos + 3)
        registrar_seccion("conectividad", seccion_conectividad)
        seccion_conectividad.grid_remove()
        entry_en(seccion_conectividad, "Plugs RJ45", var_plugs_rj45, "Ej. 24", 0, 0)
        entry_en(seccion_conectividad, "Jacks RJ45", var_jacks_rj45, "Ej. 12", 0, 1)
        entry_en(seccion_conectividad, "Keystone", var_keystone, "Ej. 12", 0, 2)
        entry_en(seccion_conectividad, "Faceplates", var_faceplate, "Ej. 12", 0, 3)
        entry_en(seccion_conectividad, "Patch cords", var_patchcord, "Ej. 12", 0, 4)

        # Rack / energía
        seccion_rack_energia = crear_seccion("🗄️ Rack, gabinete y energía", fila_textos + 4)
        registrar_seccion("rack_energia", seccion_rack_energia)
        option_en(seccion_rack_energia, "¿Se requiere rack?", var_rack_requerido, ["Sí", "No"], 0, 0, command=actualizar_detalle_rack_energia)
        option_en(seccion_rack_energia, "¿Se requiere gabinete?", var_gabinete_requerido, ["Sí", "No"], 0, 1, command=actualizar_detalle_rack_energia)
        option_en(seccion_rack_energia, "¿Se requiere UPS?", var_ups_requerida, ["Sí", "No"], 0, 2, command=actualizar_detalle_rack_energia)
        option_en(seccion_rack_energia, "¿Se requiere contacto regulado?", var_contacto_regulado, ["Sí", "No"], 0, 3, command=actualizar_detalle_rack_energia)
        option_en(seccion_rack_energia, "¿Se requiere tierra física?", var_tierra_fisica, ["Sí", "No"], 0, 4, command=actualizar_detalle_rack_energia)
        widget_tipo_rack = entry_en(seccion_rack_energia, "Tipo de rack", var_tipo_rack, "Ej. 12U", 1, 0)
        widget_tipo_gabinete = entry_en(seccion_rack_energia, "Tipo de gabinete", var_tipo_gabinete, "Ej. mural", 1, 1)
        widget_tipo_ups = entry_en(seccion_rack_energia, "Tipo/capacidad UPS", var_tipo_ups, "Ej. 1 kVA", 1, 2)
        widget_tipo_contacto_regulado = entry_en(seccion_rack_energia, "Detalle contacto regulado", var_tipo_contacto_regulado, "Ej. 2 contactos", 1, 3)
        widget_tipo_tierra_fisica = entry_en(seccion_rack_energia, "Detalle tierra física", var_tipo_tierra_fisica, "Ej. barra/cable", 1, 4)
        actualizar_detalle_rack_energia()

        # Seguridad / acceso para instalación
        seccion_seguridad = crear_seccion("🪜 Acceso, alturas y riesgos", fila_textos + 5)
        registrar_seccion("seguridad", seccion_seguridad)
        def actualizar_acceso_altura(_valor=None):
            requiere_acceso = var_escalera_requerida.get() == "Sí"
            estado = "normal" if requiere_acceso else "disabled"
            if not requiere_acceso:
                var_altura_trabajo.set("")
                var_riesgo_instalacion.set("Bajo")
            try:
                widget_altura_trabajo.configure(state=estado)
                widget_riesgo_instalacion.configure(state=estado)
            except Exception:
                logger.debug("Excepción recuperable controlada.", exc_info=True)
            try:
                actualizar_estado_preview()
            except Exception:
                logger.debug("Excepción recuperable controlada.", exc_info=True)

        option_en(seccion_seguridad, "¿Se requiere de escalera/andamio?", var_escalera_requerida, ["Sí", "No"], 0, 0, command=actualizar_acceso_altura)
        widget_altura_trabajo = entry_en(seccion_seguridad, "Altura", var_altura_trabajo, "Ej. 4 metros", 0, 1)
        widget_riesgo_instalacion = option_en(seccion_seguridad, "Riesgo", var_riesgo_instalacion, ["Bajo", "Medio", "Alto", "Crítico"], 0, 2)
        actualizar_acceso_altura()

        # Datos técnicos Seguridad y Monitoreo compactados dentro de una sola sección.
        seccion_cctv = crear_seccion("📹 Datos técnicos Seguridad y Monitoreo", fila_textos + 6)
        registrar_seccion("datos_cctv", seccion_cctv)
        entry_en(seccion_cctv, "¿Cuántas cámaras se requieren?", var_cctv_cantidad_camaras, "Ej. 8", 0, 0)
        option_en(seccion_cctv, "¿Qué tipo de cámaras se requieren?", var_cctv_tipo_camaras, ["IP", "Análoga", "Híbrida", "PTZ", "LPR", "Térmica"], 0, 1)
        entry_en(seccion_cctv, "¿Dónde se ubicará el NVR/DVR?", var_cctv_ubicacion_nvr, "Ej. SITE", 0, 2)

        entry_en(seccion_cctv, "¿Dónde estará el punto de enlace de red?", var_cctv_punto_red, "Ej. Rack/SITE", 1, 0)
        entry_en(seccion_cctv, "¿Dónde estará el punto de energía?", var_cctv_punto_energia, "Ej. Contacto regulado", 1, 1)
        entry_en(seccion_cctv, "¿Cuántos días de trabajo se proyectan?", var_cctv_dias_retencion, "Ej. 3", 1, 2)
        entry_en(seccion_cctv, "¿Cuántas personas se consideran?", var_cctv_personas_considerar, "Ej. 2", 1, 3)

        # =============================================================
        # FORMULARIO DE REPARACIÓN
        # =============================================================
        equipos_danados_items = []

        def agregar_equipo_danado(frame, coleccion):
            indice = len(coleccion)
            fila_base = 2 + indice
            var_equipo_tipo = ctk.StringVar(value="Cámara")
            var_equipo_marca = ctk.StringVar()
            var_equipo_modelo = ctk.StringVar()
            var_equipo_serie = ctk.StringVar()

            fila = ctk.CTkFrame(frame, fg_color="transparent")
            fila.grid(row=fila_base, column=0, columnspan=5, sticky="ew", padx=5, pady=(1, 2))
            for col in range(5):
                fila.grid_columnconfigure(col, weight=1)

            NativeComboBox(fila, variable=var_equipo_tipo, values=["Cámara", "DVR", "NVR", "Disco duro", "Fuente", "Monitor", "Switch", "BalUn", "Otro"], height=32).grid(row=0, column=0, sticky="ew", padx=(0, 3))
            ctk.CTkEntry(fila, textvariable=var_equipo_marca, height=32, corner_radius=9, placeholder_text="Marca").grid(row=0, column=1, sticky="ew", padx=(0, 3))
            ctk.CTkEntry(fila, textvariable=var_equipo_modelo, height=32, corner_radius=9, placeholder_text="Modelo").grid(row=0, column=2, sticky="ew", padx=(0, 3))
            ctk.CTkEntry(fila, textvariable=var_equipo_serie, height=32, corner_radius=9, placeholder_text="Número de serie").grid(row=0, column=3, sticky="ew", padx=(0, 3))

            def eliminar_fila():
                if len(coleccion) <= 1:
                    messagebox.showinfo("Información", "Debe quedar al menos un equipo dañado para documentar la reparación.")
                    return
                fila.destroy()
                coleccion[:] = [item for item in coleccion if item["frame"] is not fila]
                try:
                    actualizar_estado_preview()
                except Exception:
                    logger.debug("Excepción recuperable controlada.", exc_info=True)

            ctk.CTkButton(fila, text="Quitar", width=70, height=32, fg_color="#9CA3AF", command=eliminar_fila).grid(row=0, column=4, sticky="ew")
            coleccion.append({"frame": fila, "tipo": var_equipo_tipo, "marca": var_equipo_marca, "modelo": var_equipo_modelo, "serie": var_equipo_serie})
            for _var in (var_equipo_tipo, var_equipo_marca, var_equipo_modelo, var_equipo_serie):
                try:
                    _var.trace_add("write", lambda *_args: actualizar_estado_preview())
                except Exception:
                    logger.debug("Excepción recuperable controlada.", exc_info=True)

        seccion_rep_selector = crear_seccion("🛠️ Reparación: Selección del elemento", fila_textos + 7)
        registrar_seccion("rep_selector", seccion_rep_selector)
        option_en(
            seccion_rep_selector,
            "¿Qué se desea reparar?",
            var_rep_objetivo,
            ["Cámaras", "NVRs y/o DVRs", "Infraestructura", "Alimentación y Energía", "Conectividad"],
            0,
            0,
            command=lambda _valor: actualizar_formulario_reparacion()
        )

        seccion_rep_sintomas = crear_seccion("📍 Reparación: Ubicación, acceso y estado", fila_textos + 8)
        registrar_seccion("rep_sintomas", seccion_rep_sintomas)
        entry_en(seccion_rep_sintomas, "Ubicación de equipos", var_rep_ubicacion_equipos, "Ej. Acceso principal / SITE / Bodega", 0, 0)
        option_en(seccion_rep_sintomas, "Acceso", var_rep_acceso_equipos, ["Fácil acceso", "Difícil acceso"], 0, 1)
        lbl_estado_reparacion = ctk.CTkLabel(seccion_rep_sintomas, text="Estado de Cámaras", font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w", justify="left", wraplength=260)
        lbl_estado_reparacion.grid(row=1, column=2, sticky="w", padx=6, pady=(2, 1))
        widget_estado_reparacion = NativeComboBox(seccion_rep_sintomas, variable=var_rep_estado_camaras, values=["Apagadas", "Intermitencias", "Operando parcialmente"], height=32)
        widget_estado_reparacion.grid(row=2, column=2, sticky="ew", padx=6, pady=(0, 3))
        lbl_codigo_error = ctk.CTkLabel(seccion_rep_sintomas, text="Código de error", font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w", justify="left")
        lbl_codigo_error.grid(row=1, column=3, sticky="w", padx=6, pady=(2, 1))
        widget_codigo_error = ctk.CTkEntry(seccion_rep_sintomas, textvariable=var_rep_codigo_error, height=32, corner_radius=9, placeholder_text="Ej. 0x800 / Sin señal")
        widget_codigo_error.grid(row=2, column=3, sticky="ew", padx=6, pady=(0, 3))
        lbl_horario_falla = ctk.CTkLabel(seccion_rep_sintomas, text="Horario de la falla", font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w", justify="left")
        lbl_horario_falla.grid(row=1, column=4, sticky="w", padx=6, pady=(2, 1))
        widget_horario_falla = NativeComboBox(seccion_rep_sintomas, variable=var_rep_horario_falla, values=["Solo de noche", "Solo de día", "Día y noche", "Intermitente"], height=32)
        widget_horario_falla.grid(row=2, column=4, sticky="ew", padx=6, pady=(0, 3))

        seccion_rep_infraestructura = crear_seccion("🏗️ Reparación: Infraestructura", fila_textos + 9)
        registrar_seccion("rep_infraestructura", seccion_rep_infraestructura)
        ctk.CTkLabel(
            seccion_rep_infraestructura,
            text="Descripción de infraestructura a reparar",
            font=TEXT_SM,
            text_color=TEXT_PRIMARY,
            anchor="w"
        ).grid(row=1, column=0, columnspan=5, sticky="w", padx=6, pady=(2, 1))
        txt_rep_infraestructura = ctk.CTkTextbox(seccion_rep_infraestructura, height=120, corner_radius=9)
        txt_rep_infraestructura.grid(row=2, column=0, columnspan=5, sticky="ew", padx=6, pady=(0, 5))

        seccion_rep_energia = crear_seccion("⚡ Reparación: Alimentación y Energía", fila_textos + 10)
        registrar_seccion("rep_energia", seccion_rep_energia)
        option_en(seccion_rep_energia, "Voltaje correcto", var_rep_voltaje_correcto, ["Sí", "No", "No medido"], 0, 0)
        option_en(seccion_rep_energia, "Amperaje suficiente", var_rep_amperaje_suficiente, ["Sí", "No", "No medido"], 0, 1)
        option_en(seccion_rep_energia, "Sulfatación/falsos/humedad", var_rep_conectores_danados, ["Sí", "No"], 0, 2)

        seccion_rep_conectividad = crear_seccion("📡 Reparación: Conectividad y Transmisión de Video", fila_textos + 11)
        registrar_seccion("rep_conectividad", seccion_rep_conectividad)
        option_en(seccion_rep_conectividad, "Cableado", var_rep_tipo_cableado, ["BalUns + UTP", "Coaxial", "Red RJ45/IP", "Mixto"], 0, 0)
        option_en(seccion_rep_conectividad, "Cable dañado", var_rep_cable_danado, ["Sí", "No", "No visible"], 0, 1)
        option_en(seccion_rep_conectividad, "RJ45/switch correcto", var_rep_rj45_correcto, ["Sí", "No", "No aplica"], 0, 2)

        seccion_rep_grabador = crear_seccion("💽 Reparación: Configuración y Grabador", fila_textos + 12)
        registrar_seccion("rep_grabador", seccion_rep_grabador)
        option_en(seccion_rep_grabador, "Disco operativo", var_rep_disco_operativo, ["Sí", "No", "No aplica"], 0, 0)
        option_en(seccion_rep_grabador, "Software/firmware", var_rep_firmware_software, ["Sí", "No"], 0, 1)
        option_en(seccion_rep_grabador, "Actualización/corte", var_rep_actualizacion_corte, ["Sí", "No"], 0, 2)

        seccion_rep_equipos = crear_seccion("📦 Reparación: Información de Equipos Dañados", fila_textos + 13)
        registrar_seccion("rep_equipos", seccion_rep_equipos)
        for columna, titulo_campo in enumerate(("Tipo de equipo", "Marca", "Modelo", "Número de serie", "Acción")):
            ctk.CTkLabel(seccion_rep_equipos, text=titulo_campo, font=("Montserrat", 11, "bold"), text_color=TEXT_PRIMARY, anchor="w").grid(row=1, column=columna, sticky="w", padx=6, pady=(0, 2))
        agregar_equipo_danado(seccion_rep_equipos, equipos_danados_items)
        ctk.CTkButton(
            seccion_rep_equipos,
            text="➕ Agregar otro equipo dañado",
            height=34,
            fg_color=PRIMARY,
            command=lambda: agregar_equipo_danado(seccion_rep_equipos, equipos_danados_items)
        ).grid(row=99, column=0, columnspan=2, sticky="w", padx=6, pady=(2, 5))

        seccion_rep_descripcion = crear_seccion("📝 Reparación: Descripción general de la/las fallas", fila_textos + 14)
        registrar_seccion("rep_descripcion", seccion_rep_descripcion)
        txt_rep_descripcion_fallas = ctk.CTkTextbox(seccion_rep_descripcion, height=110, corner_radius=9)
        txt_rep_descripcion_fallas.grid(row=1, column=0, columnspan=5, sticky="ew", padx=6, pady=(0, 5))

        def actualizar_formulario_reparacion(*_args):
            """Muestra únicamente las preguntas aplicables al elemento seleccionado."""
            objetivo = var_rep_objetivo.get()
            es_camaras = objetivo == "Cámaras"
            es_grabador = objetivo == "NVRs y/o DVRs"
            es_infraestructura = objetivo == "Infraestructura"
            es_energia = objetivo == "Alimentación y Energía"
            es_conectividad = objetivo == "Conectividad"

            # Ubicación y acceso aplican salvo en infraestructura, donde se solicita
            # exclusivamente una descripción abierta con todos los pormenores.
            if es_infraestructura:
                seccion_rep_sintomas.grid_remove()
                seccion_rep_infraestructura.grid()
            else:
                seccion_rep_sintomas.grid()
                seccion_rep_infraestructura.grid_remove()

            # Estado contextual.
            if es_camaras:
                lbl_estado_reparacion.configure(text="Estado de Cámaras")
                widget_estado_reparacion.configure(values=["Apagadas", "Intermitencias", "Operando parcialmente", "Sin video"])
            elif es_grabador:
                lbl_estado_reparacion.configure(text="Estado de NVR/DVR")
                widget_estado_reparacion.configure(values=["Apagado", "Intermitente", "Operando parcialmente", "Sin grabación"])
            elif es_energia:
                lbl_estado_reparacion.configure(text="Estado de alimentación/energía")
                widget_estado_reparacion.configure(values=["Sin energía", "Intermitente", "Voltaje inestable", "Operando parcialmente"])
            elif es_conectividad:
                lbl_estado_reparacion.configure(text="Estado de conectividad")
                widget_estado_reparacion.configure(values=["Sin enlace", "Intermitente", "Pérdida de paquetes", "Operando parcialmente"])

            if es_grabador:
                lbl_codigo_error.grid()
                widget_codigo_error.grid()
                lbl_horario_falla.grid()
                widget_horario_falla.grid()
            else:
                lbl_codigo_error.grid_remove()
                widget_codigo_error.grid_remove()
                lbl_horario_falla.grid_remove()
                widget_horario_falla.grid_remove()
                var_rep_codigo_error.set("")
                var_rep_horario_falla.set("")

            for frame, visible in (
                (seccion_rep_energia, es_energia),
                (seccion_rep_conectividad, es_conectividad),
                (seccion_rep_grabador, es_grabador),
                (seccion_rep_equipos, es_camaras or es_grabador),
                (seccion_rep_descripcion, not es_infraestructura),
            ):
                frame.grid() if visible else frame.grid_remove()

            try:
                actualizar_estado_preview()
            except Exception:
                logger.debug("Excepción recuperable controlada.", exc_info=True)

        seccion_mantenimiento = crear_seccion("🧰 Mantenimiento: formulario pendiente", fila_textos + 13)
        registrar_seccion("mantenimiento", seccion_mantenimiento)
        ctk.CTkLabel(
            seccion_mantenimiento,
            text="Este formulario quedará listo para las preguntas de mantenimiento que se definirán en los siguientes movimientos.",
            font=("Montserrat", 12),
            text_color=TEXT_SECONDARY,
            anchor="w",
            justify="left"
        ).grid(row=1, column=0, columnspan=5, sticky="w", padx=6, pady=(0, 5))

        actualizar_campos_infra_existente()
        actualizar_secciones_infraestructura()
        fila_textos = fila_textos + 16

    if tipo_levantamiento == "Aires Acondicionados":
        # =============================================================
        # FORMULARIO Aires Acondicionados ESPECIALIZADO
        # =============================================================
        # El orden del levantamiento sigue el flujo operativo real:
        # necesidad -> sitio -> equipo -> ubicación -> infraestructura ->
        # materiales -> riesgos -> instalación, entrega y pruebas.

        secciones_aa = {}

        def crear_seccion_aa(titulo, fila):
            frame = ctk.CTkFrame(form_body, fg_color="#F8FAFC", corner_radius=14)
            frame.grid(row=fila, column=0, columnspan=5, sticky="ew", pady=(2, 5))
            for col in range(5):
                frame.grid_columnconfigure(col, weight=1, uniform="aa_cols")

            ctk.CTkLabel(
                frame,
                text=titulo,
                font=("Montserrat", 14, "bold"),
                text_color=TEXT_PRIMARY
            ).grid(row=0, column=0, columnspan=5, sticky="w", padx=7, pady=(5, 3))
            return frame

        def label_aa(parent_frame, texto, fila, columna):
            ctk.CTkLabel(
                parent_frame,
                text=texto,
                font=TEXT_SM,
                text_color=TEXT_PRIMARY,
                anchor="w",
                justify="left",
                wraplength=250
            ).grid(row=fila, column=columna, sticky="w", padx=6, pady=(2, 1))

        def entry_aa(parent_frame, texto, variable, placeholder, fila, columna, ancho_corto=False):
            label_aa(parent_frame, texto, fila * 2 + 1, columna)
            entry = ctk.CTkEntry(
                parent_frame,
                textvariable=variable,
                height=32,
                corner_radius=9,
                placeholder_text=placeholder
            )
            if ancho_corto:
                entry.configure(width=140)
                entry.grid(row=fila * 2 + 2, column=columna, sticky="w", padx=6, pady=(0, 3))
            else:
                entry.grid(row=fila * 2 + 2, column=columna, sticky="ew", padx=6, pady=(0, 3))
            return entry

        def option_aa(parent_frame, texto, variable, values, fila, columna, command=None):
            label_aa(parent_frame, texto, fila * 2 + 1, columna)
            option = NativeComboBox(
                parent_frame,
                variable=variable,
                values=values,
                height=32,
                command=command
            )
            option.grid(row=fila * 2 + 2, column=columna, sticky="ew", padx=6, pady=(0, 3))
            return option

        def registrar_seccion_aa(nombre, frame):
            secciones_aa[nombre] = frame

        seccion_aa_necesidad = crear_seccion_aa("❄️ 1. Necesidad inicial del servicio", fila_textos)
        registrar_seccion_aa("necesidad", seccion_aa_necesidad)
        option_aa(seccion_aa_necesidad, "¿Qué se necesita realizar?", var_aa_necesidad, ["Instalación nueva", "Reemplazo", "Reubicación", "Ampliación", "Diagnóstico previo"], 0, 0)
        entry_aa(seccion_aa_necesidad, "¿Cuántos equipos se requieren?", var_aa_cantidad_equipos, "Ej. 2", 0, 1, ancho_corto=True)
        entry_aa(seccion_aa_necesidad, "¿Qué área se va a climatizar?", var_aa_area_climatizar, "Ej. oficina principal", 0, 2)
        option_aa(seccion_aa_necesidad, "Tipo de área", var_aa_tipo_area, ["Oficina", "SITE", "Sala de juntas", "Bodega", "Comedor", "Local", "Otro"], 0, 3)
        entry_aa(seccion_aa_necesidad, "Horario de operación", var_aa_horario_operacion, "Ej. 8:00 a 18:00", 0, 4)

        seccion_aa_sitio = crear_seccion_aa("📐 2. Condiciones del sitio", fila_textos + 1)
        registrar_seccion_aa("sitio", seccion_aa_sitio)
        entry_aa(seccion_aa_sitio, "Dimensiones aproximadas del área", var_aa_dimensiones_area, "Ej. 5 x 6 m", 0, 0)
        entry_aa(seccion_aa_sitio, "Personas en el área", var_aa_personas_area, "Ej. 6", 0, 1, ancho_corto=True)
        entry_aa(seccion_aa_sitio, "Equipos que generan calor", var_aa_equipos_calor, "Ej. 4 PCs / rack", 0, 2)
        option_aa(seccion_aa_sitio, "Exposición solar", var_aa_exposicion_solar, ["Baja", "Media", "Alta"], 0, 3)
        option_aa(seccion_aa_sitio, "¿Requiere cálculo térmico?", var_aa_requiere_calculo, ["Sí", "No"], 0, 4)

        seccion_aa_equipo = crear_seccion_aa("🧊 3. Equipo requerido", fila_textos + 2)
        registrar_seccion_aa("equipo", seccion_aa_equipo)
        option_aa(seccion_aa_equipo, "Tipo de equipo requerido", var_aa_tipo_equipo, ["Mini split", "Piso techo", "Cassette", "Fan & coil", "Paquete", "Precisión", "Otro"], 0, 0)
        entry_aa(seccion_aa_equipo, "Capacidad estimada", var_aa_capacidad, "Ej. 12,000 BTU / 1 TR", 0, 1)
        option_aa(seccion_aa_equipo, "Voltaje requerido", var_aa_voltaje, ["110V", "220V", "Trifásico", "Por validar"], 0, 2)
        option_aa(seccion_aa_equipo, "Refrigerante", var_aa_refrigerante, ["R410A", "R32", "R22", "Por validar"], 0, 3)
        entry_aa(seccion_aa_equipo, "Marca/modelo sugerido", var_aa_marca_modelo, "Opcional", 0, 4)

        seccion_aa_ubicacion = crear_seccion_aa("📍 4. Ubicación de instalación", fila_textos + 3)
        registrar_seccion_aa("ubicacion", seccion_aa_ubicacion)
        entry_aa(seccion_aa_ubicacion, "Ubicación evaporadora", var_aa_ubicacion_evaporadora, "Ej. muro norte", 0, 0)
        entry_aa(seccion_aa_ubicacion, "Ubicación condensadora", var_aa_ubicacion_condensadora, "Ej. azotea/patio", 0, 1)
        entry_aa(seccion_aa_ubicacion, "Distancia entre unidades", var_aa_distancia_unidades, "Ej. 8 m", 0, 2, ancho_corto=True)
        entry_aa(seccion_aa_ubicacion, "Altura de trabajo", var_aa_altura_trabajo, "Ej. 3 m", 0, 3, ancho_corto=True)
        option_aa(seccion_aa_ubicacion, "Acceso para instalación", var_aa_acceso_instalacion, ["Fácil acceso", "Difícil acceso", "Requiere maniobra"], 0, 4)

        seccion_aa_infra = crear_seccion_aa("⚡ 5. Infraestructura necesaria", fila_textos + 4)
        registrar_seccion_aa("infraestructura", seccion_aa_infra)
        option_aa(seccion_aa_infra, "¿Alimentación eléctrica disponible?", var_aa_alimentacion_disponible, ["Sí", "No", "Por validar"], 0, 0)
        option_aa(seccion_aa_infra, "¿Breaker/protección disponible?", var_aa_breaker_disponible, ["Sí", "No", "Por validar"], 0, 1)
        option_aa(seccion_aa_infra, "¿Drenaje disponible?", var_aa_drenaje_disponible, ["Sí", "No", "Por validar"], 0, 2)
        option_aa(seccion_aa_infra, "¿Requiere perforaciones?", var_aa_perforaciones, ["Sí", "No", "Por validar"], 0, 3)
        entry_aa(seccion_aa_infra, "Ruta de tubería/canaleta", var_aa_ruta_tuberia, "Ej. plafón a azotea", 0, 4)

        seccion_aa_materiales = crear_seccion_aa("📦 6. Materiales y consumibles estimados", fila_textos + 5)
        registrar_seccion_aa("materiales", seccion_aa_materiales)
        entry_aa(seccion_aa_materiales, "Tubería de cobre", var_aa_tuberia_cobre_m, "Metros", 0, 0, ancho_corto=True)
        entry_aa(seccion_aa_materiales, "Cableado eléctrico", var_aa_cableado_m, "Metros", 0, 1, ancho_corto=True)
        entry_aa(seccion_aa_materiales, "Drenaje", var_aa_drenaje_m, "Metros", 0, 2, ancho_corto=True)
        entry_aa(seccion_aa_materiales, "Canaleta", var_aa_canaleta_m, "Metros", 0, 3, ancho_corto=True)
        option_aa(seccion_aa_materiales, "¿Requiere bomba de drenaje?", var_aa_bomba_drenaje, ["Sí", "No", "Por validar"], 0, 4)

        seccion_aa_riesgos = crear_seccion_aa("🪜 7. Preparativos, permisos y riesgos", fila_textos + 6)
        registrar_seccion_aa("riesgos", seccion_aa_riesgos)
        option_aa(seccion_aa_riesgos, "¿Requiere permiso del sitio?", var_aa_requiere_permiso, ["Sí", "No"], 0, 0)
        option_aa(seccion_aa_riesgos, "¿Requiere escalera/andamio?", var_aa_requiere_escalera, ["Sí", "No"], 0, 1)
        option_aa(seccion_aa_riesgos, "¿Se debe proteger el área?", var_aa_proteccion_area, ["Sí", "No"], 0, 2)
        entry_aa(seccion_aa_riesgos, "Días de trabajo proyectados", var_aa_dias_trabajo, "Ej. 1", 0, 3, ancho_corto=True)
        entry_aa(seccion_aa_riesgos, "Personas consideradas", var_aa_personas_trabajo, "Ej. 2", 0, 4, ancho_corto=True)

        seccion_aa_pruebas = crear_seccion_aa("✅ 8. Instalación, entrega y pruebas", fila_textos + 7)
        registrar_seccion_aa("pruebas", seccion_aa_pruebas)
        option_aa(seccion_aa_pruebas, "Prueba de vacío", var_aa_prueba_vacio, ["Sí", "No", "No aplica"], 0, 0)
        option_aa(seccion_aa_pruebas, "Prueba de fugas", var_aa_prueba_fugas, ["Sí", "No", "No aplica"], 0, 1)
        option_aa(seccion_aa_pruebas, "Prueba eléctrica", var_aa_prueba_electrica, ["Sí", "No", "No aplica"], 0, 2)
        option_aa(seccion_aa_pruebas, "Prueba de enfriamiento", var_aa_prueba_enfriamiento, ["Sí", "No", "No aplica"], 0, 3)
        option_aa(seccion_aa_pruebas, "Entrega limpia y explicación al usuario", var_aa_limpieza_entrega, ["Sí", "No"], 0, 4)
        option_aa(seccion_aa_pruebas, "Capacitación básica al usuario", var_aa_capacitacion_usuario, ["Sí", "No"], 1, 0)
        widget_aa_soporte_base = option_aa(seccion_aa_pruebas, "Soporte/base para condensadora", var_aa_soporte_base, ["Sí", "No", "Por validar"], 1, 1)

        fila_textos = fila_textos + 8

    if tipo_levantamiento == "Redes Voz y Datos":
        # =============================================================
        # FORMULARIO Redes de Voz y Datos ESPECIALIZADO
        # =============================================================
        # Flujo operativo: necesidad -> alcance -> sitio -> materiales ->
        # rack/energía -> instalación -> pruebas -> entrega.

        def crear_seccion_rvd(titulo, fila):
            frame = ctk.CTkFrame(form_body, fg_color="#F8FAFC", corner_radius=14)
            frame.grid(row=fila, column=0, columnspan=5, sticky="ew", pady=(2, 5))
            for col in range(5):
                frame.grid_columnconfigure(col, weight=1, uniform="rvd_cols")

            ctk.CTkLabel(
                frame,
                text=titulo,
                font=("Montserrat", 14, "bold"),
                text_color=TEXT_PRIMARY
            ).grid(row=0, column=0, columnspan=5, sticky="w", padx=7, pady=(5, 3))
            return frame

        def label_rvd(parent_frame, texto, fila, columna):
            ctk.CTkLabel(
                parent_frame,
                text=texto,
                font=TEXT_SM,
                text_color=TEXT_PRIMARY,
                anchor="w",
                justify="left",
                wraplength=260
            ).grid(row=fila, column=columna, sticky="w", padx=6, pady=(2, 1))

        def entry_rvd(parent_frame, texto, variable, placeholder, fila, columna, ancho_corto=False):
            label_rvd(parent_frame, texto, fila * 2 + 1, columna)
            entry = ctk.CTkEntry(
                parent_frame,
                textvariable=variable,
                height=32,
                corner_radius=9,
                placeholder_text=placeholder
            )
            if ancho_corto:
                entry.configure(width=135)
                entry.grid(row=fila * 2 + 2, column=columna, sticky="w", padx=6, pady=(0, 3))
            else:
                entry.grid(row=fila * 2 + 2, column=columna, sticky="ew", padx=6, pady=(0, 3))
            return entry

        def option_rvd(parent_frame, texto, variable, values, fila, columna, command=None):
            label_rvd(parent_frame, texto, fila * 2 + 1, columna)
            option = NativeComboBox(
                parent_frame,
                variable=variable,
                values=values,
                height=32,
                command=command
            )
            option.grid(row=fila * 2 + 2, column=columna, sticky="ew", padx=6, pady=(0, 3))
            return option

        seccion_rvd_necesidad = crear_seccion_rvd("🌐 1. Necesidad inicial y alcance", fila_textos)
        option_rvd(seccion_rvd_necesidad, "¿Qué se necesita realizar?", var_rvd_necesidad, ["Instalación nueva", "Ampliación", "Reubicación", "Remodelación", "Diagnóstico previo"], 0, 0)
        widget_rvd_tipo_servicio = option_rvd(seccion_rvd_necesidad, "Tipo de servicio", var_rvd_tipo_servicio, ["Datos", "Voz", "Voz y datos", "Fibra óptica", "Mixto"], 0, 1)
        widget_rvd_nodos = entry_rvd(seccion_rvd_necesidad, "¿Cuántos nodos de datos se requieren?", var_rvd_cantidad_nodos, "Ej. 12", 0, 2, ancho_corto=True)
        widget_rvd_voz = entry_rvd(seccion_rvd_necesidad, "¿Cuántos puntos de voz se requieren?", var_rvd_cantidad_telefonia, "Ej. 4", 0, 3, ancho_corto=True)

        def actualizar_campos_tipo_servicio_rvd(*_args):
            instalacion_nueva = var_rvd_necesidad.get() == "Instalación nueva"
            tipo_servicio = var_rvd_tipo_servicio.get()
            habilitar_nodos = not (instalacion_nueva and tipo_servicio == "Voz")
            habilitar_voz = not (instalacion_nueva and tipo_servicio == "Datos")
            if not habilitar_nodos:
                var_rvd_cantidad_nodos.set("")
            if not habilitar_voz:
                var_rvd_cantidad_telefonia.set("")
            widget_rvd_nodos.configure(state="normal" if habilitar_nodos else "disabled")
            widget_rvd_voz.configure(state="normal" if habilitar_voz else "disabled")

        widget_rvd_tipo_servicio.configure(command=lambda _valor: actualizar_campos_tipo_servicio_rvd())
        var_rvd_necesidad.trace_add("write", actualizar_campos_tipo_servicio_rvd)
        actualizar_campos_tipo_servicio_rvd()
        entry_rvd(seccion_rvd_necesidad, "Área o zona de instalación", var_rvd_area_instalacion, "Ej. oficinas planta baja", 0, 4)

        seccion_rvd_sitio = crear_seccion_rvd("📍 2. Condiciones del sitio y ruta", fila_textos + 1)
        entry_rvd(seccion_rvd_sitio, "Horario permitido para trabajo", var_rvd_horario_trabajo, "Ej. 9:00 a 18:00", 0, 0)
        option_rvd(seccion_rvd_sitio, "Acceso para instalación", var_rvd_acceso, ["Fácil acceso", "Difícil acceso", "Requiere maniobra"], 0, 1)
        entry_rvd(seccion_rvd_sitio, "Altura de trabajo", var_rvd_altura_trabajo, "Ej. 3 m", 0, 2, ancho_corto=True)
        option_rvd(seccion_rvd_sitio, "¿Requiere permiso del sitio?", var_rvd_permiso, ["Sí", "No"], 0, 3)
        option_rvd(seccion_rvd_sitio, "Nivel de riesgo", var_rvd_riesgo, ["Bajo", "Medio", "Alto"], 0, 4)

        seccion_rvd_materiales = crear_seccion_rvd("📦 3. Cableado, canalización y consumibles", fila_textos + 2)
        option_rvd(seccion_rvd_materiales, "Cable / tipo", var_rvd_tipo_cable, ["Cat5e", "Cat6", "Cat6A", "Fibra óptica monomodo", "Fibra óptica multimodo", "Coaxial", "Por validar"], 0, 0)
        entry_rvd(seccion_rvd_materiales, "Cable / cantidad o metros", var_rvd_metros_cable, "Ej. 180", 0, 1, ancho_corto=True)
        option_rvd(seccion_rvd_materiales, "Canalización / tipo", var_rvd_tipo_canalizacion, TIPOS_CANALIZACION, 0, 2)
        entry_rvd(seccion_rvd_materiales, "Canalización / cantidad o metros", var_rvd_metros_canalizacion, "Ej. 45", 0, 3, ancho_corto=True)

        option_rvd(seccion_rvd_materiales, "Jacks RJ45 / tipo", var_rvd_tipo_jacks, ["Cat5e", "Cat6", "Cat6A", "Blindado", "Por validar"], 1, 0)
        entry_rvd(seccion_rvd_materiales, "Jacks RJ45 / cantidad", var_rvd_jacks, "Ej. 12", 1, 1, ancho_corto=True)
        option_rvd(seccion_rvd_materiales, "Plugs RJ45 / tipo", var_rvd_tipo_plugs, ["Cat5e", "Cat6", "Cat6A", "Blindado", "Por validar"], 1, 2)
        entry_rvd(seccion_rvd_materiales, "Plugs RJ45 / cantidad", var_rvd_plugs, "Ej. 24", 1, 3, ancho_corto=True)

        option_rvd(seccion_rvd_materiales, "Faceplates / tipo", var_rvd_tipo_faceplates, ["1 puerto", "2 puertos", "4 puertos", "Caja de superficie", "Por validar"], 2, 0)
        entry_rvd(seccion_rvd_materiales, "Faceplates / cantidad", var_rvd_faceplates, "Ej. 12", 2, 1, ancho_corto=True)
        option_rvd(seccion_rvd_materiales, "Patch cords / tipo", var_rvd_tipo_patch_cords, ["Cat5e - 1 m", "Cat5e - 2 m", "Cat6 - 1 m", "Cat6 - 2 m", "Cat6A", "Fibra óptica", "Por validar"], 2, 2)
        entry_rvd(seccion_rvd_materiales, "Patch cords / cantidad", var_rvd_patch_cords, "Ej. 24", 2, 3, ancho_corto=True)

        widget_rvd_patch_panel = option_rvd(seccion_rvd_materiales, "¿Se requiere patch panel?", var_rvd_patch_panel, ["Sí", "No"], 3, 0)
        widget_rvd_tipo_patch_panel = option_rvd(seccion_rvd_materiales, "Patch panel / tipo", var_rvd_tipo_patch_panel, ["12 puertos Cat6", "24 puertos Cat6", "48 puertos Cat6", "Cat6A", "Fibra óptica", "Por validar"], 3, 1)
        widget_rvd_cantidad_patch_panel = entry_rvd(seccion_rvd_materiales, "Patch panel / cantidad", var_rvd_cantidad_patch_panel, "Ej. 1", 3, 2, ancho_corto=True)

        def actualizar_patch_panel_rvd(*_args):
            habilitado = var_rvd_patch_panel.get() == "Sí"
            if not habilitado:
                var_rvd_tipo_patch_panel.set("")
                var_rvd_cantidad_patch_panel.set("")
            elif not var_rvd_tipo_patch_panel.get().strip():
                var_rvd_tipo_patch_panel.set("24 puertos Cat6")
            widget_rvd_tipo_patch_panel.configure(state="readonly" if habilitado else "disabled")
            widget_rvd_cantidad_patch_panel.configure(state="normal" if habilitado else "disabled")

        widget_rvd_patch_panel.configure(command=lambda _valor: actualizar_patch_panel_rvd())
        actualizar_patch_panel_rvd()
        seccion_rvd_materiales.grid_remove()  # Sustituida por captura dinámica común.

        seccion_rvd_rack = crear_seccion_rvd("🗄️ 4. Rack, gabinete, equipo activo y energía", fila_textos + 3)
        widget_rvd_requiere_rack = option_rvd(seccion_rvd_rack, "¿Se requiere rack?", var_rvd_requiere_rack, ["Sí", "No"], 0, 0)
        widget_rvd_tipo_rack = entry_rvd(seccion_rvd_rack, "Tipo/capacidad de rack", var_rvd_tipo_rack, "Ej. rack abierto 24U", 0, 1)
        widget_rvd_requiere_gabinete = option_rvd(seccion_rvd_rack, "¿Se requiere gabinete?", var_rvd_requiere_gabinete, ["Sí", "No"], 0, 2)
        widget_rvd_tipo_gabinete = entry_rvd(seccion_rvd_rack, "Tipo/capacidad de gabinete", var_rvd_tipo_gabinete, "Ej. gabinete pared 12U", 0, 3)
        widget_rvd_ubicacion_rack = entry_rvd(seccion_rvd_rack, "Ubicación de rack/gabinete", var_rvd_ubicacion_rack, "Ej. SITE / cuarto TI", 0, 4)

        widget_rvd_requiere_switch = option_rvd(seccion_rvd_rack, "¿Se requiere switch?", var_rvd_requiere_switch, ["Sí", "No"], 1, 0)
        widget_rvd_tipo_switch = entry_rvd(seccion_rvd_rack, "Tipo/modelo o características del switch", var_rvd_tipo_switch, "Ej. administrable Gigabit", 1, 1)
        widget_rvd_puertos_switch = entry_rvd(seccion_rvd_rack, "Puertos requeridos del switch", var_rvd_puertos_switch, "Ej. 24", 1, 2, ancho_corto=True)
        widget_rvd_switch_poe = option_rvd(seccion_rvd_rack, "¿Switch con PoE?", var_rvd_switch_poe, ["Sí", "No", "Por validar"], 1, 3)

        widget_rvd_ups = option_rvd(seccion_rvd_rack, "¿Se requiere UPS?", var_rvd_ups, ["Sí", "No"], 2, 0)
        widget_rvd_detalle_ups = entry_rvd(seccion_rvd_rack, "Capacidad/detalle de UPS", var_rvd_detalle_ups, "Ej. 1500 VA", 2, 1)
        widget_rvd_contacto = option_rvd(seccion_rvd_rack, "¿Se requiere contacto regulado?", var_rvd_contacto_regulado, ["Sí", "No"], 2, 2)
        widget_rvd_detalle_contacto = entry_rvd(seccion_rvd_rack, "Cantidad/ubicación de contactos", var_rvd_detalle_contacto, "Ej. 2 en SITE", 2, 3)
        widget_rvd_tierra = option_rvd(seccion_rvd_rack, "¿Tierra física disponible?", var_rvd_tierra_fisica, ["Sí", "No"], 3, 0)
        widget_rvd_detalle_tierra = entry_rvd(seccion_rvd_rack, "Detalle o ubicación de tierra física", var_rvd_detalle_tierra, "Ej. barra de tierra en SITE", 3, 1)

        def actualizar_detalles_rack_rvd(*_args):
            requiere_rack = var_rvd_requiere_rack.get() == "Sí"
            requiere_gabinete = var_rvd_requiere_gabinete.get() == "Sí"
            requiere_switch = var_rvd_requiere_switch.get() == "Sí"
            requiere_ups = var_rvd_ups.get() == "Sí"
            requiere_contacto = var_rvd_contacto_regulado.get() == "Sí"
            tierra_disponible = var_rvd_tierra_fisica.get() == "Sí"
            if not requiere_rack: var_rvd_tipo_rack.set("")
            if not requiere_gabinete: var_rvd_tipo_gabinete.set("")
            if not (requiere_rack or requiere_gabinete): var_rvd_ubicacion_rack.set("")
            if not requiere_switch:
                var_rvd_tipo_switch.set("")
                var_rvd_puertos_switch.set("")
                var_rvd_switch_poe.set("Sí")
            if not requiere_ups: var_rvd_detalle_ups.set("")
            if not requiere_contacto: var_rvd_detalle_contacto.set("")
            if not tierra_disponible: var_rvd_detalle_tierra.set("")
            widget_rvd_tipo_rack.configure(state="normal" if requiere_rack else "disabled")
            widget_rvd_tipo_gabinete.configure(state="normal" if requiere_gabinete else "disabled")
            widget_rvd_ubicacion_rack.configure(state="normal" if (requiere_rack or requiere_gabinete) else "disabled")
            widget_rvd_tipo_switch.configure(state="normal" if requiere_switch else "disabled")
            widget_rvd_puertos_switch.configure(state="normal" if requiere_switch else "disabled")
            widget_rvd_switch_poe.configure(state="readonly" if requiere_switch else "disabled")
            widget_rvd_detalle_ups.configure(state="normal" if requiere_ups else "disabled")
            widget_rvd_detalle_contacto.configure(state="normal" if requiere_contacto else "disabled")
            widget_rvd_detalle_tierra.configure(state="normal" if tierra_disponible else "disabled")

        for widget in (widget_rvd_requiere_rack, widget_rvd_requiere_gabinete, widget_rvd_requiere_switch, widget_rvd_ups, widget_rvd_contacto, widget_rvd_tierra):
            widget.configure(command=lambda _valor: actualizar_detalles_rack_rvd())
        actualizar_detalles_rack_rvd()

        seccion_rvd_pruebas = crear_seccion_rvd("📋 5. Estimación de recursos para la instalación", fila_textos + 4)
        entry_rvd(seccion_rvd_pruebas, "Días de trabajo proyectados", var_rvd_dias_trabajo, "Ej. 2", 0, 0, ancho_corto=True)
        entry_rvd(seccion_rvd_pruebas, "Personas consideradas", var_rvd_personas_trabajo, "Ej. 3", 0, 1, ancho_corto=True)

        fila_textos = fila_textos + 5

    if tipo_levantamiento == "Plantas de Energía":
        # =============================================================
        # FORMULARIO Plantas de Energía ESPECIALIZADO
        # =============================================================
        # Orden operativo: necesidad -> carga -> sitio -> combustible -> transferencia -> instalación, pruebas y entrega.

        def crear_seccion_pe(titulo, fila):
            frame = ctk.CTkFrame(form_body, fg_color="#F8FAFC", corner_radius=14)
            frame.grid(row=fila, column=0, columnspan=5, sticky="ew", pady=(2, 5))
            for col in range(5):
                frame.grid_columnconfigure(col, weight=1, uniform="pe_cols")
            ctk.CTkLabel(frame, text=titulo, font=("Montserrat", 14, "bold"), text_color=TEXT_PRIMARY).grid(row=0, column=0, columnspan=5, sticky="w", padx=7, pady=(5, 3))
            return frame

        def label_pe(parent_frame, texto, fila, columna):
            ctk.CTkLabel(parent_frame, text=texto, font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w", justify="left", wraplength=255).grid(row=fila, column=columna, sticky="w", padx=6, pady=(2, 1))

        def entry_pe(parent_frame, texto, variable, placeholder, fila, columna, ancho_corto=False):
            label_pe(parent_frame, texto, fila * 2 + 1, columna)
            entry = ctk.CTkEntry(parent_frame, textvariable=variable, height=32, corner_radius=9, placeholder_text=placeholder)
            if ancho_corto:
                entry.configure(width=135)
                entry.grid(row=fila * 2 + 2, column=columna, sticky="w", padx=6, pady=(0, 3))
            else:
                entry.grid(row=fila * 2 + 2, column=columna, sticky="ew", padx=6, pady=(0, 3))
            return entry

        def option_pe(parent_frame, texto, variable, values, fila, columna, command=None):
            label_pe(parent_frame, texto, fila * 2 + 1, columna)
            option = NativeComboBox(parent_frame, variable=variable, values=values, height=32, command=command)
            option.grid(row=fila * 2 + 2, column=columna, sticky="ew", padx=6, pady=(0, 3))
            return option

        seccion_pe_necesidad = crear_seccion_pe("⚡ 1. Necesidad inicial del respaldo eléctrico", fila_textos)
        option_pe(seccion_pe_necesidad, "¿Qué se necesita realizar?", var_pe_necesidad, ["Instalación nueva", "Reemplazo", "Ampliación", "Reubicación", "Diagnóstico previo"], 0, 0)
        option_pe(seccion_pe_necesidad, "Tipo de planta requerida", var_pe_tipo_planta, ["Diésel", "Gas", "Gasolina", "Híbrida", "Por validar"], 0, 1)
        entry_pe(seccion_pe_necesidad, "Capacidad estimada", var_pe_capacidad, "Ej. 30 kW", 0, 2, ancho_corto=True)
        entry_pe(seccion_pe_necesidad, "Carga a respaldar", var_pe_carga_respaldar, "Ej. SITE, CCTV, oficinas", 0, 3)
        entry_pe(seccion_pe_necesidad, "Tiempo de respaldo requerido", var_pe_tiempo_respaldo, "Ej. 4 h", 0, 4, ancho_corto=True)

        seccion_pe_carga = crear_seccion_pe("🔋 2. Datos eléctricos y carga", fila_textos + 1)
        option_pe(seccion_pe_carga, "Voltaje requerido", var_pe_voltaje, ["127V", "220V", "440V", "Por validar"], 0, 0)
        option_pe(seccion_pe_carga, "Fases", var_pe_fases, ["Monofásico", "Bifásico", "Trifásico", "Por validar"], 0, 1)
        entry_pe(seccion_pe_carga, "Tablero/circuito a respaldar", var_pe_tablero_respaldo, "Ej. T-GEN / tablero TI", 0, 2)
        option_pe(seccion_pe_carga, "Transferencia requerida", var_pe_transferencia, ["Automática", "Manual", "Existente", "Por validar"], 0, 3)
        option_pe(seccion_pe_carga, "¿Requiere ATS?", var_pe_ats, ["Sí", "No", "Por validar"], 0, 4)

        seccion_pe_sitio = crear_seccion_pe("📍 3. Ubicación, sitio y maniobras", fila_textos + 2)
        entry_pe(seccion_pe_sitio, "Ubicación propuesta de la planta", var_pe_ubicacion_planta, "Ej. azotea / patio", 0, 0)
        option_pe(seccion_pe_sitio, "Base o cimentación", var_pe_base_cimentacion, ["Existente", "Requiere base", "Por validar"], 0, 1)
        option_pe(seccion_pe_sitio, "Ventilación adecuada", var_pe_ventilacion, ["Sí", "No", "Por validar"], 0, 2)
        option_pe(seccion_pe_sitio, "Restricción de ruido", var_pe_ruido_restriccion, ["Sí", "No", "Por validar"], 0, 3)
        entry_pe(seccion_pe_sitio, "Distancia al tablero", var_pe_distancia_tablero, "Ej. 25 m", 0, 4, ancho_corto=True)
        option_pe(seccion_pe_sitio, "¿Requiere maniobra/grúa?", var_pe_maniobra, ["Sí", "No", "Por validar"], 1, 0)
        option_pe(seccion_pe_sitio, "¿Requiere permisos del sitio?", var_pe_permisos, ["Sí", "No", "Por validar"], 1, 1)

        seccion_pe_combustible = crear_seccion_pe("⛽ 4. Combustible, escape y seguridad", fila_textos + 3)
        option_pe(seccion_pe_combustible, "Combustible", var_pe_combustible, ["Diésel", "Gas", "Gasolina", "Por validar"], 0, 0)
        option_pe(seccion_pe_combustible, "Tipo de tanque", var_pe_tanque, ["Integrado", "Externo", "Existente", "Por validar"], 0, 1)
        entry_pe(seccion_pe_combustible, "Autonomía estimada", var_pe_autonomia, "Ej. 8 h", 0, 2, ancho_corto=True)
        option_pe(seccion_pe_combustible, "Ruta de escape/gases", var_pe_ruta_escape, ["Adecuada", "Requiere adecuación", "Por validar"], 0, 3)
        option_pe(seccion_pe_combustible, "Protecciones eléctricas", var_pe_protecciones, ["Existentes", "Requeridas", "Por validar"], 0, 4)
        option_pe(seccion_pe_combustible, "Tierra física", var_pe_tierra_fisica, ["Existente", "Requerida", "Por validar"], 1, 0)

        seccion_pe_pruebas = crear_seccion_pe("✅ 5. Instalación, pruebas y entrega", fila_textos + 4)
        option_pe(seccion_pe_pruebas, "Prueba de arranque", var_pe_prueba_arranque, ["Sí", "No"], 0, 0)
        option_pe(seccion_pe_pruebas, "Prueba de transferencia", var_pe_prueba_transferencia, ["Sí", "No", "No aplica"], 0, 1)
        option_pe(seccion_pe_pruebas, "Prueba con carga", var_pe_prueba_carga, ["Sí", "No", "No aplica"], 0, 2)
        option_pe(seccion_pe_pruebas, "Entrega de manual/capacitación", var_pe_entrega_manual, ["Sí", "No"], 0, 3)
        entry_pe(seccion_pe_pruebas, "Días de trabajo proyectados", var_pe_dias_trabajo, "Ej. 3", 0, 4, ancho_corto=True)
        entry_pe(seccion_pe_pruebas, "Personas consideradas", var_pe_personas_trabajo, "Ej. 4", 1, 0, ancho_corto=True)

        fila_textos = fila_textos + 5

    if tipo_levantamiento == "Electricidad":
        # =============================================================
        # FORMULARIO Electricidad ESPECIALIZADO
        # =============================================================
        # Orden operativo: requerimiento -> carga -> tablero -> canalización -> materiales -> seguridad -> pruebas y entrega.

        def crear_seccion_ele(titulo, fila):
            frame = ctk.CTkFrame(form_body, fg_color="#F8FAFC", corner_radius=14)
            frame.grid(row=fila, column=0, columnspan=5, sticky="ew", pady=(2, 5))
            for col in range(5):
                frame.grid_columnconfigure(col, weight=1, uniform="ele_cols")
            ctk.CTkLabel(frame, text=titulo, font=("Montserrat", 14, "bold"), text_color=TEXT_PRIMARY).grid(row=0, column=0, columnspan=5, sticky="w", padx=7, pady=(5, 3))
            return frame

        def label_ele(parent_frame, texto, fila, columna):
            ctk.CTkLabel(parent_frame, text=texto, font=TEXT_SM, text_color=TEXT_PRIMARY, anchor="w", justify="left", wraplength=255).grid(row=fila, column=columna, sticky="w", padx=6, pady=(2, 1))

        def entry_ele(parent_frame, texto, variable, placeholder, fila, columna, ancho_corto=False):
            label_ele(parent_frame, texto, fila * 2 + 1, columna)
            entry = ctk.CTkEntry(parent_frame, textvariable=variable, height=32, corner_radius=9, placeholder_text=placeholder)
            if ancho_corto:
                entry.configure(width=135)
                entry.grid(row=fila * 2 + 2, column=columna, sticky="w", padx=6, pady=(0, 3))
            else:
                entry.grid(row=fila * 2 + 2, column=columna, sticky="ew", padx=6, pady=(0, 3))
            return entry

        def option_ele(parent_frame, texto, variable, values, fila, columna, command=None, width=None):
            label_ele(parent_frame, texto, fila * 2 + 1, columna)
            option = NativeComboBox(parent_frame, variable=variable, values=values, height=32, command=command, width=width)
            option.grid(row=fila * 2 + 2, column=columna, sticky="ew", padx=6, pady=(0, 3))
            return option

        seccion_ele_necesidad = crear_seccion_ele("🔌 1. Necesidad inicial y alcance eléctrico", fila_textos)
        option_ele(seccion_ele_necesidad, "¿Qué se necesita realizar?", var_ele_necesidad, ["Instalación nueva", "Ampliación", "Reubicación", "Corrección", "Diagnóstico previo"], 0, 0)
        tipos_servicio_electricidad = sorted([
            "Alimentador", "Alimentador principal", "Base de medición",
            "Circuito dedicado", "Cometida eléctrica", "Contactos",
            "Iluminación", "Mixto", "Tablero", "Tablero general",
            "Tablero principal", "Tablero secundario",
        ], key=str.casefold)
        option_ele(seccion_ele_necesidad, "Tipo de servicio", var_ele_tipo_servicio, tipos_servicio_electricidad, 0, 1)
        entry_ele(seccion_ele_necesidad, "Área o zona de trabajo", var_ele_area, "Ej. oficinas / SITE", 0, 2)
        entry_ele(seccion_ele_necesidad, "Cantidad de puntos", var_ele_cantidad_puntos, "Ej. 10", 0, 3, ancho_corto=True)
        entry_ele(seccion_ele_necesidad, "Carga estimada", var_ele_carga_estimacion, "Ej. 2 kW", 0, 4, ancho_corto=True)

        seccion_ele_carga = crear_seccion_ele("⚙️ 2. Datos eléctricos, tablero y protecciones", fila_textos + 1)
        option_ele(seccion_ele_carga, "Voltaje", var_ele_voltaje, ["127V", "220V", "440V", "Por validar"], 0, 0)
        option_ele(seccion_ele_carga, "Fases", var_ele_fases, ["Monofásico", "Bifásico", "Trifásico", "Por validar"], 0, 1)
        entry_ele(seccion_ele_carga, "Tablero de origen", var_ele_tablero_origen, "Ej. T-Normal", 0, 2)
        entry_ele(seccion_ele_carga, "Capacidad del tablero", var_ele_capacidad_tablero, "Ej. 100 A", 0, 3, ancho_corto=True)
        option_ele(seccion_ele_carga, "Espacios disponibles", var_ele_espacios_disponibles, ["Sí", "No", "Por validar"], 0, 4)
        entry_ele(seccion_ele_carga, "Breaker requerido", var_ele_breaker_requerido, "Ej. 1P 20A", 1, 0, ancho_corto=True)
        option_ele(seccion_ele_carga, "Tipo de circuito", var_ele_tipo_circuito, ["Normal", "Regulado", "Emergencia", "Dedicado", "Por validar"], 1, 1)

        seccion_ele_materiales = crear_seccion_ele("📦 3. Canalización, cableado y materiales", fila_textos + 2)
        # Infraestructura requerida: formato tipo + cantidad/metros.
        option_ele(seccion_ele_materiales, "Tubos / tipo", var_ele_tubos_tipo, TIPOS_TUBOS, 0, 0)
        option_ele(seccion_ele_materiales, "Tubos / tamaño", var_ele_tubos_tamano, TAMANOS_TUBOS, 0, 1)
        entry_ele(seccion_ele_materiales, "Tubos / cantidad o metros", var_ele_tubos_cantidad, "Ej. 30", 0, 2, ancho_corto=True)
        option_ele(seccion_ele_materiales, "Coples / tipo", var_ele_coples_tipo, TIPOS_COPLES, 0, 3)
        entry_ele(seccion_ele_materiales, "Coples / cantidad", var_ele_coples_cantidad, "Ej. 20", 0, 4, ancho_corto=True)
        option_ele(seccion_ele_materiales, "Registros / tipo", var_ele_registros_tipo, TIPOS_REGISTROS, 1, 0)
        entry_ele(seccion_ele_materiales, "Registros / cantidad", var_ele_registros_cantidad, "Ej. 4", 1, 1, ancho_corto=True)
        option_ele(seccion_ele_materiales, "Conectores / tipo", var_ele_conectores_tipo, TIPOS_CONECTORES, 1, 2)
        entry_ele(seccion_ele_materiales, "Conectores / cantidad", var_ele_conectores_cantidad, "Ej. 20", 1, 3, ancho_corto=True)
        option_ele(seccion_ele_materiales, "Abrazaderas / tipo", var_ele_abrazaderas_tipo, TIPOS_ABRAZADERAS, 2, 0)
        entry_ele(seccion_ele_materiales, "Abrazaderas / cantidad", var_ele_abrazaderas_cantidad, "Ej. 30", 2, 1, ancho_corto=True)
        option_ele(seccion_ele_materiales, "Cable / tipo", var_ele_cable_tipo, TIPOS_CABLE_ELECTRICO, 2, 2)
        entry_ele(seccion_ele_materiales, "Cable / cantidad o metros", var_ele_cable_cantidad, "Ej. 90", 2, 3, ancho_corto=True)

        # Datos eléctricos complementarios que siguen siendo necesarios para el cálculo.
        option_ele(seccion_ele_materiales, "Tipo de canalización", var_ele_canalizacion, TIPOS_CANALIZACION, 3, 0)
        entry_ele(seccion_ele_materiales, "Metros de canalización", var_ele_metros_canalizacion, "Ej. 30", 3, 1, ancho_corto=True)
        entry_ele(seccion_ele_materiales, "Metros de cable", var_ele_metros_cable, "Ej. 90", 3, 2, ancho_corto=True)
        option_ele(seccion_ele_materiales, "Calibre de cable", var_ele_calibre_cable, CALIBRES_CABLE_ELECTRICO, 3, 3)
        entry_ele(seccion_ele_materiales, "Contactos", var_ele_contactos, "Ej. 8", 4, 0, ancho_corto=True)
        entry_ele(seccion_ele_materiales, "Apagadores", var_ele_apagadores, "Ej. 2", 4, 1, ancho_corto=True)
        entry_ele(seccion_ele_materiales, "Luminarias", var_ele_luminarias, "Ej. 6", 4, 2, ancho_corto=True)
        option_ele(seccion_ele_materiales, "Tierra física", var_ele_tierra_fisica, ["Existente", "Requerida", "Por validar"], 4, 3)
        option_ele(seccion_ele_materiales, "Neutro disponible", var_ele_neutro, ["Sí", "No", "Por validar"], 4, 4)
        seccion_ele_materiales.grid_remove()  # Sustituida por captura dinámica común.

        seccion_ele_seguridad = crear_seccion_ele("🦺 4. Condiciones de seguridad y operación", fila_textos + 3)
        entry_ele(seccion_ele_seguridad, "Altura de trabajo", var_ele_altura_trabajo, "Ej. 3 m", 0, 0, ancho_corto=True)
        option_ele(seccion_ele_seguridad, "¿Requiere permiso del sitio?", var_ele_permiso, ["Sí", "No", "Por validar"], 0, 1)
        option_ele(seccion_ele_seguridad, "¿Se debe desenergizar?", var_ele_desenergizar, ["Sí", "No", "Por validar"], 0, 2)
        option_ele(seccion_ele_seguridad, "Nivel de riesgo", var_ele_riesgo, ["Bajo", "Medio", "Alto"], 0, 3)

        seccion_ele_pruebas = crear_seccion_ele("✅ 5. Instalación, pruebas y entrega", fila_textos + 4)
        option_ele(seccion_ele_pruebas, "Prueba de continuidad", var_ele_prueba_continuidad, ["Sí", "No", "No aplica"], 0, 0)
        option_ele(seccion_ele_pruebas, "Prueba de polaridad", var_ele_prueba_polaridad, ["Sí", "No", "No aplica"], 0, 1)
        option_ele(seccion_ele_pruebas, "Medición de voltaje", var_ele_prueba_voltaje, ["Sí", "No", "No aplica"], 0, 2)
        option_ele(seccion_ele_pruebas, "Etiquetado de circuitos", var_ele_etiquetado, ["Sí", "No"], 0, 3)
        option_ele(seccion_ele_pruebas, "Entrega de diagrama", var_ele_entrega_diagrama, ["Sí", "No", "No aplica"], 0, 4)
        entry_ele(seccion_ele_pruebas, "Días de trabajo proyectados", var_ele_dias_trabajo, "Ej. 2", 1, 0, ancho_corto=True)
        entry_ele(seccion_ele_pruebas, "Personas consideradas", var_ele_personas_trabajo, "Ej. 3", 1, 1, ancho_corto=True)

        fila_textos = fila_textos + 5

    if tipo_levantamiento in FORMULARIOS_DETALLADOS_EXTRA:
        # =============================================================
        # FORMULARIOS ESPECIALIZADOS ADICIONALES
        # =============================================================
        # Se usa una plantilla común para mantener espacios, tamaños y comportamiento
        # consistente con los formularios ya liberados.
        def crear_seccion_extra(titulo, fila):
            frame = ctk.CTkFrame(form_body, fg_color="#F8FAFC", corner_radius=14)
            frame.grid(row=fila, column=0, columnspan=5, sticky="ew", pady=(2, 5))
            for col in range(5):
                frame.grid_columnconfigure(col, weight=1, uniform="extra_cols")
            ctk.CTkLabel(
                frame,
                text=titulo,
                font=("Montserrat", 14, "bold"),
                text_color=TEXT_PRIMARY
            ).grid(row=0, column=0, columnspan=5, sticky="w", padx=7, pady=(5, 3))
            return frame

        def label_extra(parent_frame, texto, fila, columna):
            ctk.CTkLabel(
                parent_frame,
                text=texto,
                font=TEXT_SM,
                text_color=TEXT_PRIMARY,
                anchor="w",
                justify="left",
                wraplength=255
            ).grid(row=fila, column=columna, sticky="w", padx=6, pady=(2, 1))

        def entry_extra(parent_frame, texto, variable, placeholder, fila, columna, ancho_corto=False):
            label_extra(parent_frame, texto, fila * 2 + 1, columna)
            entry = ctk.CTkEntry(
                parent_frame,
                textvariable=variable,
                height=32,
                corner_radius=9,
                placeholder_text=placeholder
            )
            if ancho_corto:
                entry.configure(width=145)
                entry.grid(row=fila * 2 + 2, column=columna, sticky="w", padx=6, pady=(0, 3))
            else:
                entry.grid(row=fila * 2 + 2, column=columna, sticky="ew", padx=6, pady=(0, 3))
            if "fecha" in texto.lower():
                asociar_selector_fecha(entry, parent_frame, variable)
            return entry

        def option_extra(parent_frame, texto, variable, values, fila, columna):
            label_extra(parent_frame, texto, fila * 2 + 1, columna)
            option = NativeComboBox(parent_frame, variable=variable, values=values, height=32)
            option.grid(row=fila * 2 + 2, column=columna, sticky="ew", padx=6, pady=(0, 3))
            return option

        secciones_extra_frames = []
        extra_widgets = {}
        indice_visual = 0
        for indice_seccion, (titulo_sec, campos_sec) in enumerate(FORMULARIOS_DETALLADOS_EXTRA[tipo_levantamiento]["secciones"]):
            if tipo_levantamiento in ("Control de Accesos", "Enlaces Inalámbricos") and "Cableado, canalización e infraestructura requerida" in titulo_sec:
                continue
            seccion_extra = crear_seccion_extra(titulo_sec, fila_textos + indice_visual)
            indice_visual += 1
            secciones_extra_frames.append(seccion_extra)
            for indice_campo, (clave, tipo_campo, etiqueta, opciones_placeholder, _default) in enumerate(campos_sec):
                fila_campo = indice_campo // 5
                columna_campo = indice_campo % 5
                variable = vars_extra[clave]
                etiqueta_lower = etiqueta.lower()
                es_corto = any(palabra in etiqueta_lower for palabra in ("cantidad", "días", "personas", "metros", "distancia", "altura", "capacidad", "consumo", "área", "ancho"))
                if tipo_campo == "option":
                    extra_widgets[clave] = option_extra(seccion_extra, etiqueta, variable, opciones_placeholder, fila_campo, columna_campo)
                else:
                    extra_widgets[clave] = entry_extra(seccion_extra, etiqueta, variable, opciones_placeholder, fila_campo, columna_campo, ancho_corto=es_corto)

        # La canalización de estos formularios se captura en la sección dinámica común.

        fila_textos = fila_textos + len(secciones_extra_frames)

    # =============================================================
    # CANALIZACIÓN, CABLEADO Y MATERIALES (CAPTURA DINÁMICA)
    # =============================================================
    tipos_con_canalizacion = {
        "Seguridad y Monitoreo", "Redes Voz y Datos", "Electricidad",
        "Control de Accesos", "Enlaces Inalámbricos",
    }
    seccion_canalizacion_dinamica = None
    var_requiere_canalizacion = ctk.StringVar(value="Sí")

    def catalogo_tipos_por_categoria(categoria):
        if categoria == "Tubo": return list(TIPOS_TUBOS)
        if categoria == "Cople": return list(TIPOS_COPLES)
        if categoria == "Registro": return list(TIPOS_REGISTROS)
        if categoria == "Conector": return list(TIPOS_CONECTORES)
        if categoria == "Abrazadera": return list(TIPOS_ABRAZADERAS)
        if categoria == "Canalización": return list(TIPOS_CANALIZACION)
        if categoria == "Cable":
            if tipo_levantamiento == "Electricidad": return list(TIPOS_CABLE_ELECTRICO)
            if tipo_levantamiento == "Enlaces Inalámbricos": return list(dict.fromkeys(TIPOS_CABLE_EXTERIOR + TIPOS_CABLE_ELECTRICO))
            return list(dict.fromkeys(TIPOS_CABLE_DATOS_CONTROL + TIPOS_CABLE_ELECTRICO))
        if categoria == "Jack RJ45": return ["Cat5e", "Cat6", "Cat6A", "Blindado"]
        if categoria == "Plug RJ45": return ["Cat5e", "Cat6", "Cat6A", "Blindado"]
        if categoria == "Faceplate": return ["1 puerto", "2 puertos", "4 puertos", "Caja de superficie"]
        if categoria == "Patch cord": return ["Cat5e - 1 m", "Cat5e - 2 m", "Cat6 - 1 m", "Cat6 - 2 m", "Cat6A", "Fibra óptica"]
        if categoria == "Patch panel": return ["12 puertos Cat6", "24 puertos Cat6", "48 puertos Cat6", "Cat6A", "Fibra óptica"]
        return ["Otro"]

    def catalogo_especificacion_por_categoria(categoria):
        if categoria == "Tubo": return list(TAMANOS_TUBOS)
        if categoria == "Cable" and tipo_levantamiento == "Electricidad": return list(CALIBRES_CABLE_ELECTRICO)
        return ["No aplica", "Por definir"]

    def obtener_canalizacion_materiales_json():
        # En Seguridad y Monitoreo la canalización es parte exclusiva de
        # Instalación. Reparación y Mantenimiento no deben guardar partidas
        # ocultas ni heredarlas hacia Supabase/PDF.
        if (
            tipo_levantamiento == "Seguridad y Monitoreo"
            and var_modalidad_levantamiento.get().strip() != "Instalación"
        ):
            return []
        if tipo_levantamiento in tipos_con_canalizacion and var_requiere_canalizacion.get() == "No":
            return []
        filas = []
        for item in canalizacion_materiales_items:
            categoria = item["categoria"].get().strip()
            tipo = item["tipo"].get().strip()
            cantidad = item["cantidad"].get().strip()
            if not (categoria or tipo or cantidad):
                continue
            filas.append({
                "categoria": categoria,
                "tipo": tipo,
                "tamano_calibre_especificacion": item["especificacion"].get().strip(),
                "cantidad": cantidad,
                "unidad": item["unidad"].get().strip(),
            })
        return filas

    def canalizacion_materiales_completa():
        if tipo_levantamiento not in tipos_con_canalizacion:
            return True
        if (
            tipo_levantamiento == "Seguridad y Monitoreo"
            and var_modalidad_levantamiento.get().strip() != "Instalación"
        ):
            return True
        if var_requiere_canalizacion.get() == "No":
            return True
        filas = obtener_canalizacion_materiales_json()
        if not filas:
            return False
        for fila in filas:
            if not (fila.get("categoria") and fila.get("tipo") and fila.get("cantidad") and fila.get("unidad")):
                return False
            if fila.get("categoria") == "Tubo" and not fila.get("tamano_calibre_especificacion"):
                return False
            if fila.get("categoria") == "Cable" and tipo_levantamiento == "Electricidad" and not fila.get("tamano_calibre_especificacion"):
                return False
        return True

    def construir_resumen_canalizacion_materiales():
        filas = obtener_canalizacion_materiales_json()
        if not filas:
            return ""
        lineas = ["CANALIZACIÓN, CABLEADO Y MATERIALES:"]
        for fila in filas:
            extra = fila.get("tamano_calibre_especificacion")
            linea = f"- {fila['categoria']}: {fila['tipo']}"
            if extra and extra not in ("No aplica", "Por definir"):
                linea += f" | {extra}"
            linea += f" | {fila['cantidad']} {fila['unidad']}"
            lineas.append(linea)
        return "\n".join(lineas)

    if tipo_levantamiento in tipos_con_canalizacion:
        seccion_canalizacion_dinamica = ctk.CTkFrame(form_body, fg_color="#F8FAFC", corner_radius=14)
        seccion_canalizacion_dinamica.grid(row=fila_textos, column=0, columnspan=5, sticky="ew", pady=(2, 5))
        for col, peso in enumerate((2, 4, 3, 2, 2, 1)):
            seccion_canalizacion_dinamica.grid_columnconfigure(col, weight=peso)
        ctk.CTkLabel(seccion_canalizacion_dinamica, text="🧱 Canalización, cableado y materiales",
                     font=("Montserrat", 14, "bold"), text_color=TEXT_PRIMARY).grid(
            row=0, column=0, columnspan=6, sticky="w", padx=7, pady=(5, 1))
        ctk.CTkLabel(seccion_canalizacion_dinamica,
                     text="Agrega todas las partidas necesarias. Puedes registrar varios tipos, medidas y cantidades.",
                     font=TEXT_SM, text_color=TEXT_SECONDARY).grid(
            row=1, column=0, columnspan=6, sticky="w", padx=7, pady=(0, 4))
        ctk.CTkLabel(seccion_canalizacion_dinamica, text="¿Se requiere?", font=("Montserrat", 11, "bold")).grid(row=2, column=0, sticky="w", padx=5)
        combo_requiere = NativeComboBox(seccion_canalizacion_dinamica, variable=var_requiere_canalizacion, values=["Sí", "No"], width=120, height=31)
        combo_requiere.grid(row=3, column=0, sticky="w", padx=5, pady=(0,4))
        for col, encabezado in enumerate(("Categoría", "Tipo", "Tamaño / calibre / especificación", "Cantidad", "Unidad", "Acción")):
            ctk.CTkLabel(seccion_canalizacion_dinamica, text=encabezado, font=("Montserrat", 11, "bold"), text_color=TEXT_PRIMARY).grid(row=4, column=col, sticky="w", padx=5, pady=(0,2))

        categorias = ["Tubo", "Cople", "Registro", "Conector", "Abrazadera", "Canalización", "Cable"]
        if tipo_levantamiento == "Redes Voz y Datos":
            categorias += ["Jack RJ45", "Plug RJ45", "Faceplate", "Patch cord", "Patch panel"]

        def agregar_partida_canalizacion(categoria_inicial="Tubo"):
            fila = 5 + len(canalizacion_materiales_items)
            var_categoria = ctk.StringVar(value=categoria_inicial)
            var_tipo_item = ctk.StringVar()
            var_especificacion = ctk.StringVar()
            var_cantidad_item = ctk.StringVar()
            var_unidad_item = ctk.StringVar(value="Metro(s)" if categoria_inicial in ("Tubo", "Canalización", "Cable") else "Pieza(s)")
            combo_categoria = NativeComboBox(seccion_canalizacion_dinamica, variable=var_categoria, values=categorias, width=155, height=31)
            combo_tipo = NativeComboBox(seccion_canalizacion_dinamica, variable=var_tipo_item, values=[], width=300, height=31)
            combo_especificacion = NativeComboBox(seccion_canalizacion_dinamica, variable=var_especificacion, values=[], width=225, height=31)
            entrada_cantidad = ctk.CTkEntry(seccion_canalizacion_dinamica, textvariable=var_cantidad_item, width=120, height=31, placeholder_text="Ej. 20")
            combo_unidad = NativeComboBox(seccion_canalizacion_dinamica, variable=var_unidad_item,
                                          values=["Metro(s)", "Pieza(s)", "Caja(s)", "Rollo(s)", "Juego(s)"], width=125, height=31)
            widgets = [combo_categoria, combo_tipo, combo_especificacion, entrada_cantidad, combo_unidad]
            for col, widget in enumerate(widgets):
                widget.grid(row=fila, column=col, sticky="ew", padx=5, pady=2)
            item = {"categoria": var_categoria, "tipo": var_tipo_item, "especificacion": var_especificacion,
                    "cantidad": var_cantidad_item, "unidad": var_unidad_item, "widgets": widgets}

            def actualizar_catalogos(*_):
                categoria = var_categoria.get().strip()
                tipos = catalogo_tipos_por_categoria(categoria)
                especificaciones = catalogo_especificacion_por_categoria(categoria)
                combo_tipo.configure(values=tipos)
                combo_especificacion.configure(values=especificaciones)
                if var_tipo_item.get() not in tipos: var_tipo_item.set(tipos[0] if tipos else "")
                if var_especificacion.get() not in especificaciones: var_especificacion.set(especificaciones[0] if especificaciones else "")
                if categoria in ("Tubo", "Canalización", "Cable") and not var_unidad_item.get(): var_unidad_item.set("Metro(s)")
                elif categoria not in ("Tubo", "Canalización", "Cable") and var_unidad_item.get() == "Metro(s)": var_unidad_item.set("Pieza(s)")
            var_categoria.trace_add("write", actualizar_catalogos)
            actualizar_catalogos()

            def eliminar():
                for w in item["widgets"]:
                    try: w.destroy()
                    except Exception: pass
                try: btn_eliminar.destroy()
                except Exception: pass
                canalizacion_materiales_items[:] = [x for x in canalizacion_materiales_items if x is not item]
            btn_eliminar = ctk.CTkButton(seccion_canalizacion_dinamica, text="Eliminar", width=78, height=31,
                                         fg_color="#DC2626", hover_color="#B91C1C", command=eliminar)
            btn_eliminar.grid(row=fila, column=5, sticky="ew", padx=5, pady=2)
            item["widgets"].append(btn_eliminar)
            canalizacion_materiales_items.append(item)

        def actualizar_requiere_canalizacion(*_):
            habilitado = var_requiere_canalizacion.get() == "Sí"
            for item in canalizacion_materiales_items:
                for w in item.get("widgets", []):
                    try: w.configure(state="normal" if habilitado else "disabled")
                    except Exception: pass
        var_requiere_canalizacion.trace_add("write", actualizar_requiere_canalizacion)
        ctk.CTkButton(seccion_canalizacion_dinamica, text="➕ Agregar partida", height=32, fg_color=PRIMARY,
                      command=agregar_partida_canalizacion).grid(row=1000, column=0, columnspan=2, sticky="w", padx=5, pady=(4,5))
        agregar_partida_canalizacion("Tubo")
        fila_textos += 1

    # =============================================================
    # EQUIPOS PRINCIPALES REQUERIDOS (CATÁLOGO ESCALABLE)
    # =============================================================
    # Familia/subfamilia se mantienen estables; marca y modelo son dinámicos.
    seccion_equipos = ctk.CTkFrame(form_body, fg_color="#F8FAFC", corner_radius=14)
    seccion_equipos.grid(row=fila_textos, column=0, columnspan=5, sticky="ew", pady=(2, 5))
    for col, peso in enumerate((2, 2, 1, 2, 2, 3, 1)):
        seccion_equipos.grid_columnconfigure(col, weight=peso)

    ctk.CTkLabel(
        seccion_equipos, text="📦 Equipos principales requeridos",
        font=("Montserrat", 14, "bold"), text_color=TEXT_PRIMARY
    ).grid(row=0, column=0, columnspan=7, sticky="w", padx=7, pady=(5, 1))
    ctk.CTkLabel(
        seccion_equipos,
        text="Selecciona familia y subfamilia; captura marca y modelo vigente. Así el catálogo no queda obsoleto.",
        font=TEXT_SM, text_color=TEXT_SECONDARY, anchor="w", justify="left"
    ).grid(row=1, column=0, columnspan=7, sticky="w", padx=7, pady=(0, 4))

    for col, encabezado in enumerate(("Familia", "Subfamilia", "Cantidad", "Marca", "Modelo", "Características técnicas", "Acción")):
        ctk.CTkLabel(seccion_equipos, text=encabezado, font=("Montserrat", 12, "bold"), text_color=TEXT_PRIMARY).grid(
            row=2, column=col, sticky="w", padx=4, pady=(0, 2)
        )

    def agregar_equipo_catalogo():
        fila_eq = 3 + len(equipos_catalogo_items)
        familias = obtener_nombres_familias(tipo_levantamiento)
        familia_inicial = familias[0] if familias else "Otro"
        subfamilias = obtener_subfamilias(tipo_levantamiento, familia_inicial)
        var_familia_eq = ctk.StringVar(value=familia_inicial)
        var_subfamilia_eq = ctk.StringVar(value=subfamilias[0] if subfamilias else "Otro")
        var_cantidad_eq = ctk.StringVar(value="1")
        var_marca_eq = ctk.StringVar(value="Por definir")
        var_modelo_eq = ctk.StringVar()
        var_caracteristicas_eq = ctk.StringVar()

        om_familia = NativeComboBox(seccion_equipos, variable=var_familia_eq, values=familias, height=31)
        om_familia.grid(row=fila_eq, column=0, sticky="ew", padx=4, pady=2)
        om_subfamilia = NativeComboBox(seccion_equipos, variable=var_subfamilia_eq, values=subfamilias, height=31)
        om_subfamilia.grid(row=fila_eq, column=1, sticky="ew", padx=4, pady=2)
        ctk.CTkEntry(seccion_equipos, textvariable=var_cantidad_eq, width=80, height=31, placeholder_text="Ej. 2").grid(row=fila_eq, column=2, sticky="w", padx=4, pady=2)
        combo_marca = NativeComboBox(seccion_equipos, variable=var_marca_eq, values=MARCAS_COMUNES, state="normal", dropdown_rows=8)
        combo_marca.grid(row=fila_eq, column=3, sticky="ew", padx=4, pady=2)
        ctk.CTkEntry(seccion_equipos, textvariable=var_modelo_eq, height=31, placeholder_text="Modelo vigente o por definir").grid(row=fila_eq, column=4, sticky="ew", padx=4, pady=2)
        entry_car = ctk.CTkEntry(
            seccion_equipos, textvariable=var_caracteristicas_eq, height=31,
            placeholder_text=obtener_sugerencia_caracteristicas(tipo_levantamiento, familia_inicial)
        )
        entry_car.grid(row=fila_eq, column=5, sticky="ew", padx=4, pady=2)

        def cambiar_familia(valor):
            nuevas = obtener_subfamilias(tipo_levantamiento, valor)
            om_subfamilia.configure(values=nuevas)
            var_subfamilia_eq.set(nuevas[0] if nuevas else "Otro")
            entry_car.configure(placeholder_text=obtener_sugerencia_caracteristicas(tipo_levantamiento, valor))

        om_familia.configure(command=cambiar_familia)
        item_equipo = {
            "familia": var_familia_eq, "subfamilia": var_subfamilia_eq,
            "cantidad": var_cantidad_eq, "marca": var_marca_eq,
            "modelo": var_modelo_eq, "caracteristicas": var_caracteristicas_eq,
            "widgets": [om_familia, om_subfamilia, combo_marca],
        }

        def eliminar_equipo():
            for widget in item_equipo.get("widgets", []):
                try:
                    widget.destroy()
                except Exception:
                    logger.debug("Excepción recuperable controlada.", exc_info=True)
            equipos_catalogo_items[:] = [x for x in equipos_catalogo_items if x is not item_equipo]

        btn_eliminar = ctk.CTkButton(
            seccion_equipos, text="Eliminar", width=82, height=31,
            fg_color="#DC2626", hover_color="#B91C1C", command=eliminar_equipo
        )
        btn_eliminar.grid(row=fila_eq, column=6, sticky="ew", padx=4, pady=2)
        item_equipo["widgets"].extend([
            btn_eliminar,
            # localizar widgets creados en esa fila para borrarlos juntos
            *[w for w in seccion_equipos.grid_slaves(row=fila_eq) if w not in (btn_eliminar, om_familia, om_subfamilia)]
        ])
        equipos_catalogo_items.append(item_equipo)

    ctk.CTkButton(
        seccion_equipos, text="➕ Agregar equipo", height=32, fg_color=PRIMARY,
        command=agregar_equipo_catalogo
    ).grid(row=1000, column=0, columnspan=2, sticky="w", padx=5, pady=(4, 5))

    def obtener_equipos_catalogo_json():
        equipos = []
        for item in equipos_catalogo_items:
            familia = item["familia"].get().strip()
            if not familia:
                continue
            equipos.append({
                "familia": familia,
                "subfamilia": item["subfamilia"].get().strip(),
                "cantidad": item["cantidad"].get().strip() or "1",
                "marca": item["marca"].get().strip(),
                "modelo": item["modelo"].get().strip(),
                "caracteristicas": item["caracteristicas"].get().strip(),
            })
        return equipos

    def construir_resumen_equipos_catalogo():
        equipos = obtener_equipos_catalogo_json()
        if not equipos:
            return ""
        lineas = ["EQUIPOS PRINCIPALES REQUERIDOS:"]
        for eq in equipos:
            linea = f"- {eq['cantidad']} x {eq['familia']} / {eq['subfamilia']} | {eq['marca']} {eq['modelo']}".strip()
            if eq["caracteristicas"]:
                linea += f" | {eq['caracteristicas']}"
            lineas.append(linea)
        return "\n".join(lineas)

    fila_textos += 1

    # =============================================================
    # MATERIALES MISCELÁNEOS (COMÚN A TODOS LOS LEVANTAMIENTOS)
    # =============================================================
    # La captura inicia vacía. Si el técnico agrega una fila, el material
    # se considera requerido por definición; no se solicita un Sí/No redundante.
    seccion_misc = ctk.CTkFrame(form_body, fg_color="#F8FAFC", corner_radius=14)
    seccion_misc.grid(row=fila_textos, column=0, columnspan=5, sticky="ew", pady=(2, 5))
    seccion_misc.grid_columnconfigure(0, weight=2)
    seccion_misc.grid_columnconfigure(1, weight=1)
    seccion_misc.grid_columnconfigure(2, weight=1)
    seccion_misc.grid_columnconfigure(3, weight=3)
    seccion_misc.grid_columnconfigure(4, weight=1)

    ctk.CTkLabel(
        seccion_misc, text="🧰 Materiales misceláneos y consumibles",
        font=("Montserrat", 14, "bold"), text_color=TEXT_PRIMARY
    ).grid(row=0, column=0, columnspan=5, sticky="w", padx=7, pady=(5, 1))
    ctk.CTkLabel(
        seccion_misc,
        text="Agrega únicamente los materiales necesarios e indica cantidad, unidad y especificación para cotización.",
        font=TEXT_SM, text_color=TEXT_SECONDARY, anchor="w", justify="left"
    ).grid(row=1, column=0, columnspan=5, sticky="w", padx=7, pady=(0, 4))

    for col, encabezado in enumerate(("Material", "Cantidad", "Unidad", "Especificación / medida", "Acción")):
        ctk.CTkLabel(seccion_misc, text=encabezado, font=("Montserrat", 12, "bold"), text_color=TEXT_PRIMARY).grid(
            row=2, column=col, sticky="w", padx=5, pady=(0, 2)
        )

    def agregar_material_miscelaneo(material_catalogo=None):
        material_catalogo = material_catalogo or {}
        if isinstance(material_catalogo, str):
            material_catalogo = {"nombre": material_catalogo}

        nombre_material = material_catalogo.get("nombre", "")
        categoria_material = material_catalogo.get("categoria", "Otro")
        unidad_default = material_catalogo.get("unidad", "Pieza(s)")
        especificacion_sugerida = material_catalogo.get("especificacion_sugerida", "")

        fila = 3 + len(materiales_miscelaneos_items)
        var_material = ctk.StringVar(value=nombre_material)
        var_categoria = ctk.StringVar(value=categoria_material)
        var_cantidad = ctk.StringVar()
        var_unidad = ctk.StringVar(value=unidad_default if unidad_default in UNIDADES_MATERIAL else "Pieza(s)")
        var_especificacion = ctk.StringVar()

        entrada_material = ctk.CTkEntry(seccion_misc, textvariable=var_material, height=31, corner_radius=8)
        entrada_material.grid(row=fila, column=0, sticky="ew", padx=5, pady=2)
        if nombre_material:
            entrada_material.configure(state="readonly")

        entrada_cantidad = ctk.CTkEntry(
            seccion_misc, textvariable=var_cantidad, width=95, height=31, corner_radius=8,
            placeholder_text="Ej. 20"
        )
        entrada_cantidad.grid(row=fila, column=1, sticky="w", padx=5, pady=2)
        opcion_unidad = NativeComboBox(
            seccion_misc, variable=var_unidad, values=UNIDADES_MATERIAL,
            width=125, height=31
        )
        opcion_unidad.grid(row=fila, column=2, sticky="w", padx=5, pady=2)
        entrada_especificacion = ctk.CTkEntry(
            seccion_misc, textvariable=var_especificacion, height=31, corner_radius=8,
            placeholder_text=especificacion_sugerida or "Medida, material, color o presentación"
        )
        entrada_especificacion.grid(row=fila, column=3, sticky="ew", padx=5, pady=2)

        item_material = {
            "material": var_material,
            "categoria": var_categoria,
            "cantidad": var_cantidad,
            "unidad": var_unidad,
            "especificacion": var_especificacion,
            "widgets": [entrada_material, entrada_cantidad, opcion_unidad, entrada_especificacion],
        }

        def eliminar_material():
            for widget in item_material.get("widgets", []):
                try:
                    widget.destroy()
                except Exception:
                    logger.debug("Excepción recuperable controlada.", exc_info=True)
            materiales_miscelaneos_items[:] = [x for x in materiales_miscelaneos_items if x is not item_material]

        btn_eliminar = ctk.CTkButton(
            seccion_misc, text="Eliminar", width=82, height=31,
            fg_color="#DC2626", hover_color="#B91C1C", command=eliminar_material
        )
        btn_eliminar.grid(row=fila, column=4, sticky="ew", padx=5, pady=2)
        item_material["widgets"].append(btn_eliminar)
        materiales_miscelaneos_items.append(item_material)

    ctk.CTkButton(
        seccion_misc, text="➕ Agregar otro material", height=32, fg_color=PRIMARY,
        command=lambda: agregar_material_miscelaneo(None)
    ).grid(row=1000, column=0, columnspan=2, sticky="w", padx=5, pady=(4, 5))

    # Flujo dinámico exclusivo para Tecnología, Equipos y Periféricos.
    # - Suministro: solo información del producto/equipo; sin materiales ni mano de obra.
    # - Suministro e instalación: producto + instalación, materiales, días y personal.
    if tipo_levantamiento == "Tecnología, Equipos y Periféricos":
        def actualizar_secciones_ti(*_args):
            accion = vars_extra["accion_ti"].get().strip()

            if accion == "Suministro":
                visibles = {0, 1, 4}
                seccion_misc.grid_remove()
                # Evita guardar materiales previamente seleccionados si el usuario
                # cambia de "Suministro e instalación" a "Suministro".
                for item in list(materiales_miscelaneos_items):
                    for widget in item.get("widgets", []):
                        try:
                            widget.destroy()
                        except Exception:
                            logger.debug("Excepción recuperable controlada.", exc_info=True)
                materiales_miscelaneos_items.clear()
            elif accion == "Suministro e instalación":
                visibles = {0, 1, 4, 5}
                seccion_misc.grid()
            elif accion == "Revisión":
                visibles = {0, 1, 2, 5}
                seccion_misc.grid()
            elif accion in ("Mantenimiento", "Reparación"):
                visibles = {0, 1, 2, 3, 5}
                seccion_misc.grid()
            else:
                visibles = {0, 1}
                seccion_misc.grid_remove()

            for idx, frame_sec in enumerate(secciones_extra_frames):
                if idx in visibles:
                    frame_sec.grid()
                else:
                    frame_sec.grid_remove()

        vars_extra["accion_ti"].trace_add("write", actualizar_secciones_ti)
        actualizar_secciones_ti()

    fila_textos += 1

    if tipo_levantamiento in TIPOS_LEVANTAMIENTO_ESPECIALIZADOS:
        # En formularios especializados el resumen técnico se construye desde campos estructurados.
        # Se conserva un textbox oculto como respaldo para no romper funciones existentes.
        txt_descripcion = ctk.CTkTextbox(form_body, height=1)
        titulo_observaciones = (
            "Descripción detallada del servicio"
            if tipo_levantamiento == "Seguridad y Monitoreo" else "Observaciones"
        )
        txt_observaciones = campo_texto(titulo_observaciones, altura=100, fila=fila_textos)
    else:
        txt_descripcion = campo_texto("Descripción del levantamiento", altura=90, fila=fila_textos)
        txt_observaciones = campo_texto("Observaciones", altura=100, fila=fila_textos + 1)

    if tipo_levantamiento == "Seguridad y Monitoreo":
        def actualizar_secciones_comunes_seguridad(*_args):
            modalidad = var_modalidad_levantamiento.get()

            # La captura dinámica de canalización/materiales de infraestructura
            # corresponde únicamente a Instalación en Seguridad y Monitoreo.
            if seccion_canalizacion_dinamica is not None:
                if modalidad == "Instalación":
                    seccion_canalizacion_dinamica.grid()
                else:
                    seccion_canalizacion_dinamica.grid_remove()

            if modalidad == "Instalación":
                seccion_equipos.grid()
                seccion_misc.grid()
                txt_observaciones.master.grid()
            elif modalidad == "Reparación":
                seccion_equipos.grid_remove()
                seccion_misc.grid_remove()
                txt_observaciones.master.grid_remove()
            else:  # Mantenimiento
                seccion_equipos.grid_remove()
                seccion_misc.grid()
                txt_observaciones.master.grid()

        var_modalidad_levantamiento.trace_add("write", actualizar_secciones_comunes_seguridad)
        actualizar_secciones_comunes_seguridad()

    def obtener_materiales_miscelaneos_json():
        """Devuelve únicamente los materiales marcados como requeridos."""
        materiales = []
        for item in materiales_miscelaneos_items:
            material = item["material"].get().strip()
            if not material:
                continue
            materiales.append({
                "material": material,
                "categoria": item.get("categoria").get().strip() if item.get("categoria") else "Otro",
                "requerido": "Sí",
                "cantidad": item["cantidad"].get().strip(),
                "unidad": item["unidad"].get().strip(),
                "especificacion": item["especificacion"].get().strip(),
            })
        return materiales

    def construir_resumen_materiales_miscelaneos():
        materiales = obtener_materiales_miscelaneos_json()
        if not materiales:
            return ""
        lineas = ["MATERIALES MISCELÁNEOS Y CONSUMIBLES:"]
        for item in materiales:
            cantidad = item.get("cantidad") or "Por definir"
            unidad = item.get("unidad") or ""
            especificacion = item.get("especificacion")
            linea = f"- {item['material']}: {cantidad} {unidad}".strip()
            if especificacion:
                linea += f" | {especificacion}"
            lineas.append(linea)
        return "\n".join(lineas)

    def obtener_equipos_danados_json():
        """Devuelve los equipos dañados capturados como lista JSON-compatible."""
        equipos = []
        try:
            for item in equipos_danados_items:
                equipos.append({
                    "tipo_equipo": item["tipo"].get().strip(),
                    "marca": item["marca"].get().strip(),
                    "modelo": item["modelo"].get().strip(),
                    "numero_serie": item["serie"].get().strip(),
                })
        except Exception:
            logger.debug("Excepción recuperable controlada.", exc_info=True)
        return equipos

    def obtener_detalle_tecnico_json():
        """Devuelve los campos dinámicos del formulario especializado en JSON."""
        if tipo_levantamiento == "Aires Acondicionados":
            return {
                "tipo_levantamiento": "Aires Acondicionados",
                "necesidad_inicial": {
                    "necesidad": var_aa_necesidad.get().strip(),
                    "cantidad_equipos": var_aa_cantidad_equipos.get().strip(),
                    "area_climatizar": var_aa_area_climatizar.get().strip(),
                    "tipo_area": var_aa_tipo_area.get().strip(),
                    "horario_operacion": var_aa_horario_operacion.get().strip(),
                },
                "condiciones_sitio": {
                    "dimensiones_area": var_aa_dimensiones_area.get().strip(),
                    "personas_area": var_aa_personas_area.get().strip(),
                    "equipos_calor": var_aa_equipos_calor.get().strip(),
                    "exposicion_solar": var_aa_exposicion_solar.get().strip(),
                    "requiere_calculo_termico": var_aa_requiere_calculo.get().strip(),
                },
                "equipo_requerido": {
                    "tipo_equipo": var_aa_tipo_equipo.get().strip(),
                    "capacidad": var_aa_capacidad.get().strip(),
                    "voltaje": var_aa_voltaje.get().strip(),
                    "refrigerante": var_aa_refrigerante.get().strip(),
                    "marca_modelo_sugerido": var_aa_marca_modelo.get().strip(),
                },
                "ubicacion_instalacion": {
                    "ubicacion_evaporadora": var_aa_ubicacion_evaporadora.get().strip(),
                    "ubicacion_condensadora": var_aa_ubicacion_condensadora.get().strip(),
                    "distancia_unidades": var_aa_distancia_unidades.get().strip(),
                    "altura_trabajo": var_aa_altura_trabajo.get().strip(),
                    "acceso_instalacion": var_aa_acceso_instalacion.get().strip(),
                    "soporte_base_condensadora": var_aa_soporte_base.get().strip(),
                },
                "infraestructura_necesaria": {
                    "alimentacion_electrica_disponible": var_aa_alimentacion_disponible.get().strip(),
                    "breaker_proteccion_disponible": var_aa_breaker_disponible.get().strip(),
                    "drenaje_disponible": var_aa_drenaje_disponible.get().strip(),
                    "requiere_perforaciones": var_aa_perforaciones.get().strip(),
                    "ruta_tuberia_canaleta": var_aa_ruta_tuberia.get().strip(),
                },
                "materiales_consumibles": {
                    "tuberia_cobre_metros": var_aa_tuberia_cobre_m.get().strip(),
                    "cableado_electrico_metros": var_aa_cableado_m.get().strip(),
                    "drenaje_metros": var_aa_drenaje_m.get().strip(),
                    "canaleta_metros": var_aa_canaleta_m.get().strip(),
                    "bomba_drenaje": var_aa_bomba_drenaje.get().strip(),
                },
                "preparativos_riesgos": {
                    "requiere_permiso_sitio": var_aa_requiere_permiso.get().strip(),
                    "requiere_escalera_andamio": var_aa_requiere_escalera.get().strip(),
                    "proteger_area": var_aa_proteccion_area.get().strip(),
                    "dias_trabajo": var_aa_dias_trabajo.get().strip(),
                    "personas_trabajo": var_aa_personas_trabajo.get().strip(),
                },
                "instalacion_entrega_pruebas": {
                    "prueba_vacio": var_aa_prueba_vacio.get().strip(),
                    "prueba_fugas": var_aa_prueba_fugas.get().strip(),
                    "prueba_electrica": var_aa_prueba_electrica.get().strip(),
                    "prueba_enfriamiento": var_aa_prueba_enfriamiento.get().strip(),
                    "entrega_limpia": var_aa_limpieza_entrega.get().strip(),
                    "capacitacion_usuario": var_aa_capacitacion_usuario.get().strip(),
                }
            }

        if tipo_levantamiento == "Redes Voz y Datos":
            return {
                "tipo_levantamiento": "Redes Voz y Datos",
                "necesidad_alcance": {
                    "necesidad": var_rvd_necesidad.get().strip(),
                    "tipo_servicio": var_rvd_tipo_servicio.get().strip(),
                    "cantidad_nodos_datos": var_rvd_cantidad_nodos.get().strip(),
                    "cantidad_puntos_voz": var_rvd_cantidad_telefonia.get().strip(),
                    "area_instalacion": var_rvd_area_instalacion.get().strip(),
                },
                "condiciones_sitio": {
                    "horario_trabajo": var_rvd_horario_trabajo.get().strip(),
                    "acceso_instalacion": var_rvd_acceso.get().strip(),
                    "altura_trabajo": var_rvd_altura_trabajo.get().strip(),
                    "requiere_permiso": var_rvd_permiso.get().strip(),
                    "nivel_riesgo": var_rvd_riesgo.get().strip(),
                },
                "cableado_canalizacion_consumibles": {
                    "requiere": var_requiere_canalizacion.get().strip(),
                    "partidas": obtener_canalizacion_materiales_json(),
                },
                "rack_equipo_activo_energia": {
                    "requiere_rack": var_rvd_requiere_rack.get().strip(),
                    "tipo_rack": var_rvd_tipo_rack.get().strip(),
                    "requiere_gabinete": var_rvd_requiere_gabinete.get().strip(),
                    "tipo_gabinete": var_rvd_tipo_gabinete.get().strip(),
                    "ubicacion_rack_gabinete": var_rvd_ubicacion_rack.get().strip(),
                    "requiere_switch": var_rvd_requiere_switch.get().strip(),
                    "tipo_switch": var_rvd_tipo_switch.get().strip(),
                    "puertos_switch": var_rvd_puertos_switch.get().strip(),
                    "switch_poe": var_rvd_switch_poe.get().strip(),
                    "ups": var_rvd_ups.get().strip(),
                    "detalle_ups": var_rvd_detalle_ups.get().strip(),
                    "contacto_regulado": var_rvd_contacto_regulado.get().strip(),
                    "detalle_contacto_regulado": var_rvd_detalle_contacto.get().strip(),
                    "tierra_fisica": var_rvd_tierra_fisica.get().strip(),
                    "detalle_tierra_fisica": var_rvd_detalle_tierra.get().strip(),
                },
                "estimacion_recursos": {
                    "dias_trabajo": var_rvd_dias_trabajo.get().strip(),
                    "personas_trabajo": var_rvd_personas_trabajo.get().strip(),
                }
            }

        if tipo_levantamiento == "Plantas de Energía":
            return {
                "tipo_levantamiento": "Plantas de Energía",
                "necesidad_respaldo": {
                    "necesidad": var_pe_necesidad.get().strip(),
                    "tipo_planta": var_pe_tipo_planta.get().strip(),
                    "capacidad_estimada": var_pe_capacidad.get().strip(),
                    "carga_respaldar": var_pe_carga_respaldar.get().strip(),
                    "tiempo_respaldo": var_pe_tiempo_respaldo.get().strip(),
                },
                "datos_electricos_carga": {
                    "voltaje": var_pe_voltaje.get().strip(),
                    "fases": var_pe_fases.get().strip(),
                    "tablero_respaldo": var_pe_tablero_respaldo.get().strip(),
                    "transferencia": var_pe_transferencia.get().strip(),
                    "requiere_ats": var_pe_ats.get().strip(),
                },
                "ubicacion_sitio_maniobras": {
                    "ubicacion_planta": var_pe_ubicacion_planta.get().strip(),
                    "base_cimentacion": var_pe_base_cimentacion.get().strip(),
                    "ventilacion": var_pe_ventilacion.get().strip(),
                    "restriccion_ruido": var_pe_ruido_restriccion.get().strip(),
                    "distancia_tablero": var_pe_distancia_tablero.get().strip(),
                    "requiere_maniobra_grua": var_pe_maniobra.get().strip(),
                    "requiere_permisos": var_pe_permisos.get().strip(),
                },
                "combustible_escape_seguridad": {
                    "combustible": var_pe_combustible.get().strip(),
                    "tipo_tanque": var_pe_tanque.get().strip(),
                    "autonomia_estimada": var_pe_autonomia.get().strip(),
                    "ruta_escape_gases": var_pe_ruta_escape.get().strip(),
                    "protecciones_electricas": var_pe_protecciones.get().strip(),
                    "tierra_fisica": var_pe_tierra_fisica.get().strip(),
                },
                "instalacion_pruebas_entrega": {
                    "prueba_arranque": var_pe_prueba_arranque.get().strip(),
                    "prueba_transferencia": var_pe_prueba_transferencia.get().strip(),
                    "prueba_carga": var_pe_prueba_carga.get().strip(),
                    "entrega_manual_capacitacion": var_pe_entrega_manual.get().strip(),
                    "dias_trabajo": var_pe_dias_trabajo.get().strip(),
                    "personas_trabajo": var_pe_personas_trabajo.get().strip(),
                }
            }

        if tipo_levantamiento == "Electricidad":
            return {
                "tipo_levantamiento": "Electricidad",
                "necesidad_alcance": {
                    "necesidad": var_ele_necesidad.get().strip(),
                    "tipo_servicio": var_ele_tipo_servicio.get().strip(),
                    "area_trabajo": var_ele_area.get().strip(),
                    "cantidad_puntos": var_ele_cantidad_puntos.get().strip(),
                    "carga_estimada": var_ele_carga_estimacion.get().strip(),
                },
                "datos_electricos_tablero_protecciones": {
                    "voltaje": var_ele_voltaje.get().strip(),
                    "fases": var_ele_fases.get().strip(),
                    "tablero_origen": var_ele_tablero_origen.get().strip(),
                    "capacidad_tablero": var_ele_capacidad_tablero.get().strip(),
                    "espacios_disponibles": var_ele_espacios_disponibles.get().strip(),
                    "breaker_requerido": var_ele_breaker_requerido.get().strip(),
                    "tipo_circuito": var_ele_tipo_circuito.get().strip(),
                },
                "canalizacion_cableado_materiales": {
                    "requiere": var_requiere_canalizacion.get().strip(),
                    "partidas": obtener_canalizacion_materiales_json(),
                    "contactos": var_ele_contactos.get().strip(),
                    "apagadores": var_ele_apagadores.get().strip(),
                    "luminarias": var_ele_luminarias.get().strip(),
                    "tierra_fisica": var_ele_tierra_fisica.get().strip(),
                    "neutro_disponible": var_ele_neutro.get().strip(),
                },
                "seguridad_operacion": {
                    "altura_trabajo": var_ele_altura_trabajo.get().strip(),
                    "requiere_permiso": var_ele_permiso.get().strip(),
                    "requiere_desenergizar": var_ele_desenergizar.get().strip(),
                    "nivel_riesgo": var_ele_riesgo.get().strip(),
                },
                "instalacion_pruebas_entrega": {
                    "prueba_continuidad": var_ele_prueba_continuidad.get().strip(),
                    "prueba_polaridad": var_ele_prueba_polaridad.get().strip(),
                    "medicion_voltaje": var_ele_prueba_voltaje.get().strip(),
                    "etiquetado_circuitos": var_ele_etiquetado.get().strip(),
                    "entrega_diagrama": var_ele_entrega_diagrama.get().strip(),
                    "dias_trabajo": var_ele_dias_trabajo.get().strip(),
                    "personas_trabajo": var_ele_personas_trabajo.get().strip(),
                }
            }

        if tipo_levantamiento in FORMULARIOS_DETALLADOS_EXTRA:
            detalle = {
                "tipo_levantamiento": tipo_levantamiento,
                "secciones": {}
            }
            for titulo_sec, campos_sec in FORMULARIOS_DETALLADOS_EXTRA[tipo_levantamiento]["secciones"]:
                nombre_sec = titulo_sec.split(". ", 1)[-1].lower().replace(" ", "_").replace(",", "").replace("/", "_")
                detalle["secciones"][nombre_sec] = {
                    clave: vars_extra[clave].get().strip()
                    for clave, _tipo_campo, _etiqueta, _opciones_placeholder, _default in campos_sec
                }
            return detalle

        if tipo_levantamiento != "Seguridad y Monitoreo":
            return {}

        modalidad = var_modalidad_levantamiento.get().strip() or "Instalación"
        detalle = {
            "tipo_levantamiento": "Seguridad y Monitoreo",
            "modalidad_operativa": modalidad,
        }

        if modalidad == "Reparación":
            detalle.update({
                "elemento_a_reparar": var_rep_objetivo.get().strip(),
                "ubicacion_estado_sintomas": {
                    "ubicacion_equipos": var_rep_ubicacion_equipos.get().strip() if var_rep_objetivo.get() != "Infraestructura" else "",
                    "acceso_equipos": var_rep_acceso_equipos.get().strip() if var_rep_objetivo.get() != "Infraestructura" else "",
                    "estado": var_rep_estado_camaras.get().strip() if var_rep_objetivo.get() != "Infraestructura" else "",
                    "codigo_error_dvr_nvr": var_rep_codigo_error.get().strip() if var_rep_objetivo.get() == "NVRs y/o DVRs" else "",
                    "horario_falla": var_rep_horario_falla.get().strip() if var_rep_objetivo.get() in ("Cámaras", "NVRs y/o DVRs") else "",
                    "descripcion_infraestructura": txt_rep_infraestructura.get("1.0", "end").strip() if var_rep_objetivo.get() == "Infraestructura" else "",
                },
                "equipos_danados": obtener_equipos_danados_json(),
                "descripcion_general_fallas": txt_rep_descripcion_fallas.get("1.0", "end").strip(),
            })
            return detalle

        if modalidad == "Mantenimiento":
            detalle["acceso_alturas_riesgos"] = {
                "escalera_andamio": var_escalera_requerida.get().strip(),
                "altura_trabajo": var_altura_trabajo.get().strip() if var_escalera_requerida.get() == "Sí" else "",
                "riesgo_instalacion": var_riesgo_instalacion.get().strip() if var_escalera_requerida.get() == "Sí" else "",
            }
            detalle["mantenimiento"] = {
                "descripcion_detallada_servicio": txt_observaciones.get("1.0", "end").strip(),
            }
            return detalle

        detalle.update({
            "infraestructura_existente": {
                "existe_infraestructura": var_infra_existe.get().strip(),
                "tipo_infraestructura_existente": var_infra_tipo_existente.get().strip(),
                "estado_general": var_infra_estado.get().strip(),
            },
            "consumibles_conectividad": {
                "plugs_rj45": var_plugs_rj45.get().strip(),
                "jacks_rj45": var_jacks_rj45.get().strip(),
                "keystone": var_keystone.get().strip(),
                "faceplates": var_faceplate.get().strip(),
                "patch_cords": var_patchcord.get().strip(),
            },
            "rack_gabinete_energia": {
                "rack_requerido": var_rack_requerido.get().strip(),
                "tipo_rack": var_tipo_rack.get().strip() if var_rack_requerido.get() == "Sí" else "",
                "gabinete_requerido": var_gabinete_requerido.get().strip(),
                "tipo_gabinete": var_tipo_gabinete.get().strip() if var_gabinete_requerido.get() == "Sí" else "",
                "ups_requerida": var_ups_requerida.get().strip(),
                "tipo_ups": var_tipo_ups.get().strip() if var_ups_requerida.get() == "Sí" else "",
                "contacto_regulado": var_contacto_regulado.get().strip(),
                "detalle_contacto_regulado": var_tipo_contacto_regulado.get().strip() if var_contacto_regulado.get() == "Sí" else "",
                "tierra_fisica": var_tierra_fisica.get().strip(),
                "detalle_tierra_fisica": var_tipo_tierra_fisica.get().strip() if var_tierra_fisica.get() == "Sí" else "",
            },
            "acceso_alturas_riesgos": {
                "escalera_andamio": var_escalera_requerida.get().strip(),
                "altura_trabajo": var_altura_trabajo.get().strip(),
                "riesgo_instalacion": var_riesgo_instalacion.get().strip(),
            },
            "datos_tecnicos_cctv": {
                "cantidad_camaras": var_cctv_cantidad_camaras.get().strip(),
                "tipo_camaras": var_cctv_tipo_camaras.get().strip(),
                "dias_trabajo": var_cctv_dias_retencion.get().strip(),
                "personas_considerar": var_cctv_personas_considerar.get().strip(),
                "ubicacion_nvr_dvr": var_cctv_ubicacion_nvr.get().strip(),
                "punto_red": var_cctv_punto_red.get().strip(),
                "punto_energia": var_cctv_punto_energia.get().strip(),
            },
        })
        return detalle

    def construir_resumen_aires_acondicionados():
        """Devuelve el bloque técnico de Aires Acondicionados para PDF y Supabase."""
        if tipo_levantamiento != "Aires Acondicionados":
            return ""

        lineas = [
            "",
            "--- LEVANTAMIENTO AIRES ACONDICIONADOS ---",
            "",
            "--- 1. NECESIDAD INICIAL DEL SERVICIO ---",
            f"Necesidad: {var_aa_necesidad.get().strip() or 'No definido'}",
            f"Cantidad de equipos requeridos: {var_aa_cantidad_equipos.get().strip() or 'No definido'}",
            f"Área a climatizar: {var_aa_area_climatizar.get().strip() or 'No definido'}",
            f"Tipo de área: {var_aa_tipo_area.get().strip() or 'No definido'}",
            f"Horario de operación: {var_aa_horario_operacion.get().strip() or 'No definido'}",
            "",
            "--- 2. CONDICIONES DEL SITIO ---",
            f"Dimensiones aproximadas: {var_aa_dimensiones_area.get().strip() or 'No definido'}",
            f"Personas en el área: {var_aa_personas_area.get().strip() or 'No definido'}",
            f"Equipos que generan calor: {var_aa_equipos_calor.get().strip() or 'No definido'}",
            f"Exposición solar: {var_aa_exposicion_solar.get().strip() or 'No definido'}",
            f"Requiere cálculo térmico: {var_aa_requiere_calculo.get().strip() or 'No definido'}",
            "",
            "--- 3. EQUIPO REQUERIDO ---",
            f"Tipo de equipo: {var_aa_tipo_equipo.get().strip() or 'No definido'}",
            f"Capacidad estimada: {var_aa_capacidad.get().strip() or 'No definido'}",
            f"Voltaje requerido: {var_aa_voltaje.get().strip() or 'No definido'}",
            f"Refrigerante: {var_aa_refrigerante.get().strip() or 'No definido'}",
            f"Marca/modelo sugerido: {var_aa_marca_modelo.get().strip() or 'No definido'}",
            "",
            "--- 4. UBICACIÓN DE INSTALACIÓN ---",
            f"Ubicación evaporadora: {var_aa_ubicacion_evaporadora.get().strip() or 'No definido'}",
            f"Ubicación condensadora: {var_aa_ubicacion_condensadora.get().strip() or 'No definido'}",
            f"Distancia entre unidades: {var_aa_distancia_unidades.get().strip() or 'No definido'}",
            f"Altura de trabajo: {var_aa_altura_trabajo.get().strip() or 'No definido'}",
            f"Acceso para instalación: {var_aa_acceso_instalacion.get().strip() or 'No definido'}",
            f"Soporte/base para condensadora: {var_aa_soporte_base.get().strip() or 'No definido'}",
            "",
            "--- 5. INFRAESTRUCTURA NECESARIA ---",
            f"Alimentación eléctrica disponible: {var_aa_alimentacion_disponible.get().strip() or 'No definido'}",
            f"Breaker/protección disponible: {var_aa_breaker_disponible.get().strip() or 'No definido'}",
            f"Drenaje disponible: {var_aa_drenaje_disponible.get().strip() or 'No definido'}",
            f"Requiere perforaciones: {var_aa_perforaciones.get().strip() or 'No definido'}",
            f"Ruta de tubería/canaleta: {var_aa_ruta_tuberia.get().strip() or 'No definido'}",
            "",
            "--- 6. MATERIALES Y CONSUMIBLES ESTIMADOS ---",
            f"Tubería de cobre: {var_aa_tuberia_cobre_m.get().strip() or '0'} metros",
            f"Cableado eléctrico: {var_aa_cableado_m.get().strip() or '0'} metros",
            f"Drenaje: {var_aa_drenaje_m.get().strip() or '0'} metros",
            f"Canaleta: {var_aa_canaleta_m.get().strip() or '0'} metros",
            f"Bomba de drenaje: {var_aa_bomba_drenaje.get().strip() or 'No definido'}",
            "",
            "--- 7. PREPARATIVOS, PERMISOS Y RIESGOS ---",
            f"Requiere permiso del sitio: {var_aa_requiere_permiso.get().strip() or 'No definido'}",
            f"Requiere escalera/andamio: {var_aa_requiere_escalera.get().strip() or 'No definido'}",
            f"Proteger área de trabajo: {var_aa_proteccion_area.get().strip() or 'No definido'}",
            f"Días de trabajo proyectados: {var_aa_dias_trabajo.get().strip() or 'No definido'}",
            f"Personas consideradas: {var_aa_personas_trabajo.get().strip() or 'No definido'}",
            "",
            "--- 8. INSTALACIÓN, ENTREGA Y PRUEBAS ---",
            f"Prueba de vacío: {var_aa_prueba_vacio.get().strip() or 'No definido'}",
            f"Prueba de fugas: {var_aa_prueba_fugas.get().strip() or 'No definido'}",
            f"Prueba eléctrica: {var_aa_prueba_electrica.get().strip() or 'No definido'}",
            f"Prueba de enfriamiento: {var_aa_prueba_enfriamiento.get().strip() or 'No definido'}",
            f"Entrega limpia: {var_aa_limpieza_entrega.get().strip() or 'No definido'}",
            f"Capacitación básica al usuario: {var_aa_capacitacion_usuario.get().strip() or 'No definido'}",
        ]
        return "\n".join(lineas)

    def construir_resumen_redes_voz_datos():
        """Devuelve el bloque técnico de Redes Voz y Datos para PDF y Supabase."""
        if tipo_levantamiento != "Redes Voz y Datos":
            return ""

        lineas = [
            "",
            "--- LEVANTAMIENTO REDES DE VOZ Y DATOS ---",
            "",
            "--- 1. NECESIDAD INICIAL Y ALCANCE ---",
            f"Necesidad: {var_rvd_necesidad.get().strip() or 'No definido'}",
            f"Tipo de servicio: {var_rvd_tipo_servicio.get().strip() or 'No definido'}",
            f"Nodos de datos requeridos: {var_rvd_cantidad_nodos.get().strip() or '0'}",
            f"Puntos de voz requeridos: {var_rvd_cantidad_telefonia.get().strip() or '0'}",
            f"Área/zona de instalación: {var_rvd_area_instalacion.get().strip() or 'No definido'}",
            "",
            "--- 2. CONDICIONES DEL SITIO Y RUTA ---",
            f"Horario permitido de trabajo: {var_rvd_horario_trabajo.get().strip() or 'No definido'}",
            f"Acceso para instalación: {var_rvd_acceso.get().strip() or 'No definido'}",
            f"Altura de trabajo: {var_rvd_altura_trabajo.get().strip() or 'No definido'}",
            f"Requiere permiso del sitio: {var_rvd_permiso.get().strip() or 'No definido'}",
            f"Nivel de riesgo: {var_rvd_riesgo.get().strip() or 'No definido'}",
            "",
            "--- 3. CABLEADO, CANALIZACIÓN Y CONSUMIBLES ---",
            construir_resumen_canalizacion_materiales() or "Sin partidas capturadas",
            "",
            "--- 4. RACK, GABINETE, EQUIPO ACTIVO Y ENERGÍA ---",
            f"Requiere rack: {var_rvd_requiere_rack.get().strip() or 'No definido'}",
            f"Tipo/capacidad de rack: {var_rvd_tipo_rack.get().strip() or 'No aplica'}",
            f"Requiere gabinete: {var_rvd_requiere_gabinete.get().strip() or 'No definido'}",
            f"Tipo/capacidad de gabinete: {var_rvd_tipo_gabinete.get().strip() or 'No aplica'}",
            f"Ubicación de rack/gabinete: {var_rvd_ubicacion_rack.get().strip() or 'No aplica'}",
            f"Requiere switch: {var_rvd_requiere_switch.get().strip() or 'No definido'}",
            f"Tipo/características del switch: {var_rvd_tipo_switch.get().strip() or 'No aplica'}",
            f"Puertos requeridos del switch: {var_rvd_puertos_switch.get().strip() or 'No aplica'}",
            f"Switch con PoE: {var_rvd_switch_poe.get().strip() or 'No aplica'}",
            f"UPS requerida: {var_rvd_ups.get().strip() or 'No definido'}",
            f"Detalle UPS: {var_rvd_detalle_ups.get().strip() or 'No aplica'}",
            f"Contacto regulado requerido: {var_rvd_contacto_regulado.get().strip() or 'No definido'}",
            f"Detalle contacto regulado: {var_rvd_detalle_contacto.get().strip() or 'No aplica'}",
            f"Tierra física disponible: {var_rvd_tierra_fisica.get().strip() or 'No definido'}",
            f"Detalle tierra física: {var_rvd_detalle_tierra.get().strip() or 'No aplica'}",
            "",
            "--- 5. ESTIMACIÓN DE RECURSOS ---",
            f"Días de trabajo proyectados: {var_rvd_dias_trabajo.get().strip() or 'No definido'}",
            f"Personas consideradas: {var_rvd_personas_trabajo.get().strip() or 'No definido'}",
        ]
        return "\n".join(lineas)

    def construir_resumen_formulario_detallado():
        """Construye el resumen técnico de formularios especializados adicionales."""
        if tipo_levantamiento not in FORMULARIOS_DETALLADOS_EXTRA:
            return ""

        lineas = [
            "",
            f"--- LEVANTAMIENTO {tipo_levantamiento.upper()} ---",
            "",
        ]
        for titulo_sec, campos_sec in FORMULARIOS_DETALLADOS_EXTRA[tipo_levantamiento]["secciones"]:
            if tipo_levantamiento in ("Control de Accesos", "Enlaces Inalámbricos") and "Cableado, canalización e infraestructura requerida" in titulo_sec:
                continue
            lineas.append(f"--- {titulo_sec} ---")
            for clave, _tipo_campo, etiqueta, _opciones_placeholder, _default in campos_sec:
                valor = vars_extra[clave].get().strip() or "No definido"
                lineas.append(f"{etiqueta}: {valor}")
            lineas.append("")
        resumen_canalizacion = construir_resumen_canalizacion_materiales()
        if resumen_canalizacion:
            lineas.extend(["", resumen_canalizacion])
        return "\n".join(lineas).strip()

    def construir_resumen_cctv():
        """
        Devuelve un bloque técnico Seguridad y Monitoreo para anexarlo al levantamiento.

        El bloque ya incluye infraestructura, materiales, canalización,
        conectividad, energía y riesgos. Por ahora se almacena en campos
        descriptivos existentes para no forzar cambios inmediatos en Supabase.
        Cuando el flujo sea aprobado por operación, conviene crear tablas
        específicas para puntos de cámara, materiales y partidas.
        """
        if tipo_levantamiento != "Seguridad y Monitoreo":
            return ""

        modalidad = var_modalidad_levantamiento.get().strip() or "Instalación"

        if modalidad == "Reparación":
            equipos_lineas = []
            for idx, item in enumerate(equipos_danados_items, start=1):
                equipos_lineas.append(
                    f"Equipo {idx}: {item['tipo'].get().strip() or 'No definido'} | "
                    f"Marca: {item['marca'].get().strip() or 'No definida'} | "
                    f"Modelo: {item['modelo'].get().strip() or 'No definido'} | "
                    f"Serie: {item['serie'].get().strip() or 'No definida'}"
                )

            lineas = [
                "",
                "--- LEVANTAMIENTO Seguridad y Monitoreo / REPARACIÓN ---",
                "",
                f"¿Qué se desea reparar?: {var_rep_objetivo.get().strip() or 'No definido'}",
                "--- UBICACIÓN, ESTADO Y SÍNTOMAS DEL EQUIPO ---",
                *( [f"Descripción de infraestructura a reparar: {txt_rep_infraestructura.get('1.0', 'end').strip() or 'No definido'}"]
                   if var_rep_objetivo.get() == "Infraestructura" else [
                    f"Ubicación de equipos: {var_rep_ubicacion_equipos.get().strip() or 'No definido'}",
                    f"Acceso a equipos: {var_rep_acceso_equipos.get().strip() or 'No definido'}",
                    f"Estado: {var_rep_estado_camaras.get().strip() or 'No definido'}",
                    *([f"Código de error en DVR/NVR: {var_rep_codigo_error.get().strip() or 'No definido'}"] if var_rep_objetivo.get() == "NVRs y/o DVRs" else []),
                    *([f"Horario de la falla: {var_rep_horario_falla.get().strip() or 'No definido'}"] if var_rep_objetivo.get() == "NVRs y/o DVRs" else []),
                ]),
                "",
                "--- EQUIPOS DAÑADOS ---",
                f"Cantidad de equipos dañados: {len(equipos_danados_items)}",
                *(equipos_lineas or ["Sin equipos dañados capturados"]),
                "",
                "--- DESCRIPCIÓN GENERAL DE FALLAS ---",
                txt_rep_descripcion_fallas.get("1.0", "end").strip() or "No definido",
            ]
            return "\n".join(lineas)

        if modalidad == "Mantenimiento":
            bloques = ["", "--- LEVANTAMIENTO Seguridad y Monitoreo / MANTENIMIENTO ---", "", "--- DESCRIPCIÓN DETALLADA DEL SERVICIO ---", txt_observaciones.get("1.0", "end").strip() or "No definido"]
            resumen_equipos = construir_resumen_equipos_catalogo()
            resumen_materiales = construir_resumen_materiales_miscelaneos()
            if resumen_equipos:
                bloques.extend(["", resumen_equipos])
            if resumen_materiales:
                bloques.extend(["", resumen_materiales])
            return "\n".join(bloques)

        existe_infra = var_infra_existe.get().strip() or "No definido"

        lineas = [
            "",
            "--- LEVANTAMIENTO Seguridad y Monitoreo / INSTALACIÓN ---",
            "",
            f"Tipo operativo: {modalidad}",
            "",
            "--- INFRAESTRUCTURA DEL SITIO ---",
            f"¿Existe infraestructura?: {existe_infra}",
            f"Tipo infraestructura existente: {var_infra_tipo_existente.get().strip() or 'No definido'}",
            f"Estado general: {var_infra_estado.get().strip() or 'No definido'}",
        ]

        if existe_infra in ("No", "Parcial"):
            resumen_dinamico = construir_resumen_canalizacion_materiales()
            lineas.extend([
                "",
                "--- INFRAESTRUCTURA REQUERIDA ---",
                resumen_dinamico or "Sin partidas de canalización capturadas",
                "",
                "--- RACK, GABINETE Y ENERGÍA ---",
                f"Rack requerido: {var_rack_requerido.get().strip() or 'No'}" + (f" | Tipo: {var_tipo_rack.get().strip()}" if var_rack_requerido.get() == "Sí" and var_tipo_rack.get().strip() else ""),
                f"Gabinete requerido: {var_gabinete_requerido.get().strip() or 'No'}" + (f" | Tipo: {var_tipo_gabinete.get().strip()}" if var_gabinete_requerido.get() == "Sí" and var_tipo_gabinete.get().strip() else ""),
                f"UPS requerida: {var_ups_requerida.get().strip() or 'No'}" + (f" | Tipo/capacidad: {var_tipo_ups.get().strip()}" if var_ups_requerida.get() == "Sí" and var_tipo_ups.get().strip() else ""),
                f"Contacto regulado: {var_contacto_regulado.get().strip() or 'No'}" + (f" | Detalle: {var_tipo_contacto_regulado.get().strip()}" if var_contacto_regulado.get() == "Sí" and var_tipo_contacto_regulado.get().strip() else ""),
                f"Tierra física: {var_tierra_fisica.get().strip() or 'No'}" + (f" | Detalle: {var_tipo_tierra_fisica.get().strip()}" if var_tierra_fisica.get() == "Sí" and var_tipo_tierra_fisica.get().strip() else ""),
                "",
                "--- ACCESO, ALTURAS Y RIESGOS ---",
                f"Requiere escalera/andamio: {var_escalera_requerida.get().strip() or 'No'}",
                f"Altura de trabajo: {var_altura_trabajo.get().strip() if var_escalera_requerida.get() == 'Sí' else 'No aplica'}",
                f"Riesgo de instalación: {var_riesgo_instalacion.get().strip() if var_escalera_requerida.get() == 'Sí' else 'No aplica'}",
            ])

        lineas.extend([
            "",
            "--- DATOS TÉCNICOS Seguridad y Monitoreo ---",
            f"Cantidad de cámaras: {var_cctv_cantidad_camaras.get().strip() or 'No definido'}",
            f"Tipo de cámaras: {var_cctv_tipo_camaras.get().strip() or 'No definido'}",
            f"Días de trabajo: {var_cctv_dias_retencion.get().strip() or 'No definido'}",
            f"Personas a considerar: {var_cctv_personas_considerar.get().strip() or 'No definido'}",
            f"Ubicación NVR/DVR: {var_cctv_ubicacion_nvr.get().strip() or 'No definido'}",
            f"Punto de red: {var_cctv_punto_red.get().strip() or 'No definido'}",
            f"Punto de energía: {var_cctv_punto_energia.get().strip() or 'No definido'}",
            "",
            "--- DESCRIPCIÓN DETALLADA DEL SERVICIO ---",
            txt_observaciones.get("1.0", "end").strip() or "No definido",
        ])
        resumen_equipos = construir_resumen_equipos_catalogo()
        resumen_materiales = construir_resumen_materiales_miscelaneos()
        if resumen_equipos:
            lineas.extend(["", resumen_equipos])
        if resumen_materiales:
            lineas.extend(["", resumen_materiales])
        return "\n".join(lineas)


    def formulario_preview_completo():
        """Valida solo campos visibles/aplicables; los deshabilitados no bloquean."""
        if not var_cliente.get().strip():
            return False
        if tipo_levantamiento == "Seguridad y Monitoreo":
            modalidad = var_modalidad_levantamiento.get().strip()
            if modalidad == "Instalación":
                if not txt_observaciones.get("1.0", "end").strip():
                    return False
                obligatorios = [var_cctv_cantidad_camaras.get().strip(), var_cctv_tipo_camaras.get().strip(), var_cctv_dias_retencion.get().strip(), var_cctv_personas_considerar.get().strip(), var_cctv_ubicacion_nvr.get().strip(), var_cctv_punto_red.get().strip(), var_cctv_punto_energia.get().strip(), var_infra_existe.get().strip()]
                if not all(obligatorios):
                    return False
                if var_infra_existe.get() in ("Sí", "Parcial") and not (var_infra_tipo_existente.get().strip() and var_infra_estado.get().strip()):
                    return False
                if var_infra_existe.get() in ("No", "Parcial") and not canalizacion_materiales_completa():
                    return False
                pares = [(var_rack_requerido, var_tipo_rack), (var_gabinete_requerido, var_tipo_gabinete), (var_ups_requerida, var_tipo_ups), (var_contacto_regulado, var_tipo_contacto_regulado), (var_tierra_fisica, var_tipo_tierra_fisica)]
                if any(a.get() == "Sí" and not b.get().strip() for a,b in pares):
                    return False
                if var_escalera_requerida.get() == "Sí" and not (var_altura_trabajo.get().strip() and var_riesgo_instalacion.get().strip()):
                    return False
                return True
            if modalidad == "Mantenimiento":
                if not txt_observaciones.get("1.0", "end").strip():
                    return False
                if var_escalera_requerida.get() == "Sí" and not (
                    var_altura_trabajo.get().strip() and var_riesgo_instalacion.get().strip()
                ):
                    return False
                return True
            if modalidad == "Reparación":
                objetivo = var_rep_objetivo.get().strip()
                if not objetivo:
                    return False
                if objetivo == "Infraestructura":
                    return bool(txt_rep_infraestructura.get("1.0", "end").strip())
                if not (var_rep_ubicacion_equipos.get().strip() and var_rep_acceso_equipos.get().strip() and var_rep_estado_camaras.get().strip() and txt_rep_descripcion_fallas.get("1.0", "end").strip()):
                    return False
                if objetivo == "NVRs y/o DVRs" and not (var_rep_codigo_error.get().strip() and var_rep_horario_falla.get().strip()):
                    return False
                if objetivo in ("Cámaras", "NVRs y/o DVRs"):
                    for equipo in equipos_danados_items:
                        if not all(equipo[c].get().strip() for c in ("tipo", "marca", "modelo", "serie")):
                            return False
                return True
            return False
        descripcion = txt_descripcion.get("1.0", "end").strip()
        observaciones = txt_observaciones.get("1.0", "end").strip()
        if tipo_levantamiento in TIPOS_LEVANTAMIENTO_ESPECIALIZADOS:
            if not observaciones:
                return False
        elif not (descripcion and observaciones):
            return False
        if tipo_levantamiento == "Aires Acondicionados":
            return all([var_aa_cantidad_equipos.get().strip(), var_aa_area_climatizar.get().strip(), var_aa_ubicacion_evaporadora.get().strip(), var_aa_ubicacion_condensadora.get().strip(), var_aa_dias_trabajo.get().strip(), var_aa_personas_trabajo.get().strip()])
        if tipo_levantamiento == "Redes Voz y Datos":
            tipo_servicio = var_rvd_tipo_servicio.get().strip()
            requeridos = [
                var_rvd_necesidad.get().strip(),
                tipo_servicio,
                var_rvd_area_instalacion.get().strip(),
                var_rvd_horario_trabajo.get().strip(),
                var_rvd_altura_trabajo.get().strip(),
                var_rvd_dias_trabajo.get().strip(), var_rvd_personas_trabajo.get().strip(),
            ]
            if tipo_servicio in ("Datos", "Voz y datos", "Fibra óptica", "Mixto"):
                requeridos.append(var_rvd_cantidad_nodos.get().strip())
            if tipo_servicio in ("Voz", "Voz y datos", "Mixto"):
                requeridos.append(var_rvd_cantidad_telefonia.get().strip())
            # Patch panel, jacks, plugs, faceplates y patch cords ya se capturan
            # en la tabla dinámica de canalización. Los campos antiguos están
            # ocultos y no deben bloquear Preview/Guardar.
            if var_rvd_requiere_rack.get() == "Sí":
                requeridos.append(var_rvd_tipo_rack.get().strip())
            if var_rvd_requiere_gabinete.get() == "Sí":
                requeridos.append(var_rvd_tipo_gabinete.get().strip())
            if var_rvd_requiere_rack.get() == "Sí" or var_rvd_requiere_gabinete.get() == "Sí":
                requeridos.append(var_rvd_ubicacion_rack.get().strip())
            if var_rvd_requiere_switch.get() == "Sí":
                requeridos.extend([var_rvd_tipo_switch.get().strip(), var_rvd_puertos_switch.get().strip(), var_rvd_switch_poe.get().strip()])
            if var_rvd_ups.get() == "Sí":
                requeridos.append(var_rvd_detalle_ups.get().strip())
            if var_rvd_contacto_regulado.get() == "Sí":
                requeridos.append(var_rvd_detalle_contacto.get().strip())
            if var_rvd_tierra_fisica.get() == "Sí":
                requeridos.append(var_rvd_detalle_tierra.get().strip())
            return all(requeridos) and canalizacion_materiales_completa()
        if tipo_levantamiento == "Electricidad":
            requeridos = [
                var_ele_necesidad.get().strip(), var_ele_tipo_servicio.get().strip(),
                var_ele_area.get().strip(), var_ele_cantidad_puntos.get().strip(),
                var_ele_carga_estimacion.get().strip(), var_ele_voltaje.get().strip(),
                var_ele_fases.get().strip(), var_ele_tablero_origen.get().strip(),
                var_ele_capacidad_tablero.get().strip(), var_ele_breaker_requerido.get().strip(),
                var_ele_tipo_circuito.get().strip(),
                var_ele_altura_trabajo.get().strip(), var_ele_dias_trabajo.get().strip(),
                var_ele_personas_trabajo.get().strip(),
            ]
            return all(requeridos) and canalizacion_materiales_completa()
        if tipo_levantamiento == "Control de Accesos":
            requeridos = [
                vars_extra["cantidad_accesos"].get().strip(),
                vars_extra["ubicacion_accesos"].get().strip(),
                vars_extra["flujo_personas"].get().strip(),
                vars_extra["cantidad_lectores"].get().strip(),
                vars_extra["usuarios_iniciales"].get().strip(),
                vars_extra["dias_trabajo"].get().strip(),
                vars_extra["personas_trabajo"].get().strip(),
            ]
            return all(requeridos) and canalizacion_materiales_completa()
        if tipo_levantamiento == "Enlaces Inalámbricos":
            requeridos = [
                vars_extra["necesidad"].get().strip(),
                vars_extra["sitio_origen"].get().strip(),
                vars_extra["sitio_destino"].get().strip(),
                vars_extra["distancia"].get().strip(),
                vars_extra["ancho_banda"].get().strip(),
                vars_extra["linea_vista"].get().strip(),
                vars_extra["altura_origen"].get().strip(),
                vars_extra["altura_destino"].get().strip(),
                vars_extra["obstrucciones"].get().strip(),
                vars_extra["acceso_azotea"].get().strip(),
                vars_extra["frecuencia"].get().strip(),
                vars_extra["tipo_equipo"].get().strip(),
                vars_extra["cantidad_radios"].get().strip(),
                vars_extra["mastil_torre"].get().strip(),
                vars_extra["proteccion_clima"].get().strip(),
                vars_extra["punto_red_origen"].get().strip(),
                vars_extra["punto_red_destino"].get().strip(),
                vars_extra["energia_origen"].get().strip(),
                vars_extra["energia_destino"].get().strip(),
                vars_extra["metros_cable"].get().strip(),
                vars_extra["proteccion_tierra"].get().strip(),
                vars_extra["dias_trabajo"].get().strip(),
                vars_extra["personas_trabajo"].get().strip(),
            ]
            return all(requeridos) and canalizacion_materiales_completa()
        return True

    def titulo_pdf_levantamiento():
        titulos = {
            "Seguridad y Monitoreo": "Levantamiento Seguridad y Monitoreo",
            "Aires Acondicionados": "Levantamiento Aires Acondicionados",
            "Redes Voz y Datos": "Levantamiento Redes Voz y Datos",
            "Plantas de Energía": "Levantamiento Plantas de Energía",
            "Electricidad": "Levantamiento Electricidad",
            "Control de Accesos": "Levantamiento Control de Accesos",
            "Enlaces Inalámbricos": "Levantamiento Enlaces Inalámbricos",
            "Tecnología, Equipos y Periféricos": "Levantamiento Tecnología, Equipos y Periféricos",
            "Paneles Solares": "Levantamiento Paneles Solares",
        }
        return titulos.get(tipo_levantamiento, "Levantamiento")

    def datos_pdf_levantamiento():
        resumen = construir_resumen_aires_acondicionados() or construir_resumen_redes_voz_datos() or construir_resumen_formulario_detallado() or construir_resumen_cctv()
        return {
            "Folio de Levantamiento": var_folio.get(),
            "Tipo de Levantamiento": tipo_levantamiento or var_tipo.get(),
            "Tipo operativo": var_modalidad_levantamiento.get() if tipo_levantamiento == "Seguridad y Monitoreo" else ("Instalación" if tipo_levantamiento in TIPOS_LEVANTAMIENTO_ESPECIALIZADOS else var_tipo.get()),
            "ACO": var_aco.get(),
            "Fecha": var_fecha_programada.get(),
            "Cliente": var_cliente.get(),
            "Dirección": var_direccion.get(),
            "Teléfono": var_telefono.get(),
            "Correo": var_correo.get(),
            "Contacto": var_contacto.get(),
            "Técnico": var_tecnico.get(),
            "Supervisor": var_supervisor.get(),
            "Fecha programada": var_fecha_programada.get(),
            "Descripción": "" if tipo_levantamiento in TIPOS_LEVANTAMIENTO_ESPECIALIZADOS else txt_descripcion.get("1.0", "end").strip(),
            "Observaciones": txt_observaciones.get("1.0", "end").strip(),
            "Detalle técnico": resumen,
        }

    def registro_pdf_levantamiento(folio_override=""):
        """Construye la fuente única del PDF con la misma forma que Supabase."""
        modalidad = (
            var_modalidad_levantamiento.get().strip()
            if tipo_levantamiento == "Seguridad y Monitoreo"
            else ("Instalación" if tipo_levantamiento in TIPOS_LEVANTAMIENTO_ESPECIALIZADOS else var_tipo.get().strip())
        )
        detalle = obtener_detalle_tecnico_json() if tipo_levantamiento in TIPOS_LEVANTAMIENTO_ESPECIALIZADOS else {}
        if detalle:
            detalle = dict(detalle)
            detalle["canalizacion_materiales"] = obtener_canalizacion_materiales_json()
            detalle["equipos_principales"] = obtener_equipos_catalogo_json()
            detalle["materiales_miscelaneos"] = obtener_materiales_miscelaneos_json()

        descripcion_fallas = ""
        equipos_danados = []
        if tipo_levantamiento == "Seguridad y Monitoreo" and modalidad == "Reparación":
            descripcion_fallas = txt_rep_descripcion_fallas.get("1.0", "end").strip()
            equipos_danados = obtener_equipos_danados_json()

        return {
            "lev_folio": (folio_override or var_folio.get().strip()),
            "lev_tipo_levantamiento": tipo_levantamiento or var_tipo.get().strip(),
            "lev_modalidad_operativa": modalidad,
            "lev_aco_numero": var_aco.get().strip(),
            "lev_fecha_programada": var_fecha_programada.get().strip() or None,
            "lev_cliente": var_cliente.get().strip(),
            "lev_contacto": var_contacto.get().strip(),
            "lev_correo": var_correo.get().strip(),
            "lev_telefono": var_telefono.get().strip(),
            "lev_direccion": var_direccion.get().strip(),
            "lev_ubicacion": var_ubicacion.get().strip(),
            "lev_tecnico": var_tecnico.get().strip(),
            "lev_supervisor": var_supervisor.get().strip(),
            "lev_estatus": var_estatus.get().strip(),
            "lev_prioridad": var_prioridad.get().strip(),
            "lev_descripcion": txt_descripcion.get("1.0", "end").strip(),
            "lev_observaciones": txt_observaciones.get("1.0", "end").strip(),
            "lev_descripcion_fallas": descripcion_fallas,
            "lev_detalle_tecnico_json": json.dumps(detalle, ensure_ascii=False) if detalle else "",
            "lev_equipos_danados_json": json.dumps(equipos_danados, ensure_ascii=False) if equipos_danados else "",
        }

    def configuracion_pdf_levantamiento():
        return {
            "titulo_pdf": "Levantamientos",
            "campo_folio": "lev_folio",
        }

    def preview_pdf_levantamiento():
        if not formulario_preview_completo():
            messagebox.showwarning("Preview", "El preview se activa cuando los campos principales del levantamiento estén completos.")
            return
        generar_pdf_registro(
            registro_pdf_levantamiento(),
            configuracion_pdf_levantamiento(),
            abrir=True,
        )

    # =================================================
    # FUNCIÓN: guardar_levantamiento()

    def titulo_pdf_levantamiento():
        titulos = {
            "Seguridad y Monitoreo": "Levantamiento Seguridad y Monitoreo",
            "Aires Acondicionados": "Levantamiento Aires Acondicionados",
            "Redes Voz y Datos": "Levantamiento Redes Voz y Datos",
            "Plantas de Energía": "Levantamiento Plantas de Energía",
            "Electricidad": "Levantamiento Electricidad",
            "Control de Accesos": "Levantamiento Control de Accesos",
            "Enlaces Inalámbricos": "Levantamiento Enlaces Inalámbricos",
            "Tecnología, Equipos y Periféricos": "Levantamiento Tecnología, Equipos y Periféricos",
            "Paneles Solares": "Levantamiento Paneles Solares",
        }
        return titulos.get(tipo_levantamiento, "Levantamiento")

    def datos_pdf_levantamiento():
        resumen = construir_resumen_aires_acondicionados() or construir_resumen_redes_voz_datos() or construir_resumen_formulario_detallado() or construir_resumen_cctv()
        return {
            "Folio de Levantamiento": var_folio.get(),
            "Tipo de Levantamiento": tipo_levantamiento or var_tipo.get(),
            "Tipo operativo": var_modalidad_levantamiento.get() if tipo_levantamiento == "Seguridad y Monitoreo" else ("Instalación" if tipo_levantamiento in TIPOS_LEVANTAMIENTO_ESPECIALIZADOS else var_tipo.get()),
            "ACO": var_aco.get(),
            "Fecha": var_fecha_programada.get(),
            "Cliente": var_cliente.get(),
            "Dirección": var_direccion.get(),
            "Teléfono": var_telefono.get(),
            "Correo": var_correo.get(),
            "Contacto": var_contacto.get(),
            "Técnico": var_tecnico.get(),
            "Supervisor": var_supervisor.get(),
            "Fecha programada": var_fecha_programada.get(),
            "Descripción": "" if tipo_levantamiento in TIPOS_LEVANTAMIENTO_ESPECIALIZADOS else txt_descripcion.get("1.0", "end").strip(),
            "Observaciones": txt_observaciones.get("1.0", "end").strip(),
            "Detalle técnico": resumen,
        }

    def registro_pdf_levantamiento(folio_override=""):
        """Construye la fuente única del PDF con la misma forma que Supabase."""
        modalidad = (
            var_modalidad_levantamiento.get().strip()
            if tipo_levantamiento == "Seguridad y Monitoreo"
            else ("Instalación" if tipo_levantamiento in TIPOS_LEVANTAMIENTO_ESPECIALIZADOS else var_tipo.get().strip())
        )
        detalle = obtener_detalle_tecnico_json() if tipo_levantamiento in TIPOS_LEVANTAMIENTO_ESPECIALIZADOS else {}
        if detalle:
            detalle = dict(detalle)
            detalle["canalizacion_materiales"] = obtener_canalizacion_materiales_json()
            detalle["equipos_principales"] = obtener_equipos_catalogo_json()
            detalle["materiales_miscelaneos"] = obtener_materiales_miscelaneos_json()

        descripcion_fallas = ""
        equipos_danados = []
        if tipo_levantamiento == "Seguridad y Monitoreo" and modalidad == "Reparación":
            descripcion_fallas = txt_rep_descripcion_fallas.get("1.0", "end").strip()
            equipos_danados = obtener_equipos_danados_json()

        return {
            "lev_folio": (folio_override or var_folio.get().strip()),
            "lev_tipo_levantamiento": tipo_levantamiento or var_tipo.get().strip(),
            "lev_modalidad_operativa": modalidad,
            "lev_aco_numero": var_aco.get().strip(),
            "lev_fecha_programada": var_fecha_programada.get().strip() or None,
            "lev_cliente": var_cliente.get().strip(),
            "lev_contacto": var_contacto.get().strip(),
            "lev_correo": var_correo.get().strip(),
            "lev_telefono": var_telefono.get().strip(),
            "lev_direccion": var_direccion.get().strip(),
            "lev_ubicacion": var_ubicacion.get().strip(),
            "lev_tecnico": var_tecnico.get().strip(),
            "lev_supervisor": var_supervisor.get().strip(),
            "lev_estatus": var_estatus.get().strip(),
            "lev_prioridad": var_prioridad.get().strip(),
            "lev_descripcion": txt_descripcion.get("1.0", "end").strip(),
            "lev_observaciones": txt_observaciones.get("1.0", "end").strip(),
            "lev_descripcion_fallas": descripcion_fallas,
            "lev_detalle_tecnico_json": json.dumps(detalle, ensure_ascii=False) if detalle else "",
            "lev_equipos_danados_json": json.dumps(equipos_danados, ensure_ascii=False) if equipos_danados else "",
        }

    def configuracion_pdf_levantamiento():
        return {
            "titulo_pdf": "Levantamientos",
            "campo_folio": "lev_folio",
        }

    def preview_pdf_levantamiento():
        if not formulario_preview_completo():
            messagebox.showwarning("Preview", "El preview se activa cuando los campos principales del levantamiento estén completos.")
            return
        generar_pdf_registro(
            registro_pdf_levantamiento(),
            configuracion_pdf_levantamiento(),
            abrir=True,
        )

    # =================================================
    # FUNCIÓN: guardar_levantamiento()
    # =================================================

    def guardar_levantamiento():
        """
        Valida y guarda el levantamiento en Supabase.
        """

        folio = ""
        cliente = var_cliente.get().strip()
        aco_numero = var_aco.get().strip()
        descripcion = txt_descripcion.get("1.0", "end").strip()
        if tipo_levantamiento == "Seguridad y Monitoreo":
            descripcion = construir_resumen_cctv().strip() or "Levantamiento de Seguridad y Monitoreo"
        elif tipo_levantamiento == "Aires Acondicionados":
            descripcion = construir_resumen_aires_acondicionados().strip() or "Levantamiento de Aires Acondicionados"
        elif tipo_levantamiento == "Redes Voz y Datos":
            descripcion = construir_resumen_redes_voz_datos().strip() or "Levantamiento de Redes Voz y Datos"
        elif tipo_levantamiento in FORMULARIOS_DETALLADOS_EXTRA:
            descripcion = construir_resumen_formulario_detallado().strip() or f"Levantamiento de {tipo_levantamiento}"

        if not cliente or (tipo_levantamiento not in TIPOS_LEVANTAMIENTO_ESPECIALIZADOS and not descripcion):
            messagebox.showwarning(
                "Campos obligatorios",
                "Debes capturar cliente" + (" y descripción." if tipo_levantamiento not in TIPOS_LEVANTAMIENTO_ESPECIALIZADOS else ".")
            )
            return

        resumen_cctv = construir_resumen_cctv()
        resumen_aa = construir_resumen_aires_acondicionados()
        resumen_rvd = construir_resumen_redes_voz_datos()
        resumen_extra = construir_resumen_formulario_detallado()
        requerimientos = ""
        resumen_misc = construir_resumen_materiales_miscelaneos()
        resumen_canalizacion = construir_resumen_canalizacion_materiales()
        resumen_equipos = construir_resumen_equipos_catalogo()
        observaciones = txt_observaciones.get("1.0", "end").strip()

        if resumen_cctv:
            requerimientos = f"{requerimientos}\n{resumen_cctv}".strip()
            observaciones = f"Tipo específico de levantamiento: Seguridad y Monitoreo / {var_modalidad_levantamiento.get()}\n{observaciones}".strip()
        elif resumen_aa:
            requerimientos = f"{requerimientos}\n{resumen_aa}".strip()
            observaciones = f"Tipo específico de levantamiento: Aires Acondicionados / Instalación\n{observaciones}".strip()
        elif resumen_rvd:
            requerimientos = f"{requerimientos}\n{resumen_rvd}".strip()
            observaciones = f"Tipo específico de levantamiento: Redes Voz y Datos / Instalación\n{observaciones}".strip()
        elif resumen_extra:
            requerimientos = f"{requerimientos}\n{resumen_extra}".strip()
            observaciones = f"Tipo específico de levantamiento: {tipo_levantamiento} / Instalación\n{observaciones}".strip()

        if resumen_equipos:
            requerimientos = f"{requerimientos}\n\n{resumen_equipos}".strip()

        if resumen_misc:
            requerimientos = f"{requerimientos}\n\n{resumen_misc}".strip()

        datos = {
            "id_aco": datos_aco.get("id_aco") if aco else None,
            "id_sucursal": datos_aco.get("id_sucursal") if aco else None,
            "id_contacto": datos_aco.get("id_contacto") if aco else None,
            "lev_aco_numero": aco_numero,
            "lev_cliente": cliente,
            "lev_folio": folio,
            "lev_tipo": convertir_tipo(var_tipo.get()),
            "lev_estatus": convertir_estatus(var_estatus.get()),
            "lev_prioridad": convertir_prioridad(var_prioridad.get()),
            "lev_contacto": var_contacto.get().strip(),
            "lev_telefono": var_telefono.get().strip(),
            "lev_correo": var_correo.get().strip(),
            "lev_direccion": var_direccion.get().strip(),
            "lev_ubicacion": var_ubicacion.get().strip(),
            "lev_descripcion": descripcion,
            "lev_requerimientos": requerimientos,
            "lev_observaciones": observaciones,
            "lev_tecnico": var_tecnico.get().strip(),
            "lev_supervisor": var_supervisor.get().strip(),
            "lev_fecha_programada": var_fecha_programada.get().strip() or None,
            "lev_fecha_realizacion": None,
            "creado_por": usuario_activo.get("usuario")
        }

        if tipo_levantamiento in TIPOS_LEVANTAMIENTO_ESPECIALIZADOS:
            modalidad_operativa = (var_modalidad_levantamiento.get().strip() or "Instalación") if tipo_levantamiento == "Seguridad y Monitoreo" else "Instalación"
            detalle_tecnico = obtener_detalle_tecnico_json()
            detalle_tecnico["canalizacion_materiales"] = obtener_canalizacion_materiales_json()
            detalle_tecnico["equipos_principales"] = obtener_equipos_catalogo_json()
            detalle_tecnico["materiales_miscelaneos"] = obtener_materiales_miscelaneos_json()
            equipos_danados = obtener_equipos_danados_json() if tipo_levantamiento == "Seguridad y Monitoreo" and modalidad_operativa == "Reparación" else []
            descripcion_fallas = (
                txt_rep_descripcion_fallas.get("1.0", "end").strip()
                if tipo_levantamiento == "Seguridad y Monitoreo" and modalidad_operativa == "Reparación"
                else ""
            )
            datos.update({
                "lev_modalidad_operativa": modalidad_operativa,
                "lev_detalle_tecnico_json": json.dumps(detalle_tecnico, ensure_ascii=False),
                "lev_equipos_danados_json": json.dumps(equipos_danados, ensure_ascii=False),
                "lev_descripcion_fallas": descripcion_fallas,
            })

        resultado = crear_levantamiento(datos)

        if resultado:
            registro_creado = resultado[0] if isinstance(resultado, list) and resultado else {}
            folio = str(registro_creado.get("lev_folio") or "").strip().upper()
            if not folio:
                show_operation_error("Error al guardar", "Recuperar folio del levantamiento guardado")
                return
            var_folio.set(folio)

            registrar_movimiento(
                modulo="Levantamientos",
                accion="CREAR",
                descripcion=f"El usuario creó el levantamiento {folio}",
                registro_afectado=folio
            )

            registro_pdf = {**registro_pdf_levantamiento(folio), **datos, **registro_creado}
            ruta_pdf_destino = ruta_documentos_axia("levantamientos") / f"AXIA_{folio}.pdf"
            ruta_pdf = generar_pdf_registro(
                registro_pdf,
                configuracion_pdf_levantamiento(),
                ruta_salida=ruta_pdf_destino,
                abrir=False,
            )
            mensaje_pdf = f"\n\nPDF guardado en:\n{ruta_pdf}" if ruta_pdf else "\n\nNo se pudo guardar el PDF local."

            messagebox.showinfo(
                "Registro correcto",
                "El levantamiento fue registrado correctamente." + mensaje_pdf
            )

            app.mostrar_vista_inicio_aco()

        else:
            show_operation_error(
                "Error al guardar",
                "Registrar levantamiento"
            )

    # =================================================
    # BOTONES FIJOS
    # =================================================

    # Reordenamos el pack para que la botonera quede siempre reservada
    # al pie, incluso cuando existe panel ACO superior y el formulario crece.
    try:
        card.pack_forget()
    except Exception:
        logger.debug("Excepción recuperable controlada.", exc_info=True)

    frame_botones = ctk.CTkFrame(
        contenedor,
        fg_color="#F4F4F4",
        height=58,
        corner_radius=0
    )
    frame_botones.pack(side="bottom", fill="x", pady=(0, 0))

    card.pack(
        side="top",
        fill="both",
        expand=True,
        pady=(0, 4)
    )

    barra_botones = ctk.CTkFrame(frame_botones, fg_color="transparent")
    barra_botones.pack(anchor="center", pady=4)

    ctk.CTkButton(
        barra_botones,
        text="⬅ Atrás",
        width=120,
        height=38,
        corner_radius=10,
        fg_color="#64748B",
        hover_color="#475569",
        font=BUTTON_FONT,
        command=app.volver_atras
    ).grid(row=0, column=0, padx=4)

    btn_guardar_levantamiento = ctk.CTkButton(
        barra_botones,
        text="💾 Guardar Levantamiento",
        width=210,
        height=38,
        corner_radius=10,
        fg_color="#9CA3AF",
        hover_color="#9CA3AF",
        font=BUTTON_FONT,
        state="disabled",
        command=guardar_levantamiento
    )
    btn_guardar_levantamiento.grid(row=0, column=1, padx=4)

    btn_preview_levantamiento = ctk.CTkButton(
        barra_botones,
        text="👁 Preview PDF",
        width=165,
        height=38,
        corner_radius=10,
        fg_color="#9CA3AF",
        hover_color="#9CA3AF",
        font=BUTTON_FONT,
        state="disabled",
        command=preview_pdf_levantamiento
    )
    btn_preview_levantamiento.grid(row=0, column=2, padx=4)

    def actualizar_estado_preview():
        completo = formulario_preview_completo()
        btn_preview_levantamiento.configure(
            state="normal" if completo else "disabled",
            fg_color="#1F4E79" if completo else "#9CA3AF",
            hover_color="#173B5C" if completo else "#9CA3AF"
        )
        btn_guardar_levantamiento.configure(
            state="normal" if completo else "disabled",
            fg_color=SECONDARY if completo else "#9CA3AF",
            hover_color=BUTTON_HOVER if completo else "#9CA3AF"
        )

    variables_preview = [
        var_folio, var_cliente, var_modalidad_levantamiento,
        var_cctv_cantidad_camaras, var_cctv_dias_retencion,
        var_cctv_personas_considerar, var_cctv_ubicacion_nvr, var_cctv_punto_red,
        var_cctv_punto_energia, var_escalera_requerida, var_altura_trabajo,
        var_infra_existe, var_infra_tipo_existente, var_infra_estado,
        var_infra_tubos_tipo, var_infra_tubos_tamano, var_infra_tubos_cantidad, var_infra_coples_tipo, var_infra_coples_cantidad,
        var_infra_registros_tipo, var_infra_registros_cantidad, var_infra_conectores_tipo, var_infra_conectores_cantidad,
        var_infra_abrazaderas_tipo, var_infra_abrazaderas_cantidad, var_infra_cable_tipo, var_infra_cable_cantidad,
        var_rep_objetivo, var_rep_ubicacion_equipos, var_rep_acceso_equipos, var_rep_estado_camaras,
        var_rep_codigo_error, var_rep_horario_falla, var_rep_voltaje_correcto,
        var_rep_amperaje_suficiente, var_rep_conectores_danados, var_rep_tipo_cableado,
        var_rep_cable_danado, var_rep_rj45_correcto, var_rep_disco_operativo,
        var_rep_firmware_software, var_rep_actualizacion_corte,
        var_aa_necesidad, var_aa_cantidad_equipos, var_aa_area_climatizar,
        var_aa_tipo_area, var_aa_horario_operacion, var_aa_dimensiones_area,
        var_aa_personas_area, var_aa_tipo_equipo, var_aa_capacidad,
        var_aa_ubicacion_evaporadora, var_aa_ubicacion_condensadora,
        var_aa_dias_trabajo, var_aa_personas_trabajo,
        var_rvd_necesidad, var_rvd_tipo_servicio, var_rvd_cantidad_nodos, var_rvd_cantidad_telefonia,
        var_rvd_area_instalacion, var_rvd_horario_trabajo, var_rvd_altura_trabajo, var_rvd_acceso,
        var_rvd_permiso, var_rvd_riesgo, var_rvd_tipo_cable, var_rvd_metros_cable,
        var_rvd_tipo_canalizacion, var_rvd_metros_canalizacion, var_rvd_tipo_jacks, var_rvd_jacks,
        var_rvd_tipo_plugs, var_rvd_plugs, var_rvd_tipo_faceplates, var_rvd_faceplates,
        var_rvd_tipo_patch_cords, var_rvd_patch_cords, var_rvd_patch_panel, var_rvd_tipo_patch_panel,
        var_rvd_cantidad_patch_panel, var_rvd_requiere_rack,
        var_rvd_tipo_rack, var_rvd_requiere_gabinete, var_rvd_tipo_gabinete, var_rvd_ubicacion_rack,
        var_rvd_requiere_switch, var_rvd_tipo_switch, var_rvd_puertos_switch, var_rvd_switch_poe,
        var_rvd_ups, var_rvd_detalle_ups, var_rvd_contacto_regulado, var_rvd_detalle_contacto,
        var_rvd_tierra_fisica, var_rvd_detalle_tierra, var_rvd_dias_trabajo, var_rvd_personas_trabajo
    ]
    variables_preview.extend(vars_extra.values())
    for _var in variables_preview:
        try:
            _var.trace_add("write", lambda *_args: actualizar_estado_preview())
        except Exception:
            logger.debug("Excepción recuperable controlada.", exc_info=True)

    for _txt in [txt_descripcion, txt_observaciones]:
        try:
            _txt.bind("<KeyRelease>", lambda _event: actualizar_estado_preview(), add="+")
        except Exception:
            logger.debug("Excepción recuperable controlada.", exc_info=True)
    try:
        txt_rep_descripcion_fallas.bind("<KeyRelease>", lambda _event: actualizar_estado_preview(), add="+")
    except Exception:
        logger.debug("Excepción recuperable controlada.", exc_info=True)
    try:
        txt_rep_infraestructura.bind("<KeyRelease>", lambda _event: actualizar_estado_preview(), add="+")
    except Exception:
        logger.debug("Excepción recuperable controlada.", exc_info=True)
    actualizar_estado_preview()

    ctk.CTkButton(
        barra_botones,
        text="↩ Cancelar",
        width=130,
        height=38,
        corner_radius=10,
        fg_color="gray",
        font=BUTTON_FONT,
        command=app.mostrar_vista_inicio_aco
    ).grid(row=0, column=3, padx=4)

    enfocar_inicio_formulario(card)
