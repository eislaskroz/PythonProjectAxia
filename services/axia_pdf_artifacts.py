"""Repositorio local de artefactos PDF canónicos de AXIA PDF ENGINE Fase 3.

Un PDF definitivo se registra junto con su huella SHA-256. Las descargas
posteriores copian exactamente esos mismos bytes en lugar de volver a renderizar
el documento. Si el artefacto no existe en el equipo actual, el servicio puede
regenerarlo y registrarlo como mecanismo de compatibilidad.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.logger import configurar_logger

logger = configurar_logger(__name__)

PDF_RENDERER_VERSION = 19


def _base_dir() -> Path:
    path = Path.home() / "Documents" / "AXIA" / "pdf_engine"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _registry_path() -> Path:
    return _base_dir() / "artifacts.json"


def _safe_key(value: str) -> str:
    text = str(value or "").strip().upper()
    return "".join(ch for ch in text if ch.isalnum() or ch in "-_.")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class AxiaPdfArtifact:
    key: str
    path: Path
    sha256: str
    size: int
    created_at: str
    renderer_version: int = 1

    @property
    def exists_and_valid(self) -> bool:
        return (
            self.path.is_file()
            and self.path.stat().st_size == self.size
            and sha256_file(self.path) == self.sha256
        )


class AxiaPdfArtifactStore:
    """Índice persistente de PDFs definitivos generados en este equipo."""

    @classmethod
    def _load(cls) -> dict[str, Any]:
        path = _registry_path()
        if not path.exists():
            return {"version": 1, "artifacts": {}}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Registro inválido")
            data.setdefault("version", 1)
            data.setdefault("artifacts", {})
            return data
        except Exception:
            logger.warning("No se pudo leer el registro de PDFs AXIA", exc_info=True)
            return {"version": 1, "artifacts": {}}

    @classmethod
    def _save(cls, data: dict[str, Any]) -> None:
        destination = _registry_path()
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix="artifacts_", suffix=".json.tmp", dir=str(destination.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, destination)
        finally:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except Exception:
                pass

    @classmethod
    def register(cls, key: str, path: str | Path) -> AxiaPdfArtifact:
        normalized = _safe_key(key)
        source = Path(path).resolve()
        if not normalized:
            raise ValueError("Se requiere una clave de artefacto")
        if not source.is_file():
            raise FileNotFoundError(source)

        artifact = AxiaPdfArtifact(
            key=normalized,
            path=source,
            sha256=sha256_file(source),
            size=source.stat().st_size,
            created_at=datetime.now(timezone.utc).isoformat(),
            renderer_version=PDF_RENDERER_VERSION,
        )
        data = cls._load()
        data["artifacts"][normalized] = {
            "path": str(artifact.path),
            "sha256": artifact.sha256,
            "size": artifact.size,
            "created_at": artifact.created_at,
            "renderer_version": artifact.renderer_version,
        }
        cls._save(data)
        logger.info("PDF AXIA registrado: %s sha256=%s", normalized, artifact.sha256)
        return artifact

    @classmethod
    def find(cls, key: str, *, min_renderer_version: int | None = None) -> AxiaPdfArtifact | None:
        normalized = _safe_key(key)
        item = cls._load().get("artifacts", {}).get(normalized)
        if not isinstance(item, dict):
            return None
        try:
            artifact = AxiaPdfArtifact(
                key=normalized,
                path=Path(item["path"]),
                sha256=str(item["sha256"]),
                size=int(item["size"]),
                created_at=str(item.get("created_at") or ""),
                renderer_version=int(item.get("renderer_version") or 1),
            )
        except (KeyError, TypeError, ValueError):
            return None
        if min_renderer_version is not None and artifact.renderer_version < int(min_renderer_version):
            logger.info("Artefacto PDF obsoleto: %s version=%s requerida=%s", normalized, artifact.renderer_version, min_renderer_version)
            return None
        if not artifact.exists_and_valid:
            logger.warning("Artefacto PDF inválido o ausente: %s", normalized)
            return None
        return artifact

    @classmethod
    def export_exact(cls, key: str, destination: str | Path, *, min_renderer_version: int | None = None) -> Path | None:
        artifact = cls.find(key, min_renderer_version=min_renderer_version)
        if artifact is None:
            return None
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if artifact.path.resolve() == destination.resolve():
            return destination
        temp = destination.with_suffix(destination.suffix + ".tmp")
        shutil.copyfile(artifact.path, temp)
        os.replace(temp, destination)
        if sha256_file(destination) != artifact.sha256:
            destination.unlink(missing_ok=True)
            raise IOError("La copia del PDF no conservó su integridad")
        return destination

    @staticmethod
    def open(path: str | Path) -> None:
        path = Path(path)
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
