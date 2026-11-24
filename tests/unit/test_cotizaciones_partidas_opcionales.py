from pathlib import Path
import importlib
import sys
import types


def test_interfaz_permite_partidas_y_servicio_opcional():
    vista = (Path(__file__).resolve().parents[2] / "views" / "cotizaciones_view.py").read_text(encoding="utf-8")
    assert "＋ Agregar partida" in vista
    assert "Incluir costo de servicio / mano de obra / envío (opcional)" in vista
    assert "def quitar_partida(indice):" in vista
    assert "def alternar_servicio():" in vista
    assert "if incluir_servicio.get():" in vista


def test_guardado_con_partidas_adicionales_y_sin_costo_servicio(monkeypatch):
    def modulo(nombre, **atributos):
        m = types.ModuleType(nombre)
        for clave, valor in atributos.items():
            setattr(m, clave, valor)
        monkeypatch.setitem(sys.modules, nombre, m)

    modulo("supabase_config", supabase=None)
    modulo("services.movimientos_service", registrar_movimiento_seguro=lambda **kw: None)
    modulo("services.folios_service", solicitar_folio_cotizacion=lambda: "COT-OPCIONAL")
    modulo("services.sucursales_service", obtener_sucursal_por_id=lambda _id: {})
    modulo("services.usuarios_service", obtener_usuario_por_id=lambda _id: {})
    sys.modules.pop("services.cotizaciones_service", None)
    svc = importlib.import_module("services.cotizaciones_service")

    class Respuesta:
        def __init__(self, data):
            self.data = data

    class Tabla:
        def insert(self, payload):
            self.payload = payload
            return self

        def execute(self):
            return Respuesta([self.payload])

    class BD:
        def table(self, nombre):
            assert nombre == svc.TABLA_COTIZACIONES
            return Tabla()

    monkeypatch.setattr(svc, "supabase", BD())
    monkeypatch.setattr(svc, "solicitar_folio_cotizacion", lambda: "COT-OPCIONAL")
    monkeypatch.setattr(svc, "registrar_movimiento_seguro", lambda **kwargs: None)
    datos = {
        "id_levantamiento": 23, "lev_folio": "LEV-00133", "cot_cliente": "Cliente",
        "cot_contacto": "Contacto", "cot_sucursal": "Sucursal", "cot_asunto": "Asunto",
        "cot_esi": "Vendedora", "cot_esi_correo": "ventas@ejemplo.com",
        "cot_esi_telefono": "1234567890", "cot_jefe_operaciones": "Operaciones",
        "cot_supervisor": "Supervisor", "cot_dias": "1", "cot_personas": "2",
        "cot_plan_pagos": "PPD", "cot_vigencia": "15", "cot_descuento_pct": "0",
        "cot_iva_pct": "16",
    }
    items = [
        {"unidad_tipo": "Pieza(s)", "cantidad": "2", "proveedor": "N/A",
         "modelo": "N/A", "sku": "N/A", "marca": "N/A", "concepto": "Equipo A",
         "precio_lista": "100", "utilidad_pct": "0"},
        {"unidad_tipo": "Pieza(s)", "cantidad": "3", "proveedor": "N/A",
         "modelo": "N/A", "sku": "N/A", "marca": "N/A", "concepto": "Material adicional",
         "precio_lista": "50", "utilidad_pct": "0"},
    ]
    saved = svc.guardar_cotizacion_comercial(datos, items, "Ventas")
    assert len(saved["cot_partidas_json"]) == 2
    assert [x["concepto"] for x in saved["cot_partidas_json"]] == ["Equipo A", "Material adicional"]
    assert saved["cot_subtotal"] == 350
    assert saved["cot_total"] == 406
