"""Formularios de mantenimiento administrativo AXIA.

Se reproducen las secciones y los controles habituales de captura, sin reutilizar
las rutinas de alta (que generan folios). Los cambios se aplican únicamente por
el RPC auditado, con controles bloqueados por sección de forma predeterminada.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any, Callable

import customtkinter as ctk
from tkinter import messagebox

from ui.colors import SECONDARY, TEXT_PRIMARY, TEXT_SECONDARY, WHITE
from ui.form_fields import AxiaEntry, AxiaTextbox
from ui.native_combobox import NativeComboBox
from ui.date_picker import abrir_selector_fecha
from core.date_utils import es_campo_fecha, formatear_fecha_visual, fecha_desde_vista
from core.background_tasks import run_async
from services.admin_registros_service import EDITABLES


# Las secciones reflejan la organización de los formularios originales de
# captura. La lista blanca EDITABLES, mantenida en la función de servidor, es la
# única fuente de verdad para permitir modificaciones.
SECCIONES = {
    'db_acos': (
        ('Datos generales del ACO', 'aco_cliente aco_responsable aco_estatus'),
        ('Planeación y fechas', 'aco_fecha_inicio aco_fecha_compromiso'),
        ('Descripción y observaciones', 'aco_descripcion aco_observaciones'),
    ),
    'db_levantamientos': (
        ('Datos generales del levantamiento', 'lev_cliente lev_tipo lev_estatus lev_prioridad lev_contacto lev_telefono lev_correo'),
        ('Ubicación y personal', 'lev_direccion lev_direccion_sucursal lev_ubicacion lev_tecnico lev_supervisor'),
        ('Programación y recursos', 'lev_fecha_programada lev_fecha_realizacion lev_duracion_proyecto lev_horas_estimadas lev_dias_trabajo lev_personas_considerar lev_modalidad_operativa'),
        ('Necesidad y alcance', 'lev_descripcion lev_requerimientos lev_descripcion_fallas lev_observaciones lev_notas'),
        ('Datos técnicos del levantamiento', 'lev_detalle_tecnico_json lev_equipos_danados_json'),
    ),
    'db_ordenes_trabajo': (
        ('Información general de la orden', 'ot_cliente ot_contacto ot_sucursal ot_fecha ot_estatus ot_prioridad'),
        ('Personal y recursos', 'ot_jefe_operacion ot_supervisor ot_esi ot_numero_dias ot_numero_personas'),
        ('Asunto y descripción', 'ot_asunto ot_descripcion'),
        ('Partidas / conceptos', 'ot_partidas_json'),
    ),
    'db_ordenes_servicio': (
        ('Información general de la orden', 'os_cliente os_tipo os_estatus os_prioridad os_sucursal'),
        ('Contacto y ubicación', 'os_contacto os_telefono os_correo os_direccion os_ubicacion'),
        ('Responsables y programación', 'os_tecnico os_supervisor os_encargado os_fecha_programada os_fecha_inicio os_fecha_cierre os_hora_llegada os_hora_salida'),
        ('Servicio y actividades', 'os_descripcion os_actividades os_materiales os_observaciones'),
    ),
    'db_bitacoras': (
        ('Datos generales de la bitácora', 'bit_cliente bit_fecha bit_direccion_sucursal bit_encargado_proyecto_axia'),
        ('Operación en campo', 'bit_hora_llegada bit_hora_salida bit_tecnico bit_tecnico_sitio'),
        ('Estado y avance', 'bit_estatus bit_porcentaje_avance'),
        ('Descripción y observaciones', 'bit_descripcion bit_observaciones'),
    ),
}

NOMBRES = {
    'aco_cliente': 'Cliente', 'aco_responsable': 'Responsable AXIA', 'aco_estatus': 'Estatus',
    'aco_fecha_inicio': 'Fecha de inicio', 'aco_fecha_compromiso': 'Fecha compromiso',
    'aco_descripcion': 'Descripción del ACO', 'aco_observaciones': 'Observaciones',
    'lev_cliente': 'Cliente', 'lev_tipo': 'Tipo de levantamiento', 'lev_estatus': 'Estatus',
    'lev_prioridad': 'Prioridad', 'lev_contacto': 'Contacto', 'lev_telefono': 'Teléfono',
    'lev_correo': 'Correo electrónico', 'lev_direccion': 'Domicilio del cliente',
    'lev_direccion_sucursal': 'Domicilio de sucursal', 'lev_ubicacion': 'Ubicación / referencia',
    'lev_tecnico': 'Técnico', 'lev_supervisor': 'Supervisor', 'lev_fecha_programada': 'Fecha programada',
    'lev_fecha_realizacion': 'Fecha de realización', 'lev_duracion_proyecto': 'Duración del proyecto',
    'lev_horas_estimadas': 'Horas estimadas', 'lev_dias_trabajo': 'Días de trabajo',
    'lev_personas_considerar': 'Personas a considerar', 'lev_modalidad_operativa': 'Modalidad operativa',
    'lev_descripcion': 'Nombre / descripción del servicio', 'lev_requerimientos': 'Requerimientos',
    'lev_descripcion_fallas': 'Descripción de fallas', 'lev_observaciones': 'Observaciones',
    'lev_notas': 'Notas', 'lev_detalle_tecnico_json': 'Detalles técnicos',
    'lev_equipos_danados_json': 'Equipos dañados', 'ot_cliente': 'Cliente',
    'ot_contacto': 'Contacto', 'ot_sucursal': 'Sucursal', 'ot_fecha': 'Fecha',
    'ot_estatus': 'Estatus', 'ot_prioridad': 'Prioridad', 'ot_jefe_operacion': 'Jefe de operación',
    'ot_supervisor': 'Supervisor', 'ot_esi': 'ESI', 'ot_numero_dias': 'Número de días',
    'ot_numero_personas': 'Número de personas', 'ot_asunto': 'Asunto',
    'ot_descripcion': 'Descripción', 'ot_partidas_json': 'Partidas / conceptos',
    'os_cliente': 'Cliente', 'os_tipo': 'Tipo de orden', 'os_estatus': 'Estatus',
    'os_prioridad': 'Prioridad', 'os_sucursal': 'Sucursal', 'os_contacto': 'Contacto',
    'os_telefono': 'Teléfono', 'os_correo': 'Correo electrónico', 'os_direccion': 'Dirección',
    'os_ubicacion': 'Ubicación', 'os_tecnico': 'Técnico(s)', 'os_supervisor': 'Supervisor',
    'os_encargado': 'Encargado de servicio', 'os_fecha_programada': 'Fecha programada',
    'os_fecha_inicio': 'Fecha de inicio', 'os_fecha_cierre': 'Fecha de cierre',
    'os_hora_llegada': 'Hora de llegada', 'os_hora_salida': 'Hora de salida',
    'os_descripcion': 'Descripción del servicio', 'os_actividades': 'Actividades realizadas',
    'os_materiales': 'Materiales', 'os_observaciones': 'Observaciones',
    'bit_cliente': 'Cliente', 'bit_fecha': 'Fecha', 'bit_direccion_sucursal': 'Dirección de sucursal',
    'bit_encargado_proyecto_axia': 'Encargado del proyecto AXIA', 'bit_hora_llegada': 'Hora de llegada',
    'bit_hora_salida': 'Hora de salida', 'bit_tecnico': 'Técnico', 'bit_tecnico_sitio': 'Técnico en sitio',
    'bit_estatus': 'Estatus', 'bit_porcentaje_avance': 'Porcentaje de avance',
    'bit_descripcion': 'Descripción', 'bit_observaciones': 'Observaciones',
}

# Solo los catálogos cuyo mapeo numérico está confirmado por los formularios
# originales. Otros estados históricos se muestran con su código, sin suponer
# equivalencias que puedan alterar registros existentes.
ENUMS = {
    'lev_tipo': {'Técnico': 1, 'Comercial': 2, 'Infraestructura': 3, 'Seguridad': 4, 'Energía': 5, 'Otro': 6},
    'lev_estatus': {'Pendiente': 1, 'En proceso': 2, 'Realizado': 3, 'Cancelado': 4},
    'lev_prioridad': {'Baja': 1, 'Media': 2, 'Alta': 3, 'Urgente': 4},
    'bit_estatus': {'Pendiente': 1, 'En proceso': 2, 'Finalizada': 3},
}

TEXTO_OPCIONES = {
    'lev_duracion_proyecto': ['Un día', 'Varios días'],
    'lev_modalidad_operativa': ['Instalación', 'Reparación', 'Mantenimiento', 'Levantamiento'],
    'os_tipo': ['Urgente', 'Correctivo', 'Capacitación', 'Póliza', 'Reubicación', 'Ordinario', 'Preventivo', 'Desmantelamiento', 'Siniestro', 'Otro'],
}

CATALOGOS_PERSONAL = {
    'aco_responsable': (1, 2, 3, 4, 5, 6, 7, 8),
    'lev_tecnico': (4,), 'lev_supervisor': (2, 3),
    'ot_jefe_operacion': (2, 3, 4), 'ot_supervisor': (2, 3), 'ot_esi': (4,),
    'os_tecnico': (4,), 'os_supervisor': (2, 3), 'os_encargado': (2, 3, 4),
    'bit_tecnico': (4,), 'bit_tecnico_sitio': (4,), 'bit_encargado_proyecto_axia': (3, 4),
}
CAMPOS_CLIENTE = {'aco_cliente', 'lev_cliente', 'ot_cliente', 'os_cliente', 'bit_cliente'}
# Un cambio de nombre sin actualizar la llave foránea deja una relación
# inconsistente. Reasignar clientes/sucursales/contactos requiere un flujo
# transaccional específico, no una simple modificación de texto.
RELACIONES_PROTEGIDAS = {
    'aco_cliente': 'id_cliente', 'lev_cliente': 'id_cliente',
    'ot_cliente': 'id_cliente', 'os_cliente': 'id_cliente', 'bit_cliente': 'id_cliente',
    'lev_contacto': 'id_contacto', 'ot_contacto': 'id_contacto',
    'os_contacto': 'id_contacto', 'ot_sucursal': 'id_sucursal',
    'os_sucursal': 'id_sucursal',
}
LARGOS = {'aco_descripcion', 'aco_observaciones', 'lev_descripcion', 'lev_requerimientos',
          'lev_descripcion_fallas', 'lev_observaciones', 'lev_notas', 'ot_asunto',
          'ot_descripcion', 'os_descripcion', 'os_actividades', 'os_materiales',
          'os_observaciones', 'bit_descripcion', 'bit_observaciones'}


def secciones_efectivas(tabla: str, original: dict) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Incluye solo columnas existentes y autorizadas en el esquema real."""
    autorizadas = set(EDITABLES[tabla]); usadas = set(); resultado = []
    for titulo, campos in SECCIONES[tabla]:
        presentes = tuple(c for c in campos.split() if c in original and c in autorizadas)
        if presentes:
            resultado.append((titulo, presentes))
            usadas.update(presentes)
    restantes = tuple(c for c in EDITABLES[tabla] if c in original and c not in usadas)
    if restantes:
        resultado.append(('Otros campos de captura', restantes))
    return tuple(resultado)


def _nombre_clave(clave: str) -> str:
    return str(clave).replace('_', ' ').capitalize()


def _analizar_json(valor):
    """Los esquemas de AXIA pueden guardar objetos JSON o cadenas JSON."""
    if isinstance(valor, (dict, list)):
        return copy.deepcopy(valor), False
    if isinstance(valor, str):
        try:
            obj = json.loads(valor)
            if isinstance(obj, (dict, list)):
                return obj, True
        except (TypeError, ValueError):
            pass
    return None, False


def _serializar_json_editado(obj, es_cadena):
    return json.dumps(obj, ensure_ascii=False) if es_cadena else obj


def _convertir_hoja(texto: str, anterior: Any):
    if anterior is None:
        return None if not texto.strip() else texto
    if isinstance(anterior, bool):
        if texto not in ('Sí', 'No'):
            raise ValueError('Selecciona Sí o No.')
        return texto == 'Sí'
    if isinstance(anterior, int) and not isinstance(anterior, bool):
        return int(texto) if texto.strip() else None
    if isinstance(anterior, float):
        return float(texto) if texto.strip() else None
    return texto


def _actualizar_ruta(arbol, ruta, valor):
    nodo = arbol
    for parte in ruta[:-1]:
        nodo = nodo[parte]
    nodo[ruta[-1]] = valor


@dataclass
class ControlAdmin:
    campo: str
    seccion: str
    leer: Callable[[], Any]
    activar: Callable[[bool], None]


class FormularioSeccionado:
    """Vista de mantenimiento sin llamadas a funciones de ALTA ni folios nuevos."""

    def __init__(self, parent, tabla: str, original: dict, *, root=None):
        self.parent = parent
        self.tabla = tabla
        self.original = original
        self.root = root or parent
        self.controles: dict[str, ControlAdmin] = {}
        self.desbloqueadas: dict[str, bool] = {}
        self._catalogo_control: list[tuple[str, NativeComboBox, str]] = []
        self._cargar_catalogos_en_segundo_plano()
        for titulo, campos in secciones_efectivas(tabla, original):
            self._seccion(titulo, campos)

    def _cargar_catalogos_en_segundo_plano(self):
        """Prepara opciones sin bloquear la ventana ni modificar el registro."""
        def tarea():
            nombres = {}
            try:
                from services.usuarios_service import obtener_nombres_usuarios_por_tipos
                distintos = set(CATALOGOS_PERSONAL) & set(EDITABLES[self.tabla])
                for campo in distintos:
                    nombres[campo] = obtener_nombres_usuarios_por_tipos(
                        CATALOGOS_PERSONAL[campo], limite=1000)
            except Exception:
                pass
            if CAMPOS_CLIENTE.intersection(EDITABLES[self.tabla]):
                try:
                    from services.clientes_service import buscar_clientes
                    clientes = buscar_clientes('', limite=1000) or []
                    nombres['clientes'] = [str(c.get('cli_razonsocial') or '').strip()
                                          for c in clientes if c.get('cli_razonsocial')]
                except Exception:
                    pass
            return nombres

        def completar(nombres):
            try:
                if not self.parent.winfo_exists():
                    return
                for campo, combo, valor_original in self._catalogo_control:
                    # Nunca sobrescribir una selección hecha mientras llegaban
                    # los datos de la consulta asíncrona.
                    seleccionado = combo.get()
                    disponibles = nombres.get('clientes' if campo in CAMPOS_CLIENTE else campo, [])
                    valores = list(dict.fromkeys([valor_original, seleccionado] + [n for n in disponibles if n]))
                    if valores:
                        combo.configure(values=valores)
                        combo.set(seleccionado)
            except Exception:
                return

        # Ejecutar después de construir los controles y mostrar la ventana.
        self.parent.after(200, lambda: run_async(root=self.root, task=tarea, on_success=completar,
                                                on_error=lambda _err: None))

    def _seccion(self, titulo, campos):
        marco = ctk.CTkFrame(self.parent, fg_color=WHITE, corner_radius=10,
                             border_width=1, border_color='#DDE5F0')
        marco.pack(fill='x', padx=7, pady=6)
        cabecera = ctk.CTkFrame(marco, fg_color='transparent')
        cabecera.pack(fill='x', padx=13, pady=(8, 2))
        ctk.CTkLabel(cabecera, text=titulo, font=('Montserrat', 14, 'bold'),
                     text_color=TEXT_PRIMARY).pack(side='left')
        self.desbloqueadas[titulo] = False
        controles_seccion = []

        def alternar():
            activo = not self.desbloqueadas[titulo]
            self.desbloqueadas[titulo] = activo
            for campo in controles_seccion:
                self.controles[campo].activar(activo)
            boton.configure(text='🔒 Bloquear sección' if activo else '🔓 Desbloquear sección',
                            fg_color='#64748B' if activo else '#000A8B')

        boton = ctk.CTkButton(cabecera, text='🔓 Desbloquear sección', width=176, height=30,
                              fg_color='#000A8B', corner_radius=11, command=alternar)
        boton.pack(side='right', padx=2)
        ctk.CTkLabel(marco, text='Solo esta sección podrá modificarse al desbloquearla.',
                     font=('Montserrat', 10), text_color=TEXT_SECONDARY).pack(anchor='w',padx=13,pady=(0,5))
        contenido = ctk.CTkFrame(marco, fg_color='transparent')
        contenido.pack(fill='x', padx=11, pady=(0,10))
        for col in range(3):
            contenido.grid_columnconfigure(col, weight=1, uniform='campos_admin')
        columna = 0; fila = 0
        for campo in campos:
            valor = self.original.get(campo)
            largo = campo in LARGOS or campo.endswith('_json') or isinstance(valor, (dict, list))
            if largo and columna:
                fila += 1; columna = 0
            ncolumnas = 3 if largo else 1
            caja = ctk.CTkFrame(contenido, fg_color='transparent')
            caja.grid(row=fila, column=columna, columnspan=ncolumnas, sticky='ew', padx=4, pady=(0,9))
            ctk.CTkLabel(caja, text=NOMBRES.get(campo, _nombre_clave(campo)),
                         font=('Montserrat', 11), text_color=TEXT_PRIMARY).pack(anchor='w', pady=(0,2))
            control = self._construir_control(caja, campo, titulo, valor)
            self.controles[campo] = control
            controles_seccion.append(campo)
            if largo:
                fila += 1; columna = 0
            else:
                columna += 1
                if columna == 3:
                    fila += 1; columna = 0

    def _construir_control(self, padre, campo, seccion, valor):
        if RELACIONES_PROTEGIDAS.get(campo) and self.original.get(RELACIONES_PROTEGIDAS[campo]):
            ctk.CTkLabel(padre, text=str(valor or '—'), anchor='w',
                         font=('Montserrat',11),text_color=TEXT_PRIMARY).pack(anchor='w',pady=4)
            ctk.CTkLabel(padre,text='Vinculado a un ID: cambiarlo requiere reasignación segura.',
                         font=('Montserrat',9),text_color=TEXT_SECONDARY).pack(anchor='w')
            return ControlAdmin(campo,seccion,lambda:valor,lambda activo:None)
        if campo.endswith('_json'):
            obj, es_cadena = _analizar_json(valor)
            if isinstance(obj, (dict, list)):
                return self._control_json(padre, campo, seccion, obj, es_cadena, valor)
            # Dato histórico no JSON: se presenta protegido, nunca se reinterpreta.
            cuadro = AxiaTextbox(padre, height=70)
            cuadro.insert('1.0', str(valor or ''))
            cuadro.configure(state='disabled')
            cuadro.pack(fill='x')
            return ControlAdmin(campo, seccion, lambda: valor, lambda activo: None)

        if campo in ('os_tecnico', 'bit_tecnico', 'bit_tecnico_sitio'):
            return self._control_tecnicos(padre, campo, seccion, valor)

        if campo in ENUMS and (isinstance(valor, (int, type(None))) and not isinstance(valor, bool)):
            opciones = ENUMS[campo]
            inverso = {v: k for k, v in opciones.items()}
            etiqueta = inverso.get(valor, str(valor) if valor is not None else '')
            etiquetas = list(opciones)
            if etiqueta and etiqueta not in etiquetas:
                etiquetas.insert(0, etiqueta)
            v = ctk.StringVar(value=etiqueta)
            cb = NativeComboBox(padre, variable=v, values=etiquetas, state='disabled')
            cb.pack(fill='x')
            def leer():
                actual = v.get()
                if actual == etiqueta:
                    return valor
                return opciones[actual]
            return ControlAdmin(campo,seccion,leer,lambda activo: cb.configure(state='readonly' if activo else 'disabled'))

        # Estados/prioridades históricos sin equivalencia publicada: selector
        # de códigos, sin inventar etiquetas para no cambiar su significado.
        if (campo.endswith('_estatus') or campo.endswith('_prioridad') or campo == 'os_tipo') and isinstance(valor, (int, type(None))):
            actual = '' if valor is None else str(valor)
            codigos = list(dict.fromkeys([actual] + [str(i) for i in range(1, 5)]))
            variable = ctk.StringVar(value=actual)
            selector = NativeComboBox(padre, variable=variable, values=codigos, state='disabled')
            selector.pack(fill='x')
            ctk.CTkLabel(padre, text='Código del estado; se conserva la numeración del registro.',
                         text_color=TEXT_SECONDARY, font=('Montserrat', 9)).pack(anchor='w')
            return ControlAdmin(campo, seccion, lambda: _convertir_hoja(variable.get(), valor),
                                lambda activo: selector.configure(state='readonly' if activo else 'disabled'))

        opciones = TEXTO_OPCIONES.get(campo)
        es_catalogo = campo in CATALOGOS_PERSONAL or campo in CAMPOS_CLIENTE
        # No forzamos a que un dato histórico deje de ser seleccionable por no
        # estar hoy en el catálogo; conservarlo es esencial para el historial.
        if opciones or es_catalogo:
            actual = str(valor) if valor is not None else ''
            lista = list(dict.fromkeys([actual] + list(opciones or [])))
            v = ctk.StringVar(value=actual)
            cb = NativeComboBox(padre, variable=v, values=lista, state='disabled')
            cb.pack(fill='x')
            if es_catalogo:
                self._catalogo_control.append((campo, cb, actual))
            return ControlAdmin(campo, seccion, lambda: _convertir_hoja(v.get(), valor),
                                lambda activo: cb.configure(state='readonly' if activo else 'disabled'))

        if isinstance(valor, bool):
            v = ctk.StringVar(value='Sí' if valor else 'No')
            cb = NativeComboBox(padre, variable=v, values=['Sí','No'],state='disabled')
            cb.pack(fill='x')
            return ControlAdmin(campo,seccion,lambda: _convertir_hoja(v.get(), valor),
                                lambda activo:cb.configure(state='readonly' if activo else 'disabled'))

        if campo in LARGOS:
            cuadro = AxiaTextbox(padre,height=88 if len(str(valor or ''))<250 else 130)
            cuadro.insert('1.0',str(valor or ''))
            cuadro.configure(state='disabled')
            cuadro.pack(fill='x')
            return ControlAdmin(campo,seccion,lambda: _convertir_hoja(cuadro.get('1.0','end-1c'),valor),
                                lambda activo:cuadro.configure(state='normal' if activo else 'disabled'))

        entrada = AxiaEntry(padre, height=32)
        entrada.insert(0, '' if valor is None else str(formatear_fecha_visual(valor) if es_campo_fecha(campo) else valor))
        entrada.configure(state='disabled')
        entrada.pack(fill='x')
        if '_fecha' in campo or campo.endswith('_fecha'):
            def calendario(_event=None):
                if not self.desbloqueadas.get(seccion, False):
                    return
                variable = ctk.StringVar(value=entrada.get())
                def escribir(*_):
                    entrada.delete(0,'end')
                    entrada.insert(0,variable.get())
                variable.trace_add('write', escribir)
                abrir_selector_fecha(entrada, variable, formato_salida='iso')
            entrada.bind('<Button-1>', calendario, add='+')
        return ControlAdmin(campo,seccion,
                            lambda: fecha_desde_vista(entrada.get(), valor) if es_campo_fecha(campo)
                            else _convertir_hoja(entrada.get(),valor),
                            lambda activo:entrada.configure(state='normal' if activo else 'disabled'))

    def _control_tecnicos(self, padre, campo, seccion, valor):
        """Mismo esquema Agregar/Quitar utilizado en OS y Bitácoras de captura."""
        original = str(valor or '')
        seleccionados = [n.strip() for n in original.split(' | ') if n.strip()]
        modificado = [False]
        fila = ctk.CTkFrame(padre, fg_color='transparent')
        fila.pack(fill='x')
        elegido = ctk.StringVar()
        selector = NativeComboBox(fila, variable=elegido, values=[''],state='disabled',width=220)
        selector.pack(side='left',fill='x',expand=True,padx=(0,4))
        self._catalogo_control.append((campo,selector,''))
        etiqueta = ctk.CTkLabel(padre, text=original or 'Sin técnicos',
                                text_color=TEXT_SECONDARY,font=('Montserrat',10),
                                anchor='w',justify='left',wraplength=570)
        etiqueta.pack(anchor='w',fill='x',pady=(3,0))
        def refrescar():
            etiqueta.configure(text=' | '.join(seleccionados) if seleccionados else 'Sin técnicos')
        def agregar():
            if not self.desbloqueadas.get(seccion):
                return
            nombre=elegido.get().strip()
            disponibles=selector.cget('values')
            if nombre and nombre in disponibles and nombre not in seleccionados:
                seleccionados.append(nombre)
                modificado[0]=True
                refrescar()
        def quitar():
            if self.desbloqueadas.get(seccion) and seleccionados:
                seleccionados.pop()
                modificado[0]=True
                refrescar()
        agregar_btn=ctk.CTkButton(fila,text='+',width=35,height=30,
                                  fg_color=SECONDARY,command=agregar,state='disabled')
        agregar_btn.pack(side='left',padx=2)
        quitar_btn=ctk.CTkButton(fila,text='−',width=35,height=30,
                                  fg_color='#DC2626',command=quitar,state='disabled')
        quitar_btn.pack(side='left',padx=2)
        def activar(activo):
            selector.configure(state='readonly' if activo else 'disabled')
            agregar_btn.configure(state='normal' if activo else 'disabled')
            quitar_btn.configure(state='normal' if activo else 'disabled')
        def leer():
            return ' | '.join(seleccionados) if modificado[0] else valor
        return ControlAdmin(campo,seccion,leer,activar)

    def _control_json(self, padre, campo, seccion, datos, es_cadena, original):
        """Muestra JSON técnico como preguntas editables, nunca como texto crudo.

        Se conserva estructura/tipos y claves desconocidas. En el caso de las
        partidas OT, el editor usa las columnas originales de la orden.
        """
        base = copy.deepcopy(datos)
        if campo == 'ot_partidas_json' and isinstance(base,list):
            return self._control_partidas(padre,campo,seccion,base,es_cadena,original)
        ctk.CTkLabel(padre,text='Respuestas técnicas guardadas · conservan su estructura',
                     text_color=TEXT_SECONDARY,font=('Montserrat',10)).pack(anchor='w',pady=2)
        grupo = ctk.CTkFrame(padre, fg_color='#F6F8FC', corner_radius=8)
        grupo.pack(fill='x', padx=1, pady=3)
        hojas = []
        def crear(nodo, ruta=(), nivel=0):
            if isinstance(nodo, dict):
                for llave, sub in nodo.items():
                    if isinstance(sub,(dict,list)):
                        titulo = ctk.CTkLabel(grupo,text='  '*min(nivel,4)+_nombre_clave(llave),
                                             font=('Montserrat',11,'bold'),text_color=TEXT_PRIMARY)
                        titulo.pack(anchor='w',padx=9,pady=(7,1))
                    crear(sub,ruta+(llave,),nivel+1)
            elif isinstance(nodo,list):
                for i, sub in enumerate(nodo):
                    if isinstance(sub,(dict,list)):
                        ctk.CTkLabel(grupo,text=f'Elemento {i+1}',text_color=TEXT_SECONDARY,
                                     font=('Montserrat',10,'bold')).pack(anchor='w',padx=12,pady=(5,0))
                    crear(sub,ruta+(i,),nivel+1)
            elif ruta:
                etiqueta = _nombre_clave(ruta[-1]) if isinstance(ruta[-1],str) else f'Valor {ruta[-1]+1}'
                caja = ctk.CTkFrame(grupo,fg_color='transparent')
                caja.pack(fill='x',padx=10,pady=2)
                ctk.CTkLabel(caja,text=etiqueta,width=235,anchor='w',wraplength=225,
                             font=('Montserrat',10)).pack(side='left',padx=(0,7))
                v=ctk.StringVar(value=('Sí' if nodo else 'No') if isinstance(nodo,bool) else '' if nodo is None else str(nodo))
                if isinstance(nodo,bool):
                    control=NativeComboBox(caja,variable=v,values=['Sí','No'],state='disabled')
                    control.pack(side='left',fill='x',expand=True)
                    activar=lambda activo,w=control:w.configure(state='readonly' if activo else 'disabled')
                else:
                    control=AxiaEntry(caja,textvariable=v,height=30,state='disabled')
                    control.pack(side='left',fill='x',expand=True)
                    activar=lambda activo,w=control:w.configure(state='normal' if activo else 'disabled')
                hojas.append((ruta,v,nodo,activar))
        crear(base)
        if not hojas:
            ctk.CTkLabel(grupo,text='No hay respuestas editables en esta estructura.',
                         text_color=TEXT_SECONDARY).pack(anchor='w',padx=8,pady=4)
        def leer():
            copia=copy.deepcopy(base)
            for ruta,v,anterior in hojas:
                valor=_convertir_hoja(v.get(),anterior)
                _actualizar_ruta(copia,ruta,valor)
            return _serializar_json_editado(copia,es_cadena)
        def activar(activo):
            for _,_,_,f in hojas:
                f(activo)
        return ControlAdmin(campo,seccion,leer,activar)

    def _control_partidas(self,padre,campo,seccion,datos,es_cadena,original):
        """Tabla editable de conceptos como la orden de trabajo de captura.

        Conserva cada dict original con campos extra y su tipo; no borra
        registros sin que el administrador desbloquee esta sección.
        """
        columnas = ('parte','unidad','cantidad','modelo','marca','concepto','dia','adicional','total')
        encabezados = ('Parte','Unidad','Cantidad','Modelo','Marca','Concepto','Día','Adicional','Total')
        contenedor=ctk.CTkFrame(padre,fg_color='transparent')
        contenedor.pack(fill='x')
        acciones=ctk.CTkFrame(padre,fg_color='transparent')
        acciones.pack(fill='x',pady=(0,4))
        filas=[]
        def agregar(item=None):
            item=copy.deepcopy(item or {})
            linea=ctk.CTkFrame(contenedor,fg_color='#F7F9FC',corner_radius=7)
            linea.pack(fill='x',pady=4)
            vars_fila={}
            for i,(key,label) in enumerate(zip(columnas,encabezados)):
                columna=ctk.CTkFrame(linea,fg_color='transparent')
                columna.grid(row=0,column=i,sticky='ew',padx=2,pady=2)
                linea.grid_columnconfigure(i,weight=1)
                ctk.CTkLabel(columna,text=label,font=('Montserrat',9)).pack(anchor='w')
                valor = item.get(key, '')
                v=ctk.StringVar(value=str(valor) if valor is not None else '')
                e=AxiaEntry(columna,textvariable=v,height=29,state='disabled',width=65)
                e.pack(fill='x')
                vars_fila[key]=(v,e,valor)
            filas.append((item,vars_fila,linea))
            if self.desbloqueadas.get(seccion):
                for _, entrada, _ in vars_fila.values():
                    entrada.configure(state='normal')

        def quitar_ultima():
            if not self.desbloqueadas.get(seccion) or not filas:
                return
            item, variables, linea = filas.pop()
            linea.destroy()
            boton_quitar.configure(state='normal' if filas else 'disabled')

        boton_agregar = ctk.CTkButton(acciones,text='+ Nueva partida',width=142,height=30,
                                       fg_color=SECONDARY,command=agregar,state='disabled')
        boton_agregar.pack(side='left',padx=(0,5))
        boton_quitar = ctk.CTkButton(acciones,text='Quitar última',width=125,height=30,
                                      fg_color='#B91C1C',command=quitar_ultima,state='disabled')
        boton_quitar.pack(side='left')
        for partida in datos:
            if isinstance(partida, dict):
                agregar(partida)
        if len(filas)<len(datos):
            # Formatos antiguos no tabulares: no se altera su estructura.
            return self._control_json_legacy(padre,campo,seccion,original)
        def leer():
            resultado=[]
            for item,vars_fila,_ in filas:
                fila=copy.deepcopy(item)
                for key,(v,_,anterior) in vars_fila.items():
                    if key in fila or v.get().strip():
                        fila[key]=_convertir_hoja(v.get(),anterior)
                resultado.append(fila)
            return _serializar_json_editado(resultado,es_cadena)
        def activar(activo):
            boton_agregar.configure(state='normal' if activo else 'disabled')
            boton_quitar.configure(state='normal' if activo and filas else 'disabled')
            for _,vars_fila,_ in filas:
                for _,e,_ in vars_fila.values():
                    e.configure(state='normal' if activo else 'disabled')
        if not filas:
            ctk.CTkLabel(contenedor,text='Sin partidas registradas.',text_color=TEXT_SECONDARY).pack(anchor='w')
        return ControlAdmin(campo,seccion,leer,activar)

    def _control_json_legacy(self,padre,campo,seccion,valor):
        ctk.CTkLabel(padre,text='Formato histórico no tabular: se conserva sin cambios.',
                     text_color=TEXT_SECONDARY).pack(anchor='w')
        return ControlAdmin(campo,seccion,lambda:valor,lambda activo:None)

    def cambios(self):
        """Devuelve exclusivamente campos pertenecientes a secciones desbloqueadas."""
        cambios={}
        for campo,control in self.controles.items():
            if not self.desbloqueadas.get(control.seccion,False):
                continue
            actual=control.leer()
            previo=self.original.get(campo)
            # El JSON histórico se compara por contenido para evitar guardados
            # sin modificación debidos solo a espacios o formato de serialización.
            if campo.endswith('_json') and isinstance(previo,str) and isinstance(actual,str):
                try:
                    if json.loads(previo)==json.loads(actual):
                        continue
                except (ValueError,TypeError):
                    pass
            if actual != previo:
                if campo == 'bit_porcentaje_avance':
                    try:
                        numero=float(actual)
                    except (ValueError, TypeError) as exc:
                        raise ValueError('El porcentaje de avance debe ser numérico.') from exc
                    if not 0 <= numero <= 100:
                        raise ValueError('El porcentaje de avance debe estar entre 0 y 100.')
                if campo in ('ot_numero_dias','ot_numero_personas','lev_personas_considerar'):
                    try:
                        if int(actual) < 0:
                            raise ValueError('Debe ser cero o mayor')
                    except (TypeError,ValueError) as exc:
                        raise ValueError(f'{NOMBRES[campo]}: ingresa un número entero no negativo.') from exc
                cambios[campo]=actual
        return cambios
