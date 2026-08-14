from pathlib import Path

from services import mail_service


def _configurar_env(monkeypatch):
    monkeypatch.setenv("AXIA_MAIL_ENABLED", "1")
    monkeypatch.setenv("AXIA_MAIL_FROM", "levantamientos@axiacomunicaciones.mx")
    monkeypatch.setenv("AXIA_MAIL_TO", "mmachuca@axiacomunicaciones.mx")
    monkeypatch.setenv("AXIA_MAIL_CC", "desarrollo.01@axiacomunicaciones.mx")
    monkeypatch.setenv("AXIA_SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("AXIA_SMTP_PORT", "587")
    monkeypatch.setenv("AXIA_SMTP_USER", "levantamientos@axiacomunicaciones.mx")
    monkeypatch.setenv("AXIA_SMTP_PASSWORD", "secret")
    monkeypatch.setenv("AXIA_SMTP_SSL", "0")
    monkeypatch.setenv("AXIA_SMTP_STARTTLS", "1")


class FakeSMTP:
    last = None

    def __init__(self, host, port, timeout=None, **kwargs):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.logged = None
        self.sent = None
        self.started_tls = False
        FakeSMTP.last = self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def ehlo(self):
        return None

    def starttls(self, context=None):
        self.started_tls = True

    def login(self, user, password):
        self.logged = (user, password)

    def send_message(self, msg, from_addr=None, to_addrs=None):
        self.sent = (msg, from_addr, to_addrs)


def test_env_de_destinatarios_axia(monkeypatch):
    _configurar_env(monkeypatch)
    config = mail_service._mail_config()
    assert config["sender"] == "levantamientos@axiacomunicaciones.mx"
    assert config["to"] == ["mmachuca@axiacomunicaciones.mx"]
    assert config["cc"] == ["desarrollo.01@axiacomunicaciones.mx"]


def test_envia_pdf_de_levantamiento_con_cc(monkeypatch, tmp_path):
    _configurar_env(monkeypatch)
    monkeypatch.setattr(mail_service.smtplib, "SMTP", FakeSMTP)
    pdf = tmp_path / "AXIA_LEV-00001.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF")
    registro = {
        "lev_folio": "LEV-00001",
        "lev_cliente": "GAFSACOM",
        "lev_tipo_levantamiento": "Tecnología, Equipos y Periféricos",
        "lev_modalidad_operativa": "Instalación",
        "lev_fecha_programada": "2026-08-19",
        "lev_tecnico": "Técnico AXIA",
    }
    result = mail_service.enviar_levantamiento_pdf(registro, pdf, usuario="admin")
    assert result.sent is True
    smtp = FakeSMTP.last
    assert smtp.started_tls is True
    msg, from_addr, to_addrs = smtp.sent
    assert from_addr == "levantamientos@axiacomunicaciones.mx"
    assert "mmachuca@axiacomunicaciones.mx" in to_addrs
    assert "desarrollo.01@axiacomunicaciones.mx" in to_addrs
    assert "LEV-00001" in msg["Subject"]
    assert any(part.get_filename() == "AXIA_LEV-00001.pdf" for part in msg.iter_attachments())


def test_falla_smtp_no_lanza_excepcion(monkeypatch, tmp_path):
    _configurar_env(monkeypatch)

    class BrokenSMTP:
        def __init__(self, *args, **kwargs):
            raise OSError("sin red")

    monkeypatch.setattr(mail_service.smtplib, "SMTP", BrokenSMTP)
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"pdf")
    result = mail_service.enviar_levantamiento_pdf({"lev_folio": "LEV-9"}, pdf)
    assert result.sent is False
    assert result.status == "SEND_ERROR"
