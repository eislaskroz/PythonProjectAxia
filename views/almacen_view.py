
"""Almacén AXIA · catálogo maestro único con entradas y salidas persistentes."""
from __future__ import annotations
from ui.form_fields import AxiaEntry, AxiaTextbox

import uuid
from pathlib import Path
from tkinter import messagebox, simpledialog

from PIL import Image
import customtkinter as ctk

from app_context import obtener_usuario_actual
from core.background_tasks import run_async
from security.permissions import puede_ver_almacen
from services.almacen_service import crear_almacen, formatear_cantidad
from services.almacen_entregas_ot import validar_entrega_ot, preparar_sugerencias_ot
from services.almacen_catalogo_maestro import COLUMNAS_TABLA
from services.almacen_fechas import fecha_kardex_mexico
from services.almacen_reimpresion import generar_comprobante_historico
from services.almacen_comprobantes import (
    generar_etiqueta_entrada, generar_ticket_salida, abrir_comprobante,
)
from ui.colors import (
    WHITE, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY, BUTTON_HOVER
)
from ui.fonts import TITLE_MD, TEXT_MD, BUTTON_FONT
from ui.native_table import NativeTreeTable


def _moneda(value):
    try:
        return f"${float(str(value or 0).replace('$', '').replace(',', '')):,.2f}"
    except (ValueError, TypeError):
        return '—'


def _icono_blanco(ruta):
    """Convierte el icono a blanco y conserva su transparencia."""
    with Image.open(ruta) as imagen:
        imagen_rgba = imagen.convert('RGBA')

    alpha = imagen_rgba.getchannel('A')
    imagen_blanca = Image.new(
        'RGBA',
        imagen_rgba.size,
        (255, 255, 255, 255)
    )
    imagen_blanca.putalpha(alpha)

    return imagen_blanca


def mostrar_almacen(parent, app=None):
    usuario = dict(obtener_usuario_actual() or {})
    if not puede_ver_almacen(usuario) or not usuario.get('id_usuario'):
        messagebox.showerror(
            'Acceso denegado',
            'Se requiere una sesión activa de Administrador o Almacén.'
        )
        return

    try:
        servicio = crear_almacen()
    except Exception as exc:
        messagebox.showerror('Almacén', str(exc))
        return

    # Ruta de los iconos del módulo.
    carpeta_iconos = Path(__file__).resolve().parent.parent / 'assets' / 'iconos'

    root = ctk.CTkFrame(parent, fg_color='transparent')
    root.pack(fill='both', expand=True, padx=14, pady=(4, 12))
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)

    def ofrecer_comprobante(*, tipo, resumen, movimientos=None, codigo='', producto='',
                            cantidad='', destinatario='', motivo='', referencia='',
                            responsable='', identificador=None, fecha=None):
        """Ofrece imprimir después del COMMIT confirmado. No registra inventario."""
        es_entrada = tipo == 'ENTRADA'
        titulo = 'Entrada registrada' if es_entrada else 'Salida registrada'
        nombre = 'etiqueta Code 128 para el producto' if es_entrada else 'ticket de entrega (80 mm)'
        if not messagebox.askyesno(
            titulo, f'{resumen}\n\n¿Deseas generar {"una" if es_entrada else "un"} {nombre}?\n'
            'Se abrirá un PDF para que elijas la impresora.', parent=root.winfo_toplevel()
        ):
            return
        try:
            if es_entrada:
                ruta = generar_etiqueta_entrada(
                    codigo=codigo, producto=producto, cantidad=cantidad,
                    referencia=referencia, identificador=identificador, fecha=fecha,
                )
            else:
                ruta = generar_ticket_salida(
                    partidas=list(movimientos or ()), destinatario=destinatario,
                    motivo=motivo, referencia=referencia, responsable=responsable,
                    identificador=identificador, fecha=fecha,
                )
            try:
                abrir_comprobante(ruta)
            except Exception:
                # El PDF sigue guardado; imprimirlo no altera el movimiento.
                messagebox.showinfo('Comprobante generado',
                    f'El archivo se guardó correctamente, pero no se pudo abrir automáticamente:\n{ruta}',
                    parent=root.winfo_toplevel())
        except Exception as exc:
            messagebox.showwarning('Movimiento guardado - Comprobante pendiente',
                f'El movimiento YA quedó registrado en Supabase.\n'
                f'No vuelvas a registrarlo.\n\nNo se pudo generar el comprobante: {exc}',
                parent=root.winfo_toplevel())

    # -------- PESTAÑAS OPERATIVAS --------
    tabs = ctk.CTkTabview(
        root,
        fg_color=WHITE,
        corner_radius=10,
        border_width=0,
        segmented_button_fg_color='#71849A',
        segmented_button_selected_color=SECONDARY,
        segmented_button_selected_hover_color=BUTTON_HOVER,
        segmented_button_unselected_color='#71849A',
        segmented_button_unselected_hover_color='#526981',
        text_color=WHITE
    )
    tabs.grid(row=0, column=0, sticky='nsew')

    t_catalogo = tabs.add('Catálogo')
    t_entrada = tabs.add('Entradas')
    t_salida = tabs.add('Salidas')
    t_kardex = tabs.add('Kárdex / Historial')
    t_admin = tabs.add('Altas/Bajas/Modificaciones')

    # El contenedor de pestañas se estira a todo el ancho disponible.
    tabs.grid_columnconfigure(0, weight=1)
    tabs._segmented_button.grid_configure(
        row=0,
        column=0,
        sticky='ew',
        padx=0,
        pady=0
    )

    # Texto y altura de las cinco pestañas.
    tabs._segmented_button.configure(
        font=('Segoe UI', 14),
        text_color=WHITE,
        corner_radius=8,
        height=44
    )

    # Distribuir uniformemente el ancho entre las cinco opciones.
    for columna in range(5):
        tabs._segmented_button.grid_columnconfigure(
            columna,
            weight=1,
            uniform='pestanas_almacen'
        )

    # La fuente piloto es exclusivamente CONSULTIVA. Los movimientos siguen
    # utilizando 'registros', que se alimenta del catálogo OPERATIVO.
    maestro = {'items': [], 'total': 0, 'pagina': 1, 'limite': 100,
               'busqueda': '', 'cargado': False, 'solicitud': 0}
    vista_maestro_habilitada = False  # Una sola base operativa.
    fuente_inicial = 'Operativo'
    COLUMNAS_OPERATIVAS = (
        ('codigo', 'Código AXIA', 160), ('estado', 'Estado', 95),
        ('producto', 'Producto', 320), ('categoria_axia', 'Categoría AXIA', 180),
        ('familia_axia', 'Familia AXIA', 220), ('departamento', 'Departamento origen', 155),
        ('saldo', 'Saldo actual', 105), ('saldo_exportado', 'ELEVENTA origen', 135),
        ('costo', 'P. costo', 105), ('venta', 'P. venta', 105),
        ('p_mayoreo', 'P. mayoreo', 105), ('minimo', 'Mínimo', 90), ('maximo', 'Máximo', 90),
        ('proveedor', 'Proveedor', 145), ('codigo_proveedor', 'Cód. proveedor', 145),
        ('codigo_origen_eleventa', 'Código ELEVENTA', 145),
    )

    # -------- CATÁLOGO --------
    t_catalogo.grid_columnconfigure(0, weight=1)
    t_catalogo.grid_rowconfigure(3, weight=1)

    barra = ctk.CTkFrame(t_catalogo, fg_color='transparent')
    barra.grid(row=0, column=0, sticky='ew', padx=7, pady=6)
    barra.grid_columnconfigure(0, weight=1)

    with Image.open(carpeta_iconos / 'buscar.png') as imagen_buscar:
        imagen_buscar = imagen_buscar.convert('RGBA').copy()

    icono_buscar = ctk.CTkImage(
        light_image=imagen_buscar,
        dark_image=imagen_buscar,
        size=(18, 18)
    )

    buscar_wrap = ctk.CTkFrame(
        barra,
        fg_color='#F8FAFC',
        corner_radius=12,
        border_width=2,
        border_color='#647B96'
    )
    buscar_wrap.grid(row=0, column=0, sticky='ew', padx=(0, 8))
    buscar_wrap.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(
        buscar_wrap,
        text='',
        image=icono_buscar,
        width=24,
        height=34,
        anchor='center'
    ).grid(
        row=0,
        column=0,
        sticky='ns',
        padx=(12, 8),
        pady=3
    )

    buscar = AxiaEntry(
        buscar_wrap,
        placeholder_text='Buscar código AXIA, producto, categoría o familia...',
        height=34,
        fg_color='transparent',
        border_width=0,
        text_color=TEXT_PRIMARY
    )
    buscar.grid(
        row=0,
        column=1,
        sticky='ew',
        padx=(0, 12),
        pady=3
    )

    contador = ctk.CTkLabel(
        barra,
        text='Cargando...',
        text_color=TEXT_SECONDARY
    )
    contador.grid(row=0, column=1, padx=8)

    imagen_limpiar = _icono_blanco(carpeta_iconos / 'limpiar.png')

    icono_actualizar = ctk.CTkImage(
        light_image=imagen_limpiar,
        dark_image=imagen_limpiar,
        size=(25, 25)
    )

    btn_actualizar = ctk.CTkButton(
        barra,
        text='Actualizar',
        image=icono_actualizar,
        compound='left',
        height=30,
        width=140,
        corner_radius=10,
        border_width=1,
        border_color='#52708F',
        font=('Segoe UI', 13),
        text_color=WHITE,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        anchor='center',
        command=lambda: refrescar_catalogo_visible()
    )
    btn_actualizar.grid(row=0, column=3, padx=(4, 0))

    ctk.CTkButton(
        barra, text='Buscar', height=30, width=85,
        font=('Segoe UI', 13), command=lambda: buscar_en_catalogo()
    ).grid(row=0, column=2, padx=(2, 3))

    origen = ctk.CTkSegmentedButton(
        barra, values=['Maestro AXIA (piloto)', 'Operativo'], height=34,
        command=lambda opcion: cambiar_fuente_catalogo(opcion)
    )
    # Selector de fuentes oculto: solamente existe un catálogo real.
    # Selección inicial se aplica tras crear todos los controles.

    ayuda = ctk.CTkLabel(
        t_catalogo,
        text=(
            'CATÁLOGO ÚNICO AXIA · Selecciona un producto para su entrada o salida. '
            'Saldo actual en Supabase; ELEVENTA es referencia histórica.'
        ),
        text_color=TEXT_SECONDARY,
        anchor='w'
    )
    ayuda.grid(row=2, column=0, sticky='ew', padx=8, pady=(0, 4))

    tabla = NativeTreeTable(
        t_catalogo,
        columns=COLUMNAS_OPERATIVAS,
        height=17
    , table_id="almacen_catalogo")
    tabla.grid(row=3, column=0, sticky='nsew', padx=7, pady=5)

    # El catálogo utiliza todo el espacio libre para la tabla.
    # Se retiraron el aviso de selección y la ficha inferior de detalle.
    paginacion_maestro = ctk.CTkFrame(t_catalogo, fg_color='transparent')
    paginacion_maestro.grid(row=6, column=0, sticky='e', padx=8, pady=(0, 4))
    btn_maestro_anterior = ctk.CTkButton(
        paginacion_maestro, text='Anterior', width=90, height=30,
        command=lambda: cambiar_pagina_maestro(-1))
    btn_maestro_anterior.pack(side='left', padx=3)
    etiqueta_pagina_maestro = ctk.CTkLabel(paginacion_maestro, text='Página 1')
    etiqueta_pagina_maestro.pack(side='left', padx=10)
    btn_maestro_siguiente = ctk.CTkButton(
        paginacion_maestro, text='Siguiente', width=90, height=30,
        command=lambda: cambiar_pagina_maestro(1))
    btn_maestro_siguiente.pack(side='left', padx=3)
    paginacion_maestro.grid_remove()

    # -------- ALTAS / BAJAS / MODIFICACIONES: INDEPENDIENTE DE CONSULTA --------
    t_admin.grid_columnconfigure(0, weight=1)
    t_admin.grid_rowconfigure(2, weight=1)
    acciones = ctk.CTkFrame(t_admin, fg_color='transparent')
    acciones.grid(row=0, column=0, sticky='ew', padx=8, pady=(8, 5))
    var_inactivos = ctk.BooleanVar(value=False)

    def boton_producto(texto, columna, callback, color=SECONDARY):
        btn = ctk.CTkButton(
            acciones, text=texto, width=138, height=36, corner_radius=10,
            fg_color=color, hover_color=BUTTON_HOVER, font=('Segoe UI', 12),
            command=callback
        )
        btn.grid(row=0, column=columna, padx=(0, 7), pady=2)
        return btn

    boton_producto('+ Nuevo producto', 0, lambda: abrir_editor_producto())
    boton_producto('Editar producto', 1, lambda: abrir_editor_producto(editar=True))
    boton_producto('Dar de baja', 2, lambda: cambiar_estado_producto(False), color='#A72D37')
    boton_producto('Reactivar', 3, lambda: cambiar_estado_producto(True))
    ctk.CTkCheckBox(
        acciones, text='Ver inactivos', variable=var_inactivos,
        command=lambda: mostrar_registros(), font=('Segoe UI', 12),
        text_color=TEXT_PRIMARY
    ).grid(row=0, column=4, sticky='w', padx=(10, 0))

    barra_admin = ctk.CTkFrame(t_admin, fg_color='transparent')
    barra_admin.grid(row=1,column=0,sticky='ew',padx=8,pady=(0,4))
    barra_admin.grid_columnconfigure(0,weight=1)
    buscar_admin = AxiaEntry(barra_admin,placeholder_text='Buscar código, producto o departamento...',height=35)
    buscar_admin.grid(row=0,column=0,sticky='ew',padx=(0,8))
    ctk.CTkButton(barra_admin,text='Actualizar',width=115,command=lambda:cargar_catalogo()).grid(row=0,column=1)

    tabla_admin = NativeTreeTable(t_admin,columns=(
        ('codigo','Código',150),('estado','Estado',105),('producto','Producto',320),
        ('departamento','Departamento',150),('saldo','Saldo',110),
        ('costo','Costo',100),('minimo','Mínimo',90),('maximo','Máximo',90)),height=15, table_id="almacen_productos_admin")
    tabla_admin.grid(row=2,column=0,sticky='nsew',padx=7,pady=5)
    seleccionado_admin_txt = ctk.CTkLabel(t_admin,text='Selecciona un artículo para editarlo o darlo de baja.',
                                        text_color=TEXT_SECONDARY,anchor='w')
    seleccionado_admin_txt.grid(row=3,column=0,sticky='ew',padx=8,pady=(2,7))

    entradas = {}

    def construir_form(tab, tipo):
        tab.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            tab,
            text=('Recepción de productos y herramientas' if tipo == 'ENTRADA' else 'Salida individual de almacén'),
            font=TITLE_MD,
            text_color=TEXT_PRIMARY
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky='w',
            padx=14,
            pady=(14, 10)
        )

        definiciones = [
            ('codigo', 'Código de producto *'),
            ('cantidad', 'Cantidad * (hasta 3 decimales)'),
            ('motivo', 'Motivo / descripción *'),
            ('referencia', 'Referencia / folio de compra / OT (opcional)'),
        ]

        if tipo == 'SALIDA':
            definiciones.append(('destinatario', 'Recibe el material *'))
        else:
            definiciones.append(('destinatario', 'Proveedor / origen de mercancía *'))

        campos = {}

        for index, (key, label) in enumerate(definiciones, start=1):
            ctk.CTkLabel(
                tab,
                text=label,
                text_color=TEXT_PRIMARY,
                anchor='w'
            ).grid(
                row=index,
                column=0,
                sticky='w',
                padx=(15, 8),
                pady=7
            )

            entry = AxiaEntry(tab, height=35)
            entry.grid(
                row=index,
                column=1,
                sticky='ew',
                padx=(4, 15),
                pady=7
            )
            campos[key] = entry

        # -------- BOTÓN CONFIRMAR: CENTRADO Y CON ESTILO MEJORADO --------
        if tipo == 'ENTRADA':
            nombre_icono = 'entrada.png'
            texto_boton = 'Confirmar entrada'
        else:
            nombre_icono = 'salida.png'
            texto_boton = f'Confirmar {tipo.lower()}'

        imagen_confirmar = _icono_blanco(
            carpeta_iconos / nombre_icono
        )

        icono_confirmar = ctk.CTkImage(
            light_image=imagen_confirmar,
            dark_image=imagen_confirmar,
            size=(24, 24)
        )

        btn = ctk.CTkButton(
            tab,
            text=texto_boton,
            image=icono_confirmar,
            compound='left',
            font=('Segoe UI', 15),
            text_color=WHITE,
            fg_color=SECONDARY,
            hover_color=BUTTON_HOVER,
            height=44,
            width=230,
            corner_radius=10,
            command=lambda: guardar(tipo)
        )
        btn.grid(
            row=6,
            column=0,
            columnspan=2,
            sticky='',
            padx=15,
            pady=(8, 8)
        )

        nota = (
            'Las salidas nunca permiten un saldo negativo. '
            if tipo == 'SALIDA'
            else 'La cantidad se sumará al saldo del producto. '
        )

        ctk.CTkLabel(
            tab,
            text=nota + 'Se confirma el movimiento antes de registrarlo.',
            text_color=TEXT_SECONDARY,
            anchor='w'
        ).grid(
            row=7,
            column=0,
            columnspan=2,
            sticky='ew',
            padx=14,
            pady=4
        )

        entradas[tipo] = (campos, btn)

    construir_form(t_entrada, 'ENTRADA')
    if not servicio.remoto:
        ctk.CTkLabel(t_entrada, text='Modo simulador: los movimientos desaparecen al cerrar esta pantalla.',
                     font=('Segoe UI',11), text_color='#A65E09').grid(row=8,column=0,columnspan=2,sticky='w',padx=14)

    t_salida.grid_columnconfigure(0, weight=1)
    t_salida.grid_rowconfigure(1, weight=1)
    fila_modalidad = ctk.CTkFrame(t_salida,fg_color='transparent')
    fila_modalidad.grid(row=0,column=0,sticky='ew',padx=12,pady=(10,4))
    ctk.CTkLabel(fila_modalidad,text='Modalidad de entrega:',font=TEXT_MD,
                 text_color=TEXT_PRIMARY).pack(side='left',padx=(0,10))
    formulario_pieza = ctk.CTkFrame(t_salida,fg_color='transparent')
    formulario_pieza.grid(row=1,column=0,sticky='nsew')
    construir_form(formulario_pieza, 'SALIDA')
    formulario_ot = ctk.CTkScrollableFrame(t_salida,fg_color='transparent')
    formulario_ot.grid(row=1,column=0,sticky='nsew')
    formulario_ot.grid_remove()
    def cambiar_modalidad(value):
        if value == 'Por OT':
            formulario_pieza.grid_remove()
            formulario_ot.grid()
        else:
            formulario_ot.grid_remove()
            formulario_pieza.grid()
    control_modalidad = ctk.CTkSegmentedButton(fila_modalidad,values=['Por pieza','Por OT'],
                           command=cambiar_modalidad,height=35)
    control_modalidad.pack(side='left')
    control_modalidad.set('Por pieza')

    # Entrega de varias partidas por Orden de Trabajo (sin descuentos parciales).
    formulario_ot.grid_columnconfigure(1,weight=1)
    ctk.CTkLabel(formulario_ot,text='Entrega de materiales por Orden de Trabajo',
                 font=TITLE_MD,text_color=TEXT_PRIMARY).grid(row=0,column=0,columnspan=3,
                                                               sticky='w',padx=12,pady=(10,8))
    ctk.CTkLabel(formulario_ot,text='Folio de OT *',text_color=TEXT_PRIMARY).grid(row=1,column=0,sticky='w',padx=12)
    campo_ot = AxiaEntry(formulario_ot,height=36,placeholder_text='OT-00001')
    campo_ot.grid(row=1,column=1,sticky='ew',padx=8,pady=5)
    btn_ver_ot = ctk.CTkButton(formulario_ot,text='Consultar OT',width=125,command=lambda:consultar_ot())
    btn_ver_ot.grid(row=1,column=2,padx=12,pady=5)
    informacion_ot = ctk.CTkLabel(formulario_ot,text='Consulta la OT antes de preparar la entrega.',
                                  text_color=TEXT_SECONDARY,anchor='w',justify='left')
    informacion_ot.grid(row=2,column=0,columnspan=3,sticky='ew',padx=12,pady=(0,5))
    ctk.CTkLabel(formulario_ot,text='Partidas requeridas por la OT (referencia)',
                 text_color=TEXT_PRIMARY).grid(row=3,column=0,columnspan=3,sticky='w',padx=12,pady=(6,2))
    lista_ot = AxiaTextbox(formulario_ot,height=94,wrap='word')
    lista_ot.grid(row=4,column=0,columnspan=3,sticky='ew',padx=12,pady=(0,8))
    lista_ot.configure(state='disabled')
    fila_articulo = ctk.CTkFrame(formulario_ot,fg_color='transparent')
    fila_articulo.grid(row=5,column=0,columnspan=3,sticky='ew',padx=12,pady=5)
    fila_articulo.grid_columnconfigure(1,weight=1)
    ctk.CTkLabel(fila_articulo,text='Código del producto *').grid(row=0,column=0,sticky='w',padx=(0,10))
    campo_ot_codigo = AxiaEntry(fila_articulo,height=35,placeholder_text='Código exacto del catálogo')
    campo_ot_codigo.grid(row=0,column=1,sticky='ew',padx=(0,10))
    ctk.CTkLabel(fila_articulo,text='Cantidad *').grid(row=0,column=2,padx=(0,8))
    campo_ot_cantidad = AxiaEntry(fila_articulo,height=35,width=115)
    campo_ot_cantidad.grid(row=0,column=3,padx=(0,10))
    ctk.CTkButton(fila_articulo,text='+ Agregar',width=105,command=lambda:agregar_partida_ot()).grid(row=0,column=4)
    tabla_ot = NativeTreeTable(formulario_ot,columns=(
        ('codigo','Código',155),('producto','Producto',360),
        ('cantidad','Cantidad',115),('saldo','Saldo disponible',130)),height=6, table_id="almacen_entregas_ot")
    tabla_ot.grid(row=6,column=0,columnspan=3,sticky='ew',padx=12,pady=5)
    ctk.CTkButton(formulario_ot,text='Quitar partida seleccionada',height=33,width=210,
                  fg_color='#64748B',command=lambda:quitar_partida_ot()).grid(row=7,column=0,columnspan=3,
                      sticky='w',padx=12,pady=3)
    pie_ot=ctk.CTkFrame(formulario_ot,fg_color='transparent')
    pie_ot.grid(row=8,column=0,columnspan=3,sticky='ew',padx=12,pady=(8,5))
    pie_ot.grid_columnconfigure(1,weight=1)
    ctk.CTkLabel(pie_ot,text='Recibe el material *').grid(row=0,column=0,sticky='w',padx=(0,8))
    campo_ot_destinatario=AxiaEntry(pie_ot,height=35)
    campo_ot_destinatario.grid(row=0,column=1,sticky='ew',padx=(0,10))
    ctk.CTkLabel(pie_ot,text='Motivo *').grid(row=1,column=0,sticky='w',padx=(0,8),pady=5)
    campo_ot_motivo=AxiaEntry(pie_ot,height=35)
    campo_ot_motivo.grid(row=1,column=1,sticky='ew',padx=(0,10),pady=5)
    revision_ot = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(formulario_ot,variable=revision_ot,
        text='Revisé las partidas de la OT y verifiqué códigos, cantidades y entrega parcial o completa.',
        text_color=TEXT_PRIMARY).grid(row=9,column=0,columnspan=3,sticky='w',padx=12,pady=7)
    btn_guardar_ot=ctk.CTkButton(formulario_ot,text='Confirmar salida por OT',height=43,
                  command=lambda:guardar_ot())
    btn_guardar_ot.grid(row=10,column=0,columnspan=3,sticky='ew',padx=12,pady=(5,8))
    if not servicio.remoto:
        ctk.CTkLabel(formulario_ot,text='Modo simulador: OT no validada en Supabase; los saldos se pierden al cerrar.',
                     font=('Segoe UI',11),text_color='#A65E09').grid(row=11,column=0,columnspan=3,sticky='w',padx=12)
    partidas_ot = []
    ot_validada = {'folio':None,'pendientes':[]}
    intento_ot = {'firma':None,'id':None}

    def representar_partidas_ot():
        tabla_ot.set_rows([{**p,'producto': next((r.get('producto','') for r in registros
            if str(r.get('codigo'))==p['codigo']),''),
             'saldo':next((r.get('saldo','0') for r in registros if str(r.get('codigo'))==p['codigo']),'0')}
             for p in partidas_ot])
        revision_ot.set(False)

    def agregar_partida_ot():
        codigo=campo_ot_codigo.get().strip()
        producto=next((r for r in registros if str(r.get('codigo'))==codigo and r.get('activo',True)),None)
        if not producto:
            messagebox.showwarning('Almacén','El código debe existir y estar activo en Catálogo.')
            return
        try:
            from services.almacen_service import cantidad_valida
            cantidad=cantidad_valida(campo_ot_cantidad.get())
        except ValueError as exc:
            messagebox.showwarning('Cantidad inválida',str(exc))
            return
        from decimal import Decimal
        existente=next((p for p in partidas_ot if p['codigo']==codigo),None)
        if existente:
            cantidad+=Decimal(existente['cantidad'])
            try:
                cantidad=cantidad_valida(cantidad)
            except ValueError as exc:
                messagebox.showwarning('Cantidad inválida',str(exc))
                return
            existente['cantidad']=formatear_cantidad(cantidad)
        else:
            if len(partidas_ot)>=80:
                messagebox.showwarning('Límite','Máximo 80 códigos por entrega.')
                return
            partidas_ot.append({'codigo':codigo,'cantidad':formatear_cantidad(cantidad)})
        campo_ot_codigo.delete(0,'end')
        campo_ot_cantidad.delete(0,'end')
        representar_partidas_ot()

    def quitar_partida_ot():
        p=tabla_ot.selected_payload()
        if not p:
            messagebox.showwarning('Almacén','Selecciona una partida de la entrega.')
            return
        partidas_ot[:]=[x for x in partidas_ot if x['codigo']!=p['codigo']]
        representar_partidas_ot()

    def consultar_ot():
        folio=campo_ot.get().strip().upper()
        if not folio:
            messagebox.showwarning('Almacén','Indica primero el folio de OT.')
            return
        btn_ver_ot.configure(state='disabled')
        informacion_ot.configure(text='Verificando Orden de Trabajo...')
        def ok(datos):
            btn_ver_ot.configure(state='normal')
            ot_validada['folio']=str(datos.get('folio') or '').strip().upper()
            sugeridas,pendientes=preparar_sugerencias_ot(datos,registros)
            ot_validada['pendientes']=pendientes
            partidas_ot.clear()
            from decimal import Decimal
            suma={}
            for p in sugeridas:
                suma[p['codigo']]=suma.get(p['codigo'],Decimal('0'))+Decimal(p['cantidad'])
            partidas_ot.extend({'codigo':k,'cantidad':formatear_cantidad(v)} for k,v in suma.items())
            representar_partidas_ot()
            header='OT simulada (sin consultar Supabase)' if datos.get('simulador') else (
                f'OT verificada · {datos.get("cliente", "")} · {datos.get("asunto", "")}')
            informacion_ot.configure(text=header+' | Revisa partidas antes de confirmar.' +
                 (f' {len(pendientes)} partida(s) sin vincular.' if pendientes else ''))
            lines=[f'{str(p.get("cantidad") or "")}  {str(p.get("codigo") or "")}  {str(p.get("concepto") or "")}'
                   for p in sugeridas]
            lines += [f'POR IDENTIFICAR: {p["cantidad"]} · {p["concepto"]} (SKU: {p["codigo"] or "no indicado"})'
                      for p in pendientes]
            if not lines:
                lines=['Sin partidas precargadas. Agrega manualmente los productos de la entrega.']
            lista_ot.configure(state='normal')
            lista_ot.delete('1.0','end')
            lista_ot.insert('1.0','\n'.join(lines))
            lista_ot.configure(state='disabled')
        def err(exc):
            btn_ver_ot.configure(state='normal')
            ot_validada['folio']=None
            partidas_ot.clear()
            representar_partidas_ot()
            informacion_ot.configure(text=f'No fue posible consultar la OT: {exc}')
            messagebox.showerror('Orden de Trabajo',str(exc))
        run_async(root.winfo_toplevel(),lambda:servicio.consultar_ot(folio,usuario),ok,err)

    def guardar_ot():
        if ot_validada['folio'] is None or campo_ot.get().strip().upper()!=ot_validada['folio']:
            messagebox.showwarning('Almacén','Consulta y verifica el folio antes de registrar la entrega.')
            return
        if not revision_ot.get():
            messagebox.showwarning('Almacén','Confirma que revisaste las partidas y la entrega.')
            return
        try:
            solicitud=validar_entrega_ot(ot_validada['folio'],partidas_ot,
                    campo_ot_destinatario.get(),campo_ot_motivo.get())
            from decimal import Decimal
            for p in solicitud['partidas']:
                producto=next((r for r in registros if str(r.get('codigo'))==p['codigo']),None)
                if not producto or not producto.get('activo',True):
                    raise ValueError(f'Producto {p["codigo"]} no disponible.')
                if Decimal(str(producto.get('saldo') or 0))<Decimal(p['cantidad']):
                    raise ValueError(f'Saldo insuficiente de {p["codigo"]}. Actualiza el catálogo.')
        except (ValueError,TypeError) as exc:
            messagebox.showwarning('Revisa la entrega',str(exc))
            return
        detalle='\n'.join(f'{p["codigo"]}: {p["cantidad"]}' for p in solicitud['partidas'])
        if not messagebox.askyesno('Confirmar entrega de OT',
            f'OT: {solicitud["folio"]}\nRecibe: {solicitud["destinatario"]}\n\n'+detalle+
            '\n\nSe registrará TODO junto o NADA.\n'
            'La lista debe coincidir con lo que realmente se entrega.'):
            return
        firma=(solicitud['folio'],solicitud['destinatario'],solicitud['motivo'],
               tuple((p['codigo'],p['cantidad']) for p in solicitud['partidas']))
        if firma!=intento_ot['firma']:
            intento_ot.update(firma=firma,id=str(uuid.uuid4()))
        btn_guardar_ot.configure(state='disabled')
        status.configure(text='Registrando entrega por OT...')
        def ok(resultado):
            btn_guardar_ot.configure(state='normal')
            catalogo_por_codigo = {str(p.get('codigo')): p for p in registros}
            partidas_recibo = [
                {'codigo': item['codigo'], 'cantidad': item['cantidad'],
                 'producto': str(catalogo_por_codigo.get(str(item['codigo']), {}).get('producto') or '')}
                for item in solicitud['partidas']
            ]
            ofrecer_comprobante(
                tipo='SALIDA',
                resumen=(f'OT: {solicitud["folio"]}\n'
                         f'Partidas registradas: {resultado.get("cantidad_partidas")}\n'
                         'El Kárdex conservó los movimientos individuales.'),
                movimientos=partidas_recibo,
                referencia=solicitud['folio'],
                destinatario=solicitud['destinatario'],
                motivo=solicitud['motivo'],
                responsable=str(usuario.get('usu_nombre') or usuario.get('nombre') or usuario.get('usuario') or ''),
                identificador=intento_ot['id'],
            )
            partidas_ot.clear()
            ot_validada['folio']=None
            intento_ot.update(firma=None,id=None)
            representar_partidas_ot()
            revision_ot.set(False)
            cargar_catalogo()
            buscar_k.delete(0,'end')
            cargar_kardex()
        def err(exc):
            btn_guardar_ot.configure(state='normal')
            status.configure(text='Resultado incierto: verifica Kárdex antes de reintentar.',text_color='#B91C1C')
            messagebox.showerror('Entrega no confirmada',str(exc)+'\n\nSi reintentas sin cambiar datos se usa el mismo ID.')
        run_async(root.winfo_toplevel(),
                  lambda:servicio.registrar_salida_ot(**solicitud,usuario=usuario,idempotencia=intento_ot['id']),
                  ok,err)

    def invalidar_ot_cambiada(*_):
        if ot_validada['folio'] and campo_ot.get().strip().upper()!=ot_validada['folio']:
            ot_validada['folio']=None
            revision_ot.set(False)
    campo_ot.bind('<KeyRelease>',invalidar_ot_cambiada)


    # -------- KARDEX: BUSCADOR Y ACCIONES EN UNA ÚNICA FILA --------
    t_kardex.grid_columnconfigure(0, weight=1)
    t_kardex.grid_rowconfigure(1, weight=1)

    filtrar_k = ctk.CTkFrame(
        t_kardex,
        fg_color='transparent'
    )
    filtrar_k.grid(
        row=0,
        column=0,
        sticky='ew',
        padx=8,
        pady=8
    )
    # El buscador ocupa ~50 % de la fila; los 3 botones comparten el resto.
    # 'uniform' mantiene la proporción cuando se maximiza la ventana.
    filtrar_k.grid_columnconfigure(0, weight=3, uniform='acciones_kardex')
    for indice in (1, 2, 3):
        filtrar_k.grid_columnconfigure(indice, weight=1, uniform='acciones_kardex')

    # CORRECCIÓN: cargar buscar.png directamente, como en Catálogo.
    # No aplicar _icono_blanco a este icono.
    with Image.open(carpeta_iconos / 'buscar.png') as imagen_buscar_k:
        imagen_buscar_k = imagen_buscar_k.convert('RGBA').copy()

    icono_buscar_k = ctk.CTkImage(
        light_image=imagen_buscar_k,
        dark_image=imagen_buscar_k,
        size=(20, 20)
    )

    # Contenedor visual de la barra de búsqueda.
    buscar_k_wrap = ctk.CTkFrame(
        filtrar_k,
        fg_color='#F8FAFC',
        corner_radius=12,
        border_width=2,
        border_color='#647B96'
    )
    buscar_k_wrap.grid(
        row=0,
        column=0,
        sticky='ew',
        padx=(0, 8)
    )
    buscar_k_wrap.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(
        buscar_k_wrap,
        text='',
        image=icono_buscar_k,
        width=24,
        height=34,
        anchor='center'
    ).grid(
        row=0,
        column=0,
        sticky='ns',
        padx=(12, 8),
        pady=3
    )

    buscar_k = AxiaEntry(
        buscar_k_wrap,
        placeholder_text='Código AXIA o folio de OT (vacío: todo)',
        height=34,
        fg_color='transparent',
        border_width=0,
        text_color=TEXT_PRIMARY
    )
    buscar_k.grid(
        row=0,
        column=1,
        sticky='ew',
        padx=(0, 12),
        pady=3
    )

    # Icono blanco del botón Consultar Kardex.
    imagen_consulta = _icono_blanco(
        carpeta_iconos / 'consulta.png'
    )

    icono_consulta = ctk.CTkImage(
        light_image=imagen_consulta,
        dark_image=imagen_consulta,
        size=(24, 24)
    )

    btn_consultar_k = ctk.CTkButton(
        filtrar_k,
        text='Consultar Kardex',
        image=icono_consulta,
        compound='left',
        height=42,
        width=200,
        corner_radius=10,
        font=('Segoe UI', 14),
        text_color=WHITE,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        command=lambda: cargar_kardex()
    )
    btn_consultar_k.grid(
        row=0,
        column=1,
        sticky='ew',
        padx=(0, 8)
    )

    tabla_k = NativeTreeTable(
        t_kardex,
        columns=(
            ('fecha', 'Fecha (México)', 190),
            ('codigo', 'Código', 140),
            ('tipo', 'Movimiento', 100),
            ('cantidad', 'Cantidad', 95),
            ('saldo_anterior', 'Antes', 85),
            ('saldo_nuevo', 'Después', 85),
            ('responsable', 'Responsable', 140),
            ('destinatario', 'Recibe / origen', 150),
            ('referencia', 'Referencia', 130),
            ('motivo', 'Motivo', 240),
        ),
        height=15
    , table_id="almacen_kardex")
    tabla_k.grid(row=1, column=0, sticky='nsew', padx=7, pady=6)

    # Las reimpresiones son sólo de lectura: el servidor recupera la operación
    # ORIGINAL y la capa PDF no ejecuta registrar/salida_ot ni modifica saldos.
    btn_reimprimir_etiqueta = ctk.CTkButton(
        filtrar_k, text='Reimprimir etiqueta', width=182, height=42,
        fg_color=SECONDARY, hover_color=BUTTON_HOVER, state='disabled',
        font=('Segoe UI', 12), command=lambda: reimprimir_kardex('ENTRADA'),
    )
    btn_reimprimir_etiqueta.grid(row=0, column=2, sticky='ew', padx=(0, 8))
    btn_reimprimir_ticket = ctk.CTkButton(
        filtrar_k, text='Reimprimir ticket', width=182, height=42,
        fg_color=SECONDARY, hover_color=BUTTON_HOVER, state='disabled',
        font=('Segoe UI', 12), command=lambda: reimprimir_kardex('SALIDA'),
    )
    btn_reimprimir_ticket.grid(row=0, column=3, sticky='ew')

    reimpresion_ocupada = {'valor': False}

    def actualizar_botones_comprobante(_fila=None):
        seleccionado = tabla_k.selected_payload()
        tipo = str((seleccionado or {}).get('tipo') or '').upper()
        habilitado = not reimpresion_ocupada['valor'] and bool((seleccionado or {}).get('id'))
        btn_reimprimir_etiqueta.configure(state='normal' if habilitado and tipo == 'ENTRADA' else 'disabled')
        btn_reimprimir_ticket.configure(state='normal' if habilitado and tipo == 'SALIDA' else 'disabled')

    tabla_k._on_select = actualizar_botones_comprobante

    def reimprimir_kardex(tipo_esperado):
        registro = tabla_k.selected_payload()
        if not registro or str(registro.get('tipo') or '').upper() != tipo_esperado:
            messagebox.showwarning('Reimpresión', 'Selecciona un movimiento del tipo correspondiente.',
                                   parent=root.winfo_toplevel())
            return
        movimiento_id = str(registro.get('id') or '').strip()
        if not movimiento_id:
            messagebox.showwarning('Reimpresión', 'Este movimiento no tiene identificador de Kárdex.',
                                   parent=root.winfo_toplevel())
            return
        reimpresion_ocupada['valor'] = True
        actualizar_botones_comprobante()
        status.configure(text='Recuperando comprobante original del Kárdex...', text_color=TEXT_SECONDARY)

        def finalizar():
            reimpresion_ocupada['valor'] = False
            actualizar_botones_comprobante()

        def ok(detalle):
            finalizar()
            try:
                if str((detalle or {}).get('tipo') or '').upper() != tipo_esperado:
                    raise ValueError('El tipo de comprobante no coincide con el movimiento seleccionado.')
                ruta = generar_comprobante_historico(detalle)
            except Exception as exc:
                messagebox.showerror('No se pudo generar el comprobante', str(exc),
                                     parent=root.winfo_toplevel())
                return
            status.configure(text=f'Comprobante del Kárdex generado: {ruta.name}', text_color='#15803D')
            try:
                abrir_comprobante(ruta)
            except Exception:
                messagebox.showinfo('Comprobante generado',
                    f'El archivo quedó guardado. Puedes abrirlo manualmente:\n{ruta}',
                    parent=root.winfo_toplevel())

        def error(exc):
            finalizar()
            status.configure(text=f'No se pudo consultar el comprobante: {exc}', text_color='#B91C1C')
            messagebox.showerror('Reimpresión no disponible',
                f'{exc}\n\nVerifica que la Edge Function axia-almacen esté actualizada.\n'
                'No se modificó ningún movimiento ni existencia.',
                parent=root.winfo_toplevel())

        run_async(root.winfo_toplevel(),
                  lambda: servicio.comprobante_kardex(movimiento_id), ok, error)

    kardex_info = ctk.CTkLabel(
        t_kardex,
        text='No se han consultado movimientos.',
        text_color=TEXT_SECONDARY,
        anchor='w'
    )
    kardex_info.grid(row=2, column=0, sticky='ew', padx=8, pady=6)
    navegacion_k=ctk.CTkFrame(t_kardex,fg_color='transparent')
    navegacion_k.grid(row=3,column=0,sticky='e',padx=8,pady=(2,4))
    pagina_k={'valor':1,'ultimo_filtro':None}
    btn_anterior=ctk.CTkButton(navegacion_k,text='Página anterior',width=120,
                               command=lambda:cambiar_pagina_k(-1))
    btn_anterior.pack(side='left',padx=4)
    etiqueta_pagina=ctk.CTkLabel(navegacion_k,text='Página 1')
    etiqueta_pagina.pack(side='left',padx=8)
    btn_siguiente=ctk.CTkButton(navegacion_k,text='Página siguiente',width=120,
                                command=lambda:cambiar_pagina_k(1))
    btn_siguiente.pack(side='left',padx=4)
    btn_anterior.configure(state='disabled')
    btn_siguiente.configure(state='disabled')

    def cambiar_pagina_k(salto):
        pagina_k['valor']=max(1,pagina_k['valor']+salto)
        cargar_kardex()


    status = ctk.CTkLabel(
        root,
        text='Preparando catálogo...',
        text_color=TEXT_SECONDARY,
        anchor='w'
    )
    status.grid(row=1, column=0, sticky='ew', pady=(6, 0))

    registros = []
    pendiente: dict[str, tuple[tuple, str]] = {}

    def ejecutar(tarea, on_success, error_prefix='No fue posible completar la operación'):
        def err(exc):
            status.configure(
                text=f'{error_prefix}: {exc}',
                text_color='#B91C1C'
            )
            messagebox.showerror('AXIA Almacén', str(exc))

        run_async(root.winfo_toplevel(), tarea, on_success, err)

    def producto_seleccionado():
        p = tabla_admin.selected_payload()
        if not p:
            messagebox.showwarning('Almacén', 'Selecciona primero un producto de Altas/Bajas/Modificaciones.')
        return p

    def cambiar_estado_producto(reactivar=False):
        p = producto_seleccionado()
        if not p:
            return
        codigo = str(p['codigo'])
        activo = bool(p.get('activo', True))
        if reactivar and activo:
            messagebox.showinfo('Almacén', 'El producto ya está activo.')
            return
        if not reactivar and not activo:
            messagebox.showinfo('Almacén', 'El producto ya está desactivado.')
            return
        if not reactivar:
            try:
                if float(str(p.get('saldo', 0) or '0')) != 0:
                    messagebox.showwarning('Almacén', 'No puedes quitar un producto con existencia. Registra primero la salida o regularización correspondiente.')
                    return
            except (ValueError, TypeError):
                messagebox.showerror('Almacén', 'No se pudo comprobar el saldo del artículo.')
                return
        texto = ('Reactivar' if reactivar else 'Quitar del catálogo activo')
        if not messagebox.askyesno(
            'Confirmar cambio de catálogo',
            f'{texto}: {codigo}\n{p.get("producto", "")}\n\n'
            'Esta acción no modifica existencias ni borra el Kardex.\n'
            + ('El artículo volverá a estar disponible.' if reactivar
               else 'Se podrá reactivar más adelante desde el catálogo.')
        ):
            return
        op = servicio.reactivar_producto if reactivar else servicio.desactivar_producto
        def ok(_):
            status.configure(text=f'Producto {codigo} actualizado.', text_color='#15803D')
            cargar_catalogo()
        ejecutar(lambda: op(codigo=codigo, usuario=usuario), ok, 'No se pudo actualizar el producto')

    def abrir_editor_producto(editar=False):
        """Ficha completa del Catálogo Maestro (no permite cambiar folio/saldo)."""
        registro = producto_seleccionado() if editar else None
        if editar and not registro:
            return
        if editar and not registro.get('activo', True):
            messagebox.showwarning('Almacén', 'Reactiva el producto antes de editarlo.')
            return

        # Estas equivalencias provienen del catálogo que realmente se consultó.
        # Así no inventamos prefijos y conservamos los oficiales de AXIA.
        familias_por_categoria = {}
        for producto in registros:
            categoria = str(producto.get('categoria_axia') or '').strip()
            familia = str(producto.get('familia_axia') or '').strip()
            if categoria and familia:
                familias_por_categoria.setdefault(categoria, set()).add(familia)
        if not familias_por_categoria and not editar:
            messagebox.showwarning('Catálogo no disponible',
                'Primero consulta el catálogo para elegir una categoría y familia AXIA.')
            return

        ventana = ctk.CTkToplevel(root)
        ventana.title('AXIA Almacén · ' + ('Editar producto' if editar else 'Nuevo producto'))
        ventana.geometry('980x740')
        ventana.minsize(760, 560)
        ventana.transient(root.winfo_toplevel())
        ventana.grid_columnconfigure(0, weight=1)
        ventana.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(ventana, text='Ficha completa del Catálogo Maestro AXIA',
                     font=TITLE_MD, text_color=TEXT_PRIMARY).grid(
                         row=0, column=0, sticky='w', padx=24, pady=(16, 7))
        cuerpo = ctk.CTkScrollableFrame(ventana, fg_color='transparent')
        cuerpo.grid(row=1, column=0, sticky='nsew', padx=12, pady=(0, 4))
        for col in (1, 3):
            cuerpo.grid_columnconfigure(col, weight=1)
        entradas_producto = {}

        def valor_guardado(campo):
            if not registro:
                return ''
            equivalencias = {
                'codigo': 'codigo', 'departamento': 'departamento_origen',
                'costo': 'p_costo', 'venta': 'p_venta', 'minimo': 'inv_minimo',
                'maximo': 'inv_maximo',
            }
            v = registro.get(campo)
            if v is None:
                v = registro.get(equivalencias.get(campo, campo))
            return '' if v is None else str(v)

        def seccion(texto, fila):
            ctk.CTkLabel(cuerpo, text=texto, font=TITLE_MD,
                         text_color=TEXT_PRIMARY, anchor='w').grid(
                row=fila, column=0, columnspan=4, sticky='ew',
                padx=8, pady=(16 if fila else 6, 7))

        def campo_texto(key, label, fila, lado=0, *, editable=True, default=''):
            col = 0 if lado == 0 else 2
            ctk.CTkLabel(cuerpo, text=label, anchor='w', text_color=TEXT_PRIMARY
                         ).grid(row=fila, column=col, sticky='w', padx=(10, 8), pady=7)
            widget = AxiaEntry(cuerpo, height=34)
            widget.grid(row=fila, column=col+1, sticky='ew', padx=(0, 14), pady=7)
            value = valor_guardado(key) if editar else default
            if value:
                widget.insert(0, value)
            if not editable:
                widget.configure(state='disabled')
            else:
                entradas_producto[key] = widget
            return widget

        seccion('Identificación y clasificación', 0)
        codigo_widget = campo_texto('codigo', 'Código AXIA', 1, editable=False,
                            default='Se asignará automáticamente al guardar')
        campo_texto('producto', 'Producto *', 1, lado=1)
        categorias = sorted(familias_por_categoria)
        categorias_iniciales = categorias or [valor_guardado('categoria_axia')]
        if editar and valor_guardado('categoria_axia') not in categorias_iniciales:
            categorias_iniciales.append(valor_guardado('categoria_axia'))
        categoria_inicial = valor_guardado('categoria_axia') if editar else categorias_iniciales[0]
        ctk.CTkLabel(cuerpo,text='Categoría AXIA *',anchor='w',text_color=TEXT_PRIMARY
                     ).grid(row=2,column=0,sticky='w',padx=(10,8),pady=7)
        selector_categoria = ctk.CTkOptionMenu(cuerpo, values=categorias_iniciales,
            height=34, fg_color='#31597B', button_color=SECONDARY,
            text_color=WHITE)
        selector_categoria.grid(row=2,column=1,sticky='ew',padx=(0,14),pady=7)
        familias_iniciales = sorted(familias_por_categoria.get(categoria_inicial, []))
        if editar and valor_guardado('familia_axia') not in familias_iniciales:
            familias_iniciales.append(valor_guardado('familia_axia'))
        if not familias_iniciales:
            familias_iniciales = ['Sin familia']
        ctk.CTkLabel(cuerpo,text='Familia AXIA *',anchor='w',text_color=TEXT_PRIMARY
                     ).grid(row=2,column=2,sticky='w',padx=(10,8),pady=7)
        selector_familia = ctk.CTkOptionMenu(cuerpo, values=familias_iniciales,
            height=34, fg_color='#31597B', button_color=SECONDARY,
            text_color=WHITE)
        selector_familia.grid(row=2,column=3,sticky='ew',padx=(0,14),pady=7)
        if categoria_inicial:
            selector_categoria.set(categoria_inicial)
        selector_familia.set(valor_guardado('familia_axia') if editar else familias_iniciales[0])
        def actualizar_familias(categoria):
            opciones = sorted(familias_por_categoria.get(categoria, [])) or ['Sin familia']
            selector_familia.configure(values=opciones)
            selector_familia.set(opciones[0])
        selector_categoria.configure(command=actualizar_familias)

        campo_texto('departamento', 'Departamento original', 3)
        campo_texto('unidad_inventario', 'Unidad de inventario', 3, lado=1)
        seccion('Proveedor y referencias comerciales', 4)
        campo_texto('proveedor', 'Proveedor', 5)
        campo_texto('codigo_proveedor', 'Código proveedor', 5, lado=1)
        campo_texto('costo', 'Precio de costo', 6, default='0')
        campo_texto('venta', 'Precio de venta', 6, lado=1, default='0')
        campo_texto('p_mayoreo', 'Precio mayoreo', 7, default='0')
        campo_texto('minimo', 'Inventario mínimo', 7, lado=1, default='0')
        campo_texto('maximo', 'Inventario máximo', 8, default='0')
        seccion('Información de clasificación', 9)
        campo_texto('seguimiento_sugerido', 'Seguimiento sugerido', 10)
        campo_texto('estado_clasificacion', 'Estado de clasificación', 10, lado=1,
                    default='Validado')
        campo_texto('posible_equivalencia', 'Posible equivalencia', 11)
        seccion('Datos históricos de consulta · solo lectura', 12)
        campo_texto('codigo_origen_eleventa', 'Código origen ELEVENTA', 13,
                    editable=False)
        campo_texto('fila_origen_eleventa', 'Fila original ELEVENTA', 13, lado=1,
                    editable=False)
        campo_texto('existencia_eleventa', 'Existencia ELEVENTA original', 14,
                    editable=False)
        campo_texto('saldo', 'Saldo actual en Supabase', 14, lado=1,
                    editable=False, default='0')
        campo_texto('saldo_inicial_origen', 'Origen del saldo inicial', 15,
                    editable=False)
        campo_texto('estatus', 'Estatus del catálogo', 15, lado=1,
                    editable=False, default='Activo')
        ctk.CTkLabel(cuerpo, text='El Código AXIA se asigna al crear el producto y no se modifica. '
            'Los saldos únicamente cambian mediante Entradas y Salidas. '
            'Los datos históricos de ELEVENTA se conservan.',
            wraplength=850, text_color=TEXT_SECONDARY, justify='left', anchor='w').grid(
                row=16, column=0, columnspan=4, sticky='ew', padx=10, pady=(12, 14))

        solicitud_alta_id = str(uuid.uuid4())  # Mismo ID para reintentos de esta alta.
        controles = ctk.CTkFrame(ventana, fg_color='transparent')
        controles.grid(row=2, column=0, sticky='e', padx=22, pady=(8, 16))
        ctk.CTkButton(controles,text='Cancelar',width=110,fg_color='#64748B',
            command=ventana.destroy).pack(side='left',padx=(0,10))

        def guardar_producto():
            datos = {k: w.get().strip() for k, w in entradas_producto.items()}
            datos['categoria_axia'] = selector_categoria.get().strip()
            datos['familia_axia'] = selector_familia.get().strip()
            try:
                from services.almacen_service import validar_producto_maestro
                validos = validar_producto_maestro(datos,
                    codigo=str(registro['codigo']) if editar else None)
                if not editar:
                    validos['solicitud_id'] = solicitud_alta_id
            except ValueError as exc:
                messagebox.showwarning('Revisa el producto',str(exc),parent=ventana)
                return
            ref = (str(registro['codigo']) if editar else 'Código AXIA automático')
            if not messagebox.askyesno('Confirmar',
                ('Guardar cambios de' if editar else 'Registrar') +
                f'\n{ref} · {validos["producto"]}?', parent=ventana):
                return
            btn_guardar.configure(state='disabled')
            operacion = servicio.editar_producto if editar else servicio.crear_producto
            args = {'datos': validos, 'usuario': usuario}
            if editar:
                args['codigo'] = str(registro['codigo'])
            def ok(resultado):
                codigo_final = (resultado or {}).get('codigo', ref) if isinstance(resultado, dict) else ref
                if ventana.winfo_exists():
                    ventana.destroy()
                status.configure(text=f'Producto {codigo_final} guardado correctamente.',
                                 text_color='#15803D')
                cargar_catalogo()
            def err(exc):
                if ventana.winfo_exists():
                    btn_guardar.configure(state='normal')
                messagebox.showerror('No se guardó el producto',str(exc),parent=ventana)
            run_async(root.winfo_toplevel(), lambda:operacion(**args), ok, err)

        btn_guardar = ctk.CTkButton(controles, text='Guardar producto', width=160,
                                    command=guardar_producto)
        btn_guardar.pack(side='left')
        ventana.after(70,lambda:ventana.grab_set() if ventana.winfo_exists() else None)

    def inicializar():
        if not servicio.remoto:
            cargar_catalogo()
            return

        password = simpledialog.askstring(
            'AXIA Almacén · Autenticación adicional',
            'Confirma tu contraseña AXIA para consultar Almacén seguro.\n'
            'La autorización dura 15 minutos y no se guarda en el equipo.',
            parent=root.winfo_toplevel(),
            show='*'
        )

        if not password:
            status.configure(
                text='Sesión de Almacén no iniciada. No se muestran datos de Supabase.'
            )
            return

        nickname = str(usuario.get('usuario') or '')
        status.configure(text='Validando acceso en el servidor...')

        def ok(_):
            status.configure(
                text='Sesión segura validada.',
                text_color='#15803D'
            )
            # El catálogo maestro alimenta todas las operaciones.
            cargar_catalogo()

        ejecutar(
            lambda: servicio.iniciar_sesion(
                nickname,
                password,
                usuario['id_usuario']
            ),
            ok,
            'Autenticación rechazada'
        )

    def es_vista_maestro():
        return origen.get() == 'Maestro AXIA (piloto)' and vista_maestro_habilitada

    def cambiar_fuente_catalogo(opcion):
        if opcion == 'Maestro AXIA (piloto)' and not vista_maestro_habilitada:
            origen.set('Operativo')
            messagebox.showinfo('Catálogo Maestro',
                'El catálogo de Supabase solo está disponible en modo remoto_pruebas '
                'con una sesión segura de Almacén. En simulador se muestra el catálogo operativo local.')
            return
        tabla.set_columns(COLUMNAS_TABLA if es_vista_maestro() else COLUMNAS_OPERATIVAS)
        if es_vista_maestro():
            ayuda.configure(text='Catálogo Maestro AXIA: SOLO CONSULTA. Existencia ELEVENTA histórica; '
                                 'no se usa para Entradas, Salidas ni Kárdex.')
            paginacion_maestro.grid()
            if not maestro['cargado']:
                cargar_catalogo_maestro(pagina=1)
            else:
                representar_maestro()
        else:
            ayuda.configure(text='Catálogo operativo: selecciona un producto para preparar entradas o salidas.')
            paginacion_maestro.grid_remove()
            mostrar_registros()

    def refrescar_catalogo_visible():
        if es_vista_maestro():
            cargar_catalogo_maestro(pagina=maestro['pagina'])
        else:
            cargar_catalogo()

    def buscar_en_catalogo():
        if es_vista_maestro():
            maestro['busqueda'] = buscar.get().strip()
            cargar_catalogo_maestro(pagina=1)
        else:
            mostrar_registros()

    def representar_maestro():
        if not es_vista_maestro():
            return
        tabla.set_rows(maestro['items'])
        total = maestro['total']
        pagina = maestro['pagina']
        limite = maestro['limite']
        contador.configure(text=f'{total:,} resultados')
        ultima = max(1, (total + limite - 1) // limite)
        etiqueta_pagina_maestro.configure(text=f'Página {pagina} de {ultima}')
        btn_maestro_anterior.configure(state='normal' if pagina > 1 else 'disabled')
        btn_maestro_siguiente.configure(state='normal' if pagina < ultima else 'disabled')

    def cargar_catalogo_maestro(*, pagina=1):
        if not vista_maestro_habilitada:
            return
        maestro['solicitud'] += 1
        solicitud = maestro['solicitud']
        filtro = maestro['busqueda']
        status.configure(text='Consultando Catálogo Maestro piloto en Supabase...',
                         text_color=TEXT_SECONDARY)
        btn_maestro_anterior.configure(state='disabled')
        btn_maestro_siguiente.configure(state='disabled')

        def ok(resultado):
            if solicitud != maestro['solicitud']:
                return
            maestro['items'] = list(resultado.get('items') or [])
            maestro['total'] = int(resultado.get('total') or 0)
            maestro['pagina'] = int(resultado.get('pagina') or pagina)
            maestro['cargado'] = True
            representar_maestro()
            status.configure(text=f'Catálogo Maestro: {maestro["total"]:,} artículos. '
                             'Solo consulta; sin movimientos de inventario.',
                             text_color='#15803D')

        ejecutar(lambda: servicio.catalogo_maestro_piloto(
            pagina=pagina, limite=maestro['limite'], busqueda=filtro), ok,
            'No fue posible consultar el catálogo maestro')

    def cambiar_pagina_maestro(salto):
        max_pagina = max(1, (maestro['total'] + maestro['limite'] - 1)//maestro['limite'])
        pagina = min(max_pagina, max(1, maestro['pagina'] + salto))
        if pagina != maestro['pagina']:
            cargar_catalogo_maestro(pagina=pagina)

    def mostrar_registros(*_):
        def tabla_data(rows):
            return [{**r,'estado':'Activo' if r.get('activo',True) else 'Inactivo',
                     'costo':_moneda(r.get('costo')),
                     'saldo_exportado':r.get('saldo_exportado','—')} for r in rows]
        # Los datos operativos alimentan SOLO las transacciones operativas.
        criterio_admin=buscar_admin.get().strip().casefold()
        admin_visible=[r for r in registros if (var_inactivos.get() or r.get('activo',True))
                       and (not criterio_admin or any(criterio_admin in str(r.get(campo,'')).casefold()
                           for campo in ('codigo','producto','departamento','categoria_axia','familia_axia','codigo_origen_eleventa','proveedor')))]
        tabla_admin.set_rows(tabla_data(admin_visible))
        if es_vista_maestro():
            representar_maestro()
            return
        criterio = buscar.get().strip().casefold()
        consulta = [r for r in registros if r.get('activo',True) and
                    (not criterio or any(criterio in str(r.get(campo,'')).casefold()
                       for campo in ('codigo','producto','departamento','categoria_axia','familia_axia','codigo_origen_eleventa','proveedor')))]
        tabla.set_rows(tabla_data(consulta))
        contador.configure(text=f'{len(consulta):,} productos')

    def cargar_catalogo():
        status.configure(text='Consultando Catálogo Maestro AXIA en Supabase...', text_color=TEXT_SECONDARY)

        def ok(items):
            nonlocal registros
            registros = list(items or [])
            mostrar_registros()
            if es_vista_maestro():
                if not maestro['cargado'] and not maestro['solicitud']:
                    cargar_catalogo_maestro(pagina=1)
            elif servicio.remoto and not registros:
                status.configure(text='Catálogo operativo vacío. No se autorizaron existencias.',
                                 text_color='#A65E09')
            else:
                status.configure(text=f'Catálogo Maestro conectado: {len(registros):,} productos.',
                                 text_color='#15803D')

        ejecutar(lambda: servicio.catalogo(incluir_inactivos=True), ok,
                 'No se pudo consultar el Catálogo Maestro AXIA')

    def seleccionar(registro):
        # Mantener las acciones existentes al seleccionar una fila de Catálogo.
        # La ficha inferior ya no se muestra para aprovechar el espacio de la tabla.
        if es_vista_maestro():
            return
        codigo = str(registro.get('codigo') or '')
        for formulario, _ in entradas.values():
            campo = formulario['codigo']
            campo.delete(0, 'end')
            if registro.get('activo', True):
                campo.insert(0, codigo)

        buscar_k.delete(0, 'end')
        buscar_k.insert(0, codigo)
        campo_ot_codigo.delete(0, 'end')
        if registro.get('activo', True):
            campo_ot_codigo.insert(0, codigo)

    tabla._on_select = seleccionar
    def seleccionar_admin(registro):
        seleccionado_admin_txt.configure(text=f'Seleccionado: {registro.get("codigo", "")} · '
                                    f'{str(registro.get("producto") or "")[:100]}')
    tabla_admin._on_select = seleccionar_admin
    buscar.bind('<Return>', lambda _event: buscar_en_catalogo())
    buscar.bind('<KeyRelease>', lambda event: mostrar_registros() if not es_vista_maestro() else None)
    buscar_admin.bind('<KeyRelease>', mostrar_registros)

    def guardar(tipo):
        campos, boton = entradas[tipo]
        payload = {
            key: entry.get().strip()
            for key, entry in campos.items()
        }

        codigo = payload['codigo']
        producto = next(
            (r for r in registros if str(r.get('codigo')) == codigo),
            None
        )

        if not producto or not producto.get('activo', True):
            messagebox.showwarning(
                'Producto no localizado',
                'El código debe coincidir con un producto del catálogo.'
            )
            return

        try:
            from services.almacen_service import cantidad_valida

            cantidad = cantidad_valida(payload['cantidad'])

            if not payload['motivo']:
                raise ValueError('Escribe el motivo del movimiento.')

            if tipo == 'SALIDA' and not payload['destinatario']:
                raise ValueError('Indica quién recibe la salida.')
            if tipo == 'ENTRADA' and not payload['destinatario']:
                raise ValueError('Indica el proveedor o el origen de la mercancía recibida.')

        except ValueError as exc:
            messagebox.showwarning('Datos incompletos', str(exc))
            return

        confirmacion = (
            f'{tipo} DE ALMACÉN\n\n'
            f'Producto: {codigo} · {producto.get("producto", "")}\n'
            f'Cantidad: {formatear_cantidad(cantidad)}\n'
            f'Motivo: {payload["motivo"]}\n'
            f'Referencia: {payload["referencia"] or "—"}\n'
            f'Recibe / origen: {payload["destinatario"] or "—"}\n\n'
            + (
                'SIMULADOR LOCAL: sin persistencia.'
                if not servicio.remoto
                else (
                    'LABORATORIO: persistirá solo en las tablas de PRUEBAS.'
                    if servicio.laboratorio
                    else 'MOVIMIENTO REAL: el servidor validará permisos y existencias.'
                )
            )
        )

        if not messagebox.askyesno('Confirmar movimiento', confirmacion):
            return

        firma = (
            codigo,
            tipo,
            str(cantidad),
            payload['motivo'],
            payload['referencia'],
            payload['destinatario']
        )

        if tipo not in pendiente or pendiente[tipo][0] != firma:
            pendiente[tipo] = (firma, str(uuid.uuid4()))

        idem = pendiente[tipo][1]
        boton.configure(state='disabled')
        status.configure(
            text=f'Registrando {tipo.lower()}...',
            text_color=TEXT_SECONDARY
        )

        def ok(mov):
            pendiente.pop(tipo, None)
            boton.configure(state='normal')
            status.configure(
                text=f'{tipo} registrada. Saldo posterior: {mov.get("saldo_nuevo")}',
                text_color='#15803D'
            )

            prefijo = (
                'Movimiento registrado en el Catálogo Maestro AXIA (Supabase).'
                if servicio.remoto and not servicio.laboratorio else
                'Movimiento registrado en el Almacén.'
            )
            resumen = (f'{prefijo}\nCódigo: {codigo}\n'
                       f'Cantidad: {formatear_cantidad(cantidad)}\n'
                       f'Saldo resultante: {mov.get("saldo_nuevo")}')
            if tipo == 'ENTRADA':
                ofrecer_comprobante(
                    tipo='ENTRADA', resumen=resumen, codigo=codigo,
                    producto=str(producto.get('producto') or ''), cantidad=cantidad,
                    referencia=payload['referencia'],
                    identificador=mov.get('id') or idem,
                    fecha=mov.get('fecha'),
                )
            else:
                ofrecer_comprobante(
                    tipo='SALIDA', resumen=resumen,
                    movimientos=[{'codigo': codigo, 'producto': str(producto.get('producto') or ''),
                                   'cantidad': cantidad}],
                    destinatario=payload['destinatario'], motivo=payload['motivo'],
                    referencia=payload['referencia'],
                    responsable=str(usuario.get('usu_nombre') or usuario.get('nombre') or usuario.get('usuario') or ''),
                    identificador=mov.get('id') or idem, fecha=mov.get('fecha'),
                )

            cargar_catalogo()
            buscar_k.delete(0, 'end')
            buscar_k.insert(0, codigo)
            cargar_kardex()

        def error(exc):
            boton.configure(state='normal')
            status.configure(
                text='No se confirmó el resultado: revisa el Kardex antes de repetir.',
                text_color='#B91C1C'
            )
            messagebox.showerror(
                'No se confirmó el movimiento',
                f'{exc}\n\nPor seguridad, si repites sin modificar los campos '
                'se enviará el mismo ID de operación, evitando un cargo duplicado.'
            )

        run_async(
            root.winfo_toplevel(),
            lambda: servicio.registrar(
                codigo=codigo,
                tipo=tipo,
                cantidad=str(cantidad),
                motivo=payload['motivo'],
                referencia=payload['referencia'],
                destinatario=payload['destinatario'],
                usuario=usuario,
                idempotencia=idem
            ),
            ok,
            error
        )

    def cargar_kardex():
        codigo = buscar_k.get().strip() or None
        if codigo != pagina_k['ultimo_filtro']:
            pagina_k['valor']=1
            pagina_k['ultimo_filtro']=codigo
        pagina=pagina_k['valor']
        kardex_info.configure(text='Consultando Kárdex...')
        actualizar_botones_comprobante()
        btn_anterior.configure(state='disabled')
        btn_siguiente.configure(state='disabled')

        def ok(items):
            rows = list(items or [])
            tabla_k.set_rows([{
                    **m,
                    'fecha': fecha_kardex_mexico(m.get('fecha')),
                    'cantidad': str(m.get('cantidad') or ''),
                    'saldo_anterior': str(m.get('saldo_anterior') or ''),
                    'saldo_nuevo': str(m.get('saldo_nuevo') or ''),
                } for m in rows])
            actualizar_botones_comprobante()
            kardex_info.configure(text=f'{len(rows)} movimientos · '                  + (f'Filtro {codigo}' if codigo else 'todos los artículos'))
            etiqueta_pagina.configure(text=f'Página {pagina}')
            btn_anterior.configure(state='normal' if pagina > 1 else 'disabled')
            btn_siguiente.configure(state='normal' if len(rows)==200 else 'disabled')
            tabs.set('Kárdex / Historial')

        ejecutar(
            lambda: servicio.kardex(codigo,pagina=pagina,limite=200),
            ok,
            'No se pudo consultar Kárdex'
        )

    origen.set(fuente_inicial)
    ayuda.configure(text='CATÁLOGO ÚNICO AXIA · Saldo disponible en Supabase. '
                          'ELEVENTA es únicamente el saldo original importado.')
    if vista_maestro_habilitada:
        tabla.set_columns(COLUMNAS_TABLA)
        ayuda.configure(text='Catálogo Maestro AXIA: SOLO CONSULTA. Existencia ELEVENTA histórica; '
                             'no se usa para Entradas, Salidas ni Kárdex.')
        paginacion_maestro.grid()
    root.after(30, inicializar)
