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


class TableColumnManager:
    """Evita que ttk comprima las columnas; conserva el ancho elegido por usuario."""

    def __init__(self, tree: ttk.Treeview, table_id: str):
        if not table_id:
            raise ValueError("Cada tabla necesita un identificador persistente")
        self.tree = tree
        self.table_id = table_id
        self.defaults: dict[str, int] = {}
        self.saved = read_preferences().get(table_id, {})
        self._current_widths: dict[str, int] = {}
        tree.bind("<ButtonRelease-1>", self._on_release, add="+")
        tree.bind("<Shift-MouseWheel>", self._wheel_horizontal, add="+")
        tree.bind("<Shift-Button-4>", lambda _: tree.xview_scroll(-3, "units"), add="+")
        tree.bind("<Shift-Button-5>", lambda _: tree.xview_scroll(3, "units"), add="+")

    def configure_columns(self, columns: Sequence[tuple[str, str, int]]) -> None:
        old_ids = tuple(self.tree["columns"])
        for key in old_ids:
            if key in self.defaults:
                self._current_widths[key] = self.tree.column(key, "width")
        new_ids = tuple(key for key, _, _ in columns)
        if old_ids != new_ids:
            self.tree.configure(columns=new_ids)
        for key, title, default_width in columns:
            self.defaults.setdefault(key, max(_MIN_WIDTH, int(default_width)))
            width = (self._current_widths.get(key) or self.saved.get(key)
                     or self.defaults[key])
            self.tree.heading(key, text=title, anchor="w")
            # stretch=False: el canvas horizontal recibe el ancho sobrante;
            # la columna NO vuelve a encogerse al actualizar la consulta.
            self.tree.column(key, width=width, minwidth=_MIN_WIDTH,
                             anchor="w", stretch=False)
            self._current_widths[key] = width

    def _on_release(self, _event=None) -> None:
        # La acción de redimensionar de ttk puede completarse después del
        # callback del widget; consultar al volver al ciclo de interfaz.
        self.tree.after_idle(self.capture_changed_widths)

    def capture_changed_widths(self) -> None:
        if not self.tree.winfo_exists():
            return
        updated = {}
        for key in self.tree["columns"]:
            width = valid_width(self.tree.column(key, "width"))
            if width is not None:
                updated[key] = width
        if not updated or all(self._current_widths.get(key) == width for key, width in updated.items()):
            return
        self._current_widths.update(updated)
        self.saved.update(updated)
        write_preferences(self.table_id, self.saved)

    def reset_widths(self) -> None:
        for key in self.tree["columns"]:
            width = self.defaults.get(key)
            if width is not None:
                self.tree.column(key, width=width, stretch=False)
                self._current_widths[key] = width
                self.saved.pop(key, None)
        write_preferences(self.table_id, self.saved)

    def _wheel_horizontal(self, event) -> str:
        delta = int(getattr(event, "delta", 0))
        if delta:
            self.tree.xview_scroll(-3 * (1 if delta > 0 else -1), "units")
        return "break"
