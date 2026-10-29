"""Almacén AXIA: simulador efímero y cliente seguro (laboratorio persistente).

La simulación NO persiste datos y NO consume existencias de ELEVENTA.
En producción únicamente la Edge Function es capaz de ordenar la transacción.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from threading import Lock


def _valor_decimal(value) -> Decimal:
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("La cantidad debe ser un número válido.") from None


def cantidad_valida(value) -> Decimal:
    n = _valor_decimal(value)
    if not n.is_finite() or not (Decimal('0') < n <= Decimal('1000000')):
        raise ValueError("La cantidad debe ser mayor que cero y no superar 1,000,000.")
    if n.as_tuple().exponent < -3:
        raise ValueError("Máximo tres decimales para la cantidad.")
    return n


def catalogo_eleventa() -> list[dict]:
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
    with (base / 'assets' / 'almacen_catalogo_eleventa.json').open(encoding='utf-8') as fh:
        return json.load(fh)


def formatear_cantidad(value) -> str:
    return format(Decimal(str(value)).quantize(Decimal('0.001')), 'f').rstrip('0').rstrip('.') or '0'



def validar_producto(datos: dict) -> dict:
    """Normaliza y valida datos maestros; nunca edita existencias por catálogo."""
    codigo = str(datos.get('codigo') or '').strip()
    nombre = str(datos.get('producto') or datos.get('nombre') or '').strip()
    departamento = str(datos.get('departamento') or 'SIN DEPARTAMENTO').strip()
    if not 1 <= len(codigo) <= 120 or not 1 <= len(nombre) <= 500:
        raise ValueError('Código (1-120) y nombre (1-500) son obligatorios.')
    if not 1 <= len(departamento) <= 150:
        raise ValueError('El departamento debe tener entre 1 y 150 caracteres.')

    normalized = {'codigo': codigo, 'producto': nombre, 'departamento': departamento}
    for campo, escala in (('costo', 2), ('venta', 2), ('minimo', 3), ('maximo', 3)):
        bruto = str(datos.get(campo, 0) or '0').replace('$', '').replace(',', '').strip()
        valor = _valor_decimal(bruto)
        if not valor.is_finite() or not (0 <= valor <= Decimal('999999999999')):
            raise ValueError(f'{campo}: introduce un número positivo válido.')
        if valor != valor.quantize(Decimal('1').scaleb(-escala)):
            raise ValueError(f'{campo}: máximo {escala} decimales.')
        normalized[campo] = format(valor, f'.{escala}f')
    return normalized


class AlmacenSimulador:
    """Pruebas en memoria. Saldos empiezan siempre desde CERO; sin persistencia."""

    remoto = False

    def __init__(self, catalogo: list[dict] | None = None):
        self._catalogo = [{**dict(p), 'activo': bool(p.get('activo', True))} for p in (catalogo if catalogo is not None else catalogo_eleventa())]
        self._por_codigo = {str(p['codigo']).strip(): p for p in self._catalogo}
        if len(self._por_codigo) != len(self._catalogo):
            raise ValueError('Hay códigos duplicados en el catálogo. No se permite iniciar movimientos de prueba.')
        self._saldos: dict[str, Decimal] = {}
        self._movimientos: list[dict] = []
        self._idempotencias: dict[str, dict] = {}
        self._lock = Lock()

    def catalogo(self, incluir_inactivos=False) -> list[dict]:
        return [
            {**p, 'saldo': formatear_cantidad(self._saldos.get(str(p['codigo']).strip(), 0)),
             'saldo_exportado': p.get('existencia', '')}
            for p in self._catalogo if incluir_inactivos or p.get('activo', True)
        ]

    def crear_producto(self, *, datos: dict, usuario: dict) -> dict:
        self._autorizar_catalogo(usuario)
        validado = validar_producto(datos)
        with self._lock:
            codigo = validado['codigo']
            if codigo in self._por_codigo:
                raise ValueError('Ese código ya existe (incluso si está desactivado).')
            p = {**validado, 'activo': True, 'existencia': '0'}
            self._catalogo.append(p)
            self._por_codigo[codigo] = p
            return dict(p)

    def editar_producto(self, *, codigo: str, datos: dict, usuario: dict) -> dict:
        self._autorizar_catalogo(usuario)
        validado = validar_producto({**datos, 'codigo': codigo})
        if str(datos.get('codigo', codigo)).strip() != codigo:
            raise ValueError('El código no puede cambiar: identifica los movimientos del Kardex.')
        with self._lock:
            p = self._por_codigo.get(codigo)
            if not p or not p.get('activo', True):
                raise ValueError('No se encontró un producto activo con ese código.')
            p.update(validado)
            return dict(p)

    def desactivar_producto(self, *, codigo: str, usuario: dict) -> dict:
        self._autorizar_catalogo(usuario)
        with self._lock:
            p = self._por_codigo.get(codigo)
            if not p or not p.get('activo', True):
                raise ValueError('El producto ya no existe en el catálogo activo.')
            if self._saldos.get(codigo, Decimal('0')) != 0:
                raise ValueError('No se puede quitar un producto con existencia. Primero regulariza el saldo mediante movimientos.')
            p['activo'] = False
            return dict(p)

    def reactivar_producto(self, *, codigo: str, usuario: dict) -> dict:
        self._autorizar_catalogo(usuario)
        with self._lock:
            p = self._por_codigo.get(codigo)
            if not p or p.get('activo', True):
                raise ValueError('Selecciona un producto desactivado.')
            p['activo'] = True
            return dict(p)

    @staticmethod
    def _autorizar_catalogo(usuario):
        from security.permissions import puede_ver_almacen
        if not puede_ver_almacen(usuario) or not usuario.get('id_usuario'):
            raise PermissionError('Solo Administrador o Almacén autenticado puede gestionar productos.')

    def kardex(self, codigo: str | None = None, pagina=1, limite=200) -> list[dict]:
        pagina = max(1, int(pagina))
        limite = min(200, max(1, int(limite)))
        filtro = str(codigo or '').strip()
        registros = [dict(m) for m in reversed(self._movimientos)
                     if not filtro or m['codigo'] == filtro or m['referencia'] == filtro]
        inicio = (pagina - 1) * limite
        return registros[inicio:inicio+limite]

    def registrar(self, *, codigo: str, tipo: str, cantidad, motivo: str,
                  referencia: str, destinatario: str, usuario: dict,
                  idempotencia: str | None = None) -> dict:
        from security.permissions import puede_ver_almacen
        if not puede_ver_almacen(usuario) or not usuario.get('id_usuario'):
            raise PermissionError('Solo Administrador o Almacén autenticado puede registrar movimientos.')
        tipo = str(tipo).strip().upper()
        if tipo not in ('ENTRADA', 'SALIDA'):
            raise ValueError('El movimiento debe ser ENTRADA o SALIDA.')
        qty = cantidad_valida(cantidad)
        codigo = str(codigo).strip()
        if codigo not in self._por_codigo or not self._por_codigo[codigo].get('activo', True):
            raise ValueError('Selecciona un producto activo del catálogo.')
        motivo = str(motivo).strip()
        referencia = str(referencia).strip()
        destinatario = str(destinatario).strip()
        if not motivo or len(motivo) > 250:
            raise ValueError('El motivo es obligatorio (máximo 250 caracteres).')
        if len(referencia) > 120 or len(destinatario) > 120:
            raise ValueError('Referencia y destinatario admiten máximo 120 caracteres.')
        if tipo == 'SALIDA' and not destinatario:
            raise ValueError('Para una salida indica quién recibe el material.')
        key = idempotencia or str(uuid.uuid4())
        with self._lock:
            if key in self._idempotencias:
                old = self._idempotencias[key]
                if any((old[k] != val) for k, val in {
                    'codigo': codigo, 'tipo': tipo, 'cantidad': formatear_cantidad(qty),
                    'motivo': motivo, 'referencia': referencia, 'destinatario': destinatario,
                    'responsable_id': str(usuario['id_usuario']),
                }.items()):
                    raise ValueError('El identificador de la operación ya existe con datos distintos.')
                return dict(old)
            anterior = self._saldos.get(codigo, Decimal('0'))
            nuevo = anterior + qty if tipo == 'ENTRADA' else anterior - qty
            if nuevo < 0:
                raise ValueError(f'Existencia de prueba insuficiente: {formatear_cantidad(anterior)}.')
            mov = {
                'id': str(uuid.uuid4()), 'idempotencia': key, 'codigo': codigo,
                'producto': self._por_codigo[codigo].get('producto', ''),
                'tipo': tipo, 'cantidad': formatear_cantidad(qty),
                'saldo_anterior': formatear_cantidad(anterior), 'saldo_nuevo': formatear_cantidad(nuevo),
                'motivo': motivo, 'referencia': referencia, 'destinatario': destinatario,
                'responsable_id': str(usuario['id_usuario']),
                'responsable': str(usuario.get('usuario') or usuario.get('nombre') or ''),
                'fecha': datetime.now().astimezone().isoformat(timespec='seconds'),
            }
            self._saldos[codigo] = nuevo
            self._movimientos.append(mov)
            self._idempotencias[key] = mov
            return dict(mov)

    def consultar_ot(self, folio: str, usuario: dict) -> dict:
        """En simulador, una OT se usa como referencia manual sin validación remota."""
        self._autorizar_catalogo(usuario)
        folio = str(folio or '').strip().upper()
        if not folio or len(folio) > 120:
            raise ValueError('Especifica el folio de la OT.')
        return {'folio': folio, 'partidas': [], 'simulador': True}

    def registrar_salida_ot(self, *, folio, partidas, destinatario, motivo,
                           usuario, idempotencia=None):
        from services.almacen_entregas_ot import validar_entrega_ot
        self._autorizar_catalogo(usuario)
        solicitud = validar_entrega_ot(folio, partidas, destinatario, motivo)
        key = idempotencia or str(uuid.uuid4())
        with self._lock:
            firma = (solicitud['folio'], solicitud['destinatario'], solicitud['motivo'],
                     tuple((p['codigo'],p['cantidad']) for p in solicitud['partidas']),
                     str(usuario['id_usuario']))
            # Se guarda aparte para que los reintentos de OT no multipliquen los descuentos.
            if not hasattr(self, '_entregas_ot'):
                self._entregas_ot = {}
            if key in self._entregas_ot:
                anterior = self._entregas_ot[key]
                if anterior['firma'] != firma:
                    raise ValueError('Esta solicitud ya se utilizó con datos diferentes.')
                return {**anterior['resultado'], 'repetido': True}
            previas = {}
            for item in solicitud['partidas']:
                codigo = item['codigo']
                p = self._por_codigo.get(codigo)
                if not p or not p.get('activo', True):
                    raise ValueError(f'Producto {codigo} inexistente o inactivo.')
                saldo = self._saldos.get(codigo, Decimal('0'))
                qty = cantidad_valida(item['cantidad'])
                if saldo < qty:
                    raise ValueError(f'Existencia insuficiente de {codigo}: {formatear_cantidad(saldo)}.')
                previas[codigo] = (saldo, qty)
            # Todas las cantidades se validaron ANTES de alterar un saldo.
            movimientos = []
            for item in solicitud['partidas']:
                codigo = item['codigo']
                anterior, qty = previas[codigo]
                nuevo = anterior - qty
                mov = {
                    'id':str(uuid.uuid4()), 'idempotencia':str(uuid.uuid4()),
                    'codigo':codigo,'producto':self._por_codigo[codigo].get('producto',''),
                    'tipo':'SALIDA','cantidad':formatear_cantidad(qty),
                    'saldo_anterior':formatear_cantidad(anterior),
                    'saldo_nuevo':formatear_cantidad(nuevo),
                    'motivo':solicitud['motivo'],'referencia':solicitud['folio'],
                    'destinatario':solicitud['destinatario'],
                    'responsable_id':str(usuario['id_usuario']),
                    'responsable':str(usuario.get('usuario') or usuario.get('nombre') or ''),
                    'fecha':datetime.now().astimezone().isoformat(timespec='seconds'),
                }
                self._saldos[codigo] = nuevo
                self._movimientos.append(mov)
                movimientos.append(mov)
            resultado = {'folio':solicitud['folio'], 'movimientos':movimientos,
                         'cantidad_partidas':len(movimientos), 'repetido':False}
            self._entregas_ot[key] = {'firma':firma,'resultado':resultado}
            return dict(resultado)


class AlmacenRemoto:
    """Cliente de Edge Function. El escritorio no posee claves de servicio.

    La sesión firmada sólo vive en memoria; debe iniciarse con la contraseña
    del usuario AXIA, que se comprueba en servidor.
    """
    remoto = True

    def __init__(self, laboratorio: bool = False):
        from supabase_config import SUPABASE_URL, SUPABASE_KEY
        self.endpoint = SUPABASE_URL.rstrip('/') + '/functions/v1/axia-almacen'
        self.anon_key = SUPABASE_KEY
        self.token = None
        self._usuario_id = None
        # El ambiente se define en el cliente y se codifica en acciones distintas.
        # Las tablas de produccion NO son manipuladas por la modalidad laboratorio.
        self.laboratorio = False  # El entorno único no habilita rutas paralelas.
        self._sufijo = ''

    def _peticion(self, accion: str, payload: dict | None = None, *, autenticar=False):
        import requests
        headers = {'apikey': self.anon_key, 'Content-Type': 'application/json'}
        if not autenticar:
            if not self.token:
                raise PermissionError('Inicia sesión segura de Almacén para continuar.')
            headers['X-Axia-Almacen-Session'] = self.token
        try:
            response = requests.post(self.endpoint, headers=headers,
                                     json={'accion': accion, **(payload or {})}, timeout=25)
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise RuntimeError('No se pudo confirmar el resultado con el servidor. Consulta el Kardex antes de repetir.') from exc
        if response.status_code == 401:
            self.token = None
            raise PermissionError(data.get('error', 'La sesión de Almacén ha expirado.'))
        if response.status_code >= 400 or not data.get('ok'):
            raise RuntimeError(data.get('error', 'Operación de Almacén rechazada.'))
        return data.get('resultado')

    def iniciar_sesion(self, nickname: str, password: str, expected_id):
        result = self._peticion('login', {'nickname': nickname, 'password': password}, autenticar=True)
        if str(result.get('id_usuario')) != str(expected_id):
            self.token = None
            raise PermissionError('La identidad de Almacén no coincide con el usuario abierto en AXIA DESKTOP.')
        self.token = result['token']
        self._usuario_id = str(expected_id)

    def catalogo(self, incluir_inactivos=False):
        return self._peticion('catalogo' + self._sufijo, {'incluir_inactivos': bool(incluir_inactivos)})

    def kardex(self, codigo=None, pagina=1, limite=200):
        return self._peticion('kardex' + self._sufijo,
                              {'codigo': codigo or None, 'pagina':int(pagina),'limite':int(limite)})

    def _comprobar_usuario(self, usuario):
        if str(usuario.get('id_usuario')) != self._usuario_id:
            raise PermissionError('Se ha cambiado de usuario. Inicia sesión otra vez.')

    def crear_producto(self, *, datos: dict, usuario: dict):
        self._comprobar_usuario(usuario)
        return self._peticion('crear_producto' + self._sufijo, {'producto': validar_producto(datos)})

    def editar_producto(self, *, codigo: str, datos: dict, usuario: dict):
        self._comprobar_usuario(usuario)
        validado = validar_producto({**datos, 'codigo': codigo})
        if str(datos.get('codigo', codigo)).strip() != codigo:
            raise ValueError('No se permite cambiar el código de un producto registrado.')
        return self._peticion('editar_producto' + self._sufijo, {'codigo': codigo, 'producto': validado})

    def desactivar_producto(self, *, codigo: str, usuario: dict):
        self._comprobar_usuario(usuario)
        return self._peticion('desactivar_producto' + self._sufijo, {'codigo': str(codigo)})

    def reactivar_producto(self, *, codigo: str, usuario: dict):
        self._comprobar_usuario(usuario)
        return self._peticion('reactivar_producto' + self._sufijo, {'codigo': str(codigo)})

    def registrar(self, *, codigo, tipo, cantidad, motivo, referencia, destinatario, usuario, idempotencia=None):
        if str(usuario.get('id_usuario')) != self._usuario_id:
            raise PermissionError('Se ha cambiado de usuario. Inicia sesión otra vez.')
        return self._peticion('registrar' + self._sufijo, {
            'codigo': str(codigo), 'tipo': str(tipo).upper(),
            'cantidad': str(cantidad_valida(cantidad)),
            'motivo': str(motivo).strip(), 'referencia': str(referencia).strip(),
            'destinatario': str(destinatario).strip(),
            'idempotencia': idempotencia or str(uuid.uuid4()),
        })

    def consultar_ot(self, folio: str, usuario: dict):
        self._comprobar_usuario(usuario)
        return self._peticion('consultar_ot' + self._sufijo,
                              {'folio': str(folio or '').strip().upper()})

    def registrar_salida_ot(self, *, folio, partidas, destinatario, motivo,
                           usuario, idempotencia=None):
        from services.almacen_entregas_ot import validar_entrega_ot
        self._comprobar_usuario(usuario)
        solicitud = validar_entrega_ot(folio,partidas,destinatario,motivo)
        return self._peticion('salida_ot' + self._sufijo,
                              {**solicitud,'idempotencia':idempotencia or str(uuid.uuid4())})


def crear_almacen():
    """Una sola base operativa de Supabase desde python main.py.

    La autenticación y los movimientos permanecen protegidos por la Edge Function.
    """
    return AlmacenRemoto(laboratorio=False)
