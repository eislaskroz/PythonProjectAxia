"""Pruebas aisladas del contrato de registro de Obra Civil y su idempotencia."""
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


def _service_contract():
    # Extraer las dos funciones aisladas evita exigir una sesión real de
    # Supabase durante CI; los métodos son los mismos del código productivo.
    ruta = Path(__file__).resolve().parents[2] / "services" / "obras_civiles_service.py"
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    funciones = [n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name in (
        "_consultar_solicitud", "crear_obra_civil"
    )]
    ns = {
        "TABLA_OBRAS_CIVILES": "db_obras_civiles",
        "normalizar_campos_fecha": lambda datos: datos,
        "logger": Mock(),
        "register_error": Mock(),
        "registrar_movimiento_seguro": Mock(),
    }
    exec(compile(ast.Module(body=funciones, type_ignores=[]), str(ruta), "exec"), ns)
    return ns


class _Rpc:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = 0

    def execute(self):
        self.calls += 1
        res = next(self.results)
        if isinstance(res, Exception):
            raise res
        return SimpleNamespace(data=res)


class _Table:
    def __init__(self, result):
        self.result = result
        self.payload = None
        self.calls = 0

    def insert(self, payload):
        self.payload = payload
        return self

    def execute(self):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return SimpleNamespace(data=self.result)


class _Sb:
    def __init__(self, rpc, table):
        self.rpc_result = rpc
        self.table_result = table
        self.rpc_args = []

    def rpc(self, name, params):
        self.rpc_args.append((name, params))
        return self.rpc_result

    def table(self, name):
        assert name == "db_obras_civiles"
        return self.table_result


REQUEST = "997f4fd9-3bee-4562-bc1d-b46ce17b3cba"
REG = {"obc_id": "1", "obc_folio": "OBC-0002"}


def test_registro_nuevo_usa_uuid_y_no_envia_folio_cliente():
    ns = _service_contract()
    t = _Table([REG])
    sb = _Sb(_Rpc([[]]), t)
    ns["supabase"] = sb
    respuesta = ns["crear_obra_civil"]({"obc_request_id": REQUEST, "obc_folio": "OBC-0001", "obc_cliente": "TEST"})
    assert respuesta == [REG]
    assert "obc_folio" not in t.payload
    assert t.payload["obc_request_id"] == REQUEST
    assert t.calls == 1


def test_reintento_solicitud_confirmada_no_hace_otro_insert():
    ns = _service_contract()
    t = _Table(AssertionError("NUNCA insertar dos veces"))
    sb = _Sb(_Rpc([[REG]]), t)
    ns["supabase"] = sb
    assert ns["crear_obra_civil"]({"obc_request_id": REQUEST}) == [REG]
    assert t.calls == 0


def test_corte_de_red_tras_insert_recupera_registro_por_token():
    ns = _service_contract()
    t = _Table(ConnectionError("conexión terminada"))
    sb = _Sb(_Rpc([[], [REG]]), t)
    ns["supabase"] = sb
    assert ns["crear_obra_civil"]({"obc_request_id": REQUEST}) == [REG]
    assert t.calls == 1
    assert sb.rpc_result.calls == 2


def test_sin_rpc_no_intenta_insertar_y_falla_cerrado():
    ns = _service_contract()
    t = _Table([REG])
    sb = _Sb(_Rpc([RuntimeError("función aún no instalada")]), t)
    ns["supabase"] = sb
    assert ns["crear_obra_civil"]({"obc_request_id": REQUEST}) is None
    assert t.calls == 0


def test_sin_confirmacion_no_genera_segundo_insert():
    ns = _service_contract()
    t = _Table(ConnectionError("corte"))
    sb = _Sb(_Rpc([[], []]), t)
    ns["supabase"] = sb
    assert ns["crear_obra_civil"]({"obc_request_id": REQUEST}) is None
    assert t.calls == 1


def test_version_de_escritorio_copias_en_sync():
    proyecto = Path(__file__).resolve().parents[2]
    import re
    version = re.search(r'APP_VERSION = "([^\"]+)"', (proyecto / "core/version.py").read_text()).group(1)
    instalador = re.search(r'#define MyAppVersion "([^\"]+)"', (proyecto / "installer/AXIA.iss").read_text()).group(1)
    assert version == instalador
