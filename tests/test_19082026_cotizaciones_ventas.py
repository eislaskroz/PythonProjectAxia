from pathlib import Path

from security.permissions import puede_cotizar_levantamientos
from services.ordenes_trabajo_schema import partidas_desde_detalle_levantamiento

ROOT = Path(__file__).resolve().parents[1]


def test_permiso_cotizaciones_ventas_y_admin():
    assert puede_cotizar_levantamientos({"usu_tipo": 6}) is True
    assert puede_cotizar_levantamientos({"usu_tipo": 1}) is True
    for tipo in (2, 3, 4, 5):
        assert puede_cotizar_levantamientos({"usu_tipo": tipo}) is False


def test_sidebar_cotizaciones_entre_levantamientos_y_aco():
    src = (ROOT / "ui" / "app_sidebar.py").read_text(encoding="utf-8")
    assert src.index('"📋 Levantamientos"') < src.index('"💲 Cotizaciones"') < src.index('"🏠 ACO"')


def test_schema_contiene_campos_comerciales():
    src = (ROOT / "services" / "levantamientos_schema.py").read_text(encoding="utf-8")
    for campo in ("lev_validado_ventas", "lev_validado_por", "lev_fecha_validacion", "lev_cotizacion_json"):
        assert f'"{campo}"' in src


def test_migracion_crea_jsonb_y_estado_validacion():
    src = (ROOT / "migrations" / "20260819_cotizaciones_levantamientos.sql").read_text(encoding="utf-8").lower()
    assert "lev_cotizacion_json jsonb" in src
    assert "lev_validado_ventas boolean" in src


def test_extraccion_partidas_para_cotizacion():
    detalle = {
        "canalizacion_materiales": [
            {"categoria": "Tubo", "tipo": "IMC", "tamano": '1/2"', "cantidad": "10", "unidad": "Metro(s)"}
        ],
        "equipos_principales": [
            {"familia": "CCTV", "subfamilia": "Cámara", "cantidad": "2", "marca": "AX", "modelo": "X1"}
        ],
        "materiales_miscelaneos": [
            {"material": "Taquetes", "cantidad": "20", "unidad": "Pieza(s)"}
        ],
    }
    rows = partidas_desde_detalle_levantamiento(detalle)
    assert len(rows) == 3
    assert {x["_grupo"] for x in rows} == {"Materiales", "Equipos", "Misceláneos"}


def test_validacion_persiste_preautorizacion_despues_del_correo():
    src = (ROOT / "views" / "orden_servicio_conversion_view.py").read_text(encoding="utf-8")
    assert '"lev_validado_ventas": True' in src
    assert '"lev_validado_por"' in src
    assert '"lev_fecha_validacion"' in src
