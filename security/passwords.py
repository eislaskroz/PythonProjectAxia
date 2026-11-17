# =====================================================
# MÓDULO DE SEGURIDAD PARA CONTRASEÑAS
# =====================================================
import bcrypt
import hashlib
import re
import os
import hmac


# =====================================================
# CONSTANTES DE IDENTIFICACIÓN
# =====================================================

# Un hash SHA-256 en hexadecimal siempre tiene 64 caracteres.
PATRON_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")

# Los hashes bcrypt normalmente inician con alguno de estos prefijos.
PREFIJOS_BCRYPT = (
    "$2a$",
    "$2b$",
    "$2y$"
)


# =====================================================
# FUNCIÓN: es_hash_bcrypt()
# =====================================================
def es_hash_bcrypt(password_guardado):
    if not password_guardado:
        return False

    return password_guardado.startswith(PREFIJOS_BCRYPT)


# =====================================================
# FUNCIÓN: es_hash_sha256()
# =====================================================
def es_hash_sha256(password_guardado):
    if not password_guardado:
        return False

    return bool(PATRON_SHA256.fullmatch(password_guardado))


# =====================================================
# FUNCIÓN: generar_hash_password()
# =====================================================
def generar_hash_password(password):
    if password is None:
        raise ValueError("La contraseña no puede ser None")

    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password_bytes, salt)

    return password_hash.decode("utf-8")


# =====================================================
# FUNCIÓN: generar_hash_sha256_legacy()
# =====================================================
def generar_hash_sha256_legacy(password):
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


# =====================================================
# FUNCIÓN: verificar_password()
# =====================================================
def verificar_password(password_plano, password_guardado):
    if not password_plano or not password_guardado:
        return False

    # =============================================
    # CASO 1: PASSWORD GUARDADO CON BCRYPT
    # =============================================
    if es_hash_bcrypt(password_guardado):
        try:
            return bcrypt.checkpw(
                password_plano.encode("utf-8"),
                password_guardado.encode("utf-8")
            )
        except ValueError:
            return False

    # =============================================
    # CASO 2: PASSWORD HEREDADO CON SHA-256
    # =============================================
    if es_hash_sha256(password_guardado):
        return generar_hash_sha256_legacy(password_plano) == password_guardado

    # CASO 3: texto plano heredado. Deshabilitado por defecto.
    permitir_plano = os.getenv("AXIA_ALLOW_LEGACY_PLAINTEXT_PASSWORDS", "0").strip().lower() in {"1", "true", "yes"}
    return permitir_plano and hmac.compare_digest(password_plano, password_guardado)


# =====================================================
# FUNCIÓN: requiere_migracion_a_bcrypt()
# =====================================================
def requiere_migracion_a_bcrypt(password_guardado):
    return not es_hash_bcrypt(password_guardado)


def validar_fortaleza_password(password: str) -> tuple[bool, str]:
    password = str(password or "")
    if len(password) < 10:
        return False, "La contraseña debe tener al menos 10 caracteres."
    if not re.search(r"[A-Z]", password):
        return False, "La contraseña debe incluir una letra mayúscula."
    if not re.search(r"[a-z]", password):
        return False, "La contraseña debe incluir una letra minúscula."
    if not re.search(r"\d", password):
        return False, "La contraseña debe incluir un número."
    if not re.search(r"[^A-Za-z0-9]", password):
        return False, "La contraseña debe incluir un carácter especial."
    return True, "Contraseña válida."