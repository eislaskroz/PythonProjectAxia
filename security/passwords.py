# =====================================================
# MÓDULO DE SEGURIDAD PARA CONTRASEÑAS
# =====================================================
"""
Este archivo centraliza todo lo relacionado con contraseñas.

Objetivo:
- Guardar nuevas contraseñas con bcrypt.
- Validar contraseñas existentes con bcrypt.
- Permitir migración automática desde SHA-256 heredado.
- Permitir migración automática desde texto plano heredado, si existiera.

IMPORTANTE:
Nunca se debe desencriptar una contraseña.
Las contraseñas se verifican comparando el texto capturado
contra el hash almacenado.
"""

import bcrypt
import hashlib
import re


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
    """
    Determina si el valor almacenado parece ser un hash bcrypt.

    Parámetro:
        password_guardado (str):
            Valor almacenado actualmente en la base de datos.

    Retorna:
        bool:
            True si parece bcrypt.
            False si no parece bcrypt.
    """

    if not password_guardado:
        return False

    return password_guardado.startswith(PREFIJOS_BCRYPT)


# =====================================================
# FUNCIÓN: es_hash_sha256()
# =====================================================
def es_hash_sha256(password_guardado):
    """
    Determina si el valor almacenado parece ser un hash SHA-256.
    """

    if not password_guardado:
        return False

    return bool(PATRON_SHA256.fullmatch(password_guardado))


# =====================================================
# FUNCIÓN: generar_hash_password()
# =====================================================
def generar_hash_password(password):
    """
    Genera un hash bcrypt para una contraseña nueva.

    Parámetro:
        password (str):
            Contraseña en texto plano capturada desde la UI.

    Retorna:
        str:
            Hash bcrypt listo para guardarse en Supabase.

    Notas:
        bcrypt.gensalt() genera una sal única por contraseña.
        Por eso, la misma contraseña nunca produce el mismo hash.
    """

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
    """
    Genera SHA-256 únicamente para comparar passwords antiguos.

    NO usar para guardar nuevas contraseñas.
    Se conserva para que los usuarios existentes puedan iniciar sesión
    y migrarse automáticamente a bcrypt.
    """

    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


# =====================================================
# FUNCIÓN: verificar_password()
# =====================================================
def verificar_password(password_plano, password_guardado):
    """
    Verifica si una contraseña capturada coincide con lo guardado.

    Soporta tres escenarios:
    1. bcrypt: formato actual recomendado.
    2. SHA-256: formato heredado de AXIA.
    3. Texto plano: formato heredado inseguro, solo para migración.

    Parámetros:
        password_plano (str):
            Contraseña que escribió el usuario.

        password_guardado (str):
            Valor actual en la columna usu_password.

    Retorna:
        bool:
            True si coincide.
            False si no coincide.
    """

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

    # =============================================
    # CASO 3: PASSWORD HEREDADO EN TEXTO PLANO
    # =============================================
    return password_plano == password_guardado


# =====================================================
# FUNCIÓN: requiere_migracion_a_bcrypt()
# =====================================================
def requiere_migracion_a_bcrypt(password_guardado):
    """
    Indica si una contraseña almacenada debe migrarse a bcrypt.

    Retorna True cuando:
    - está en SHA-256,
    - está en texto plano,
    - o no tiene formato bcrypt.
    """

    return not es_hash_bcrypt(password_guardado)
