"""Almacén AXIA: simulador efímero y cliente del servicio protegido.

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


class AlmacenSimulador:
    """Pruebas en memoria. Saldos empiezan siempre desde CERO; sin persistencia."""

    remoto = False

    def __init__(self, catalogo: list[dict] | None = None):
        self._catalogo = [dict(p) for p in (catalogo if catalogo is not None else catalogo_eleventa())]
        self._por_codigo = {str(p['codigo']).strip(): p for p in self._catalogo}
        if len(self._por_codigo) != len(self._catalogo):
            raise ValueError('Hay códigos duplicados en el catálogo. No se permite iniciar movimientos de prueba.')
        self._saldos: dict[str, Decimal] = {}
        self._movimientos: list[dict] = []
        self._idempotencias: dict[str, dict] = {}
        self._lock = Lock()

    def catalogo(self) -> list[dict]:
        return [
            {**p, 'saldo': formatear_cantidad(self._saldos.get(str(p['codigo']).strip(), 0)),
             'saldo_exportado': p.get('existencia', '')}
            for p in self._catalogo
        ]

    def kardex(self, codigo: str | None = None) -> list[dict]:
        return [dict(m) for m in reversed(self._movimientos)
                if not codigo or m['codigo'] == codigo]

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
        if codigo not in self._por_codigo:
            raise ValueError('Selecciona un producto válido del catálogo.')
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


class AlmacenRemoto:
    """Cliente de Edge Function. El escritorio no posee claves de servicio.

    La sesión firmada sólo vive en memoria; debe iniciarse con la contraseña
    del usuario AXIA, que se comprueba en servidor.
    """
    remoto = True

    def __init__(self):
        from supabase_config import SUPABASE_URL, SUPABASE_KEY
        self.endpoint = SUPABASE_URL.rstrip('/') + '/functions/v1/axia-almacen'
        self.anon_key = SUPABASE_KEY
        self.token = None
        self._usuario_id = None

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

    def catalogo(self):
        return self._peticion('catalogo')

    def kardex(self, codigo=None):
        return self._peticion('kardex', {'codigo': codigo or None})

    def registrar(self, *, codigo, tipo, cantidad, motivo, referencia, destinatario, usuario, idempotencia=None):
        if str(usuario.get('id_usuario')) != self._usuario_id:
            raise PermissionError('Se ha cambiado de usuario. Inicia sesión otra vez.')
        return self._peticion('registrar', {
            'codigo': str(codigo), 'tipo': str(tipo).upper(),
            'cantidad': str(cantidad_valida(cantidad)),
            'motivo': str(motivo).strip(), 'referencia': str(referencia).strip(),
            'destinatario': str(destinatario).strip(),
            'idempotencia': idempotencia or str(uuid.uuid4()),
        })


def crear_almacen():
    # Sólo la activación deliberada permite conectarse a Supabase; por defecto
    # el módulo es un simulador sin persistencia ni alteración de inventario.
    modo = os.getenv('AXIA_ALMACEN_MODO', 'simulador').lower().strip()
    if modo == 'remoto':
        return AlmacenRemoto()
    if modo != 'simulador':
        raise ValueError('AXIA_ALMACEN_MODO inválido. Usa simulador o remoto.')
    return AlmacenSimulador()
