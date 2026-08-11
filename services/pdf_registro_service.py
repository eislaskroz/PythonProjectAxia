"""PDF corporativo y legible para registros recuperados de Supabase."""
from __future__ import annotations

import json
import re
from pathlib import Path
from tkinter import filedialog, messagebox

from services.axia_pdf_engine import AxiaPdfEngine
from services.axia_pdf_artifacts import AxiaPdfArtifactStore, PDF_RENDERER_VERSION
from services.levantamiento_seguridad_pdf import (
    es_levantamiento,
    generar_pdf_levantamiento_maestro,
)

PREFIJOS = re.compile(r"^(lev|os|ot|bit|obc|aco|usu|cli|suc)_", re.I)
VACIOS = (None, "", [], {})

ETIQUETAS = {
    "id": "Identificador",
    "folio": "Folio",
    "aco_numero": "Número de ACO",
    "cliente": "Cliente",
    "contacto": "Contacto",
    "telefono": "Teléfono",
    "correo": "Correo electrónico",
    "direccion": "Dirección",
    "ubicacion": "Ubicación",
    "estatus": "Estatus",
    "prioridad": "Prioridad",
    "creado_por": "Creado por",
    "created_at": "Fecha de registro",
    "updated_at": "Última actualización",
    "fecha_actualizacion": "Última actualización",
    "fecha_programada": "Fecha programada",
    "descripcion": "Descripción",
    "observaciones": "Observaciones",
    "modalidad_operativa": "Modalidad operativa",
    "tipo_levantamiento": "Especialidad del levantamiento",
    "infraestructura_existente": "Infraestructura existente",
    "existe_infraestructura": "¿Existe infraestructura?",
    "tipo_infraestructura_existente": "Tipo de infraestructura existente",
    "infraestructura_requerida": "Infraestructura requerida",
    "rack_gabinete_energia": "Rack, gabinete y energía",
    "acceso_alturas_riesgos": "Acceso, alturas y riesgos",
    "datos_tecnicos_cctv": "Datos técnicos de seguridad y monitoreo",
    "equipos_principales": "Equipos principales requeridos",
    "materiales_miscelaneos": "Materiales misceláneos y consumibles",
    "equipos_danados": "Equipos dañados",
    "canalizacion": "Canalización",
    "cable": "Cableado",
    "tipo": "Tipo",
    "metros": "Metros",
    "cantidad": "Cantidad",
    "marca": "Marca",
    "modelo": "Modelo",
    "numero_serie": "Número de serie",
    "especificaciones": "Especificaciones",
    "especificacion": "Especificación",
    "caracteristicas": "Características",
    "categoria": "Categoría",
    "familia": "Familia",
    "subfamilia": "Subfamilia",
    "material": "Material",
    "unidad": "Unidad",
    "tipo_equipo": "Tipo de equipo",
    "rack_requerido": "¿Se requiere rack?",
    "tipo_rack": "Tipo de rack",
    "gabinete_requerido": "¿Se requiere gabinete?",
    "tipo_gabinete": "Tipo de gabinete",
    "ups_requerida": "¿Se requiere UPS?",
    "tipo_ups": "Tipo de UPS",
    "contacto_regulado": "¿Se requiere contacto regulado?",
    "detalle_contacto_regulado": "Detalle del contacto regulado",
    "tierra_fisica": "¿Existe tierra física?",
    "detalle_tierra_fisica": "Detalle de tierra física",
    "escalera_andamio": "¿Requiere escalera o andamio?",
    "altura_trabajo": "Altura de trabajo",
    "riesgo_instalacion": "Riesgo de instalación",
    "cantidad_camaras": "Cantidad de cámaras",
    "tipo_camaras": "Tipo de cámaras",
    "dias_trabajo": "Días de trabajo",
    "personas_considerar": "Personas requeridas",
    "ubicacion_nvr_dvr": "Ubicación del NVR/DVR",
    "punto_red": "Punto de red",
    "punto_energia": "Punto de energía",
}

OCULTAR = {
    "firma", "firma_base64", "firma_tecnico", "firma_tecnico_base64",
    "lev_firma", "lev_firma_tecnico", "detalle_tecnico", "requerimientos",
}

# Listas capturadas en formularios que deben presentarse como tablas, no como
# texto corrido. Las columnas conocidas mantienen un orden estable; cualquier
# catálogo nuevo de materiales/equipos/insumos se adapta dinámicamente.
TABLAS_CONOCIDAS = {
    "equipos_principales": (
        "Equipos principales requeridos",
        ("familia", "subfamilia", "cantidad", "marca", "modelo", "caracteristicas"),
    ),
    "materiales_miscelaneos": (
        "Materiales misceláneos y consumibles",
        ("material", "categoria", "cantidad", "unidad", "especificacion"),
    ),
    "equipos_danados": (
        "Equipos dañados",
        ("tipo_equipo", "marca", "modelo", "numero_serie"),
    ),
}

PALABRAS_TABLA = (
    "material", "materiales", "equipo", "equipos", "insumo", "insumos",
    "consumible", "consumibles", "partida", "partidas",
)


def _limpiar_clave(campo: str) -> str:
    clave = PREFIJOS.sub("", str(campo or "").strip())
    return clave.removesuffix("_json")


def _etiqueta(campo: str) -> str:
    clave = _limpiar_clave(campo)
    if clave in ETIQUETAS:
        return ETIQUETAS[clave]
    texto = clave.replace("_", " ").strip()
    return texto[:1].upper() + texto[1:]


def _normalizar(valor):
    if isinstance(valor, str):
        texto = valor.strip()
        if texto and texto[:1] in "[{":
            try:
                return json.loads(texto)
            except Exception:
                return valor
    return valor


def _texto(valor) -> str:
    valor = _normalizar(valor)
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if valor is None:
        return ""
    return str(valor).strip()


def _es_vacio(valor) -> bool:
    valor = _normalizar(valor)
    return valor in VACIOS


def _quitar_resumenes_tabulares(texto: str) -> str:
    """Evita duplicar en texto los registros que ya se muestran como tabla."""
    resultado = str(texto or "")
    patrones = (
        r"(?ims)\n*EQUIPOS PRINCIPALES REQUERIDOS:\s*\n(?:-.*(?:\n|$))*",
        r"(?ims)\n*MATERIALES MISCELÁNEOS Y CONSUMIBLES:\s*\n(?:-.*(?:\n|$))*",
        r"(?ims)\n*---\s*EQUIPOS DAÑADOS\s*---.*?(?=\n---|\Z)",
    )
    for patron in patrones:
        resultado = re.sub(patron, "\n", resultado)
    return re.sub(r"\n{3,}", "\n\n", resultado).strip()


def _es_lista_tabular(campo: str, valor) -> bool:
    if not isinstance(valor, (list, tuple)) or not valor:
        return False
    if not all(isinstance(_normalizar(item), dict) for item in valor):
        return False
    clave = _limpiar_clave(campo).casefold()
    return clave in TABLAS_CONOCIDAS or any(p in clave for p in PALABRAS_TABLA)


def _construir_tabla(campo: str, lista) -> tuple[str, list[str], list[dict]] | None:
    registros = [dict(_normalizar(item)) for item in lista if isinstance(_normalizar(item), dict)]
    if not registros:
        return None
    clave = _limpiar_clave(campo).casefold()
    if clave in TABLAS_CONOCIDAS:
        titulo, claves_columnas = TABLAS_CONOCIDAS[clave]
    else:
        titulo = _etiqueta(campo)
        claves_columnas = tuple(
            dict.fromkeys(
                k for registro in registros for k in registro.keys()
                if _limpiar_clave(k) not in OCULTAR
            )
        )
    columnas = [_etiqueta(k) for k in claves_columnas]
    filas = []
    for registro in registros:
        fila = {}
        for clave_columna, etiqueta in zip(claves_columnas, columnas):
            valor = registro.get(clave_columna, "")
            if isinstance(valor, (dict, list, tuple)):
                valor = json.dumps(valor, ensure_ascii=False)
            fila[etiqueta] = _texto(valor)
        if any(str(v).strip() for v in fila.values()):
            filas.append(fila)
    return (titulo, columnas, filas) if filas else None


def _filas_lista(lista):
    lineas = []
    for indice, item in enumerate(lista, 1):
        item = _normalizar(item)
        if isinstance(item, dict):
            partes = []
            for clave, valor in item.items():
                if _es_vacio(valor) or _limpiar_clave(clave) in OCULTAR:
                    continue
                partes.append(f"{_etiqueta(clave)}: {_texto(valor)}")
            if partes:
                lineas.append(f"Elemento {indice}: " + " | ".join(partes))
        elif not _es_vacio(item):
            lineas.append(f"Elemento {indice}: {_texto(item)}")
    return lineas


def _secciones_desde_dict(diccionario: dict, titulo_raiz: str | None = None, tablas: list | None = None):
    """Convierte JSON anidado en secciones y pares legibles, sin exponer sintaxis JSON."""
    secciones = []
    pares_raiz = []

    for campo, valor in (diccionario or {}).items():
        clave = _limpiar_clave(campo)
        valor = _normalizar(valor)
        if clave in OCULTAR or _es_vacio(valor):
            continue

        if isinstance(valor, dict):
            lineas = []
            for subcampo, subvalor in valor.items():
                subclave = _limpiar_clave(subcampo)
                subvalor = _normalizar(subvalor)
                if subclave in OCULTAR or _es_vacio(subvalor):
                    continue
                if isinstance(subvalor, list):
                    if _es_lista_tabular(subcampo, subvalor):
                        tabla = _construir_tabla(subcampo, subvalor)
                        if tabla and tablas is not None:
                            tablas.append(tabla)
                    else:
                        lineas.extend(_filas_lista(subvalor))
                elif isinstance(subvalor, dict):
                    for k2, v2 in subvalor.items():
                        if not _es_vacio(v2):
                            lineas.append(f"{_etiqueta(k2)}: {_texto(v2)}")
                else:
                    lineas.append(f"{_etiqueta(subcampo)}: {_texto(subvalor)}")
            if lineas:
                secciones.append((_etiqueta(campo), lineas))
        elif isinstance(valor, list):
            if _es_lista_tabular(campo, valor):
                tabla = _construir_tabla(campo, valor)
                if tabla and tablas is not None:
                    tablas.append(tabla)
            else:
                lineas = _filas_lista(valor)
                if lineas:
                    secciones.append((_etiqueta(campo), lineas))
        else:
            pares_raiz.append(f"{_etiqueta(campo)}: {_texto(valor)}")

    if pares_raiz and titulo_raiz:
        secciones.insert(0, (titulo_raiz, pares_raiz))
    return secciones


def _clasificar_registro(registro: dict, configuracion: dict | None):
    cfg = configuracion or {}
    campo_folio = cfg.get("campo_folio", "")
    if campo_folio.startswith("lev_") or "lev_folio" in registro:
        return "levantamiento"
    if campo_folio.startswith("os_") or "os_folio" in registro:
        return "orden_servicio"
    if campo_folio.startswith("ot_") or "ot_folio" in registro:
        return "orden_trabajo"
    if campo_folio.startswith("bit_") or "bit_folio" in registro:
        return "bitacora"
    if campo_folio.startswith("obc_") or "obc_folio" in registro:
        return "obra_civil"
    return "aco"


def _construir_datos(registro: dict, configuracion: dict | None = None) -> tuple[dict, bool]:
    tipo = _clasificar_registro(registro, configuracion)
    datos = {}
    secciones = []
    tablas_pdf = []

    # Datos generales: solo valores simples. JSON y listas se convierten después.
    for campo, valor in (registro or {}).items():
        clave = _limpiar_clave(campo)
        normalizado = _normalizar(valor)
        if clave in OCULTAR or _es_vacio(normalizado) or isinstance(normalizado, (dict, list)):
            continue
        # Evitar columnas técnicas repetidas o sin valor para el usuario.
        if clave.endswith("_id") and clave != "id":
            continue
        datos[_etiqueta(campo)] = _texto(normalizado)

    # Procesar cada JSON como secciones humanas.
    for campo, valor in (registro or {}).items():
        normalizado = _normalizar(valor)
        if isinstance(normalizado, dict):
            secciones.extend(_secciones_desde_dict(normalizado, _etiqueta(campo), tablas_pdf))
        elif isinstance(normalizado, list) and normalizado:
            if _es_lista_tabular(campo, normalizado):
                tabla = _construir_tabla(campo, normalizado)
                if tabla:
                    tablas_pdf.append(tabla)
            else:
                lineas = _filas_lista(normalizado)
                if lineas:
                    secciones.append((_etiqueta(campo), lineas))

    if tablas_pdf:
        for etiqueta_dato, valor_dato in list(datos.items()):
            if isinstance(valor_dato, str):
                datos[etiqueta_dato] = _quitar_resumenes_tabulares(valor_dato)

    # Eliminar duplicados frecuentes generados por columnas resumen.
    for repetido in ("Detalle técnico", "Requerimientos"):
        datos.pop(repetido, None)

    # Folio y fecha normalizados para encabezado.
    folios = {
        "lev_folio": "Folio LEV", "os_folio": "Folio OS", "ot_folio": "Folio OT",
        "bit_folio": "Folio BIT", "obc_folio": "Folio OBC", "aco_numero": "Número de ACO",
    }
    for campo, etiqueta in folios.items():
        if _texto(registro.get(campo)):
            datos[etiqueta] = _texto(registro.get(campo))
            break
    for campo in ("lev_fecha", "lev_fecha_programada", "os_fecha", "os_fecha_programada", "ot_fecha", "ot_fecha_programada", "bit_fecha", "obc_fecha", "fecha_registro", "created_at"):
        if _texto(registro.get(campo)):
            datos["Fecha"] = _texto(registro.get(campo))
            break

    if secciones:
        # El mismo bloque puede existir dentro del JSON técnico y en una columna
        # auxiliar (por ejemplo equipos dañados). Se conserva una sola copia.
        unicas = []
        firmas = set()
        for titulo_seccion, lineas in secciones:
            firma = (str(titulo_seccion).strip().casefold(), tuple(str(x).strip().casefold() for x in lineas))
            if firma in firmas:
                continue
            firmas.add(firma)
            unicas.append((titulo_seccion, lineas))
        datos["Detalle técnico"] = "\n".join(
            [f"--- {titulo.upper()} ---\n" + "\n".join(lineas) for titulo, lineas in unicas]
        )

    # Se adjuntan como metadato interno para que el perfil genérico cree
    # DataTableBlock. No se muestran como un campo de datos generales.
    if tablas_pdf:
        unicas_tabla = []
        firmas_tabla = set()
        for titulo_tabla, columnas, filas in tablas_pdf:
            firma = (str(titulo_tabla).casefold(), tuple(columnas), tuple(tuple(f.get(c, "") for c in columnas) for f in filas))
            if firma in firmas_tabla:
                continue
            firmas_tabla.add(firma)
            unicas_tabla.append((titulo_tabla, columnas, filas))
        datos["_tablas_pdf"] = unicas_tabla

    mostrar_firmas = tipo != "levantamiento"
    return datos, mostrar_firmas


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


def generar_pdf_registro(
    registro: dict,
    configuracion: dict | None = None,
    *,
    ruta_salida: str | Path | None = None,
    abrir: bool = True,
):
    """Genera un registro con el formato definitivo de AXIA.

    Es el punto común para preview, descarga administrativa y PDF local
    posterior al guardado.
    """
    if not registro:
        return False
    titulo, folio = _titulo_y_folio(registro, configuracion)

    # Plantilla maestra de levantamientos: todos los tipos y modalidades pasan
    # por el mismo generador estructurado. Preview, PDF definitivo y descarga
    # administrativa comparten exactamente la misma lógica visual.
    if es_levantamiento(registro):
        if ruta_salida is None:
            safe = "_".join(str(registro.get("lev_tipo_levantamiento") or "Levantamiento").split())
            ruta_salida = AxiaPdfEngine._preview_path(f"Levantamiento_{safe}")
        resultado = generar_pdf_levantamiento_maestro(
            registro, ruta_salida=Path(ruta_salida), abrir=abrir
        )
        if isinstance(resultado, (str, Path)) and Path(resultado).is_file():
            AxiaPdfArtifactStore.register(folio, resultado)
        return resultado

    datos, mostrar_firmas = _construir_datos(registro, configuracion)
    profile_data = dict(datos)
    profile_data.update({
        "_titulo_pdf": titulo,
        "_folio": folio,
        "_mostrar_firmas": mostrar_firmas,
    })
    request = AxiaPdfEngine.prepare_profile(
        profile_key="registro_generico",
        data=profile_data,
    )
    if ruta_salida is None and abrir:
        artifact = AxiaPdfArtifactStore.find(
            folio, min_renderer_version=PDF_RENDERER_VERSION
        ) if folio != "registro_AXIA" else None
        if artifact is not None:
            AxiaPdfArtifactStore.open(artifact.path)
            return str(artifact.path)
        return AxiaPdfEngine.preview_request(request)
    if ruta_salida is None:
        ruta_salida = AxiaPdfEngine._preview_path(titulo)
    if abrir:
        from dataclasses import replace
        resultado = AxiaPdfEngine.render(
            replace(request, ruta_salida=Path(ruta_salida), abrir=True)
        )
    else:
        resultado = AxiaPdfEngine.save_request(request, ruta_salida)
    if isinstance(resultado, (str, Path)) and Path(resultado).is_file():
        AxiaPdfArtifactStore.register(folio, resultado)
    return resultado


def previsualizar_pdf_registro(registro: dict, configuracion: dict | None = None) -> bool:
    if not registro:
        messagebox.showwarning("Vista previa PDF", "No hay un registro seleccionado.")
        return False
    return bool(generar_pdf_registro(registro, configuracion, abrir=True))


def guardar_pdf_registro(registro: dict, configuracion: dict | None = None) -> bool:
    if not registro:
        messagebox.showwarning("Guardar PDF", "No hay un registro seleccionado.")
        return False
    _titulo, folio = _titulo_y_folio(registro, configuracion)
    ruta = filedialog.asksaveasfilename(
        title="Guardar PDF definitivo", defaultextension=".pdf",
        initialfile=f"AXIA_{folio}.pdf", filetypes=[("Documento PDF", "*.pdf")],
    )
    if not ruta:
        return False
    exacto = AxiaPdfArtifactStore.export_exact(
        folio, Path(ruta), min_renderer_version=PDF_RENDERER_VERSION
    )
    if exacto:
        messagebox.showinfo(
            "Guardar PDF",
            f"PDF definitivo copiado sin regeneración:\n{exacto}",
        )
        return True

    resultado = generar_pdf_registro(
        registro, configuracion, ruta_salida=Path(ruta), abrir=False
    )
    if resultado:
        messagebox.showinfo(
            "Guardar PDF",
            f"No existía una copia canónica local. El PDF fue regenerado, registrado y guardado en:\n{ruta}",
        )
        return True
    return False
