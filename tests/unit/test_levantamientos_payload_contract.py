from pathlib import Path


SOURCE = Path(__file__).resolve().parents[2] / "views" / "levantamiento_view.py"


def _source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_seguridad_monitoreo_persiste_resumen_y_detalle_tecnico() -> None:
    source = _source()
    assert 'if resumen_cctv:' in source
    assert 'requerimientos = f"{requerimientos}\\n{resumen_cctv}".strip()' in source
    assert '"lev_requerimientos": requerimientos' in source
    assert '"lev_detalle_tecnico_json": json.dumps(detalle_tecnico, ensure_ascii=False)' in source


def test_redes_voz_datos_persiste_resumen_y_detalle_tecnico() -> None:
    source = _source()
    assert 'elif resumen_rvd:' in source
    assert 'requerimientos = f"{requerimientos}\\n{resumen_rvd}".strip()' in source
    assert 'Tipo específico de levantamiento: Redes Voz y Datos / Instalación' in source
    assert '"lev_requerimientos": requerimientos' in source
    assert '"lev_detalle_tecnico_json": json.dumps(detalle_tecnico, ensure_ascii=False)' in source


def test_redes_no_reintroduce_consumibles_adicionales() -> None:
    source = _source()
    assert 'var_rvd_consumibles' not in source
