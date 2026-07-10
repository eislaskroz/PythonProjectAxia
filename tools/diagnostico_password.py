"""Diagnóstico local para validar hashes bcrypt guardados en Supabase.

Uso:
    python tools/diagnostico_password.py

No modifica datos. Solo imprime longitud/formato de usu_password por usuario.
"""
from supabase_config import supabase, TABLA_USUARIOS
from security.passwords import es_hash_bcrypt

resp = supabase.table(TABLA_USUARIOS).select("id_usuario, usu_nickname, usu_password").execute()
for u in resp.data or []:
    pwd = u.get("usu_password") or ""
    print(
        f"{u.get('id_usuario')} | {u.get('usu_nickname')} | "
        f"len={len(pwd)} | bcrypt={es_hash_bcrypt(pwd)} | inicio={pwd[:7]}"
    )
