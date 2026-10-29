"""Controles nativos de alto rendimiento para tablas y listas de AXIA."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from .table_columns import TableColumnManager
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
        table_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self._payloads: dict[str, dict[str, Any]] = {}
        self._on_select = on_select
        self._on_open = on_open
        self._column_id = table_id
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        ids = [item[0] for item in columns]
        self.tree = ttk.Treeview(self, columns=ids, show=show, height=height, selectmode="browse")
        self.vscroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.hscroll = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vscroll.set, xscrollcommand=self.hscroll.set)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("AXIA.Treeview", background="#F8FAFC", foreground="#0F172A",
                        fieldbackground="#F8FAFC", rowheight=28, borderwidth=0, relief="flat")
        style.map("AXIA.Treeview", background=[("selected", "#2563EB")],
                  foreground=[("selected", "#FFFFFF")])
        style.configure("AXIA.Treeview.Heading", background="#0F172A", foreground="#FFFFFF",
                        relief="flat", padding=(10, 8), borderwidth=0,
                        font=("Segoe UI", 10))
        style.map("AXIA.Treeview.Heading", background=[("active", "#1E293B")])
        style.configure("Vertical.TScrollbar", troughcolor="#EEF4FF", background="#5B8DEF",
                        arrowcolor="#0F172A", borderwidth=0)
        style.configure("Horizontal.TScrollbar", troughcolor="#EEF4FF", background="#5B8DEF",
                        arrowcolor="#0F172A", borderwidth=0)
        self.tree.configure(style="AXIA.Treeview")
        self._columns_manager = TableColumnManager(
            self.tree, table_id or f"tabla_{type(master).__name__}_{id(self)}"
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vscroll.grid(row=0, column=1, sticky="ns")
        self.hscroll.grid(row=1, column=0, sticky="ew")

        self._columns_manager.configure_columns(columns)
        self._context_menu = tk.Menu(self, tearoff=0)
        self._context_menu.add_command(label="Copiar contenido de celda", command=self._copy_cell)
        self._context_menu.add_command(label="Copiar fila completa", command=self._copy_row)
        self._context_menu.add_separator()
        self._context_menu.add_command(label="Restablecer anchos", command=self._columns_manager.reset_widths)
        self._context_cell: tuple[str, str] | None = None
        self.tree.bind("<Button-3>", self._show_context, add="+")

        self.tree.bind("<<TreeviewSelect>>", self._selected, add="+")
        self.tree.bind("<Double-1>", self._opened, add="+")
        self.tree.bind("<Return>", self._opened, add="+")

    def set_columns(self, columns: Sequence[tuple[str, str, int]]) -> None:
        self._columns_manager.configure_columns(columns)

    def _show_context(self, event) -> None:
        row = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        self._context_cell = (row, column) if row and column and column != '#0' else None
        self._context_menu.entryconfigure(0, state='normal' if self._context_cell else 'disabled')
        self._context_menu.entryconfigure(1, state='normal' if self._context_cell else 'disabled')
        try:
            self._context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._context_menu.grab_release()

    def _copy_cell(self) -> None:
        if self._context_cell:
            row, column = self._context_cell
            if self.tree.exists(row):
                self._clipboard(str(self.tree.set(row, column)))

    def _copy_row(self) -> None:
        if self._context_cell:
            row, _ = self._context_cell
            if self.tree.exists(row):
                self._clipboard('\t'.join(str(v) for v in self.tree.item(row, 'values')))

    def _clipboard(self, value: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(value)

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
            self.tree.item(iid, tags=("fila_azul",) if index % 2 else ("fila_blanca",))
        self.tree.tag_configure("fila_blanca", background="#FFFFFF", foreground="#0F172A")
        self.tree.tag_configure("fila_azul", background="#EAF3FF", foreground="#0F172A")

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
