from __future__ import annotations

import io
from pathlib import Path
from PIL import Image, ImageOps

MAX_BYTES = 10485760
MAX_PIXELS = 25_000_000
FORMATS = {'JPEG': ('.jpg', 'image/jpeg'), 'PNG': ('.png', 'image/png'), 'WEBP': ('.webp', 'image/webp')}
EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}


def preparar_imagen(archivo, *, max_bytes=MAX_BYTES):
    archivo = Path(archivo)
    with archivo.open('rb') as fh:
        raw = fh.read(max_bytes + 1)
    if not 0 < len(raw) <= max_bytes:
        raise ValueError(f'{archivo.name}: archivo vacío o superior al límite de {max_bytes // 1048576} MiB.')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            fmt = image.format
            if fmt not in FORMATS or image.width * image.height > MAX_PIXELS or getattr(image, 'n_frames', 1) != 1:
                raise ValueError('Formato, dimensiones o animación no permitidos.')
            image.load()
            ext, mime = FORMATS[fmt]
            original_ext = archivo.suffix.lower()
            matches = original_ext == ext or (fmt == 'JPEG' and original_ext == '.jpeg')
            if matches and (fmt != 'JPEG' or raw.endswith(b'\xff\xd9')):
                return raw, archivo.name, original_ext[1:], mime
            normalized = ImageOps.exif_transpose(image)
            mode = 'RGBA' if 'A' in normalized.getbands() or 'transparency' in normalized.info else 'RGB'
            out = io.BytesIO()
            normalized.convert(mode).save(out, format='PNG')
            raw = out.getvalue()
            if len(raw) > max_bytes:
                raise ValueError(f'La imagen normalizada supera {max_bytes // 1048576} MiB.')
            return raw, archivo.stem + '.png', 'png', 'image/png'
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ValueError(f'{archivo.name}: imagen no válida o incompatible ({exc}).') from None


def validar_imagenes(rutas):
    for ruta in rutas or []:
        preparar_imagen(ruta)
