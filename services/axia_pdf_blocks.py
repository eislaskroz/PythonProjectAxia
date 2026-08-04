"""Bloques reutilizables de AXIA PDF ENGINE Fase 4.

El documento deja de depender de un generador distinto por formulario. Cada
formulario declara bloques de contenido y el motor corporativo decide cómo
renderizarlos. Los adaptadores heredados siguen disponibles para permitir una
migración gradual sin romper pantallas existentes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze_value(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted((_freeze_value(item) for item in value), key=str))
    return value


def _freeze_mapping(values: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(
        {str(key): _freeze_value(value) for key, value in dict(values or {}).items()}
    )


@dataclass(frozen=True)
class AxiaPdfBlock:
    """Bloque base de contenido AXIA."""

    kind: str


@dataclass(frozen=True)
class GeneralDataBlock(AxiaPdfBlock):
    """Pares etiqueta/valor mostrados en la cabecera de datos generales."""

    values: Mapping[str, Any] = field(default_factory=dict)

    def __init__(self, values: Mapping[str, Any] | None = None):
        object.__setattr__(self, "kind", "general_data")
        object.__setattr__(self, "values", _freeze_mapping(values))


@dataclass(frozen=True)
class TechnicalDetailBlock(AxiaPdfBlock):
    """Detalle técnico estructurado o texto heredado por secciones."""

    text: str = ""

    def __init__(self, text: str | None = None):
        object.__setattr__(self, "kind", "technical_detail")
        object.__setattr__(self, "text", str(text or "").strip())


@dataclass(frozen=True)
class DataTableBlock(AxiaPdfBlock):
    """Tabla repetible con columnas y registros."""

    title: str = ""
    columns: tuple[str, ...] = ()
    rows: tuple[Mapping[str, Any], ...] = ()

    def __init__(
        self,
        title: str,
        columns: Sequence[str],
        rows: Iterable[Mapping[str, Any]] | None = None,
    ):
        object.__setattr__(self, "kind", "data_table")
        object.__setattr__(self, "title", str(title or "").strip())
        object.__setattr__(self, "columns", tuple(str(c) for c in columns or ()))
        object.__setattr__(
            self,
            "rows",
            tuple(_freeze_mapping(row) for row in (rows or ())),
        )


@dataclass(frozen=True)
class SignatureBlock(AxiaPdfBlock):
    """Configuración de la zona de firmas del documento."""

    visible: bool | None = None
    client_signature_base64: str | None = None
    technician_signature_base64: str | None = None

    def __init__(
        self,
        *,
        visible: bool | None = None,
        client_signature_base64: str | None = None,
        technician_signature_base64: str | None = None,
    ):
        object.__setattr__(self, "kind", "signatures")
        object.__setattr__(self, "visible", visible)
        object.__setattr__(self, "client_signature_base64", client_signature_base64)
        object.__setattr__(self, "technician_signature_base64", technician_signature_base64)


@dataclass(frozen=True)
class AxiaPdfDocument:
    """Documento canónico compuesto por bloques reutilizables."""

    title: str
    blocks: tuple[AxiaPdfBlock, ...]
    schema_version: int = 1

    @classmethod
    def from_legacy(
        cls,
        *,
        title: str,
        data: Mapping[str, Any],
        tables=None,
        client_signature_base64: str | None = None,
        technician_signature_base64: str | None = None,
        show_signatures: bool | None = None,
    ) -> "AxiaPdfDocument":
        source = dict(data or {})
        detail = str(source.pop("Detalle técnico", "") or "").strip()
        blocks: list[AxiaPdfBlock] = [GeneralDataBlock(source)]
        if detail:
            blocks.append(TechnicalDetailBlock(detail))
        for title_table, columns, rows in (tables or ()):  # contrato histórico
            blocks.append(DataTableBlock(title_table, columns, rows))
        blocks.append(
            SignatureBlock(
                visible=show_signatures,
                client_signature_base64=client_signature_base64,
                technician_signature_base64=technician_signature_base64,
            )
        )
        return cls(title=str(title or "Documento AXIA"), blocks=tuple(blocks))

    def to_legacy(self) -> dict[str, Any]:
        """Adapta bloques al renderizador corporativo existente.

        Esta frontera temporal permite migrar formularios uno por uno. El resto
        de AXIA ya opera sobre bloques y no necesita conocer el formato heredado.
        """
        data: dict[str, Any] = {}
        tables: list[tuple[str, tuple[str, ...], list[dict[str, Any]]]] = []
        client_signature = None
        technician_signature = None
        show_signatures = None

        details: list[str] = []
        for block in self.blocks:
            if isinstance(block, GeneralDataBlock):
                data.update(dict(block.values))
            elif isinstance(block, TechnicalDetailBlock) and block.text:
                details.append(block.text)
            elif isinstance(block, DataTableBlock):
                tables.append(
                    (
                        block.title,
                        block.columns,
                        [dict(row) for row in block.rows],
                    )
                )
            elif isinstance(block, SignatureBlock):
                client_signature = block.client_signature_base64
                technician_signature = block.technician_signature_base64
                show_signatures = block.visible

        if details:
            data["Detalle técnico"] = "\n".join(details)
        return {
            "titulo": self.title,
            "datos": data,
            "secciones_tabla": tables,
            "firma_base64": client_signature,
            "firma_tecnico_base64": technician_signature,
            "mostrar_firmas": show_signatures,
        }

    def blocks_of(self, block_type: type[AxiaPdfBlock]) -> tuple[AxiaPdfBlock, ...]:
        return tuple(block for block in self.blocks if isinstance(block, block_type))
