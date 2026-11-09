"""Verificaciones locales del historial personal sin conexión a Supabase."""
import ast
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]


def _funciones():
    source = (ROOT / 'services/mis_documentos_service.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    funcs = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    compiled = compile(ast.Module(body=funcs, type_ignores=[]), '<mis_documentos>', 'exec')
    return compiled


class FakeQuery:
    def __init__(self, datos):
        self.datos = datos
        self.condicion = None
        self.rango = None
    def select(self, campos):
        assert 'creado_por' in campos
        return self
    def eq(self, campo, autor):
        assert campo == 'creado_por'
        self.condicion = autor
        return self
    def order(self, *args, **kwargs):
        return self
    def range(self, inicio, fin):
        self.rango = (inicio, fin)
        return self
    def execute(self):
        assert self.condicion
        filas = [x for x in self.datos if x['creado_por'] == self.condicion]
        return SimpleNamespace(data=filas[self.rango[0]:self.rango[1]+1])


class FakeSupabase:
    def __init__(self, datos):
        self.datos = datos
    def table(self, tabla):
        return FakeQuery(self.datos[tabla])


def _ctx(role=4, nick='operador1', ident=9):
    rows = {
        'db_levantamientos': [
            {'lev_folio':'LEV-1', 'creado_por':'operador1'},
            {'lev_folio':'LEV-2', 'creado_por':'otro'},
        ],
        'db_bitacoras': [
            {'bit_folio':'BIT-1', 'creado_por':'operador1'},
            {'bit_folio':'BIT-2', 'creado_por':'otro'},
        ],
        'db_ordenes_servicio': [
            {'os_folio':'OS-1', 'creado_por':'operador1'},
            {'os_folio':'OS-2', 'creado_por':'otro'},
        ],
    }
    usuario = {'usu_tipo':role, 'usuario':nick, 'id_usuario':ident}
    env = dict(obtener_usuario_actual=lambda:usuario, obtener_tipo_usuario=lambda u:u['usu_tipo'],
               OPERADOR=4, supabase=FakeSupabase(rows),
               CONFIG={
                   'levantamientos':('db_levantamientos', 'lev_folio,creado_por', ('lev_folio',)),
                   'bitacoras':('db_bitacoras', 'bit_folio', ('bit_folio',)),
                   'ordenes_servicio':('db_ordenes_servicio', 'os_folio', ('os_folio',)),
               })
    exec(_funciones(), env)
    return env


def test_historial_filtra_en_servidor_para_los_tres_formatos():
    e = _ctx()
    for tipo in ('levantamientos','bitacoras','ordenes_servicio'):
        filas = e['consultar_mis_documentos'](tipo)
        assert len(filas) == 1
        assert filas[0]['creado_por'] == 'operador1'


def test_busquedas_no_devuelven_registros_de_otros():
    e = _ctx()
    assert e['consultar_mis_documentos']('bitacoras','BIT-2') == []
    assert len(e['consultar_mis_documentos']('bitacoras','BIT-1')) == 1


def test_acceso_denegado_sin_sesion_valida():
    for role,nick,ident in ((1,'admin',9),(4,'DESCONOCIDO',9),(4,'operador',None)):
        e = _ctx(role,nick,ident)
        try:
            e['consultar_mis_documentos']('levantamientos')
            assert False, 'No se debe permitir la consulta'
        except PermissionError:
            pass
