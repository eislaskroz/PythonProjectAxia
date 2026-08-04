import json

from services.axia_pdf_engine import AxiaPdfEngine
from services.pdf_registro_service import _construir_datos


def test_materiales_y_equipos_se_convierten_en_tablas_pdf():
    registro = {
        "lev_folio": "LEV-00999",
        "lev_cliente": "CLIENTE PRUEBA",
        "lev_detalle_tecnico_json": json.dumps({
            "alcance": {"tipo": "Instalación"},
            "equipos_principales": [
                {
                    "familia": "Cámara",
                    "subfamilia": "Bala",
                    "cantidad": "2",
                    "marca": "AXIA",
                    "modelo": "TEST",
                    "caracteristicas": "Exterior",
                }
            ],
            "materiales_miscelaneos": [
                {
                    "material": "Taquetes",
                    "categoria": "Fijación",
                    "cantidad": "20",
                    "unidad": "Pieza",
                    "especificacion": "1/4",
                }
            ],
        }, ensure_ascii=False),
    }
    datos, _ = _construir_datos(registro, {"campo_folio": "lev_folio"})
    request = AxiaPdfEngine.prepare_profile(
        profile_key="registro_generico",
        data={**datos, "_titulo_pdf": "Levantamiento", "_folio": "LEV-00999"},
    )
    tablas = request.secciones_tabla
    assert [tabla[0] for tabla in tablas] == [
        "Equipos principales requeridos",
        "Materiales misceláneos y consumibles",
    ]
    assert tablas[0][2][0]["Familia"] == "Cámara"
    assert tablas[1][2][0]["Material"] == "Taquetes"
    assert "Elemento 1" not in request.datos.get("Detalle técnico", "")
