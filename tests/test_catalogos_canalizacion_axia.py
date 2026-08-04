from views.levantamientos.catalogos_canalizacion import (
    CALIBRES_CABLE_ELECTRICO,
    TAMANOS_TUBOS,
    TIPOS_ABRAZADERAS,
    TIPOS_CABLE_ELECTRICO,
    TIPOS_CONECTORES,
    TIPOS_COPLES,
    TIPOS_REGISTROS,
    TIPOS_TUBOS,
    TIPOS_TUBOS_CON_TAMANO,
)


def test_catalogos_axia_contienen_valores_entregados():
    assert "Opresor" in TIPOS_COPLES
    assert "Ducto Polietileno Alta Densidad" in TIPOS_COPLES
    assert "Pared delgada (EMT)" in TIPOS_TUBOS
    assert "Resina termoendurecible reforzada (RTRC)" in TIPOS_TUBOS
    assert '2" 1/2" (63mm)' in TAMANOS_TUBOS
    assert "Cajas Condulets (LB, LL, LR, C, T)" in TIPOS_REGISTROS
    assert "Presión o empalme rápido (Wago)" in TIPOS_CONECTORES
    assert "Tipo P" in TIPOS_ABRAZADERAS
    assert "SJT (Uso rudo)" in TIPOS_CABLE_ELECTRICO
    assert "8 AWG (Hasta 40A)" in CALIBRES_CABLE_ELECTRICO


def test_tubos_combinan_tipo_y_tamano_para_el_control_actual():
    assert len(TIPOS_TUBOS_CON_TAMANO) == len(TIPOS_TUBOS) * len(TAMANOS_TUBOS)
    assert 'Pared delgada (EMT) — 1/2" (13mm)' in TIPOS_TUBOS_CON_TAMANO
