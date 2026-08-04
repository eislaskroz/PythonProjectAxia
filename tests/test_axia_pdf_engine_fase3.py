from pathlib import Path

from services.axia_pdf_artifacts import AxiaPdfArtifactStore, sha256_file


def test_registro_y_exportacion_conservan_bytes(monkeypatch, tmp_path):
    registry = tmp_path / "pdf_engine" / "artifacts.json"
    monkeypatch.setattr(
        "services.axia_pdf_artifacts._registry_path", lambda: registry
    )

    original = tmp_path / "AXIA_LEV-00001.pdf"
    original.write_bytes(b"%PDF-1.4\nAXIA-CANONICAL\n%%EOF")
    artifact = AxiaPdfArtifactStore.register("LEV-00001", original)

    destino = tmp_path / "descargas" / "AXIA_LEV-00001.pdf"
    exported = AxiaPdfArtifactStore.export_exact("LEV-00001", destino)

    assert exported == destino
    assert destino.read_bytes() == original.read_bytes()
    assert sha256_file(destino) == artifact.sha256


def test_artefacto_modificado_no_se_reutiliza(monkeypatch, tmp_path):
    registry = tmp_path / "pdf_engine" / "artifacts.json"
    monkeypatch.setattr(
        "services.axia_pdf_artifacts._registry_path", lambda: registry
    )

    original = tmp_path / "AXIA_LEV-00002.pdf"
    original.write_bytes(b"PDF ORIGINAL")
    AxiaPdfArtifactStore.register("LEV-00002", original)
    original.write_bytes(b"PDF ALTERADO")

    assert AxiaPdfArtifactStore.find("LEV-00002") is None
    assert AxiaPdfArtifactStore.export_exact("LEV-00002", tmp_path / "copia.pdf") is None


def test_clave_de_folio_se_normaliza(monkeypatch, tmp_path):
    registry = tmp_path / "pdf_engine" / "artifacts.json"
    monkeypatch.setattr(
        "services.axia_pdf_artifacts._registry_path", lambda: registry
    )

    original = tmp_path / "documento.pdf"
    original.write_bytes(b"PDF")
    AxiaPdfArtifactStore.register(" lev-00003 ", original)

    assert AxiaPdfArtifactStore.find("LEV-00003") is not None


def test_artefacto_de_version_anterior_se_regenera(monkeypatch, tmp_path):
    import json
    from services.axia_pdf_artifacts import PDF_RENDERER_VERSION

    registry = tmp_path / "pdf_engine" / "artifacts.json"
    registry.parent.mkdir(parents=True)
    original = tmp_path / "AXIA_LEV-00004.pdf"
    original.write_bytes(b"PDF ANTIGUO")
    registry.write_text(json.dumps({
        "version": 1,
        "artifacts": {
            "LEV-00004": {
                "path": str(original),
                "sha256": sha256_file(original),
                "size": original.stat().st_size,
                "created_at": "2026-08-03T00:00:00+00:00",
                "renderer_version": PDF_RENDERER_VERSION - 1,
            }
        },
    }), encoding="utf-8")
    monkeypatch.setattr("services.axia_pdf_artifacts._registry_path", lambda: registry)

    assert AxiaPdfArtifactStore.find(
        "LEV-00004", min_renderer_version=PDF_RENDERER_VERSION
    ) is None
