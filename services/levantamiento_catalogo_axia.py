"""Consulta de solo lectura del Catálogo Maestro AXIA para Levantamientos.

Una sesión de alcance `levantamientos_lectura` NO permite acciones de Almacén.
El nombre y el código del producto quedan congelados en el JSON del LEV.
"""
from __future__ import annotations

from services.almacen_service import AlmacenRemoto


class CatalogoAxiaLevantamientos(AlmacenRemoto):
    def iniciar_lectura(self, nickname: str, password: str, expected_id: object) -> None:
        resultado = self._peticion(
            'login_levantamientos', {'nickname': nickname, 'password': password}, autenticar=True
        )
        if str(resultado.get('id_usuario')) != str(expected_id):
            self.token = None
            raise PermissionError('La cuenta validada no coincide con el usuario activo en AXIA.')
        self.token = str(resultado['token'])
        self._usuario_id = str(expected_id)

    def buscar(self, texto: str = '', *, limite: int = 80) -> list[dict]:
        resultado = self._peticion('catalogo_levantamientos', {
            'buscar': str(texto or '').strip()[:100], 'limite': max(1, min(int(limite), 100)),
        })
        return list(resultado or [])


def referencia_axia(producto: dict) -> dict:
    """Snapshot no comercial: sin proveedor ni costos, estable al editar catálogo."""
    return {
        'codigo_axia': str(producto.get('codigo_axia') or '').strip(),
        'producto_axia': str(producto.get('producto') or '').strip(),
        'categoria_axia': str(producto.get('categoria_axia') or '').strip(),
        'familia_axia': str(producto.get('familia_axia') or '').strip(),
        'unidad_inventario_axia': str(producto.get('unidad_inventario') or '').strip(),
    }


def categoria_canalizacion_axia(producto: dict) -> str:
    """Mantiene las categorías históricas y sus conversiones de unidad."""
    t = ' '.join(str(producto.get(k) or '') for k in ('producto', 'familia_axia')).casefold()
    for palabra, categoria in (
        ('patch cord', 'Patch cord'), ('patchcord', 'Patch cord'),
        ('patch panel', 'Patch panel'), ('faceplate', 'Faceplate'),
        ('jack rj45', 'Jack RJ45'), ('plug rj45', 'Plug RJ45'),
        ('canaleta', 'Canaleta'), ('tubo', 'Tubo'), ('conduit', 'Tubo'),
        ('cable', 'Cable'), ('cople', 'Cople'), ('registro', 'Registro'),
        ('conector', 'Conectores'), ('abrazadera', 'Abrazadera'),
        ('codo', 'Codos'), ('caja', 'Cajas'), ('tapa', 'Tapas'),
    ):
        if palabra in t:
            return categoria
    return 'Otro AXIA'


def unidad_levantamiento_axia(producto: dict) -> str:
    unidad = str(producto.get('unidad_inventario') or '').strip().casefold()
    if 'metro' in unidad: return 'Metro(s)'
    if 'rollo' in unidad: return 'Rollo(s)'
    if 'juego' in unidad: return 'Juego(s)'
    if 'caja' in unidad: return 'Caja(s)'
    return 'Pieza(s)'
