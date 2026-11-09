"""Historial personal de documentos operativos (rol Operador 4).

El filtro de autor se ejecuta en Supabase ANTES de paginar.
Nunca se consulta la tabla completa para filtrar después en la interfaz.
"""
from app_context import obtener_usuario_actual
from security.permissions import obtener_tipo_usuario, OPERADOR
from supabase_config import supabase
from services.levantamientos_service import TABLA_LEVANTAMIENTOS, COLUMNAS_LEVANTAMIENTOS
from services.bitacoras_service import TABLA_BITACORAS, COLUMNAS_BITACORAS
from services.ordenes_servicio_service import TABLA_ORDENES, COLUMNAS_ORDENES

CONFIG = {
    "levantamientos": (TABLA_LEVANTAMIENTOS, COLUMNAS_LEVANTAMIENTOS, ("lev_folio", "lev_aco_numero", "lev_cliente", "lev_descripcion")),
    "bitacoras": (TABLA_BITACORAS, COLUMNAS_BITACORAS, ("bit_folio", "bit_aco_numero", "bit_cliente", "bit_descripcion")),
    "ordenes_servicio": (TABLA_ORDENES, COLUMNAS_ORDENES, ("os_folio", "os_aco_numero", "os_cliente", "os_descripcion")),
}


def _autor_operador():
    usuario = obtener_usuario_actual() or {}
    if obtener_tipo_usuario(usuario) != OPERADOR or not usuario.get("id_usuario"):
        raise PermissionError("El historial personal requiere una sesión válida de Operador.")
    autor = str(usuario.get("usuario") or "").strip()
    if not autor or autor.upper() == "DESCONOCIDO":
        raise PermissionError("No fue posible identificar al autor de los documentos.")
    return autor


def consultar_mis_documentos(tipo, termino="", limite=100):
    autor = _autor_operador()
    if tipo not in CONFIG:
        raise ValueError("Tipo de documento no permitido")
    tabla, columnas, campos_busqueda = CONFIG[tipo]
    # 'creado_por' es OBLIGATORIO. No usamos la capa de compatibilidad que
    # podría omitir columnas ausentes: en ese caso se debe mostrar un error,
    # nunca relajar el filtro de acceso.
    seleccion = list(dict.fromkeys([*(x.strip() for x in columnas.split(",")), "creado_por"]))
    limite = max(1, min(int(limite), 200))
    termino = str(termino or "").strip().casefold()
    encontrados = []
    pagina = 0
    tamano = 100
    # Cota de lectura para no sobrecargar equipos modestos.
    while pagina < 20 and len(encontrados) < limite:
        inicio = pagina * tamano
        respuesta = (supabase.table(tabla).select(",".join(seleccion))
                     .eq("creado_por", autor).order("fecha_registro", desc=True)
                     .range(inicio, inicio + tamano - 1).execute())
        registros = list(respuesta.data or [])
        for registro in registros:
            if str(registro.get("creado_por") or "").strip() != autor:
                continue
            if termino and not any(termino in str(registro.get(c) or "").casefold() for c in campos_busqueda):
                continue
            encontrados.append(registro)
            if len(encontrados) >= limite:
                break
        if len(registros) < tamano:
            break
        pagina += 1
    return encontrados
