
from core.logger import configurar_logger

logger = configurar_logger(__name__)
import os
from cryptography.fernet import Fernet
import security.data_encryption as encryption

def test_cifrado_y_descifrado(monkeypatch):
    monkeypatch.setenv("AXIA_DATA_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("AXIA_REQUIRE_ENCRYPTION", "1")
    monkeypatch.setenv("AXIA_AUTO_PROVISION_DEV_KEY", "0")
    encryption._obtener_fernet.cache_clear()
    cifrado = encryption.cifrar_valor("dato sensible")
    assert cifrado.startswith(encryption.PREFIX)
    assert encryption.descifrar_valor(cifrado) == "dato sensible"

def test_sin_llave_falla_cerrado(monkeypatch):
    monkeypatch.delenv("AXIA_DATA_KEY", raising=False)
    monkeypatch.setenv("AXIA_REQUIRE_ENCRYPTION", "1")
    monkeypatch.setenv("AXIA_AUTO_PROVISION_DEV_KEY", "0")
    monkeypatch.setattr(encryption, "aprovisionar_clave_desarrollo", lambda: None)
    encryption._obtener_fernet.cache_clear()
    try:
        encryption.cifrar_valor("dato")
    except encryption.EncryptionConfigurationError:
        logger.debug("Excepción recuperable controlada.", exc_info=True)
    else:
        raise AssertionError("El cifrado obligatorio no debe fallar abierto")
