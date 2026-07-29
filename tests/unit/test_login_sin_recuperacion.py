from pathlib import Path


def test_login_no_expone_recuperacion_de_password():
    contenido = Path("login.py").read_text(encoding="utf-8").lower()
    frases_retiradas = (
        "¿olvidaste tu contraseña?",
        "abrir_cambio_password",
        "restablecimiento seguro",
    )
    for frase in frases_retiradas:
        assert frase not in contenido
