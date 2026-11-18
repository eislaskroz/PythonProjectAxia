import tkinter as tk

from ui.native_combobox import NativeComboBox


def test_predictive_ui():
    root = tk.Tk()
    root.geometry("500x300+20+20")
    events = []
    combo = NativeComboBox(
        root,
        values=["Protección y Potencia", "Conduit metálico", "Apagador sencillo"],
        state="readonly",
        command=lambda value: events.append(value),
    )
    combo.pack()
    root.update()
    try:
        combo.insert(0, "proteccion")
        combo._on_search(type("Key", (), {"keysym": "n", "state": 0})())
        root.update()
        assert combo.get() == "proteccion"
        assert combo._axia_matches == ("Protección y Potencia",)
        combo._on_down()
        combo._on_return()
        assert combo.get() == "Protección y Potencia"
        assert events == ["Protección y Potencia"]

        combo.delete(0, tk.END)
        combo.insert(0, "valor inventado")
        combo._on_search(type("Key", (), {"keysym": "o", "state": 0})())
        combo._on_return()
        assert combo.get() == "Protección y Potencia"

        combo.configure(values=["Tubo", "Codo"])
        assert combo.cget("values") == ("Codo", "Tubo")
        combo.delete(0, tk.END)
        combo.insert(0, "tub")
        combo._on_search(type("Key", (), {"keysym": "b", "state": 0})())
        combo._on_return()
        assert combo.get() == "Tubo"
        assert events == ["Protección y Potencia", "Tubo"]
        combo.configure(state="disabled")
        assert str(combo.cget("state")) == "disabled"
    finally:
        root.destroy()
