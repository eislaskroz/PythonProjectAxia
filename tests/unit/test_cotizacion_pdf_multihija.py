from pathlib import Path

from pypdf import PdfReader

from services.cotizacion_pdf import generar_pdf_cotizacion


def _sample_data(rows=80):
    partidas = []
    for i in range(rows):
        partidas.append({
            "lote": str(i + 1),
            "unidad_tipo": "Servicio",
            "cantidad": "1",
            "modelo": f"MOD-{i:03d}",
            "sku": f"SKU-{i:03d}",
            "marca": "AXIA",
            "concepto": f"Partida de prueba multi página número {i + 1} con descripción amplia",
            "precio_unitario": 100 + i,
            "importe": 100 + i,
            "observaciones": "OK",
        })
    subtotal = sum(100 + i for i in range(rows))
    return {
        "cot_folio": "COT-MULTI-01",
        "cot_cliente": "CLIENTE PRUEBA",
        "cot_asunto": "PRUEBA MULTI PAGINA",
        "cot_plan_pagos": "PPD",
        "cot_partidas_json": partidas,
        "cot_subtotal": subtotal,
        "cot_descuento_pct": 5,
        "cot_subtotal_descuento": subtotal * 0.95,
        "cot_iva_pct": 16,
        "cot_iva": subtotal * 0.152,
        "cot_total": subtotal * 1.102,
    }


def test_cotizacion_multipagina_repite_partidas_y_cierra_con_totales(tmp_path):
    ruta = generar_pdf_cotizacion(_sample_data(), tmp_path / "multi.pdf", abrir=False)
    reader = PdfReader(str(ruta))
    assert len(reader.pages) >= 2
    last_text = reader.pages[-1].extract_text() or ""
    assert "SUBTOTAL" in last_text
    assert "TOTAL" in last_text
    assert "COTIZACIÓN" in last_text


def test_totales_se_mantienen_compactos_en_codigo():
    codigo = (Path(__file__).resolve().parents[2] / "services" / "cotizacion_pdf.py").read_text("utf8")
    assert "CondPageBreak" in codigo
    assert "KeepTogether" in codigo
    assert "colWidths=[1.65 * inch, 1.30 * inch]" in codigo
