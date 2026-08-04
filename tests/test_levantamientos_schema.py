from services.levantamientos_schema import (
    COLUMNAS_LEVANTAMIENTOS_SET,
    CAMPOS_CONVERSION_EDITABLES,
    filtrar_payload_levantamiento,
)


def test_contrato_levantamientos_no_contiene_columnas_legacy():
    assert "lev_fecha" not in COLUMNAS_LEVANTAMIENTOS_SET
    assert "lev_firma" not in COLUMNAS_LEVANTAMIENTOS_SET
    assert "lev_motivo" not in COLUMNAS_LEVANTAMIENTOS_SET
    assert "lev_fecha_realizacion" in COLUMNAS_LEVANTAMIENTOS_SET
    assert "lev_firma_cliente" in COLUMNAS_LEVANTAMIENTOS_SET


def test_alias_lev_fecha_se_normaliza_sin_enviarse_a_supabase():
    payload = filtrar_payload_levantamiento({"lev_fecha": "2026-08-15", "campo_inexistente": 1})
    assert payload == {"lev_fecha_realizacion": "2026-08-15"}


def test_conversion_solo_admite_campos_reales_y_autorizados():
    payload = filtrar_payload_levantamiento(
        {
            "lev_cliente": "AXIA",
            "lev_fecha": "2026-08-15",
            "lev_folio": "NO-DEBE-CAMBIAR",
            "fecha_registro": "NO-DEBE-CAMBIAR",
            "inventado": "NO",
        },
        campos_permitidos=CAMPOS_CONVERSION_EDITABLES,
    )
    assert payload == {
        "lev_cliente": "AXIA",
        "lev_fecha_realizacion": "2026-08-15",
    }
