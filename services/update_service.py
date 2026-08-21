"""Servicio de actualización de AXIA.

La aplicación consulta metadatos de versión en Supabase y descarga un
instalador firmado/publicado por AXIA. El instalador Inno conserva el mismo
AppId, por lo que actualiza la instalación existente sin desinstalarla.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import requests

from core.app_paths import executable_dir, user_data_dir
from core.logger import configurar_logger
from core.version import APP_VERSION, es_version_mas_nueva

logger = configurar_logger(__name__)

TABLA_ACTUALIZACIONES = "db_actualizaciones"


@dataclass(frozen=True)
class ActualizacionDisponible:
    version: str
    url: str
    sha256: str
    obligatoria: bool
    notas: str
    canal: str
    fecha_publicacion: str


def actualizaciones_habilitadas() -> bool:
    valor = os.getenv("AXIA_UPDATE_CHECK_ENABLED", "true").strip().lower()
    return valor not in {"0", "false", "no", "off"}


def canal_actualizaciones() -> str:
    return (os.getenv("AXIA_UPDATE_CHANNEL", "stable") or "stable").strip().lower()


def obtener_actualizacion_disponible() -> ActualizacionDisponible | None:
    """Devuelve la versión activa más reciente si supera la instalada.

    Cualquier fallo de red/esquema se considera no crítico: AXIA sigue
    funcionando y deja el detalle en logs.
    """
    if not actualizaciones_habilitadas():
        return None

    try:
        from supabase_config import supabase

        canal = canal_actualizaciones()
        respuesta = (
            supabase.table(TABLA_ACTUALIZACIONES)
            .select(
                "act_version,act_url,act_sha256,act_obligatoria,act_notas,"
                "act_canal,act_fecha_publicacion"
            )
            .eq("act_activa", True)
            .eq("act_canal", canal)
            .order("act_fecha_publicacion", desc=True)
            .limit(20)
            .execute()
        )
        filas = respuesta.data or []
        candidatas = [
            fila for fila in filas
            if es_version_mas_nueva(str(fila.get("act_version") or ""), APP_VERSION)
        ]
        if not candidatas:
            return None
        # La consulta viene ordenada por fecha de publicación; tomamos la más
        # reciente que sea superior a la versión instalada.
        fila = candidatas[0]
        url = str(fila.get("act_url") or "").strip()
        version = str(fila.get("act_version") or "").strip()
        if not url.lower().startswith(("https://", "http://")):
            logger.warning("Actualización %s ignorada: URL inválida.", version)
            return None
        return ActualizacionDisponible(
            version=version,
            url=url,
            sha256=str(fila.get("act_sha256") or "").strip().lower(),
            obligatoria=bool(fila.get("act_obligatoria")),
            notas=str(fila.get("act_notas") or "").strip(),
            canal=str(fila.get("act_canal") or canal),
            fecha_publicacion=str(fila.get("act_fecha_publicacion") or ""),
        )
    except Exception:
        logger.exception("No fue posible comprobar actualizaciones de AXIA.")
        return None


def _ruta_instalador(version: str) -> Path:
    limpia = "".join(c if c.isalnum() or c in ".-_" else "_" for c in version)
    carpeta = user_data_dir() / "updates"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta / f"AXIA_Setup_{limpia}.exe"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for bloque in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest().lower()


def descargar_actualizacion(actualizacion: ActualizacionDisponible) -> Path:
    """Descarga y valida el instalador de una actualización."""
    destino = _ruta_instalador(actualizacion.version)
    temporal = destino.with_suffix(".download")
    try:
        with requests.get(actualizacion.url, stream=True, timeout=(10, 120)) as respuesta:
            respuesta.raise_for_status()
            with temporal.open("wb") as fh:
                for bloque in respuesta.iter_content(chunk_size=1024 * 512):
                    if bloque:
                        fh.write(bloque)
        if temporal.stat().st_size < 1024:
            raise RuntimeError("El instalador descargado está vacío o incompleto.")
        if actualizacion.sha256:
            obtenido = _sha256(temporal)
            if obtenido != actualizacion.sha256:
                raise RuntimeError(
                    "La firma SHA-256 del instalador no coincide con la publicada. "
                    "La actualización fue cancelada."
                )
        temporal.replace(destino)
        logger.info("Actualización AXIA %s descargada en %s", actualizacion.version, destino)
        return destino
    finally:
        try:
            if temporal.exists():
                temporal.unlink()
        except Exception:
            logger.debug("No fue posible limpiar el temporal de actualización.", exc_info=True)


def programar_instalacion(instalador: Path) -> Path:
    """Lanza un proceso externo que actualiza AXIA después de cerrar la app.

    El archivo CMD vive en LocalAppData, por lo que no es reemplazado durante
    la actualización de Program Files. Al terminar, vuelve a abrir AXIA.
    """
    instalador = Path(instalador).resolve()
    app_exe = executable_dir() / "AXIA.exe"
    if not instalador.is_file():
        raise FileNotFoundError(f"No existe el instalador: {instalador}")

    carpeta = user_data_dir() / "updates"
    carpeta.mkdir(parents=True, exist_ok=True)
    cmd_path = carpeta / "aplicar_actualizacion.cmd"
    contenido = (
        "@echo off\r\n"
        "setlocal\r\n"
        "timeout /t 2 /nobreak >nul\r\n"
        f'start "" /wait "{instalador}" /VERYSILENT /SP- /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS\r\n'
        "if errorlevel 1 exit /b %errorlevel%\r\n"
        f'if exist "{app_exe}" start "" "{app_exe}"\r\n'
        'del "%~f0"\r\n'
    )
    cmd_path.write_text(contenido, encoding="utf-8")

    kwargs = {"cwd": str(carpeta)}
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    subprocess.Popen(["cmd.exe", "/c", str(cmd_path)], **kwargs)
    logger.info("Instalación de actualización programada mediante %s", cmd_path)
    return cmd_path
