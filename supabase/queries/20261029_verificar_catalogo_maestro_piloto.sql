-- SOLO CONSULTA. Verifica tabla piloto previamente cargada; no modifica inventarios.
SELECT
  count(*) AS registros_piloto,
  count(DISTINCT codigo_axia) AS codigos_axia_unicos,
  count(*) FILTER (WHERE proveedor IS NOT NULL OR codigo_proveedor IS NOT NULL) AS proveedores_capturados,
  count(DISTINCT categoria_axia) AS categorias,
  count(DISTINCT (prefijo_familia, prefijo_categoria)) AS familias,
  count(*) FILTER (WHERE posible_equivalencia IS NOT NULL) AS candidatos_equivalencia
FROM public.axia_almacen_catalogo_piloto;

SELECT relname AS tabla, relrowsecurity AS rls_habilitado
FROM pg_class WHERE oid = 'public.axia_almacen_catalogo_piloto'::regclass;
