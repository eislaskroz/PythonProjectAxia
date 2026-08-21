"""Fondos temáticos para los formularios de levantamiento AXIA.

El wallpaper se implementa como un widget hijo colocado con ``place`` dentro
del área desplazable del formulario. No participa en ``pack``/``grid`` y se
crea ANTES que los controles, por lo que permanece visualmente detrás de ellos
sin quedar oculto debajo del canvas interno de CustomTkinter.

La imagen se aclara y se repite en mosaico a lo ancho y a lo largo de todo el
contenido para conservar el efecto tipo WhatsApp incluso en formularios largos.
"""
from pathlib import Path
import tkinter as tk
from PIL import Image, ImageTk

_BACKGROUND_FILES = {
    "Seguridad y Monitoreo": "fondo_seguridad_monitoreo.png",
    "Redes Voz y Datos": "fondo_redes_voz_datos.png",
    "Control de Accesos": "fondo_control_accesos.png",
    "Enlaces Inalámbricos": "fondo_enlaces_inalambricos.png",
    "Tecnología, Equipos y Periféricos": "fondo_tecnologia.png",
    "Electricidad": "fondo_electricidad.png",
    "Paneles Solares": "fondo_paneles_solares.png",
    "Plantas de Energía": "fondo_plantas_energia.png",
    "Aires Acondicionados": "fondo_aires_acondicionados.png",
}

_SOURCE_CACHE = {}


def _ruta_fondo(tipo_levantamiento):
    nombre = _BACKGROUND_FILES.get(tipo_levantamiento)
    if not nombre:
        return None
    return Path(__file__).resolve().parent.parent / "assets" / nombre


def _cargar_fuente(ruta: Path):
    key = str(ruta)
    if key not in _SOURCE_CACHE:
        with Image.open(ruta) as src:
            _SOURCE_CACHE[key] = src.convert("RGB").copy()
    return _SOURCE_CACHE[key]


def _preparar_wallpaper(ruta: Path, size, intensidad=0.20):
    """Construye un wallpaper suave y repetido sin deformar la ilustración.

    El mosaico usa aproximadamente 55 % del ancho disponible. Esto mantiene
    los iconos a una escala parecida a un fondo de WhatsApp y permite repetir
    el patrón horizontal y verticalmente en formularios extensos.
    """
    target_w = max(1, int(size[0]))
    target_h = max(1, int(size[1]))
    img = _cargar_fuente(ruta)

    tile_w = min(target_w, max(420, int(target_w * 0.55)))
    scale = tile_w / max(1, img.width)
    tile_h = max(1, int(img.height * scale))
    tile = img.resize((tile_w, tile_h), Image.Resampling.LANCZOS)

    # Atenuación: 10 % imagen / 90 % blanco. El dibujo sigue identificable,
    # pero no compite con textos, Entry, ComboBox ni botones.
    white = Image.new("RGB", tile.size, "white")
    tile = Image.blend(white, tile, max(0.0, min(1.0, float(intensidad))))

    wallpaper = Image.new("RGB", (target_w, target_h), "white")
    y = 0
    fila = 0
    while y < target_h:
        # Desfase alternado para evitar una cuadrícula rígida de mosaicos.
        offset_x = -(tile_w // 2) if fila % 2 else 0
        x = offset_x
        while x < target_w:
            wallpaper.paste(tile, (x, y))
            x += tile_w
        y += tile_h
        fila += 1
    return wallpaper


def instalar_fondo_en_frame(frame, tipo_levantamiento, intensidad=0.10):
    """Instala un wallpaper real detrás de todo el contenido del formulario.

    ``frame`` puede ser el contenedor principal o una subsección visual. En
    subsecciones permite que el mismo patrón se vea dentro de las tarjetas
    claras, evitando bloques blancos que corten el wallpaper. El ``tk.Label`` se crea inmediatamente y con ``place``;
    por ello no consume espacio. Al estar creado antes que el resto de widgets,
    los controles posteriores quedan naturalmente encima.
    """
    ruta = _ruta_fondo(tipo_levantamiento)
    if ruta is None or not ruta.exists():
        return None

    # No bajar este widget con lower()/tag_lower(): eso lo colocaría por debajo
    # del canvas/fondo opaco de CustomTkinter y volvería invisible la imagen.
    fondo = tk.Label(
        frame,
        bd=0,
        highlightthickness=0,
        relief="flat",
        takefocus=0,
        bg="white",
    )
    fondo.place(x=0, y=0, relwidth=1, relheight=1)

    state = {
        "after_id": None,
        "photo": None,
        "widget": fondo,
        "last_size": None,
    }
    frame._axia_background_state = state

    def _render():
        state["after_id"] = None
        try:
            if not frame.winfo_exists() or not fondo.winfo_exists():
                return
        except Exception:
            return

        # En CTkScrollableFrame el frame interior crece con el contenido. Al
        # usar sus dimensiones reales, el wallpaper cubre también la zona que
        # sólo aparece al hacer scroll.
        try:
            frame.update_idletasks()
        except Exception:
            pass
        width = max(1, frame.winfo_width())
        height = max(1, frame.winfo_height())
        size = (width, height)
        if size == state["last_size"] or width < 40 or height < 40:
            return
        state["last_size"] = size

        wallpaper = _preparar_wallpaper(ruta, size, intensidad=intensidad)
        photo = ImageTk.PhotoImage(wallpaper, master=fondo)
        state["photo"] = photo
        fondo.configure(image=photo)
        fondo.place_configure(x=0, y=0, relwidth=1, relheight=1)

    def _schedule(_event=None):
        if state["after_id"] is not None:
            try:
                frame.after_cancel(state["after_id"])
            except Exception:
                pass
        # Un pequeño retardo deja que grid/pack terminen de calcular la altura
        # completa del contenido antes de generar el mosaico.
        state["after_id"] = frame.after(40, _render)

    frame.bind("<Configure>", _schedule, add="+")
    _schedule()
    return state
