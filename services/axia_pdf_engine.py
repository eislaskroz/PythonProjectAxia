"""AXIA PDF ENGINE - Fase 5.

Motor único basado en bloques reutilizables. Preview, guardado y descarga
trabajan sobre el mismo :class:`AxiaPdfDocument` inmutable.
"""
from __future__ import annotations

import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from core.logger import configurar_logger
from services.axia_pdf_blocks import AxiaPdfBlock, AxiaPdfDocument
from services.axia_pdf_profiles import AxiaPdfProfileRegistry

logger = configurar_logger(__name__)


@dataclass(frozen=True)
class AxiaPdfRequest:
    """Solicitud inmutable de renderizado de un documento AXIA."""

    document: AxiaPdfDocument
    ruta_salida: str | Path | None = None
    abrir: bool = True

    # Propiedades de compatibilidad con Fases 1-3 y pruebas existentes.
    @property
    def titulo(self) -> str:
        return self.document.title

    @property
    def datos(self) -> Mapping[str, Any]:
        return self.document.to_legacy()["datos"]

    @property
    def secciones_tabla(self):
        return self.document.to_legacy()["secciones_tabla"]

    @property
    def firma_base64(self):
        return self.document.to_legacy()["firma_base64"]

    @property
    def firma_tecnico_base64(self):
        return self.document.to_legacy()["firma_tecnico_base64"]

    @property
    def mostrar_firmas(self):
        return self.document.to_legacy()["mostrar_firmas"]


class AxiaPdfEngine:
    """Motor único de salida PDF de AXIA."""

    @staticmethod
    def prepare(
        *,
        titulo: str,
        datos: Mapping[str, Any],
        secciones_tabla=None,
        firma_base64: str | None = None,
        firma_tecnico_base64: str | None = None,
        mostrar_firmas: bool | None = None,
    ) -> AxiaPdfRequest:
        """Adapta el contrato histórico a un documento de bloques."""
        document = AxiaPdfDocument.from_legacy(
            title=titulo,
            data=datos,
            tables=secciones_tabla,
            client_signature_base64=firma_base64,
            technician_signature_base64=firma_tecnico_base64,
            show_signatures=mostrar_firmas,
        )
        return AxiaPdfRequest(document=document)

    @staticmethod
    def prepare_document(
        *,
        titulo: str,
        bloques: Sequence[AxiaPdfBlock],
    ) -> AxiaPdfRequest:
        """API nativa Fase 4 para formularios nuevos o migrados.

        Cada formulario solo declara los bloques que necesita; no implementa
        lógica propia de ReportLab ni duplica plantillas.
        """
        document = AxiaPdfDocument(
            title=str(titulo or "Documento AXIA"),
            blocks=tuple(bloques or ()),
        )
        return AxiaPdfRequest(document=document)


    @staticmethod
    def prepare_profile(*, profile_key: str, data: Mapping[str, Any]) -> AxiaPdfRequest:
        """API declarativa Fase 5 basada en perfiles registrados."""
        document = AxiaPdfProfileRegistry.build(profile_key, data)
        return AxiaPdfRequest(document=document)

    @staticmethod
    def _preview_path(titulo: str) -> Path:
        nombre = "".join(
            caracter if caracter.isalnum() or caracter in "-_" else "_"
            for caracter in str(titulo or "documento")
        ).strip("_") or "documento"
        carpeta = Path(tempfile.gettempdir()) / "AXIA" / "preview"
        carpeta.mkdir(parents=True, exist_ok=True)
        return carpeta / f"AXIA_PREVIEW_{nombre}.pdf"

    @classmethod
    def render(cls, request: AxiaPdfRequest):
        if not isinstance(request, AxiaPdfRequest):
            raise TypeError("request debe ser una instancia de AxiaPdfRequest")

        logger.info(
            "AXIA PDF ENGINE F5: generando '%s' bloques=%s destino=%s abrir=%s",
            request.titulo,
            len(request.document.blocks),
            request.ruta_salida or "temporal",
            request.abrir,
        )

        from views.formato_helpers import _generar_pdf_base

        legacy = request.document.to_legacy()
        return _generar_pdf_base(
            legacy["titulo"],
            legacy["datos"],
            secciones_tabla=legacy["secciones_tabla"],
            firma_base64=legacy["firma_base64"],
            firma_tecnico_base64=legacy["firma_tecnico_base64"],
            mostrar_firmas=legacy["mostrar_firmas"],
            ruta_salida=request.ruta_salida,
            abrir=request.abrir,
        )

    @classmethod
    def preview_request(cls, request: AxiaPdfRequest):
        destino = cls._preview_path(request.titulo)
        return cls.render(replace(request, ruta_salida=destino, abrir=True))

    @classmethod
    def save_request(cls, request: AxiaPdfRequest, ruta_salida: str | Path):
        return cls.render(replace(request, ruta_salida=Path(ruta_salida), abrir=False))

    @classmethod
    def preview(cls, titulo: str, datos: Mapping[str, Any], **kwargs):
        kwargs.pop("abrir", None)
        kwargs.pop("ruta_salida", None)
        return cls.preview_request(cls.prepare(titulo=titulo, datos=datos, **kwargs))

    @classmethod
    def save(
        cls,
        titulo: str,
        datos: Mapping[str, Any],
        ruta_salida: str | Path,
        **kwargs,
    ):
        kwargs.pop("abrir", None)
        kwargs.pop("ruta_salida", None)
        return cls.save_request(
            cls.prepare(titulo=titulo, datos=datos, **kwargs), ruta_salida
        )

    @classmethod
    def generate(
        cls,
        *,
        titulo: str,
        datos: Mapping[str, Any],
        secciones_tabla=None,
        firma_base64: str | None = None,
        firma_tecnico_base64: str | None = None,
        mostrar_firmas: bool | None = None,
        ruta_salida: str | Path | None = None,
        abrir: bool = True,
    ):
        kwargs = {
            "secciones_tabla": secciones_tabla,
            "firma_base64": firma_base64,
            "firma_tecnico_base64": firma_tecnico_base64,
            "mostrar_firmas": mostrar_firmas,
        }
        if ruta_salida is None and abrir:
            return cls.preview(titulo, datos, **kwargs)
        if ruta_salida is None:
            ruta_salida = cls._preview_path(titulo)
        request = cls.prepare(titulo=titulo, datos=datos, **kwargs)
        return cls.render(
            replace(request, ruta_salida=Path(ruta_salida), abrir=bool(abrir))
        )
