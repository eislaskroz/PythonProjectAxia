from services.axia_pdf_blocks import (
    AxiaPdfDocument,
    DataTableBlock,
    GeneralDataBlock,
    SignatureBlock,
    TechnicalDetailBlock,
)
from services.axia_pdf_engine import AxiaPdfEngine


def test_documento_legacy_se_convierte_en_bloques():
    request = AxiaPdfEngine.prepare(
        titulo="Levantamiento",
        datos={"Folio LEV": "LEV-1", "Detalle técnico": "--- RED ---\nCable: UTP"},
        secciones_tabla=[("Equipos", ["Marca"], [{"Marca": "AXIA"}])],
        mostrar_firmas=False,
    )
    assert len(request.document.blocks_of(GeneralDataBlock)) == 1
    assert len(request.document.blocks_of(TechnicalDetailBlock)) == 1
    assert len(request.document.blocks_of(DataTableBlock)) == 1
    assert len(request.document.blocks_of(SignatureBlock)) == 1


def test_bloques_regresan_al_contrato_corporativo():
    document = AxiaPdfDocument(
        title="Prueba",
        blocks=(
            GeneralDataBlock({"Cliente": "AXIA"}),
            TechnicalDetailBlock("--- SERVICIO ---\nDescripción: Prueba"),
            DataTableBlock("Materiales", ["Material"], [{"Material": "Cable"}]),
            SignatureBlock(visible=True),
        ),
    )
    legacy = document.to_legacy()
    assert legacy["datos"]["Cliente"] == "AXIA"
    assert "SERVICIO" in legacy["datos"]["Detalle técnico"]
    assert legacy["secciones_tabla"][0][0] == "Materiales"
    assert legacy["mostrar_firmas"] is True


def test_prepare_document_es_api_nativa_fase4():
    request = AxiaPdfEngine.prepare_document(
        titulo="Orden de trabajo",
        bloques=[GeneralDataBlock({"Folio OT": "OT-1"}), SignatureBlock(visible=True)],
    )
    assert request.titulo == "Orden de trabajo"
    assert request.datos["Folio OT"] == "OT-1"
    assert request.mostrar_firmas is True


def test_bloques_congelan_datos_mutables():
    source = {"Cliente": "AXIA", "Lista": [{"A": 1}]}
    block = GeneralDataBlock(source)
    source["Cliente"] = "CAMBIADO"
    source["Lista"][0]["A"] = 2
    assert block.values["Cliente"] == "AXIA"
    assert block.values["Lista"][0]["A"] == 1
