"""Utilidades unificadas de búsqueda parcial para servicios AXIA."""
from core.search_utils import normalizar_termino_busqueda, puntaje_coincidencia
from services.query_compat import execute_select_compatible


def buscar_parcial_supabase(*, supabase, tabla, columnas, termino, campos, id_campos=(), orden=None, limite=100):
    termino_normalizado = normalizar_termino_busqueda(termino)
    if not termino_normalizado:
        return []
    limite = max(1, min(int(limite), 250))
    encontrados = {}
    errores = []
    for campo in campos:
        try:
            def configurar(query, campo=campo):
                query = query.ilike(campo, f"%{termino_normalizado}%")
                if orden:
                    query = query.order(orden, desc=True)
                return query.limit(limite)
            respuesta = execute_select_compatible(supabase, tabla, columnas, configurar)
            for registro in respuesta.data or []:
                llave = None
                for id_campo in id_campos:
                    llave = registro.get(id_campo)
                    if llave not in (None, ""):
                        break
                if llave is None:
                    llave = tuple((campo, registro.get(campo)) for campo in campos)
                encontrados[llave] = registro
        except Exception as exc:
            errores.append((campo, exc))
    if not encontrados and len(errores) == len(tuple(campos)):
        raise RuntimeError(f"No fue posible consultar {tabla} en Supabase.") from errores[0][1]
    resultados = list(encontrados.values())
    resultados.sort(key=lambda r: (puntaje_coincidencia(r, termino_normalizado, campos), str(next((r.get(c) for c in id_campos if r.get(c)), ""))))
    return resultados[:limite]
