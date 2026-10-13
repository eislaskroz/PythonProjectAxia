"""AXIA Almacén · Etapa 3: catálogo, entradas, salidas y Kardex.

Por defecto es un simulador EFÍMERO. Para conectar con Supabase se requiere:
  - SQL de migración y Edge Function desplegados;
  - AXIA_ALMACEN_MODO=remoto;
  - autenticación del propio usuario, verificada por la Edge Function;
  - autorización posterior del catálogo y existencias de apertura.
"""
from __future__ import annotations

import uuid
from tkinter import messagebox, simpledialog
import customtkinter as ctk

from app_context import obtener_usuario_actual
from core.background_tasks import run_async
from security.permissions import puede_ver_almacen
from services.almacen_service import crear_almacen, formatear_cantidad
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY, BUTTON_HOVER
from ui.fonts import TITLE_MD, TEXT_MD, BUTTON_FONT
from ui.native_table import NativeTreeTable


def _moneda(value):
    try:
        return f"${float(str(value or 0).replace('$', '').replace(',', '')):,.2f}"
    except (ValueError, TypeError):
        return '—'


def mostrar_almacen(parent, app=None):
    usuario = dict(obtener_usuario_actual() or {})
    if not puede_ver_almacen(usuario) or not usuario.get('id_usuario'):
        messagebox.showerror('Acceso denegado', 'Se requiere una sesión activa de Administrador o Almacén.')
        return
    try:
        servicio = crear_almacen()
    except Exception as exc:
        messagebox.showerror('Almacén', str(exc))
        return

    root = ctk.CTkFrame(parent, fg_color='transparent')
    root.pack(fill='both', expand=True, padx=14, pady=(4, 12))
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)

    cab = ctk.CTkFrame(root, fg_color=WHITE, corner_radius=14)
    cab.grid(row=0, column=0, sticky='ew', pady=(0, 8))
    cab.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(cab, text='AXIA ALMACÉN · Entradas, salidas y Kardex · Etapa 3', font=TITLE_MD,
                 text_color=TEXT_PRIMARY, anchor='w').grid(row=0, column=0, sticky='ew', padx=14, pady=(10, 3))
    if not servicio.remoto:
        banner = ('SIMULADOR LOCAL: saldos en cero; se pierden al cerrar esta pantalla. '
                  'No modifica Supabase ni las existencias de ELEVENTA.')
    elif servicio.laboratorio:
        banner = ('LABORATORIO SUPABASE: movimientos de PRUEBA guardados entre sesiones. '
                  'Saldos iniciales en cero y tablas SEPARADAS. No afecta inventario real.')
    else:
        banner = ('INVENTARIO REAL: movimiento BLOQUEADO hasta contar con autorizacion '
                  'formal de Almacen, corte fisico y activacion segura.')
    ctk.CTkLabel(cab, text=banner, font=TEXT_MD, text_color='#A65E09',
                 wraplength=1150, justify='left', anchor='w').grid(row=1, column=0, sticky='ew', padx=14, pady=(0, 9))

    tabs = ctk.CTkTabview(
        root, fg_color=WHITE, segmented_button_fg_color='#E2E8F0',
        segmented_button_selected_color='#BFDBFE',
        segmented_button_selected_hover_color='#93C5FD',
        segmented_button_unselected_color='#E2E8F0',
        segmented_button_unselected_hover_color='#CBD5E1',
        text_color='#111827')
    tabs.grid(row=1, column=0, sticky='nsew')
    t_catalogo = tabs.add('Catálogo')
    t_entrada = tabs.add('Entrada')
    t_salida = tabs.add('Salida')
    t_kardex = tabs.add('Kardex')

    # -------- CATÁLOGO --------
    t_catalogo.grid_columnconfigure(0, weight=1)
    t_catalogo.grid_rowconfigure(2, weight=1)
    barra = ctk.CTkFrame(t_catalogo, fg_color='transparent')
    barra.grid(row=0, column=0, sticky='ew', padx=7, pady=6)
    barra.grid_columnconfigure(0, weight=1)
    buscar = ctk.CTkEntry(barra, placeholder_text='Buscar por código, nombre o departamento...', height=34)
    buscar.grid(row=0, column=0, sticky='ew', padx=(0, 8))
    contador = ctk.CTkLabel(barra, text='Cargando...', text_color=TEXT_SECONDARY)
    contador.grid(row=0, column=1, padx=8)
    ctk.CTkButton(barra, text='Actualizar', width=105, command=lambda: cargar_catalogo()).grid(row=0, column=2)
    ayuda = ctk.CTkLabel(t_catalogo, text='Selecciona un producto para cargar su código en Entrada y Salida. '
             'El saldo operativo es independiente de la existencia exportada.',
             text_color=TEXT_SECONDARY, anchor='w')
    ayuda.grid(row=1, column=0, sticky='ew', padx=8, pady=(0, 4))
    tabla = NativeTreeTable(t_catalogo, columns=(
        ('codigo', 'Código', 150), ('producto', 'Producto', 320),
        ('departamento', 'Departamento', 150), ('saldo', 'Saldo actual', 110),
        ('saldo_exportado', 'Eleventa (histórico)', 145), ('costo', 'P. costo', 110),
        ('minimo', 'Mínimo', 90), ('maximo', 'Máximo', 90),
    ), height=17)
    tabla.grid(row=2, column=0, sticky='nsew', padx=7, pady=5)
    seleccionado_txt = ctk.CTkLabel(t_catalogo, text='Selecciona una fila de la tabla.',
                                    text_color=TEXT_SECONDARY, anchor='w')
    seleccionado_txt.grid(row=3, column=0, sticky='ew', padx=8, pady=(2, 7))

    # -------- FORMULARIOS DE MOVIMIENTO --------
    entradas = {}
    def construir_form(tab, tipo):
        tab.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(tab, text=f'Registrar {tipo.lower()} de material', font=TITLE_MD,
                     text_color=TEXT_PRIMARY).grid(row=0, column=0, columnspan=2, sticky='w', padx=14, pady=(14, 10))
        definiciones = [
            ('codigo', 'Código de producto *'),
            ('cantidad', 'Cantidad * (hasta 3 decimales)'),
            ('motivo', 'Motivo / descripción *'),
            ('referencia', 'Referencia / folio / OT (opcional)'),
        ]
        if tipo == 'SALIDA':
            definiciones.append(('destinatario', 'Recibe el material *'))
        else:
            definiciones.append(('destinatario', 'Origen / proveedor (opcional)'))
        campos = {}
        for index, (key, label) in enumerate(definiciones, start=1):
            ctk.CTkLabel(tab, text=label, text_color=TEXT_PRIMARY, anchor='w').grid(
                row=index, column=0, sticky='w', padx=(15, 8), pady=7)
            entry = ctk.CTkEntry(tab, height=35)
            entry.grid(row=index, column=1, sticky='ew', padx=(4, 15), pady=7)
            campos[key] = entry
        btn = ctk.CTkButton(tab, text=f'Confirmar {tipo.lower()}', font=BUTTON_FONT,
                            fg_color=SECONDARY, hover_color=BUTTON_HOVER, height=38,
                            command=lambda: guardar(tipo))
        btn.grid(row=6, column=1, sticky='e', padx=(4, 15), pady=(18, 8))
        nota = ('Las salidas nunca permiten un saldo negativo. '
                if tipo == 'SALIDA' else 'La cantidad se sumará al saldo del producto. ')
        ctk.CTkLabel(tab, text=nota + 'Se confirma el movimiento antes de registrarlo.',
                     text_color=TEXT_SECONDARY, anchor='w').grid(row=7, column=0, columnspan=2,
                         sticky='ew', padx=14, pady=4)
        entradas[tipo] = (campos, btn)
    construir_form(t_entrada, 'ENTRADA')
    construir_form(t_salida, 'SALIDA')

    # -------- KARDEX --------
    t_kardex.grid_columnconfigure(0, weight=1)
    t_kardex.grid_rowconfigure(1, weight=1)
    filtrar_k = ctk.CTkFrame(t_kardex, fg_color='transparent')
    filtrar_k.grid(row=0, column=0, sticky='ew', padx=8, pady=8)
    filtrar_k.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(filtrar_k, text='Código (vacío: últimos 200):').grid(row=0, column=0, padx=(0, 8))
    buscar_k = ctk.CTkEntry(filtrar_k, height=33)
    buscar_k.grid(row=0, column=1, sticky='ew', padx=(0, 10))
    ctk.CTkButton(filtrar_k, text='Consultar Kardex', width=160,
                  command=lambda: cargar_kardex()).grid(row=0, column=2)
    tabla_k = NativeTreeTable(t_kardex, columns=(
        ('fecha', 'Fecha', 165), ('codigo', 'Código', 140),
        ('tipo', 'Movimiento', 100), ('cantidad', 'Cantidad', 95),
        ('saldo_anterior', 'Antes', 85), ('saldo_nuevo', 'Después', 85),
        ('responsable', 'Responsable', 140), ('destinatario', 'Recibe / origen', 150),
        ('referencia', 'Referencia', 130), ('motivo', 'Motivo', 240),
    ), height=15)
    tabla_k.grid(row=1, column=0, sticky='nsew', padx=7, pady=6)
    kardex_info = ctk.CTkLabel(t_kardex, text='No se han consultado movimientos.',
                               text_color=TEXT_SECONDARY, anchor='w')
    kardex_info.grid(row=2, column=0, sticky='ew', padx=8, pady=6)
    status = ctk.CTkLabel(root, text='Preparando catálogo...', text_color=TEXT_SECONDARY, anchor='w')
    status.grid(row=2, column=0, sticky='ew', pady=(6, 0))

    registros = []
    pendiente: dict[str, tuple[tuple, str]] = {}

    def ejecutar(tarea, on_success, error_prefix='No fue posible completar la operación'):
        def err(exc):
            status.configure(text=f'{error_prefix}: {exc}', text_color='#B91C1C')
            messagebox.showerror('AXIA Almacén', str(exc))
        run_async(root.winfo_toplevel(), tarea, on_success, err)

    def inicializar():
        if not servicio.remoto:
            cargar_catalogo()
            return
        password = simpledialog.askstring(
            'AXIA Almacén · Autenticación adicional',
            'Confirma tu contraseña AXIA para consultar Almacén seguro.\n'
            'La autorización dura 15 minutos y no se guarda en el equipo.',
            parent=root.winfo_toplevel(), show='*')
        if not password:
            status.configure(text='Sesión de Almacén no iniciada. No se muestran datos de Supabase.')
            return
        nickname = str(usuario.get('usuario') or '')
        status.configure(text='Validando acceso en el servidor...')
        def ok(_):
            status.configure(text='Sesión segura validada.', text_color='#15803D')
            cargar_catalogo()
        ejecutar(lambda: servicio.iniciar_sesion(nickname, password, usuario['id_usuario']), ok,
                 'Autenticación rechazada')

    def mostrar_registros(*_):
        criterio = buscar.get().strip().casefold()
        visible = [r for r in registros if not criterio or any(
            criterio in str(r.get(campo, '')).casefold() for campo in ('codigo','producto','departamento'))]
        tabla.set_rows([{**r, 'costo': _moneda(r.get('costo')),
                         'saldo_exportado': r.get('saldo_exportado', '—')} for r in visible])
        contador.configure(text=f'{len(visible):,} / {len(registros):,} productos')

    def cargar_catalogo():
        status.configure(text='Consultando catálogo...', text_color=TEXT_SECONDARY)
        def ok(items):
            nonlocal registros
            registros = list(items or [])
            mostrar_registros()
            if servicio.remoto and not registros:
                status.configure(text='Catálogo de Supabase vacío: pendiente de importación autorizada.', text_color='#A65E09')
            else:
                status.configure(text=f'Catálogo consultado: {len(registros):,} productos.', text_color='#15803D')
        ejecutar(servicio.catalogo, ok, 'No se pudo consultar el catálogo')

    def seleccionar(registro):
        codigo = str(registro.get('codigo') or '')
        for formulario, _ in entradas.values():
            campo = formulario['codigo']
            campo.delete(0, 'end')
            campo.insert(0, codigo)
        buscar_k.delete(0, 'end')
        buscar_k.insert(0, codigo)
        seleccionado_txt.configure(text=f'Seleccionado: {codigo} · {str(registro.get("producto") or "")[:100]}')

    tabla._on_select = seleccionar
    buscar.bind('<KeyRelease>', mostrar_registros)

    def guardar(tipo):
        campos, boton = entradas[tipo]
        payload = {key: entry.get().strip() for key, entry in campos.items()}
        codigo = payload['codigo']
        producto = next((r for r in registros if str(r.get('codigo')) == codigo), None)
        if not producto:
            messagebox.showwarning('Producto no localizado', 'El código debe coincidir con un producto del catálogo.')
            return
        try:
            from services.almacen_service import cantidad_valida
            cantidad = cantidad_valida(payload['cantidad'])
            if not payload['motivo']:
                raise ValueError('Escribe el motivo del movimiento.')
            if tipo == 'SALIDA' and not payload['destinatario']:
                raise ValueError('Indica quién recibe la salida.')
        except ValueError as exc:
            messagebox.showwarning('Datos incompletos', str(exc))
            return
        confirmacion = (f'{tipo} DE ALMACÉN\n\nProducto: {codigo} · {producto.get("producto", "")}\n'
                        f'Cantidad: {formatear_cantidad(cantidad)}\n'
                        f'Motivo: {payload["motivo"]}\nReferencia: {payload["referencia"] or "—"}\n'
                        f'Recibe / origen: {payload["destinatario"] or "—"}\n\n'
                        + ('SIMULADOR LOCAL: sin persistencia.' if not servicio.remoto
                           else ('LABORATORIO: persistirá solo en las tablas de PRUEBAS.'
                                 if servicio.laboratorio else 'MOVIMIENTO REAL: el servidor validará permisos y existencias.')))
        if not messagebox.askyesno('Confirmar movimiento', confirmacion):
            return
        firma = (codigo, tipo, str(cantidad), payload['motivo'],
                 payload['referencia'], payload['destinatario'])
        if tipo not in pendiente or pendiente[tipo][0] != firma:
            pendiente[tipo] = (firma, str(uuid.uuid4()))
        idem = pendiente[tipo][1]
        boton.configure(state='disabled')
        status.configure(text=f'Registrando {tipo.lower()}...', text_color=TEXT_SECONDARY)
        def ok(mov):
            pendiente.pop(tipo, None)
            boton.configure(state='normal')
            status.configure(text=f'{tipo} registrada. Saldo posterior: {mov.get("saldo_nuevo")}', text_color='#15803D')
            messagebox.showinfo('Movimiento registrado',
                ('Movimiento de PRUEBA registrado en memoria.\nNo se modificó ELEVENTA ni Supabase.\n\n'
                 if not servicio.remoto else ('Movimiento de laboratorio registrado en Supabase.\nNo afecta el inventario real.\n\n'
                 if servicio.laboratorio else 'Movimiento registrado en el inventario real de Supabase.\n\n'))
                + f'Código: {codigo}\nCantidad: {formatear_cantidad(cantidad)}\n'
                  f'Saldo resultante: {mov.get("saldo_nuevo")}')
            cargar_catalogo()
            buscar_k.delete(0, 'end')
            buscar_k.insert(0, codigo)
            cargar_kardex()
        def error(exc):
            boton.configure(state='normal')
            status.configure(text='No se confirmó el resultado: revisa el Kardex antes de repetir.', text_color='#B91C1C')
            messagebox.showerror('No se confirmó el movimiento',
                f'{exc}\n\nPor seguridad, si repites sin modificar los campos se enviará el mismo ID de operación, evitando un cargo duplicado.')
        run_async(root.winfo_toplevel(), lambda: servicio.registrar(
            codigo=codigo, tipo=tipo, cantidad=str(cantidad), motivo=payload['motivo'],
            referencia=payload['referencia'], destinatario=payload['destinatario'],
            usuario=usuario, idempotencia=idem), ok, error)

    def cargar_kardex():
        codigo = buscar_k.get().strip() or None
        kardex_info.configure(text='Consultando Kardex...')
        def ok(items):
            rows = list(items or [])
            tabla_k.set_rows([{
                **m,
                'fecha': str(m.get('fecha') or '')[:19].replace('T',' '),
                'cantidad': str(m.get('cantidad') or ''),
                'saldo_anterior': str(m.get('saldo_anterior') or ''),
                'saldo_nuevo': str(m.get('saldo_nuevo') or ''),
            } for m in rows])
            kardex_info.configure(text=f'{len(rows)} movimientos · ' + (f'Producto {codigo}' if codigo else 'últimos movimientos'))
            tabs.set('Kardex')
        ejecutar(lambda: servicio.kardex(codigo), ok, 'No se pudo consultar Kardex')

    # Lanza carga después de que Tk haya colocado la pantalla.
    root.after(30, inicializar)
