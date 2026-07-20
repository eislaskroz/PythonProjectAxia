"""Generación de PDF operativo a partir de registros recuperados de Supabase."""

from __future__ import annotations

import json
import re
from pathlib import Path
from tkinter import filedialog, messagebox

from views.formato_helpers import generar_pdf_preview


def _etiqueta(campo: str) -> str:
    texto = str(campo or "").strip()
    texto = re.sub(r"^(lev|os|ot|bit|obc|aco|usu|cli|suc)_", "", texto, flags=re.I)
    texto = texto.replace("_json", "").replace("_", " ")
    return texto[:1].upper() + texto[1:]


def _valor_texto(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False, indent=2, default=str)
    return str(valor)


def _aplanar(registro: dict) -> dict:
    """Convierte el registro y sus JSON anidados en campos legibles para el PDF."""
    datos = {}
    bloques = []

    for campo, valor in (registro or {}).items():
        if valor in (None, "", [], {}):
            continue

        etiqueta = _etiqueta(campo)
        if isinstance(valor, dict):
            bloques.append(f"--- {etiqueta.upper()} ---")
            for subcampo, subvalor in valor.items():
                if subvalor in (None, "", [], {}):
                    continue
                if isinstance(subvalor, dict):
                    bloques.append(f"{_etiqueta(subcampo)}:")
                    for clave2, valor2 in subvalor.items():
                        if valor2 not in (None, "", [], {}):
                            bloques.append(f"  {_etiqueta(clave2)}: {_valor_texto(valor2)}")
                elif isinstance(subvalor, list):
                    bloques.append(f"{_etiqueta(subcampo)}: {_valor_texto(subvalor)}")
                else:
                    bloques.append(f"{_etiqueta(subcampo)}: {_valor_texto(subvalor)}")
        elif isinstance(valor, list):
            bloques.append(f"--- {etiqueta.upper()} ---")
            for indice, item in enumerate(valor, start=1):
                bloques.append(f"Elemento {indice}: {_valor_texto(item)}")
        else:
            datos[etiqueta] = _valor_texto(valor)

    # Claves esperadas por la plantilla corporativa, tomadas del registro original.
    folios = {
        "lev_folio": "Folio LEV",
        "os_folio": "Folio OS",
        "ot_folio": "Folio OT",
        "bit_folio": "Folio BIT",
        "obc_folio": "Folio OBC",
    }
    for campo, etiqueta_pdf in folios.items():
        valor = (registro or {}).get(campo)
        if str(valor or "").strip():
            datos[etiqueta_pdf] = str(valor).strip()
            break

    for campo in ("lev_fecha", "lev_fecha_programada", "os_fecha", "os_fecha_programada", "ot_fecha", "ot_fecha_programada", "bit_fecha", "obc_fecha", "created_at"):
        valor = (registro or {}).get(campo)
        if str(valor or "").strip():
            datos["Fecha"] = str(valor).strip()
            break

    if bloques:
        datos["Detalle técnico"] = "\n".join(bloques)
    return datos


def _titulo_y_folio(registro: dict, configuracion: dict | None = None):
    configuracion = configuracion or {}
    titulo = configuracion.get("titulo_pdf") or configuracion.get("titulo") or "Registro AXIA"
    campo_folio = configuracion.get("campo_folio")
    folio = str((registro or {}).get(campo_folio) or "") if campo_folio else ""
    if not folio:
        for campo in ("lev_folio", "os_folio", "ot_folio", "bit_folio", "obc_folio", "aco_numero"):
            if str((registro or {}).get(campo) or "").strip():
                folio = str(registro[campo]).strip()
                break
    return titulo, folio or "registro_AXIA"


def previsualizar_pdf_registro(registro: dict, configuracion: dict | None = None) -> bool:
    """Regenera el PDF con la información actual y lo abre en el visor predeterminado."""
    if not registro:
        messagebox.showwarning("Vista previa PDF", "No hay un registro seleccionado.")
        return False
    titulo, _folio = _titulo_y_folio(registro, configuracion)
    return bool(generar_pdf_preview(titulo, _aplanar(registro), abrir=True))


def guardar_pdf_registro(registro: dict, configuracion: dict | None = None) -> bool:
    """Regenera el PDF y permite elegir dónde guardarlo."""
    if not registro:
        messagebox.showwarning("Guardar PDF", "No hay un registro seleccionado.")
        return False

    titulo, folio = _titulo_y_folio(registro, configuracion)
    ruta = filedialog.asksaveasfilename(
        title="Guardar PDF regenerado",
        defaultextension=".pdf",
        initialfile=f"AXIA_{folio}.pdf",
        filetypes=[("Documento PDF", "*.pdf")],
    )
    if not ruta:
        return False

    resultado = generar_pdf_preview(
        titulo,
        _aplanar(registro),
        ruta_salida=Path(ruta),
        abrir=False,
    )
    if resultado:
        messagebox.showinfo("Guardar PDF", f"PDF regenerado correctamente:\n{ruta}")
        return True
    return False
