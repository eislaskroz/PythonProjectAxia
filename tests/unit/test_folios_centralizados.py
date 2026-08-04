from types import SimpleNamespace, ModuleType
import importlib
import sys
import pytest

fake_config = ModuleType("supabase_config")
fake_config.supabase = SimpleNamespace()
sys.modules.setdefault("supabase_config", fake_config)

folios = importlib.import_module("services.folios_service")


class FakeRpc:
    def __init__(self, data):
        self.data = data

    def execute(self):
        return SimpleNamespace(data=self.data)


class FakeSupabase:
    def __init__(self, data):
        self.data = data
        self.called = []

    def rpc(self, name):
        self.called.append(name)
        return FakeRpc(self.data)


def test_rpc_devuelve_folio_cinco_digitos(monkeypatch):
    fake = FakeSupabase("LEV-00042")
    monkeypatch.setattr(folios, "supabase", fake)
    assert folios.solicitar_folio_levantamiento() == "LEV-00042"
    assert fake.called == ["generar_folio_levantamiento"]


def test_rpc_rechaza_formato_invalido(monkeypatch):
    monkeypatch.setattr(folios, "supabase", FakeSupabase("LEV-0042"))
    with pytest.raises(folios.FolioCentralError):
        folios.solicitar_folio_levantamiento()


def test_generador_lev_usa_rpc(monkeypatch):
    monkeypatch.setattr(folios, "solicitar_folio_levantamiento", lambda: "LEV-00123")
    assert folios.generar_siguiente_folio("LEV") == "LEV-00123"
