"""Editor de croquis técnico (etapa 1): objetos editables y PNG retrocompatible."""
from __future__ import annotations

import copy
import math
from tkinter import Canvas, Scrollbar, Toplevel, messagebox, simpledialog

import customtkinter as ctk
from PIL import Image, ImageTk

from services.croquis_documento import (
    CroquisDocumento, WIDTH, HEIGHT, bounds, hit_test, translate, resize, rotate_90, text_bitmap,
)
from ui.colors import SECONDARY, BUTTON_HOVER, TEXT_PRIMARY, TEXT_SECONDARY, WHITE
from utils import centrar_ventana

TOOLS = (
    ("Seleccionar", "select"), ("Lápiz", "stroke"), ("Borrador", "erase"),
    ("Línea", "line"), ("Flecha", "arrow"), ("Rectángulo", "rectangle"),
    ("Círculo / óvalo", "ellipse"), ("Texto", "text"),
)
COLORS = ("#172554", "#0369F8", "#16A34A", "#DC2626", "#F59E0B", "#7C3AED", "#111827")
DARK = "#0F2337"
SURFACE = "#F5F8FC"


def anotacion_plano_popup(parent, variable_base64, on_change=None, titulo="Anotaciones tipo plano"):
    """Abre un editor modal sin cambiar el contrato PNG Base64 existente."""
    try:
        doc = CroquisDocumento(str(variable_base64.get() or "").strip())
    except Exception as exc:
        messagebox.showerror("Editor de croquis", f"No se pudo abrir la anotación:\n{exc}", parent=parent)
        return

    win = Toplevel(parent)
    win.title(titulo)
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    ww = min(1380, max(900, int(sw * .94)))
    wh = min(850, max(640, int(sh * .87)))
    win.minsize(900, 630)
    win.transient(parent.winfo_toplevel())
    centrar_ventana(win, ww, wh, padre=parent.winfo_toplevel())
    win.grab_set()

    state = {"tool": "select", "color": COLORS[0], "width": 3, "zoom": .80,
             "selected": None, "start": None, "last": None, "preview": None,
             "drag": None, "before": None, "initial": None,
             "bg_key": None, "bg_image": None, "grid": False, "text_images": []}

    root = ctk.CTkFrame(win, fg_color=WHITE, corner_radius=0)
    root.pack(fill="both", expand=True)

    top = ctk.CTkFrame(root, fg_color=WHITE, corner_radius=0)
    top.pack(fill="x", padx=15, pady=(10, 6))
    ctk.CTkLabel(top, text="AXIA  |  Editor de croquis", font=("Montserrat", 19, "bold"),
                 text_color=TEXT_PRIMARY).pack(anchor="w")
    ctk.CTkLabel(top, text="Dibuja, selecciona y modifica elementos. Los cambios se guardan al pulsar 'Guardar croquis'.",
                 font=("Montserrat", 10), text_color=TEXT_SECONDARY).pack(anchor="w")

    commands = ctk.CTkFrame(root, fg_color="#EFF4FA", corner_radius=10)
    commands.pack(fill="x", padx=12, pady=(0, 7))
    commands_left = ctk.CTkFrame(commands, fg_color="transparent")
    commands_left.pack(side="left", padx=6, pady=5)
    commands_right = ctk.CTkFrame(commands, fg_color="transparent")
    commands_right.pack(side="right", padx=6, pady=5)

    body = ctk.CTkFrame(root, fg_color=WHITE, corner_radius=0)
    body.pack(fill="both", expand=True, padx=12)
    rail = ctk.CTkFrame(body, width=147, fg_color="#F3F6FA", corner_radius=9)
    rail.pack(side="left", fill="y", padx=(0, 8))
    rail.pack_propagate(False)
    ctk.CTkLabel(rail, text="HERRAMIENTAS", font=("Montserrat", 10, "bold"),
                 text_color=TEXT_SECONDARY).pack(pady=(12, 9))
    tool_buttons = {}

    center = ctk.CTkFrame(body, fg_color="#E8EEF5", corner_radius=9)
    center.pack(side="left", fill="both", expand=True)
    canvas_box = ctk.CTkFrame(center, fg_color="transparent")
    canvas_box.pack(fill="both", expand=True, padx=8, pady=8)
    drawing = Canvas(canvas_box, bg="white", highlightthickness=1, highlightbackground="#CBD5E1",
                     xscrollincrement=1, yscrollincrement=1, cursor="crosshair")
    xbar = Scrollbar(canvas_box, orient="horizontal", command=drawing.xview)
    ybar = Scrollbar(canvas_box, orient="vertical", command=drawing.yview)
    drawing.configure(xscrollcommand=xbar.set, yscrollcommand=ybar.set)
    canvas_box.grid_rowconfigure(0, weight=1)
    canvas_box.grid_columnconfigure(0, weight=1)
    # Usamos grid en este marco para conservar ambas barras de desplazamiento.
    drawing.grid(row=0, column=0, sticky="nsew")
    ybar.grid(row=0, column=1, sticky="ns")
    xbar.grid(row=1, column=0, sticky="ew")

    properties = ctk.CTkFrame(body, width=198, fg_color="#F3F6FA", corner_radius=9)
    properties.pack(side="right", fill="y", padx=(8, 0))
    properties.pack_propagate(False)
    ctk.CTkLabel(properties, text="PROPIEDADES", font=("Montserrat", 10, "bold"),
                 text_color=TEXT_SECONDARY).pack(pady=(12, 8))
    selected_info = ctk.CTkLabel(properties, text="Ningún elemento seleccionado",
                                 wraplength=175, justify="left", font=("Montserrat", 10),
                                 text_color=TEXT_SECONDARY)
    selected_info.pack(fill="x", padx=10, pady=(0, 12))
    ctk.CTkLabel(properties, text="Color del trazo / texto", font=("Montserrat", 10),
                 text_color=TEXT_PRIMARY).pack(anchor="w", padx=10)
    palette = ctk.CTkFrame(properties, fg_color="transparent")
    palette.pack(fill="x", padx=8, pady=7)
    palette_buttons = []
    ctk.CTkLabel(properties, text="Grosor del trazo", font=("Montserrat", 10),
                 text_color=TEXT_PRIMARY).pack(anchor="w", padx=10, pady=(7, 4))

    zoom_label = ctk.CTkLabel(commands_right, text="80%", width=45, font=("Montserrat", 11, "bold"),
                              text_color=TEXT_PRIMARY)
    hint = ctk.CTkLabel(center, text="Selecciona un elemento para moverlo o arrastra la esquina para cambiar su tamaño.",
                        font=("Montserrat", 10), text_color=TEXT_SECONDARY)
    hint.pack(fill="x", pady=(0, 7))
    status = ctk.CTkLabel(root, text="", height=20, font=("Montserrat", 10),
                          text_color=TEXT_SECONDARY, anchor="w")
    status.pack(fill="x", padx=18)

    def coords(ev):
        z = state["zoom"]
        return (max(0., min(WIDTH, drawing.canvasx(ev.x) / z)),
                max(0., min(HEIGHT, drawing.canvasy(ev.y) / z)))

    def set_zoom(value):
        state["zoom"] = max(.40, min(2.0, round(value, 2)))
        state["bg_key"] = None
        zoom_label.configure(text=f"{round(state['zoom'] * 100)}%")
        repaint()

    def repaint():
        z = state["zoom"]
        drawing.delete("all")
        state["text_images"] = []  # Referencias vivas de textos girados en Tk.
        drawing.configure(scrollregion=(0, 0, WIDTH * z, HEIGHT * z))
        key = (z, id(doc.background))
        if state["bg_key"] != key:
            background = doc.background.resize((max(1, round(WIDTH*z)), max(1, round(HEIGHT*z))), Image.Resampling.BILINEAR)
            state["bg_image"] = ImageTk.PhotoImage(background)
            state["bg_key"] = key
        drawing.create_image(0, 0, image=state["bg_image"], anchor="nw")
        if state["grid"]:
            spacing = 25
            for x in range(0, WIDTH+1, spacing):
                drawing.create_line(x*z, 0, x*z, HEIGHT*z, fill="#E0E7EF", width=1)
            for y in range(0, HEIGHT+1, spacing):
                drawing.create_line(0, y*z, WIDTH*z, y*z, fill="#E0E7EF", width=1)
        for obj in doc.objects:
            paint_obj(obj, z)
        if state["preview"] is not None:
            paint_obj(state["preview"], z, preview=True)
        index = state["selected"]
        if index is not None and index < len(doc.objects):
            x0,y0,x1,y1 = bounds(doc.objects[index])
            pad = 5
            drawing.create_rectangle((x0-pad)*z,(y0-pad)*z,(x1+pad)*z,(y1+pad)*z,
                                     outline="#0369F8", width=1.5, dash=(5, 3))
            sz = 5
            hx, hy = (x1+pad)*z, (y1+pad)*z
            drawing.create_rectangle(hx-sz,hy-sz,hx+sz,hy+sz,
                                     fill="#0369F8", outline="white", width=2)
        status.configure(text=f"  {len(doc.objects)} objeto(s)   ·   Zoom: {round(z*100)}%   ·   Cuadrícula: {'Sí' if state['grid'] else 'No'}"
                              + ("   ·   Croquis antiguo: el fondo no se puede editar por objetos" if doc.legacy_background else ""))

    def paint_obj(obj, z, preview=False):
        kind = obj["kind"]
        color = "#FFFFFF" if kind == "erase" else obj.get("color", COLORS[0])
        w = max(1, float(obj.get("width", 3)) * z)
        if kind in ("stroke", "erase"):
            points = obj.get("points", [])
            if len(points) > 1:
                flattened = [v*z for p in points for v in p]
                drawing.create_line(*flattened, fill=color, width=w,
                                    capstyle="round", joinstyle="round", smooth=False)
            elif points:
                x,y = points[0]
                drawing.create_oval(x*z-w/2,y*z-w/2,x*z+w/2,y*z+w/2,fill=color,outline=color)
        elif kind in ("line", "arrow"):
            c = [v*z for v in obj["coords"]]
            kw = {"fill":color, "width":w, "capstyle":"round"}
            if kind == "arrow":
                kw.update(arrow="last", arrowshape=(max(9, w*3), max(10, w*3.5), max(4, w*1.6)))
            drawing.create_line(*c, **kw)
        elif kind in ("rectangle", "ellipse"):
            x0,y0,x1,y1 = bounds(obj)
            func = drawing.create_rectangle if kind == "rectangle" else drawing.create_oval
            func(x0*z,y0*z,x1*z,y1*z, outline=color, width=w)
        elif kind == "text":
            if int(obj.get("rotation", 0)) % 360:
                bitmap = text_bitmap(obj)
                bitmap = bitmap.resize((max(1, round(bitmap.width*z)), max(1, round(bitmap.height*z))), Image.Resampling.BILINEAR)
                picture = ImageTk.PhotoImage(bitmap)
                state["text_images"].append(picture)
                drawing.create_image(obj["x"]*z, obj["y"]*z, image=picture, anchor="nw")
            else:
                drawing.create_text(obj["x"]*z,obj["y"]*z,anchor="nw",
                                    text=obj.get("text", ""), fill=color,
                                    font=("Arial", max(8, round(obj.get("size",20)*z))))

    def select_tool(tool):
        state["tool"] = tool
        drawing.configure(cursor="arrow" if tool == "select" else "crosshair")
        for name, btn in tool_buttons.items():
            btn.configure(fg_color=DARK if name == tool else SECONDARY)
        if tool != "select":
            state["selected"] = None
        update_properties()
        repaint()

    for name, code in TOOLS:
        btn = ctk.CTkButton(rail, text=name, anchor="w", height=34, width=132,
                            fg_color=DARK if code == "select" else SECONDARY,
                            hover_color=BUTTON_HOVER, font=("Montserrat", 11),
                            command=lambda val=code: select_tool(val))
        btn.pack(padx=7, pady=3)
        tool_buttons[code] = btn

    def update_properties():
        index = state["selected"]
        if index is not None and index < len(doc.objects):
            obj = doc.objects[index]
            names = dict((code, name) for name, code in TOOLS)
            selected_info.configure(text=f"Seleccionado: {names.get(obj['kind'], obj['kind'])}\n"
                                         f"Haz doble clic para editar texto")
        else:
            selected_info.configure(text="Ningún elemento seleccionado")

    def choose_color(color):
        state["color"] = color
        index = state["selected"]
        if index is not None:
            doc.modify(index, color=color)
        for item, button in palette_buttons:
            button.configure(border_color="#0F2337" if item == color else "#DDE5EC",
                             border_width=3 if item == color else 1)
        repaint()

    for i, color in enumerate(COLORS):
        swatch = ctk.CTkButton(palette, text="", width=22, height=23, corner_radius=5,
                               fg_color=color, hover_color=color,
                               border_color=DARK if i == 0 else "#DDE5EC",
                               border_width=3 if i == 0 else 1,
                               command=lambda v=color: choose_color(v))
        swatch.grid(row=i//5, column=i%5, padx=3, pady=3)
        palette_buttons.append((color, swatch))

    thickness = ctk.CTkOptionMenu(properties, values=["2 px", "3 px", "5 px", "8 px", "12 px"],
                                  width=165, height=29, fg_color=SECONDARY,
                                  button_color=DARK, font=("Montserrat", 11))
    thickness.set("3 px")
    thickness.pack(padx=10, pady=(0, 10))

    def choose_thickness(value):
        number = int(value.split()[0]); state["width"] = number
        index = state["selected"]
        if index is not None:
            doc.modify(index, width=number)
            repaint()
    thickness.configure(command=choose_thickness)

    def selected_required():
        i = state["selected"]
        if i is None or i >= len(doc.objects):
            messagebox.showinfo("Editor de croquis", "Selecciona primero un elemento con la herramienta Seleccionar.", parent=win)
            return None
        return i

    def edit_text(_event=None):
        idx = state["selected"]
        if idx is None or doc.objects[idx]["kind"] != "text":
            return
        old = doc.objects[idx]["text"]
        value = simpledialog.askstring("Editar texto", "Modifica la anotación:", initialvalue=old, parent=win)
        if value is not None and value.strip():
            doc.modify(idx, text=value)
            repaint()

    def duplicate():
        i = selected_required()
        if i is None: return
        state["selected"] = doc.duplicate(i)
        repaint(); update_properties()

    def remove():
        i = selected_required()
        if i is None: return
        doc.delete(i)
        state["selected"] = None
        repaint(); update_properties()

    def rotate_selected():
        i = selected_required()
        if i is None: return
        before = doc.capture()
        rotate_90(doc.objects[i])
        doc.commit(before)
        repaint(); update_properties()

    def change_order(front):
        i = selected_required()
        if i is None: return
        before = doc.capture()
        value = doc.objects.pop(i)
        if front:
            doc.objects.append(value); state["selected"] = len(doc.objects)-1
        else:
            doc.objects.insert(0, value); state["selected"] = 0
        doc.commit(before)
        repaint()

    def prop_button(text, command, color=SECONDARY):
        ctk.CTkButton(properties, text=text, height=30, width=169,
                      fg_color=color, hover_color=BUTTON_HOVER, font=("Montserrat", 10),
                      command=command).pack(padx=9, pady=3)
    prop_button("Editar texto", edit_text)
    prop_button("Duplicar elemento", duplicate)
    prop_button("Girar 90°", rotate_selected)
    prop_button("Traer al frente", lambda: change_order(True))
    prop_button("Enviar al fondo", lambda: change_order(False))
    prop_button("Eliminar seleccionado", remove, color="#DC2626")

    def undo():
        if doc.undo():
            state["selected"] = None
            state["bg_key"] = None
            repaint(); update_properties()

    def redo():
        if doc.redo():
            state["selected"] = None
            state["bg_key"] = None
            repaint(); update_properties()

    def clear():
        if (doc.objects or doc.legacy_background) and not messagebox.askyesno(
                "Limpiar croquis", "¿Borrar todo el contenido? Puedes deshacer esta operación.", parent=win):
            return
        doc.clear(); state["selected"] = None
        state["bg_key"] = None
        repaint(); update_properties()

    def grid_toggle():
        state["grid"] = not state["grid"]
        grid_btn.configure(fg_color=DARK if state["grid"] else SECONDARY)
        repaint()

    def top_button(host, label, cmd, color=SECONDARY, width=89):
        return ctk.CTkButton(host, text=label, height=30, width=width,
                             fg_color=color, hover_color=BUTTON_HOVER,
                             font=("Montserrat", 10, "bold"), command=cmd)

    top_button(commands_left, "↶ Deshacer", undo, width=94).pack(side="left", padx=2)
    top_button(commands_left, "↷ Rehacer", redo, width=94).pack(side="left", padx=2)
    grid_btn = top_button(commands_left, "# Cuadrícula", grid_toggle, width=105)
    grid_btn.pack(side="left", padx=2)
    top_button(commands_left, "Limpiar", clear, color="#DC2626", width=75).pack(side="left", padx=2)
    top_button(commands_right, "−", lambda: set_zoom(state["zoom"] - .15), width=35).pack(side="left", padx=2)
    zoom_label.pack(side="left", padx=3)
    top_button(commands_right, "+", lambda: set_zoom(state["zoom"] + .15), width=35).pack(side="left", padx=2)
    top_button(commands_right, "Ajustar", lambda: fit_zoom(), width=65).pack(side="left", padx=2)

    def fit_zoom():
        usable = max(400, drawing.winfo_width()-25)
        available_h = max(300, drawing.winfo_height()-25)
        set_zoom(min(1, usable / WIDTH, available_h / HEIGHT))

    def initial_object(kind, x, y):
        if kind in ("stroke", "erase"):
            return {"kind":kind, "points":[[x,y]], "color":state["color"],
                    "width":16 if kind == "erase" else state["width"]}
        return {"kind":kind, "coords":[x,y,x,y], "color":state["color"], "width":state["width"]}

    def down(ev):
        x,y = coords(ev)
        state["start"] = (x,y)
        state["last"] = (x,y)
        state["preview"] = None
        state["drag"] = None
        tool = state["tool"]
        if tool == "text":
            value = simpledialog.askstring("Agregar texto", "Escribe una anotación:", parent=win)
            if value and value.strip():
                doc.add({"kind":"text", "text":value, "x":x, "y":y, "size":20, "color":state["color"]})
                repaint()
            return
        if tool == "select":
            selected = state["selected"]
            if selected is not None and selected < len(doc.objects):
                x0,y0,x1,y1 = bounds(doc.objects[selected]); pad=5
                if math.dist((x,y),(x1+pad,y1+pad)) <= 12/state["zoom"]:
                    state["before"] = doc.capture()
                    state["initial"] = copy.deepcopy(doc.objects[selected])
                    state["drag"] = "resize"
                    return
            clicked = hit_test(doc.objects, x, y, 7/state["zoom"])
            state["selected"] = clicked
            if clicked is not None:
                state["before"] = doc.capture()
                state["initial"] = copy.deepcopy(doc.objects[clicked])
                state["drag"] = "move"
            update_properties(); repaint()
        else:
            state["preview"] = initial_object(tool,x,y)
            repaint()

    def motion(ev):
        if state["start"] is None:
            return
        x,y = coords(ev)
        tool = state["tool"]
        if tool == "select":
            idx = state["selected"]
            if idx is None or state["drag"] is None:
                return
            obj = copy.deepcopy(state["initial"])
            if state["drag"] == "move":
                translate(obj, x-state["start"][0], y-state["start"][1])
            else:
                anchor = bounds(state["initial"])[:2]
                resize(obj, anchor, (x,y), state["initial"])
            doc.objects[idx] = obj
        elif state["preview"] is not None:
            if tool in ("stroke", "erase"):
                if math.dist((x,y),state["last"]) >= 1.0:
                    state["preview"]["points"].append([x,y])
            else:
                state["preview"]["coords"][2:] = [x,y]
        state["last"] = (x,y)
        repaint()

    def up(ev):
        if state["start"] is None: return
        x,y = coords(ev)
        if state["tool"] == "select":
            if state["drag"] and state["before"] is not None:
                doc.commit(state["before"])
        elif state["preview"] is not None:
            obj = state["preview"]
            if obj["kind"] in ("stroke", "erase"):
                if len(obj["points"]) == 1:
                    obj["points"].append([x+.1,y+.1])
            else:
                obj["coords"][2:] = [x,y]
            if obj["kind"] in ("stroke", "erase") or math.dist((obj["coords"][0],obj["coords"][1]),(x,y)) >= 3:
                doc.add(obj)
        state["start"] = state["last"] = state["preview"] = None
        state["drag"] = state["before"] = state["initial"] = None
        repaint()

    drawing.bind("<ButtonPress-1>", down)
    drawing.bind("<B1-Motion>", motion)
    drawing.bind("<ButtonRelease-1>", up)
    drawing.bind("<Double-Button-1>", lambda ev: edit_text() if state["tool"] == "select" else None)
    drawing.bind("<Control-MouseWheel>", lambda e: set_zoom(state["zoom"] + (.1 if e.delta>0 else -.1)))
    drawing.bind("<Delete>", lambda ev: remove() if state["selected"] is not None else None)
    win.bind("<Control-z>", lambda ev: undo())
    win.bind("<Control-y>", lambda ev: redo())
    win.bind("<Control-d>", lambda ev: duplicate() if state["selected"] is not None else None)

    bottom = ctk.CTkFrame(root, fg_color=WHITE, corner_radius=0)
    bottom.pack(fill="x", padx=12, pady=(0, 11))
    ctk.CTkButton(bottom, text="Cancelar", width=140, height=35, fg_color="#64748B",
                  command=win.destroy).pack(side="left")

    def save():
        try:
            variable_base64.set(doc.export_base64())
            if on_change:
                on_change()
        except Exception as exc:
            messagebox.showerror("Editor de croquis", f"No fue posible guardar la anotación:\n{exc}", parent=win)
            return
        win.destroy()

    ctk.CTkButton(bottom, text="Guardar croquis", width=175, height=35,
                  fg_color=SECONDARY, hover_color=BUTTON_HOVER,
                  command=save).pack(side="right")
    win.protocol("WM_DELETE_WINDOW", win.destroy)
    win.after(180, fit_zoom)
    repaint()
