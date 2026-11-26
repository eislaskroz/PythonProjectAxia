from io import BytesIO
from types import SimpleNamespace
import sys
import time
from unittest.mock import Mock
import pytest
from PIL import Image
from services import desktop_evidence_access as client
from services import levantamiento_seguridad_pdf as renderer
from services import sesion_axia_compartida as session
from app_context import obtener_usuario_actual

PATH = "LEV-00145/foto.jpg"
ITEM = {"bucket": "levantamientos-evidencias", "storage_path": PATH, "mime": "image/jpeg"}

@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setitem(sys.modules, "supabase_config", SimpleNamespace(SUPABASE_URL="https://example.supabase.co", SUPABASE_KEY="public-test"))
    monkeypatch.setitem(obtener_usuario_actual(), "id_usuario", 20)
    session.establecer_sesion("test-session", 20, int(time.time())+1000)
    monkeypatch.delenv("AXIA_DESKTOP_EVIDENCE_GRANT", raising=False)
    yield
    session.cerrar_sesion()


def test_authenticated_request_and_download(setup, monkeypatch):
    grant = "a"*64
    monkeypatch.setenv("AXIA_DESKTOP_EVIDENCE_GRANT", grant)
    signed = "https://example.supabase.co/storage/v1/object/sign/levantamientos-evidencias/LEV-00145/foto.jpg?token=test"
    post = Mock(return_value=SimpleNamespace(status_code=200, json=lambda: {"ok": True, "signedUrl": signed}))
    response = Mock(); response.status_code = 200; response.iter_content.return_value = [b"test", b"photo"]
    manager = Mock(); manager.__enter__ = Mock(return_value=response); manager.__exit__ = Mock(return_value=False)
    get = Mock(return_value=manager)
    monkeypatch.setattr(client.requests,"post",post); monkeypatch.setattr(client.requests,"get",get)
    assert client.descargar_evidencia_field(PATH) == b"testphoto"
    kwargs = post.call_args.kwargs
    assert kwargs["headers"]["Authorization"] == "Bearer test-session"
    assert kwargs["headers"]["apikey"] == "public-test"
    assert kwargs["headers"]["X-AXIA-Desktop-Grant"] == grant
    assert post.call_args.args[0].endswith("/desktop-evidence-access")
    assert "headers" not in get.call_args.kwargs


def test_no_session_no_network(setup, monkeypatch):
    session.cerrar_sesion()
    post=Mock(); monkeypatch.setattr(client.requests,"post",post)
    with pytest.raises(client.EvidenciaNoDisponible): client.descargar_evidencia_field(PATH)
    post.assert_not_called()


@pytest.mark.parametrize("status",[401,403,404,500])
def test_failed_request_no_fallback(setup, monkeypatch, status):
    post=Mock(return_value=SimpleNamespace(status_code=status)); get=Mock()
    monkeypatch.setattr(client.requests,"post",post); monkeypatch.setattr(client.requests,"get",get)
    with pytest.raises(client.EvidenciaNoDisponible): client.descargar_evidencia_field(PATH)
    get.assert_not_called()


def test_foreign_signed_url_denied(setup, monkeypatch):
    monkeypatch.setattr(client.requests,"post",Mock(return_value=SimpleNamespace(status_code=200,json=lambda:{"ok":True,"signedUrl":"https://foreign.example/foto"})))
    get=Mock();monkeypatch.setattr(client.requests,"get",get)
    with pytest.raises(client.EvidenciaNoDisponible): client.descargar_evidencia_field(PATH)
    get.assert_not_called()


def test_protected_render_aborts_before_writing(tmp_path, monkeypatch):
    original=tmp_path/"final.pdf";original.write_bytes(b"existing")
    monkeypatch.setattr(renderer,"descargar_evidencia_field",Mock(side_effect=client.EvidenciaNoDisponible("denied")))
    @renderer._validar_evidencias_field
    def render(*args,**kwargs): pytest.fail("Should not render")
    with pytest.raises(client.EvidenciaNoDisponible): render({"lev_evidencias_json":[ITEM]},ruta_salida=original)
    assert original.read_bytes()==b"existing"


def test_atomic_render_uses_cache(tmp_path, monkeypatch):
    buf=BytesIO();Image.new("RGB",(10,10),"blue").save(buf,"JPEG")
    fetch=Mock(return_value=buf.getvalue()); monkeypatch.setattr(renderer,"descargar_evidencia_field",fetch)
    @renderer._validar_evidencias_field
    def render(registro, *, ruta_salida, abrir=False):
        assert renderer._cargar_archivo_evidencia(ITEM)==buf.getvalue()
        ruta_salida.write_bytes(b"result")
    final=tmp_path/"final.pdf"
    assert render({"lev_evidencias_json":[ITEM]},ruta_salida=final)==str(final)
    assert final.read_bytes()==b"result";fetch.assert_called_once_with(PATH)


def test_actual_pdf_contains_photo(tmp_path, monkeypatch):
    from pypdf import PdfReader
    buf=BytesIO();Image.new("RGB",(20,20),"blue").save(buf,"JPEG")
    monkeypatch.setattr(renderer,"descargar_evidencia_field",Mock(return_value=buf.getvalue()))
    dest=tmp_path/"evidence.pdf"
    registro={"lev_folio":"LEV-00145","lev_tipo":11,"lev_tipo_levantamiento":"General","lev_cliente":"Demo","lev_descripcion":"Prueba","lev_evidencias_json":[ITEM]}
    renderer.generar_pdf_levantamiento_maestro(registro,ruta_salida=dest,abrir=False)
    reader=PdfReader(dest)
    assert any("evidencia fotográfica" in (p.extract_text() or "").casefold() for p in reader.pages)
    # PDF includes the blue mock photo as a 20x20 XObject (distinct from page background/logo).
    assert any(any(obj.get_object().get("/Width")==20 and obj.get_object().get("/Height")==20 for obj in (page.get("/Resources") or {}).get("/XObject",{}).get_object().values()) for page in reader.pages if (page.get("/Resources") or {}).get("/XObject"))
