from dataclasses import replace
from pathlib import Path

from services.axia_pdf_engine import AxiaPdfEngine, AxiaPdfRequest


def test_prepare_crea_instantanea_de_datos():
    datos = {"Folio": "LEV-1", "Cliente": "AXIA"}
    request = AxiaPdfEngine.prepare(titulo="Levantamiento", datos=datos)
    datos["Cliente"] = "MODIFICADO"
    assert request.datos["Cliente"] == "AXIA"


def test_preview_y_save_conservan_mismo_contenido(monkeypatch, tmp_path):
    capturadas = []

    def render_falso(cls, request):
        capturadas.append(request)
        return str(request.ruta_salida)

    monkeypatch.setattr(AxiaPdfEngine, "render", classmethod(render_falso))
    request = AxiaPdfEngine.prepare(
        titulo="Levantamiento Seguridad y Monitoreo",
        datos={"Folio": "LEV-00001", "Cliente": "AXIA"},
        mostrar_firmas=True,
    )

    AxiaPdfEngine.preview_request(request)
    AxiaPdfEngine.save_request(request, tmp_path / "AXIA_LEV-00001.pdf")

    assert len(capturadas) == 2
    preview, definitivo = capturadas
    assert preview.titulo == definitivo.titulo
    assert preview.datos == definitivo.datos
    assert preview.secciones_tabla == definitivo.secciones_tabla
    assert preview.mostrar_firmas == definitivo.mostrar_firmas
    assert preview.abrir is True
    assert definitivo.abrir is False
    assert preview.ruta_salida != definitivo.ruta_salida


def test_render_rechaza_solicitud_invalida():
    try:
        AxiaPdfEngine.render({})
    except TypeError as error:
        assert "AxiaPdfRequest" in str(error)
    else:
        raise AssertionError("Se esperaba TypeError")


def test_generate_fase1_delega_a_preview(monkeypatch):
    llamada = {}

    def preview_falso(cls, titulo, datos, **kwargs):
        llamada.update(titulo=titulo, datos=datos, kwargs=kwargs)
        return "preview.pdf"

    monkeypatch.setattr(AxiaPdfEngine, "preview", classmethod(preview_falso))
    resultado = AxiaPdfEngine.generate(titulo="Prueba", datos={"A": 1})
    assert resultado == "preview.pdf"
    assert llamada["titulo"] == "Prueba"
    assert llamada["datos"] == {"A": 1}
