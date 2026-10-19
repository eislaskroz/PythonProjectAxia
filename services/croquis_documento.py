"""Documento de croquis AXIA: capas editables dentro del mismo PNG Base64.

La interfaz y el PDF ENGINE siguen recibiendo PNG Base64. Los objetos se guardan
como metadatos del PNG; los levantamientos antiguos sin metadatos son una capa
raster de fondo, preservada al guardar. La cuadrícula es solo de edición.
"""
from __future__ import annotations

import base64
import copy
import io
import json
import math
from typing import Any

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

WIDTH, HEIGHT = 980, 460
PNG_KEY = "axia_croquis_document_v1"
BASE_KEY = "axia_croquis_background_v1"
MAX_UNDO = 30


def _font(size: int):
    for name in ("arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, max(10, int(size)))
        except (OSError, ValueError):
            pass
    return ImageFont.load_default()


def bounds(obj: dict) -> tuple[float, float, float, float]:
    kind = obj["kind"]
    if kind in ("stroke", "erase"):
        points = obj.get("points", [])
        if not points:
            return (0, 0, 0, 0)
        return (min(p[0] for p in points), min(p[1] for p in points),
                max(p[0] for p in points), max(p[1] for p in points))
    if kind == "text":
        x, y = obj["x"], obj["y"]
        size = int(obj.get("size", 20))
        lines = str(obj.get("text", "")).split("\n")
        width = max(8, max(len(line) for line in lines) * size * .58)
        height = max(16, len(lines) * size * 1.3)
        if int(obj.get("rotation", 0)) % 180 == 90:
            width, height = height, width
        return (x, y, x + width, y + height)
    x0, y0, x1, y1 = obj["coords"]
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


def translate(obj: dict, dx: float, dy: float) -> None:
    if obj["kind"] in ("stroke", "erase"):
        obj["points"] = [[x + dx, y + dy] for x, y in obj["points"]]
    elif obj["kind"] == "text":
        obj["x"] += dx
        obj["y"] += dy
    else:
        c = obj["coords"]
        obj["coords"] = [c[0] + dx, c[1] + dy, c[2] + dx, c[3] + dy]


def resize(obj: dict, anchor: tuple[float, float], point: tuple[float, float], initial: dict) -> None:
    """Reescala el objeto tomando como ancla su esquina superior izquierda."""
    x0, y0, x1, y1 = bounds(initial)
    sx = (point[0] - anchor[0]) / max(1, x1 - x0)
    sy = (point[1] - anchor[1]) / max(1, y1 - y0)
    sx = max(.1, min(12., sx))
    sy = max(.1, min(12., sy))
    kind = initial["kind"]
    if kind in ("stroke", "erase"):
        obj["points"] = [[anchor[0] + (x - anchor[0]) * sx,
                          anchor[1] + (y - anchor[1]) * sy]
                         for x, y in initial["points"]]
    elif kind == "text":
        obj["size"] = max(10, min(150, round(initial.get("size", 20) * max(sx, sy))))
    else:
        c = initial["coords"]
        obj["coords"] = [anchor[0] + (c[0] - anchor[0]) * sx,
                         anchor[1] + (c[1] - anchor[1]) * sy,
                         anchor[0] + (c[2] - anchor[0]) * sx,
                         anchor[1] + (c[3] - anchor[1]) * sy]


def rotate_90(obj: dict) -> None:
    """Rota un elemento 90° en sentido horario, conservando su posición central."""
    kind = obj["kind"]
    if kind == "text":
        obj["rotation"] = (int(obj.get("rotation", 0)) + 90) % 360
        return
    x0, y0, x1, y1 = bounds(obj)
    cx, cy = (x0+x1)/2, (y0+y1)/2
    def rotated(x, y):
        return [cx - (y - cy), cy + (x - cx)]
    if kind in ("stroke", "erase"):
        obj["points"] = [rotated(x, y) for x, y in obj["points"]]
    elif kind in ("line", "arrow"):
        a,b,c,d = obj["coords"]
        obj["coords"] = rotated(a,b) + rotated(c,d)
    else:
        w, h = x1-x0, y1-y0
        obj["coords"] = [cx-h/2, cy-w/2, cx+h/2, cy+w/2]


def text_bitmap(obj: dict) -> Image.Image:
    """Texto transparente de Pillow para rotación sin alterar la salida PNG."""
    font = _font(obj.get("size", 20))
    content = str(obj.get("text", ""))
    trial = Image.new("RGBA", (1,1), (0,0,0,0))
    bbox = ImageDraw.Draw(trial).multiline_textbbox((0,0), content, font=font, spacing=3)
    width = max(1, int(bbox[2]-bbox[0])+4)
    height = max(1, int(bbox[3]-bbox[1])+4)
    img = Image.new("RGBA", (width,height), (0,0,0,0))
    ImageDraw.Draw(img).multiline_text((2-bbox[0],2-bbox[1]), content, font=font,
                                     fill=obj.get("color", "#172554"), spacing=3)
    angle = int(obj.get("rotation",0)) % 360
    return img.rotate(-angle, expand=True) if angle else img


def _segment_distance(x, y, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    den = vx * vx + vy * vy
    t = max(0., min(1., ((x - ax) * vx + (y - ay) * vy) / den)) if den else 0.
    return math.hypot(x - (ax + t * vx), y - (ay + t * vy))


def hit_test(objects: list[dict], x: float, y: float, tolerance: float = 8) -> int | None:
    """Obtiene el objeto visible de mayor prioridad bajo el puntero."""
    for i in range(len(objects) - 1, -1, -1):
        obj = objects[i]
        kind = obj["kind"]
        x0, y0, x1, y1 = bounds(obj)
        tol = max(tolerance, float(obj.get("width", 3)) / 2 + 2)
        if kind == "text":
            if x0 - tol <= x <= x1 + tol and y0 - tol <= y <= y1 + tol:
                return i
        elif kind in ("stroke", "erase"):
            p = obj.get("points", [])
            if p and (len(p) == 1 and math.dist((x,y), p[0]) <= tol or
                      any(_segment_distance(x, y, *a, *b) <= tol for a, b in zip(p, p[1:]))):
                return i
        elif kind in ("line", "arrow"):
            if _segment_distance(x, y, *obj["coords"]) <= tol:
                return i
        elif kind == "rectangle":
            if x0 - tol <= x <= x1 + tol and y0 - tol <= y <= y1 + tol:
                return i
        elif kind == "ellipse":
            rx, ry = max(1, (x1 - x0) / 2), max(1, (y1 - y0) / 2)
            k = math.hypot((x - (x0+x1)/2) / rx, (y - (y0+y1)/2) / ry)
            if k <= 1 + tol / min(rx, ry):
                return i
    return None


def render_object(draw: ImageDraw.ImageDraw, obj: dict) -> None:
    kind = obj["kind"]
    color = "white" if kind == "erase" else obj.get("color", "#172554")
    width = max(1, int(obj.get("width", 3)))
    if kind in ("stroke", "erase"):
        p = [tuple(map(float, v)) for v in obj.get("points", [])]
        if len(p) > 1:
            draw.line(p, fill=color, width=width, joint="curve")
            rad = width / 2
            for px, py in (p[0], p[-1]):
                draw.ellipse((px-rad,py-rad,px+rad,py+rad), fill=color)
        elif p:
            x, y = p[0]; rad = width / 2
            draw.ellipse((x-rad,y-rad,x+rad,y+rad), fill=color)
    elif kind in ("line", "arrow"):
        x0, y0, x1, y1 = obj["coords"]
        draw.line((x0,y0,x1,y1), fill=color, width=width)
        if kind == "arrow":
            angle = math.atan2(y1-y0, x1-x0)
            tip = max(11, width * 3)
            p1 = (x1-tip*math.cos(angle-.48), y1-tip*math.sin(angle-.48))
            p2 = (x1-tip*math.cos(angle+.48), y1-tip*math.sin(angle+.48))
            draw.polygon([(x1,y1),p1,p2], fill=color)
    elif kind in ("rectangle", "ellipse"):
        x0,y0,x1,y1 = bounds(obj)
        rect = (x0,y0,max(x0+1,x1),max(y0+1,y1))
        if kind == "rectangle":
            draw.rectangle(rect, outline=color, width=width)
        else:
            draw.ellipse(rect, outline=color, width=width)
    elif kind == "text":
        draw.multiline_text((obj["x"], obj["y"]), obj.get("text", ""),
                            font=_font(obj.get("size", 20)), fill=color, spacing=3)


class CroquisDocumento:
    def __init__(self, image_b64: str = ""):
        self.background = Image.new("RGB", (WIDTH, HEIGHT), "white")
        self.objects: list[dict[str, Any]] = []
        self.legacy_background = False
        self.undo_stack: list[tuple] = []
        self.redo_stack: list[tuple] = []
        if image_b64:
            self.load(image_b64)

    def load(self, image_b64: str):
        data = base64.b64decode(image_b64)
        with Image.open(io.BytesIO(data)) as source:
            metadata = source.info.get(PNG_KEY)
            if metadata:
                payload = json.loads(metadata)
                if payload.get("version") != 1 or not isinstance(payload.get("objects"), list):
                    raise ValueError("Versión de croquis no compatible")
                self.objects = payload["objects"]
                background_data = source.info.get(BASE_KEY)
                if background_data:
                    with Image.open(io.BytesIO(base64.b64decode(background_data))) as bkg:
                        self.background = bkg.convert("RGB").resize((WIDTH, HEIGHT))
                    self.legacy_background = True
                else:
                    self.background = Image.new("RGB", (WIDTH, HEIGHT), "white")
            else:
                self.background = source.convert("RGB").resize((WIDTH, HEIGHT))
                self.legacy_background = True
                self.objects = []

    def capture(self):
        return (copy.deepcopy(self.objects), self.background.copy(), self.legacy_background)

    def commit(self, previous):
        if self.objects != previous[0] or self.background.tobytes() != previous[1].tobytes():
            self.undo_stack.append(previous)
            if len(self.undo_stack) > MAX_UNDO:
                self.undo_stack.pop(0)
            self.redo_stack.clear()
            return True
        return False

    def add(self, obj: dict):
        before = self.capture()
        self.objects.append(copy.deepcopy(obj))
        self.commit(before)

    def modify(self, index: int, **changes):
        before = self.capture()
        self.objects[index].update(changes)
        self.commit(before)

    def delete(self, index: int):
        before = self.capture()
        del self.objects[index]
        self.commit(before)

    def duplicate(self, index: int) -> int:
        obj = copy.deepcopy(self.objects[index]); translate(obj, 18, 18)
        self.add(obj)
        return len(self.objects) - 1

    def clear(self):
        before = self.capture()
        self.background = Image.new("RGB", (WIDTH, HEIGHT), "white")
        self.legacy_background = False
        self.objects.clear()
        self.commit(before)

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        self.redo_stack.append(self.capture())
        self.objects, self.background, self.legacy_background = self.undo_stack.pop()
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            return False
        self.undo_stack.append(self.capture())
        self.objects, self.background, self.legacy_background = self.redo_stack.pop()
        return True

    def render(self) -> Image.Image:
        img = self.background.copy()
        draw = ImageDraw.Draw(img)
        for obj in self.objects:
            if obj.get("kind") == "text" and int(obj.get("rotation", 0)) % 360:
                bitmap = text_bitmap(obj)
                img.paste(bitmap, (int(obj["x"]), int(obj["y"])), bitmap)
            else:
                render_object(draw, obj)
        return img

    def export_base64(self) -> str:
        result = self.render()
        info = PngImagePlugin.PngInfo()
        doc = {"version": 1, "width": WIDTH, "height": HEIGHT, "objects": self.objects}
        info.add_text(PNG_KEY, json.dumps(doc, ensure_ascii=False, separators=(",", ":")), zip=True)
        if self.legacy_background:
            buffer = io.BytesIO()
            self.background.save(buffer, "PNG", optimize=True)
            info.add_text(BASE_KEY, base64.b64encode(buffer.getvalue()).decode("ascii"), zip=True)
        output = io.BytesIO()
        result.save(output, format="PNG", pnginfo=info, optimize=True)
        return base64.b64encode(output.getvalue()).decode("ascii")
