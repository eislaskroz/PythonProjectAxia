from __future__ import annotations

import hashlib
import ctypes
import os
import subprocess
import re
import sys
import json
from urllib.parse import urlsplit, urlunsplit
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


def normalizar_url_actualizacion(valor: str) -> str:
    url = str(valor or "").strip().strip('"\'')
    if not url:
        raise ValueError("La actualización no tiene una URL de descarga configurada.")

    url = url.replace("\\", "/").replace(" ", "%20")

    url = re.sub(r"^(https?://)(?:https?://)+", r"\1", url, flags=re.IGNORECASE)

    if url.lower().startswith("www."):
        url = "https://" + url

    partes = urlsplit(url)
    if partes.scheme.lower() not in {"http", "https"}:
        raise ValueError("La URL de actualización debe comenzar con https:// o http://.")
    if not partes.hostname or partes.hostname.lower() in {"http", "https"}:
        raise ValueError("La URL de actualización no contiene un servidor válido.")

    ruta = re.sub(r"/{2,}", "/", partes.path or "/")
    normalizada = urlunsplit((partes.scheme.lower(), partes.netloc, ruta, partes.query, partes.fragment))
    return normalizada


def obtener_actualizacion_disponible() -> ActualizacionDisponible | None:
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

        fila = candidatas[0]
        version = str(fila.get("act_version") or "").strip()
        try:
            url = normalizar_url_actualizacion(str(fila.get("act_url") or ""))
        except ValueError as exc:
            logger.warning("Actualización %s ignorada: %s", version, exc)
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
    destino = _ruta_instalador(actualizacion.version)
    temporal = destino.with_suffix(".download")
    try:
        url = normalizar_url_actualizacion(actualizacion.url)
        try:
            with requests.get(
                url,
                stream=True,
                timeout=(10, 120),
                allow_redirects=True,
                headers={"User-Agent": f"AXIA-Desktop/{APP_VERSION}"},
            ) as respuesta:
                respuesta.raise_for_status()
                with temporal.open("wb") as fh:
                    for bloque in respuesta.iter_content(chunk_size=1024 * 512):
                        if bloque:
                            fh.write(bloque)
        except requests.RequestException as exc:
            logger.exception("No fue posible descargar la actualización desde %s", url)
            raise RuntimeError(
                "No fue posible conectar con el servidor de actualizaciones de AXIA. "
                "Verifica tu conexión a Internet o inténtalo nuevamente más tarde."
            ) from exc
        if temporal.stat().st_size < 1024:
            raise RuntimeError("El instalador descargado está vacío o incompleto.")

        with temporal.open("rb") as fh:
            firma_mz = fh.read(2)
        if firma_mz != b"MZ":
            raise RuntimeError(
                "El servidor respondió, pero el archivo descargado no es un instalador válido de Windows. "
                "Verifica que act_url apunte directamente al archivo .exe y no a una página web."
            )

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




def consumir_estado_actualizacion() -> dict | None:
    path = user_data_dir() / "updates" / "actualizacion_estado.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else None
    except Exception:
        logger.exception("No fue posible leer el estado de la actualización.")
        return None
    finally:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            logger.debug("No fue posible limpiar el estado de actualización.", exc_info=True)

def programar_instalacion(instalador: Path) -> Path:
    instalador = Path(instalador).resolve()
    if not instalador.is_file():
        raise FileNotFoundError(f"No existe el instalador: {instalador}")
    if os.name != "nt":
        raise RuntimeError("La instalación automática de AXIA sólo está disponible en Windows.")

    carpeta = user_data_dir() / "updates"
    carpeta.mkdir(parents=True, exist_ok=True)
    log_path = carpeta / "inno_actualizacion.log"

    parametros = (
        f'/SILENT /SP- /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS '
        f'/LOG="{log_path}"'
    )

    try:
        resultado = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            str(instalador),
            parametros,
            str(instalador.parent),
            1,
        )
    except Exception as exc:
        logger.exception("No fue posible iniciar el instalador elevado.")
        raise RuntimeError(
            "Windows no pudo iniciar el instalador de la actualización con permisos de administrador."
        ) from exc

    if int(resultado) <= 32:
        codigos = {
            2: "No se encontró el instalador descargado.",
            5: "Windows rechazó la elevación de permisos o el usuario canceló el UAC.",
            8: "Windows no tiene memoria suficiente para iniciar el instalador.",
            31: "Windows no pudo asociar el instalador con una aplicación ejecutable.",
        }
        detalle = codigos.get(int(resultado), f"ShellExecute devolvió el código {int(resultado)}.")
        raise RuntimeError(f"No fue posible iniciar la actualización. {detalle}")

    logger.info(
        "Instalador AXIA lanzado directamente con elevación. Archivo=%s | log=%s",
        instalador, log_path,
    )
    return instalador