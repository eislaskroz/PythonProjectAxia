from pathlib import Path

import services.mail_service as mail


class DummyResponse:
    ok = True
    status_code = 200
    text = '{"ok":true}'
    def json(self):
        return {"ok": True, "requestId": "test-123"}


def test_mail_uses_relay_without_smtp(monkeypatch, tmp_path: Path):
    pdf = tmp_path / "LEV-00001.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF")
    captured = {}

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "public-anon-key")
    monkeypatch.setenv("AXIA_MAIL_ENABLED", "1")
    monkeypatch.delenv("AXIA_MAIL_RELAY_URL", raising=False)

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return DummyResponse()

    monkeypatch.setattr(mail.requests, "post", fake_post)
    result = mail.enviar_correo(
        subject="Prueba", body="Contenido", attachments=[pdf],
        to=["gte.ventas@axiacomunicaciones.mx"], flow="levantamiento_registrado",
    )
    assert result.sent is True
    assert captured["url"].endswith("/functions/v1/axia-mail-relay")
    assert captured["json"]["attachments"][0]["contentBase64"]
    assert "smtp" not in str(captured).lower()
