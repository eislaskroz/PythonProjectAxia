"""Controles nativos de alto rendimiento para tablas y listas de AXIA."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Iterable, Sequence


class NativeTreeTable(ttk.Frame):
    """Tabla ttk.Treeview con scroll vertical/horizontal y payload por fila."""

    def __init__(
        self,
        master=None,
        *,
        columns: Sequence[tuple[str, str, int]] = (),
        on_select: Callable[[dict[str, Any]], Any] | None = None,
        on_open: Callable[[dict[str, Any]], Any] | None = None,
        show: str = "headings",
        height: int = 14,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self._payloads: dict[str, dict[str, Any]] = {}
        self._on_select = on_select
        self._on_open = on_open
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        ids = [item[0] for item in columns]
        self.tree = ttk.Treeview(self, columns=ids, show=show, height=height, selectmode="browse")
        self.vscroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.hscroll = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vscroll.set, xscrollcommand=self.hscroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vscroll.grid(row=0, column=1, sticky="ns")
        self.hscroll.grid(row=1, column=0, sticky="ew")

        for key, title, width in columns:
            self.tree.heading(key, text=title, anchor="w")
            self.tree.column(key, width=width, minwidth=max(60, min(width, 120)), anchor="w", stretch=True)

        self.tree.bind("<<TreeviewSelect>>", self._selected, add="+")
        self.tree.bind("<Double-1>", self._opened, add="+")
        self.tree.bind("<Return>", self._opened, add="+")

    def set_columns(self, columns: Sequence[tuple[str, str, int]]) -> None:
        ids = [item[0] for item in columns]
        self.tree.configure(columns=ids)
        for key, title, width in columns:
            self.tree.heading(key, text=title, anchor="w")
            self.tree.column(key, width=width, minwidth=max(60, min(width, 120)), anchor="w", stretch=True)

    def clear(self) -> None:
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)
        self._payloads.clear()

    def set_rows(
        self,
        rows: Iterable[dict[str, Any]],
        *,
        value_keys: Sequence[str] | None = None,
        value_factory: Callable[[dict[str, Any]], Sequence[Any]] | None = None,
    ) -> None:
        self.clear()
        columns = tuple(self.tree["columns"])
        keys = tuple(value_keys or columns)
        for index, row in enumerate(rows):
            values = value_factory(row) if value_factory else [row.get(key, "") for key in keys]
            iid = self.tree.insert("", "end", values=tuple("" if v is None else str(v) for v in values))
            self._payloads[iid] = row
            if index % 2:
                self.tree.item(iid, tags=("alternate",))
        self.tree.tag_configure("alternate", background="#F5F7FA")

    def selected_payload(self) -> dict[str, Any] | None:
        selection = self.tree.selection()
        return self._payloads.get(selection[0]) if selection else None

    def _selected(self, _event=None) -> None:
        payload = self.selected_payload()
        if payload is not None and callable(self._on_select):
            self._on_select(payload)

    def _opened(self, _event=None) -> None:
        payload = self.selected_payload()
        if payload is not None and callable(self._on_open):
            self._on_open(payload)


class NativeLongList(ttk.Frame):
    """Listbox nativo para catálogos/listas largas con scroll."""

    def __init__(self, master=None, *, on_select=None, height: int = 12, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self._items: list[Any] = []
        self._on_select = on_select
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.listbox = tk.Listbox(self, height=height, activestyle="dotbox", exportselection=False)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.bind("<<ListboxSelect>>", self._selected, add="+")

    def set_items(self, items: Iterable[Any], *, text_factory=str) -> None:
        self.listbox.delete(0, "end")
        self._items = list(items)
        for item in self._items:
            self.listbox.insert("end", text_factory(item))

    def selected_item(self) -> Any | None:
        selected = self.listbox.curselection()
        return self._items[selected[0]] if selected else None

    def _selected(self, _event=None) -> None:
        item = self.selected_item()
        if item is not None and callable(self._on_select):
            self._on_select(item)
