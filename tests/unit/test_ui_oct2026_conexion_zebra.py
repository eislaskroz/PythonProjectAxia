"""Regresiones visuales y de consultas de lectura; no requieren Supabase."""

from pathlib import Path

import pytest

from services.query_compat import (
    es_error_conexion_transitoria,
    ejecutar_lectura_con_reintento,
    execute_select_compatible,
)

ROOT = Path(__file__).resolve().parents[2]


def test_reintenta_conexion_cortada_solo_en_lecturas():
    llamadas = []

    def leer():
        llamadas.append(1)
        if len(llamadas) == 1:
            raise RuntimeError('<ConnectionTerminated error_code:1, last_stream_id:5, additional_data:None>')
        return {'registros': 4}

    assert ejecutar_lectura_con_reintento(leer, espera=0) == {'registros': 4}
    assert len(llamadas) == 2


def test_no_reintenta_error_de_permisos_o_validacion():
    llamadas = []

    def leer():
        llamadas.append(1)
        raise RuntimeError('permission denied for table db_levantamientos')

    with pytest.raises(RuntimeError, match='permission denied'):
        ejecutar_lectura_con_reintento(leer, espera=0)
    assert len(llamadas) == 1


def test_select_reconstruye_query_en_cada_intento():
    eventos = []

    class Query:
        def execute(self):
            eventos.append('execute')
            if eventos.count('execute') == 1:
                raise RuntimeError('<ConnectionTerminated error_code:1, last_stream_id:5>')
            return type('Result', (), {'data': [1]})()

        def limit(self, limite):
            return self

    class Table:
        def select(self, columns):
            eventos.append('select')
            return Query()

    class Client:
        def table(self, name):
            return Table()

    resultado = execute_select_compatible(Client(), 'db_levantamientos', 'lev_folio', lambda q: q.limit(10))
    assert resultado.data == [1]
    assert eventos.count('select') == eventos.count('execute') == 2


def test_busquedas_no_superponen_etiquetas_blancas():
    for nombre in (
        'admin_operational_editor_view.py', 'clientes_admin_view.py',
        'orden_servicio_conversion_view.py', 'reportes_view.py',
        'usuarios_admin_view.py', 'direccion_general_view.py',
        'inicio_aco_view.py',
    ):
        contenido = (ROOT / 'views' / nombre).read_text(encoding='utf-8-sig')
        assert '.configure(placeholder_text=' in contenido, nombre
        assert 'placeholder.place(in_=' not in contenido, nombre
        assert 'placeholder_aco = ctk.CTkLabel' not in contenido


def test_tablas_usen_zebra_y_mantengan_seleccion():
    native = (ROOT / 'ui/native_table.py').read_text()
    direccion = (ROOT / 'views/direccion_general_view.py').read_text()
    assert '"#FFFFFF"' in native and '"#EAF3FF"' in native
    assert 'self.tree.tag_configure("fila_azul"' in native
    assert '"selected", "#2563EB"' in native
    assert "tree.tag_configure('fila_azul'" in direccion


def test_reconoce_conexion_http2_cortada():
    assert es_error_conexion_transitoria(RuntimeError('<ConnectionTerminated error_code:1>'))
    assert not es_error_conexion_transitoria(ValueError('invalid input syntax'))
