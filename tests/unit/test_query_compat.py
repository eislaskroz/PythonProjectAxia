from types import SimpleNamespace

import pytest

from services.query_compat import execute_select_compatible


class FakeQuery:
    def __init__(self, client, columns):
        self.client = client
        self.columns = columns
        self.filters = []

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, *_args):
        return self

    def execute(self):
        self.client.calls.append(self.columns)
        if "columna_opcional" in self.columns:
            raise RuntimeError("Could not find the 'columna_opcional' column of 'tabla' in the schema cache")
        return SimpleNamespace(data=[{"folio": "LEV-0004"}])


class FakeTable:
    def __init__(self, client):
        self.client = client

    def select(self, columns):
        return FakeQuery(self.client, columns)


class FakeClient:
    def __init__(self):
        self.calls = []

    def table(self, _name):
        return FakeTable(self)


def test_reintenta_sin_columna_ausente():
    client = FakeClient()
    response = execute_select_compatible(
        client,
        "tabla",
        "folio,columna_opcional",
        lambda query: query.eq("folio", "LEV-0004"),
    )
    assert response.data == [{"folio": "LEV-0004"}]
    assert client.calls == ["folio,columna_opcional", "folio"]


def test_no_oculta_errores_ajenos_al_esquema():
    class BrokenQuery(FakeQuery):
        def execute(self):
            raise RuntimeError("network timeout")

    class BrokenTable(FakeTable):
        def select(self, columns):
            return BrokenQuery(self.client, columns)

    class BrokenClient(FakeClient):
        def table(self, _name):
            return BrokenTable(self)

    with pytest.raises(RuntimeError, match="network timeout"):
        execute_select_compatible(BrokenClient(), "tabla", "folio")
