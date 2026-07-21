"""Limitación local de intentos de acceso para reducir fuerza bruta."""
from __future__ import annotations
import json, os, time
from pathlib import Path
from core.app_paths import user_data_dir
from core.logger import configurar_logger
logger = configurar_logger(__name__)
_FILE = user_data_dir() / "login_guard.json"

def _settings():
    try: max_attempts=max(3,int(os.getenv("AXIA_LOGIN_MAX_ATTEMPTS","5")))
    except ValueError: max_attempts=5
    try: lock_minutes=max(1,int(os.getenv("AXIA_LOGIN_LOCK_MINUTES","15")))
    except ValueError: lock_minutes=15
    return max_attempts, lock_minutes

def _load():
    try: return json.loads(_FILE.read_text(encoding="utf-8")) if _FILE.exists() else {}
    except Exception:
        logger.warning("No se pudo leer login_guard; se reinicia.", exc_info=True); return {}

def _save(data):
    tmp=_FILE.with_suffix('.tmp'); tmp.write_text(json.dumps(data),encoding='utf-8'); tmp.replace(_FILE)

def estado(nickname):
    key=str(nickname or '').strip().casefold(); data=_load(); item=data.get(key,{})
    until=float(item.get('locked_until',0) or 0); remaining=max(0,int(until-time.time()))
    if remaining<=0 and until:
        data.pop(key,None); _save(data)
    return remaining

def registrar_fallo(nickname):
    key=str(nickname or '').strip().casefold(); data=_load(); item=data.get(key,{})
    attempts=int(item.get('attempts',0))+1; maximum,minutes=_settings(); item={'attempts':attempts,'locked_until':0}
    if attempts>=maximum: item={'attempts':0,'locked_until':time.time()+minutes*60}
    data[key]=item; _save(data); return estado(nickname)

def registrar_exito(nickname):
    key=str(nickname or '').strip().casefold(); data=_load()
    if key in data: data.pop(key,None); _save(data)
