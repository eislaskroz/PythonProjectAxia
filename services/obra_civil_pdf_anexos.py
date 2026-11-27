from __future__ import annotations

import hashlib
import io
import os
from collections.abc import Mapping
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfReader, PdfWriter

from services.desktop_evidence_access import EvidenciaNoDisponible
from ui.pdf_progress import progreso_pdf

_MAX_BYTES = 30 * 1024 * 1024
_EXTENSIONS = {'.pdf', '.dwg', '.dxf', '.png', '.jpg', '.jpeg', '.webp'}


def _leer_anexos(items, folio):
    from services import desktop_historical_evidence as historico
    from supabase_config import SUPABASE_URL

    if not isinstance(items, (list, tuple)):
        raise EvidenciaNoDisponible('La lista de anexos de Obra Civil no es válida.')
    lectores = []
    cache = {}
    progreso_pdf('Verificando archivos adjuntos…', 0, len(items))
    for indice, item in enumerate(items, 1):
        try:
            ruta = historico.ruta_historica(item, folio, str(SUPABASE_URL).rstrip('/'))
            if ruta:
                if not ruta.startswith('obras-civiles-archivos/'):
                    raise ValueError('Módulo incorrecto')
                extension = Path(ruta).suffix.lower()
                if ruta not in cache:
                    if historico.consulta_historica_activa():
                        cache[ruta] = historico.descargar_archivo_historico(ruta, folio)
                    else:
                        from supabase_config import supabase
                        cache[ruta] = supabase.storage.from_(historico.BUCKET).download(ruta)
                raw = cache[ruta]
            else:
                if isinstance(item, Mapping) or not isinstance(item, (str, Path)):
                    raise ValueError('Referencia no autorizada')
                local = Path(item)
                extension = local.suffix.lower()
                if not local.is_file() or not 0 < local.stat().st_size <= _MAX_BYTES:
                    raise ValueError('Archivo local no disponible')
                raw = local.read_bytes()
            if extension not in _EXTENSIONS or not 0 < len(raw) <= _MAX_BYTES:
                raise ValueError('Archivo inválido')
            if isinstance(item, Mapping):
                sha256 = item.get('sha256')
                size = item.get('size_bytes')
                if sha256 and hashlib.sha256(raw).hexdigest() != sha256:
                    raise ValueError('Hash de anexo incorrecto')
                if size is not None and int(size) != len(raw):
                    raise ValueError('Tamaño de anexo incorrecto')
            mime = str(item.get('mime') or item.get('mime_type') or '').lower() if isinstance(item, Mapping) else ''
            if extension == '.pdf' or mime == 'application/pdf':
                if extension != '.pdf' or not raw.startswith(b'%PDF-'):
                    raise ValueError('Formato PDF incorrecto')
                lector = PdfReader(io.BytesIO(raw))
                if lector.is_encrypted or not len(lector.pages):
                    raise ValueError('PDF vacío o protegido')
                if any(pagina.get('/Annots') for pagina in lector.pages):
                    import fitz
                    with fitz.open(stream=raw, filetype='pdf') as documento:
                        documento.bake(annots=True, widgets=True)
                        lector = PdfReader(io.BytesIO(documento.tobytes()))
                lectores.append(lector)
        except EvidenciaNoDisponible:
            raise
        except Exception:
            raise EvidenciaNoDisponible(f'No se pudo recuperar o validar el anexo {indice} de Obra Civil. No se generó el PDF.') from None
        progreso_pdf('Verificando archivos adjuntos…', indice, len(items))
    return lectores


def generar_con_anexos_obra_civil(destino, items, folio, renderizar):
    destino = Path(destino)
    lectores = _leer_anexos(items, folio)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='.axia_obc_', dir=destino.parent) as temporal:
        base = Path(temporal) / 'base.pdf'
        final = Path(temporal) / 'final.pdf'
        progreso_pdf('Generando documento de Obra Civil…')
        if not renderizar(base) or not base.is_file():
            raise EvidenciaNoDisponible('No se pudo generar el documento de Obra Civil.')
        if not lectores:
            os.replace(base, destino)
            return str(destino)
        try:
            writer = PdfWriter()
            lector_base = PdfReader(base)
            if lector_base.metadata:
                writer.add_metadata({str(k): str(v) for k, v in lector_base.metadata.items() if v is not None})
            for pagina in lector_base.pages:
                writer.add_page(pagina)
            total = sum(len(lector.pages) for lector in lectores)
            completadas = 0
            progreso_pdf('Incorporando páginas de los PDF adjuntos…', 0, total)
            for lector in lectores:
                for pagina in lector.pages:
                    writer.add_page(pagina, excluded_keys=['/Annots', '/AA'])
                    completadas += 1
                    progreso_pdf('Incorporando páginas de los PDF adjuntos…', completadas, total)
            progreso_pdf('Guardando PDF completo…')
            with final.open('wb') as stream:
                writer.write(stream)
            os.replace(final, destino)
        except Exception:
            raise EvidenciaNoDisponible('No fue posible incorporar todos los PDF adjuntos. Se conservó el documento anterior, si existía.') from None
    return str(destino)
