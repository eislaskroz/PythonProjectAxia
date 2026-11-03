"""Anchos persistentes y scroll horizontal para las tablas de AXIA DESKTOP.

Solo guarda preferencias visuales (identificador de tabla y anchos), nunca filas.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from tkinter import ttk
from typing import Sequence

_MIN_WIDTH = 65
_MAX_WIDTH = 1800


def preferences_path() -> Path:
    """Ruta fuera de la instalación, válida también tras actualizar con Inno Setup."""
    app_data = os.environ.get("LOCALAPPDATA")
    if app_data:
        return Path(app_data) / "AXIA" / "preferencias_tablas.json"
    return Path.home() / ".config" / "AXIA" / "preferencias_tablas.json"


def valid_width(value: object) -> int | None:
    try:
        width = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return width if _MIN_WIDTH <= width <= _MAX_WIDTH else None


def read_preferences(path: Path | None = None) -> dict[str, dict[str, int]]:
    path = path or preferences_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        result = {}
        for table_id, columns in data.items():
            if not isinstance(table_id, str) or not isinstance(columns, dict):
                continue
            result[table_id] = {
                key: width for key, raw in columns.items()
                if isinstance(key, str) and (width := valid_width(raw)) is not None
            }
        return result
    except (OSError, ValueError, TypeError):
        return {}


def write_preferences(table_id: str, widths: dict[str, int], path: Path | None = None) -> bool:
    path = path or preferences_path()
    data = read_preferences(path)
    data[table_id] = {key: width for key, value in widths.items()
                      if (width := valid_width(value)) is not None}
    temp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)
        return True
    except OSError:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def distribuir_anchos(minimos: Sequence[int], espacio: int) -> list[int]:
    """Llena el ancho de una tabla sin comprimir columnas ni su contenido.

    En pantallas estrechas mantiene los mínimos y deja disponible el scroll
    horizontal; el alto del Treeview y sus scrollbars no se alteran.
    """
    result = [max(_MIN_WIDTH, int(width)) for width in minimos]
    extra = max(0, int(espacio) - sum(result))
    if not result or not extra:
        return result
    # El contenido descriptivo gana más espacio que folios/estados cortos.
    pesos = [max(20, width - 55) for width in result]
    total = sum(pesos)
    repartido = 0
    for index, peso in enumerate(pesos[:-1]):
        aumento = extra * peso // total
        result[index] += aumento
        repartido += aumento
    result[-1] += extra - repartido
    return result


class TableColumnManager:
    """Anchos persistentes, autoajuste horizontal y scroll cuando sea necesario.

    Los anchos automáticos NO se guardan como preferencias del usuario.
    El redimensionado manual sí se conserva entre pantallas y sesiones.
    """

    def __init__(self, tree: ttk.Treeview, table_id: str):
        if not table_id:
            raise ValueError("Cada tabla necesita un identificador persistente")
        self.tree = tree
        self.table_id = table_id
        self.defaults: dict[str, int] = {}
        self.saved = read_preferences().get(table_id, {})
        self._current_widths: dict[str, int] = {}
        self._last_applied: dict[str, int] = {}
        self._content_widths: dict[str, int] = {}
        self._column_titles: dict[str, str] = {}
        self._pending_layout = False
        self._in_layout = False
        self._last_available = 0
        tree.bind("<ButtonRelease-1>", self._on_release, add="+")
        tree.bind("<Configure>", self._on_resize, add="+")
        tree.bind("<Shift-MouseWheel>", self._wheel_horizontal, add="+")
        tree.bind("<Shift-Button-4>", lambda _: tree.xview_scroll(-3, "units"), add="+")
        tree.bind("<Shift-Button-5>", lambda _: tree.xview_scroll(3, "units"), add="+")

    def configure_columns(self, columns: Sequence[tuple[str, str, int]]) -> None:
        old_ids = tuple(self.tree["columns"])
        for key in old_ids:
            if key in self.defaults:
                old = int(self.tree.column(key, "width"))
                # No confundir el autoajuste visual con una decisión manual.
                if key not in self._last_applied or old != self._last_applied[key]:
                    self._current_widths[key] = old
        new_ids = tuple(key for key, _, _ in columns)
        if old_ids != new_ids:
            self.tree.configure(columns=new_ids)
        self._column_titles = {key: title for key, title, _ in columns}
        self._content_widths = {k: v for k, v in self._content_widths.items() if k in new_ids}
        for key, title, default_width in columns:
            self.defaults.setdefault(key, max(_MIN_WIDTH, int(default_width)))
            width = (self._current_widths.get(key) or self.saved.get(key)
                     or self.defaults[key])
            self.tree.heading(key, text=title, anchor="w")
            # Evita que ttk comprima los datos; cuando falte espacio hay scroll.
            self.tree.column(key, width=width, minwidth=_MIN_WIDTH,
                             anchor="w", stretch=False)
            self._last_applied[key] = width
        self._schedule_layout()

    def set_content_widths(self, widths: dict[str, int]) -> None:
        """Recibe medidas de contenido ya mostrado, nunca datos de la BD."""
        self._content_widths = {
            key: min(520, max(_MIN_WIDTH, int(width)))
            for key, width in widths.items() if key in self.tree["columns"]
        }
        self._schedule_layout()

    def _on_resize(self, _event=None) -> None:
        self._schedule_layout()

    def _schedule_layout(self) -> None:
        if self._pending_layout:
            return
        if not hasattr(self.tree, 'after_idle'):
            return
        self._pending_layout = True
        self.tree.after_idle(self._apply_layout)

    def _apply_layout(self) -> None:
        self._pending_layout = False
        if self._in_layout:
            return
        try:
            if not self.tree.winfo_exists():
                return
            viewport = int(self.tree.winfo_width())
        except (AttributeError, ValueError, TypeError):
            return
        if viewport < 40:
            return
        keys = tuple(self.tree['columns'])
        if not keys:
            return
        # Mantener las elecciones manuales. En ausencia de una preferencia,
        # mostrar completo encabezado y una longitud razonable de cada dato.
        base = []
        for key in keys:
            preference = self._current_widths.get(key) or self.saved.get(key)
            header_min = len(self._column_titles.get(key, '')) * 8 + 28
            if preference:
                base.append(max(_MIN_WIDTH, int(preference)))
            else:
                base.append(max(self.defaults.get(key, _MIN_WIDTH),
                                header_min, self._content_widths.get(key, 0)))
        target = distribuir_anchos(base, max(40, viewport - 2))
        if all(self._last_applied.get(key) == width for key, width in zip(keys, target)):
            return
        self._in_layout = True
        try:
            for key, width in zip(keys, target):
                if self._last_applied.get(key) != width:
                    self.tree.column(key, width=width, stretch=False)
                    self._last_applied[key] = width
        finally:
            self._in_layout = False
        self._last_available = viewport

    def _on_release(self, _event=None) -> None:
        # El resize de ttk puede completarse tras el callback del widget.
        self.tree.after_idle(self.capture_changed_widths)

    def capture_changed_widths(self) -> None:
        if not self.tree.winfo_exists():
            return
        updated = {}
        for key in self.tree["columns"]:
            width = valid_width(self.tree.column(key, "width"))
            if width is not None and width != self._last_applied.get(key):
                updated[key] = width
        if not updated:
            return
        self._current_widths.update(updated)
        self.saved.update(updated)
        write_preferences(self.table_id, self.saved)
        self._last_applied.update(updated)
        self._schedule_layout()

    def reset_widths(self) -> None:
        self._current_widths.clear()
        for key in self.tree["columns"]:
            width = self.defaults.get(key)
            if width is not None:
                self.tree.column(key, width=width, stretch=False)
                self._last_applied[key] = width
                self.saved.pop(key, None)
        write_preferences(self.table_id, self.saved)
        self._schedule_layout()

    def _wheel_horizontal(self, event) -> str:
        delta = int(getattr(event, "delta", 0))
        if delta:
            self.tree.xview_scroll(-3 * (1 if delta > 0 else -1), "units")
        return "break"
