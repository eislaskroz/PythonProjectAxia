"""Catálogo Maestro AXIA en entorno piloto: SOLO LECTURA.

No traslada existencias de ELEVENTA a saldos operativos ni autoriza movimientos.
"""
from __future__ import annotations

CAMPOS_ORIGINALES = (
    ('codigo_axia', 'Código AXIA'),
    ('codigo_proveedor', 'Código Proveedor'),
    ('proveedor', 'Proveedor'),
    ('producto', 'Producto'),
    ('departamento_origen', 'Departamento original'),
    ('p_costo', 'P. Costo'),
    ('p_venta', 'P. Venta'),
    ('p_mayoreo', 'P. Mayoreo'),
    ('existencia_eleventa', 'Existencia (ELEVENTA)'),
    ('inv_minimo', 'Inv. Mínimo'),
    ('inv_maximo', 'Inv. Máximo'),
)
CAMPOS_ADICIONALES = (
    ('categoria_axia', 'Categoría AXIA'),
    ('familia_axia', 'Familia AXIA'),
    ('prefijo_familia', 'Prefijo familia'),
    ('prefijo_categoria', 'Prefijo categoría'),
    ('seguimiento_sugerido', 'Seguimiento sugerido'),
    ('estado_clasificacion', 'Estado de clasificación'),
    ('fila_origen_eleventa', 'Fila original ELEVENTA'),
    ('codigo_origen_eleventa', 'Código original ELEVENTA'),
    ('posible_equivalencia', 'Posible equivalencia'),
    ('unidad_inventario', 'Unidad de inventario'),
    ('estatus', 'Estatus original'),
    ('saldo_actual', 'Saldo actual en Supabase'),
    ('activo', 'Activo'),
    ('saldo_inicial_origen', 'Origen del saldo inicial'),
    ('creado_el', 'Fecha de alta en catálogo'),
)
COLUMNAS_TABLA = (
    ('codigo_axia', 'Código AXIA', 150),
    ('producto', 'Producto', 340),
    ('categoria_axia', 'Categoría AXIA', 205),
    ('familia_axia', 'Familia AXIA', 240),
    ('departamento_origen', 'Departamento original', 180),
    ('p_costo', 'P. Costo', 105),
    ('p_venta', 'P. Venta', 105),
    ('p_mayoreo', 'P. Mayoreo', 110),
    ('existencia_eleventa', 'Existencia ELEVENTA', 150),
    ('inv_minimo', 'Inv. Mínimo', 110),
    ('inv_maximo', 'Inv. Máximo', 110),
    ('proveedor', 'Proveedor', 150),
    ('codigo_proveedor', 'Código proveedor', 150),
    ('codigo_origen_eleventa', 'Código origen ELEVENTA', 175),
)


def ficha_producto_maestro(registro: dict) -> str:
    """Muestra 11 campos originales + atributos de clasificación (sin perder nulos)."""
    def mostrar(valor):
        return '— (pendiente)' if valor is None or valor == '' else str(valor)
    lineas = [f'{titulo}: {mostrar(registro.get(clave))}'
              for clave, titulo in CAMPOS_ORIGINALES]
    lineas += ['']
    lineas += [f'{titulo}: {mostrar(registro.get(clave))}'
               for clave, titulo in CAMPOS_ADICIONALES]
    lineas.append('\nLos movimientos cambian SALDO ACTUAL. ELEVENTA es la referencia histórica importada.')
    return '\n'.join(lineas)


def validar_paginacion(pagina=1, limite=100, busqueda=''):
    if not isinstance(pagina, int) or isinstance(pagina, bool) or not 1 <= pagina <= 100000:
        raise ValueError('Página del catálogo piloto inválida.')
    if not isinstance(limite, int) or isinstance(limite, bool) or not 1 <= limite <= 100:
        raise ValueError('Máximo 100 artículos por consulta.')
    filtro = str(busqueda or '').strip()
    if len(filtro) > 80:
        raise ValueError('La búsqueda admite hasta 80 caracteres.')
    return {'pagina': pagina, 'limite': limite, 'busqueda': filtro}
