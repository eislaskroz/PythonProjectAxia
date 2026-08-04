import pytest

from services.axia_pdf_blocks import GeneralDataBlock, SignatureBlock, TechnicalDetailBlock
from services.axia_pdf_engine import AxiaPdfEngine
from services.axia_pdf_profiles import (
    AxiaPdfProfile,
    AxiaPdfProfileRegistry,
    FieldSpec,
    TableSpec,
)


def test_perfil_declarativo_construye_documento():
    profile = AxiaPdfProfile(
        key="prueba_f5",
        title="Levantamiento AXIA",
        general_fields=(
            FieldSpec("Folio", "folio", required=True),
            FieldSpec("Cliente", "cliente"),
        ),
        detail_source="detalle",
        show_signatures=False,
    )
    AxiaPdfProfileRegistry.register(profile, replace=True)
    request = AxiaPdfEngine.prepare_profile(
        profile_key="prueba_f5",
        data={"folio": "LEV-1", "cliente": "AXIA", "detalle": "Servicio"},
    )
    assert request.titulo == "Levantamiento AXIA"
    assert request.datos["Folio"] == "LEV-1"
    assert len(request.document.blocks_of(GeneralDataBlock)) == 1
    assert len(request.document.blocks_of(TechnicalDetailBlock)) == 1
    assert request.document.blocks_of(SignatureBlock)[0].visible is False


def test_perfil_valida_campos_obligatorios():
    profile = AxiaPdfProfile(
        key="requerido_f5",
        title="Documento",
        general_fields=(FieldSpec("Folio", "folio", required=True),),
    )
    AxiaPdfProfileRegistry.register(profile, replace=True)
    with pytest.raises(ValueError, match="Folio"):
        AxiaPdfEngine.prepare_profile(profile_key="requerido_f5", data={})


def test_tablas_declarativas_se_omiten_si_estan_vacias():
    profile = AxiaPdfProfile(
        key="tabla_f5",
        title="Documento",
        tables=(TableSpec("Materiales", ("Material",), "materiales"),),
    )
    AxiaPdfProfileRegistry.register(profile, replace=True)
    request = AxiaPdfEngine.prepare_profile(profile_key="tabla_f5", data={"materiales": []})
    assert request.secciones_tabla == []


def test_registro_impide_duplicados_sin_replace():
    profile = AxiaPdfProfile(key="duplicado_f5", title="Documento")
    AxiaPdfProfileRegistry.register(profile, replace=True)
    with pytest.raises(ValueError, match="ya existe"):
        AxiaPdfProfileRegistry.register(profile)


def test_perfil_generico_integrado_en_pdf_registro():
    request = AxiaPdfEngine.prepare_profile(
        profile_key="registro_generico",
        data={
            "_titulo_pdf": "Levantamientos",
            "_folio": "LEV-9",
            "Cliente": "ASCENDUM",
            "Detalle técnico": "--- SERVICIO ---\nPrueba",
            "_mostrar_firmas": False,
        },
    )
    assert request.titulo == "Levantamientos"
    assert request.datos["Folio"] == "LEV-9"
    assert request.datos["Cliente"] == "ASCENDUM"
    assert request.mostrar_firmas is False


def test_registro_guardado_normaliza_folio_y_fecha_para_encabezado():
    from services.pdf_registro_service import _construir_datos, _titulo_y_folio

    registro = {
        "lev_folio": "LEV-00042",
        "lev_fecha_programada": "2026-08-14",
        "lev_cliente": "AXIA",
    }
    datos, _ = _construir_datos(registro, {"campo_folio": "lev_folio"})
    titulo, folio = _titulo_y_folio(
        registro, {"titulo_pdf": "Levantamientos", "campo_folio": "lev_folio"}
    )
    request = AxiaPdfEngine.prepare_profile(
        profile_key="registro_generico",
        data={**datos, "_titulo_pdf": titulo, "_folio": folio, "_mostrar_firmas": False},
    )

    assert request.datos["Folio"] == "LEV-00042"
    assert request.datos["Fecha"] == "2026-08-14"


def test_fecha_registro_es_respaldo_para_pdf_administrativo():
    from services.pdf_registro_service import _construir_datos

    datos, _ = _construir_datos(
        {"lev_folio": "LEV-00043", "fecha_registro": "2026-08-03T15:31:57+00:00"},
        {"campo_folio": "lev_folio"},
    )
    assert datos["Fecha"] == "2026-08-03T15:31:57+00:00"
