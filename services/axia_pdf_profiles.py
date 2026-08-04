"""Perfiles declarativos de AXIA PDF ENGINE Fase 5.

Los formularios dejan de construir bloques manualmente. Cada tipo de documento
registra un perfil que declara título, campos generales, detalle técnico,
tablas y firmas. El motor transforma datos crudos en un AxiaPdfDocument.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

from services.axia_pdf_blocks import (
    AxiaPdfBlock,
    AxiaPdfDocument,
    DataTableBlock,
    GeneralDataBlock,
    SignatureBlock,
    TechnicalDetailBlock,
)

ValueGetter = Callable[[Mapping[str, Any]], Any]
RowsGetter = Callable[[Mapping[str, Any]], Iterable[Mapping[str, Any]]]


def _read_path(data: Mapping[str, Any], path: str, default: Any = "") -> Any:
    current: Any = data
    for part in str(path or "").split("."):
        if not part:
            continue
        if not isinstance(current, Mapping) or part not in current:
            return default
        current = current[part]
    return current


def _non_empty(value: Any) -> bool:
    return value not in (None, "", [], {}, ())


@dataclass(frozen=True)
class FieldSpec:
    label: str
    source: str | ValueGetter
    required: bool = False
    formatter: Callable[[Any], Any] | None = None

    def resolve(self, data: Mapping[str, Any]) -> Any:
        value = self.source(data) if callable(self.source) else _read_path(data, self.source)
        if self.formatter is not None:
            value = self.formatter(value)
        if self.required and not _non_empty(value):
            raise ValueError(f"Falta el campo obligatorio para PDF: {self.label}")
        return value


@dataclass(frozen=True)
class TableSpec:
    title: str
    columns: tuple[str, ...]
    source: str | RowsGetter

    def resolve(self, data: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
        rows = self.source(data) if callable(self.source) else _read_path(data, self.source, ())
        if not rows:
            return ()
        if not isinstance(rows, (list, tuple)):
            raise TypeError(f"La tabla '{self.title}' debe recibir una lista de registros")
        normalized = []
        for row in rows:
            if isinstance(row, Mapping):
                normalized.append(dict(row))
        return tuple(normalized)


@dataclass(frozen=True)
class AxiaPdfProfile:
    key: str
    title: str | Callable[[Mapping[str, Any]], str]
    general_fields: tuple[FieldSpec, ...] = ()
    detail_source: str | ValueGetter | None = None
    tables: tuple[TableSpec, ...] = ()
    show_signatures: bool | Callable[[Mapping[str, Any]], bool] | None = None
    extra_blocks: Callable[[Mapping[str, Any]], Sequence[AxiaPdfBlock]] | None = None
    schema_version: int = 1

    def build(self, data: Mapping[str, Any]) -> AxiaPdfDocument:
        source = dict(data or {})
        title = self.title(source) if callable(self.title) else self.title
        general: dict[str, Any] = {}
        for spec in self.general_fields:
            value = spec.resolve(source)
            if _non_empty(value):
                general[spec.label] = value

        blocks: list[AxiaPdfBlock] = []
        if general:
            blocks.append(GeneralDataBlock(general))

        if self.detail_source is not None:
            detail = (
                self.detail_source(source)
                if callable(self.detail_source)
                else _read_path(source, self.detail_source)
            )
            if _non_empty(detail):
                blocks.append(TechnicalDetailBlock(str(detail)))

        for table in self.tables:
            rows = table.resolve(source)
            if rows:
                blocks.append(DataTableBlock(table.title, table.columns, rows))

        if self.extra_blocks is not None:
            blocks.extend(tuple(self.extra_blocks(source) or ()))

        signatures = (
            self.show_signatures(source)
            if callable(self.show_signatures)
            else self.show_signatures
        )
        blocks.append(SignatureBlock(visible=signatures))
        return AxiaPdfDocument(
            title=str(title or "Documento AXIA"),
            blocks=tuple(blocks),
            schema_version=self.schema_version,
        )


class AxiaPdfProfileRegistry:
    _profiles: dict[str, AxiaPdfProfile] = {}

    @classmethod
    def register(cls, profile: AxiaPdfProfile, *, replace: bool = False) -> None:
        key = str(profile.key or "").strip().casefold()
        if not key:
            raise ValueError("El perfil PDF requiere una clave")
        if key in cls._profiles and not replace:
            raise ValueError(f"El perfil PDF '{profile.key}' ya existe")
        cls._profiles[key] = profile

    @classmethod
    def get(cls, key: str) -> AxiaPdfProfile:
        normalized = str(key or "").strip().casefold()
        if normalized not in cls._profiles:
            raise KeyError(f"No existe el perfil PDF '{key}'")
        return cls._profiles[normalized]

    @classmethod
    def build(cls, key: str, data: Mapping[str, Any]) -> AxiaPdfDocument:
        return cls.get(key).build(data)

    @classmethod
    def keys(cls) -> tuple[str, ...]:
        return tuple(sorted(cls._profiles))


def _generic_table_blocks(data: Mapping[str, Any]) -> Sequence[AxiaPdfBlock]:
    blocks: list[AxiaPdfBlock] = []
    for item in data.get("_tablas_pdf", ()) or ():
        try:
            title, columns, rows = item
        except (TypeError, ValueError):
            continue
        if rows:
            blocks.append(DataTableBlock(str(title), tuple(columns), rows))
    return tuple(blocks)


def register_builtin_profiles() -> None:
    """Registra perfiles base para las entidades actuales de AXIA."""
    generic = AxiaPdfProfile(
        key="registro_generico",
        title=lambda d: str(d.get("_titulo_pdf") or "Registro AXIA"),
        general_fields=(
            FieldSpec("Folio", lambda d: d.get("_folio") or ""),
            FieldSpec("Cliente", lambda d: d.get("Cliente") or d.get("cliente") or ""),
            FieldSpec("Contacto", lambda d: d.get("Contacto") or d.get("contacto") or ""),
            FieldSpec("Teléfono", lambda d: d.get("Teléfono") or d.get("telefono") or ""),
            FieldSpec("Correo electrónico", lambda d: d.get("Correo electrónico") or d.get("correo") or ""),
            FieldSpec("Fecha", lambda d: d.get("Fecha") or d.get("fecha") or ""),
        ),
        detail_source=lambda d: d.get("Detalle técnico") or d.get("detalle_tecnico") or "",
        extra_blocks=_generic_table_blocks,
        show_signatures=lambda d: bool(d.get("_mostrar_firmas", False)),
    )
    AxiaPdfProfileRegistry.register(generic, replace=True)


register_builtin_profiles()
