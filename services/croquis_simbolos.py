"""Símbolos técnicos propios de AXIA, dibujados vectorialmente (sin recursos externos)."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

SYMBOLS = {
    'camara_bullet': 'Seguridad · Cámara bullet',
    'camara_domo': 'Seguridad · Cámara domo',
    'grabador': 'Seguridad · NVR / DVR',
    'rack': 'Redes · Rack',
    'switch': 'Redes · Switch',
    'punto_red': 'Redes · Punto de datos',
    'wifi': 'Redes · Punto de acceso WiFi',
    'contacto': 'Electricidad · Contacto',
    'luminaria': 'Electricidad · Luminaria',
    'lector': 'Acceso · Lector de tarjeta',
    'aire': 'Climatización · Minisplit',
    'panel': 'Solar · Panel fotovoltaico',
}


def symbol_bitmap(symbol: str, color: str = '#172554', width: int = 128,
                  height: int = 128, rotation: int = 0) -> Image.Image:
    """Genera un pictograma transparente a resolución escalable."""
    w, h = 128, 128
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = 5
    def line(points, size=k): d.line(points, fill=color, width=size, joint='curve')
    def rect(box, rad=7): d.rounded_rectangle(box, radius=rad, outline=color, width=k)
    def ell(box): d.ellipse(box, outline=color, width=k)
    if symbol == 'camara_bullet':
        d.polygon([(23,39),(87,39),(99,60),(35,60)], outline=color); line([(24,39),(88,39),(100,60),(35,60),(24,39)])
        ell((91,43,108,60)); line([(58,61),(58,83),(81,83)]); line([(77,83),(77,101)])
    elif symbol == 'camara_domo':
        ell((22,28,107,107)); line([(24,73),(105,73)]); ell((54,47,75,68))
    elif symbol == 'grabador':
        rect((18,35,110,92)); line([(21,69),(107,69)]); ell((31,76,40,85)); ell((48,76,57,85))
    elif symbol == 'rack':
        rect((35,15,93,115)); [rect((42,y,86,y+20),3) for y in (24,51,78)];
        [d.ellipse((75,y+7,79,y+11), fill=color) for y in (24,51,78)]
    elif symbol == 'switch':
        rect((14,39,114,89)); [d.rectangle((24+i*19,52,35+i*19,64),outline=color,width=3) for i in range(5)]
        ell((91,73,99,81))
    elif symbol == 'punto_red':
        rect((33,24,95,104)); rect((47,38,81,65),2); line([(50,83),(78,83)]); line([(55,64),(55,74),(73,74),(73,64)])
    elif symbol == 'wifi':
        for box in ((14,20,114,120),(30,38,98,106),(45,56,83,94)):
            d.arc(box, 210, 330, fill=color, width=6)
        d.ellipse((59,92,69,102), fill=color)
    elif symbol == 'contacto':
        rect((26,20,102,110),13); d.rounded_rectangle((44,48,52,73),3,fill=color)
        d.rounded_rectangle((76,48,84,73),3,fill=color); ell((59,77,69,88))
    elif symbol == 'luminaria':
        ell((39,27,89,77)); line([(47,73),(53,91),(75,91),(81,73)]); line([(53,100),(76,100)])
        for p in [((64,9),(64,19)),((22,30),(33,38)),((106,30),(95,38)),((22,81),(34,76)),((106,81),(94,76))]: line(p,3)
    elif symbol == 'lector':
        rect((36,16,92,113),9); ell((51,32,77,58)); line([(48,76),(80,76)]); line([(50,91),(77,91)])
    elif symbol == 'aire':
        rect((14,28,114,85),12); line([(29,53),(99,53)]); line([(38,71),(89,71)])
        for x in (38,64,90): line([(x,91),(x-5,110)],3)
    elif symbol == 'panel':
        d.polygon([(26,24),(99,24),(112,88),(15,88)], outline=color)
        line([(26,24),(99,24),(112,88),(15,88),(26,24)])
        line([(53,24),(50,88)],3); line([(78,24),(85,88)],3); line([(20,56),(105,56)],3)
        line([(45,90),(41,106),(84,106),(79,90)],4)
    else:
        rect((21,21,107,107)); line([(64,35),(64,91)]); line([(36,64),(92,64)])
    img = img.rotate(-int(rotation) % 360, expand=False)
    return img.resize((max(1, int(width)), max(1, int(height))), Image.Resampling.LANCZOS)
