"""
Genera una llave Fernet para AXIA_DATA_KEY.

Uso:
    python generar_clave_cifrado.py

Después copia el resultado en tu archivo .env:
    AXIA_DATA_KEY=...
"""

from cryptography.fernet import Fernet

print(Fernet.generate_key().decode())
