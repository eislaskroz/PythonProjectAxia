-- AXIA DESKTOP 2.05.10: alta real de productos con código AXIA automático.
-- Requiere catálogo operativo único de la versión 2.04.08.
-- No cambia saldos, partidas ni movimientos existentes.
-- Respaldar public.axia_almacen_catalogo ANTES de ejecutar.
BEGIN;

ALTER TABLE public.axia_almacen_catalogo
  ADD COLUMN IF NOT EXISTS alta_solicitud_id uuid;
ALTER TABLE public.axia_almacen_catalogo
  ADD COLUMN IF NOT EXISTS alta_solicitud_firma text;
CREATE UNIQUE INDEX IF NOT EXISTS ux_axia_almacen_alta_solicitud
  ON public.axia_almacen_catalogo(alta_solicitud_id);

-- Seguridad: solo service_role (Edge Function) puede ejecutar esta RPC.
-- La creación es atómica, idempotente por solicitud, y bloquea el consecutivo
-- compartido por un mismo par de prefijos para evitar folios duplicados.
CREATE OR REPLACE FUNCTION public.axia_almacen_maestro_crear_producto(
    p_datos jsonb,
    p_idempotencia uuid
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $fn$
DECLARE
    v_categoria text := btrim(coalesce(p_datos->>'categoria_axia', ''));
    v_familia text := btrim(coalesce(p_datos->>'familia_axia', ''));
    v_producto text := btrim(coalesce(p_datos->>'producto', ''));
    v_pf text;
    v_pc text;
    v_codigo text;
    v_num integer;
    v_anterior text;
    v_firma_actual text := pg_catalog.md5(p_datos::text);
    v_firma_anterior text;
BEGIN
    IF p_idempotencia IS NULL OR p_datos IS NULL OR
       length(v_producto) NOT BETWEEN 1 AND 500 OR
       length(v_categoria) NOT BETWEEN 1 AND 150 OR
       length(v_familia) NOT BETWEEN 1 AND 200 THEN
        RAISE EXCEPTION 'FICHA_INVALIDA';
    END IF;

    -- Si se repite la misma alta por timeout, no se crea un segundo artículo.
    SELECT codigo_axia, alta_solicitud_firma INTO v_anterior, v_firma_anterior
      FROM public.axia_almacen_catalogo
      WHERE alta_solicitud_id = p_idempotencia;
    IF v_anterior IS NOT NULL THEN
      IF v_firma_anterior IS DISTINCT FROM v_firma_actual THEN
        RAISE EXCEPTION 'IDEMPOTENCIA_CON_DATOS_DISTINTOS';
      END IF;
      RETURN pg_catalog.jsonb_build_object('codigo', v_anterior, 'repetido', true);
    END IF;

    -- Los prefijos se extraen de una familia/categoría YA existente.
    -- Nunca se generan códigos aleatorios ni se aceptan enviados por DESKTOP.
    SELECT prefijo_familia, prefijo_categoria INTO v_pf, v_pc
      FROM public.axia_almacen_catalogo
     WHERE categoria_axia = v_categoria AND familia_axia = v_familia
       AND prefijo_familia ~ '^[A-Z]{3}$'
       AND prefijo_categoria ~ '^[A-Z]{3}$'
     ORDER BY codigo_axia LIMIT 1;
    IF v_pf IS NULL OR v_pc IS NULL THEN
       RAISE EXCEPTION 'FAMILIA_NO_REGISTRADA';
    END IF;

    -- Bloquear por los PREFIJOS, no por texto de categoría (pueden coincidir).
    PERFORM pg_catalog.pg_advisory_xact_lock(
      pg_catalog.hashtextextended(v_pf || '-' || v_pc, 20411)
    );
    -- Doble comprobación después de esperar el bloqueo.
    SELECT codigo_axia, alta_solicitud_firma INTO v_anterior, v_firma_anterior
      FROM public.axia_almacen_catalogo
     WHERE alta_solicitud_id = p_idempotencia;
    IF v_anterior IS NOT NULL THEN
       IF v_firma_anterior IS DISTINCT FROM v_firma_actual THEN
          RAISE EXCEPTION 'IDEMPOTENCIA_CON_DATOS_DISTINTOS';
       END IF;
       RETURN pg_catalog.jsonb_build_object('codigo', v_anterior, 'repetido', true);
    END IF;

    SELECT coalesce(max(right(codigo_axia, 5)::integer), 0) + 1
      INTO v_num
      FROM public.axia_almacen_catalogo
     WHERE codigo_axia LIKE v_pf || '-' || v_pc || '-%'
       AND codigo_axia ~ '^[A-Z]{3}-[A-Z]{3}-[0-9]{5}$';
    IF v_num > 99999 THEN
       RAISE EXCEPTION 'CONSECUTIVO_AGOTADO';
    END IF;
    v_codigo := v_pf || '-' || v_pc || '-' || lpad(v_num::text, 5, '0');

    -- Campos históricos de ELEVENTA son NULL: las altas nuevas no existían
    -- en la exportación original. Saldo real = 0 (solo cambia con movimientos).
    INSERT INTO public.axia_almacen_catalogo (
      codigo_axia, alta_solicitud_id, alta_solicitud_firma, codigo_proveedor, proveedor, producto,
      departamento_origen, p_costo, p_venta, p_mayoreo,
      existencia_eleventa, inv_minimo, inv_maximo,
      categoria_axia, familia_axia, prefijo_familia, prefijo_categoria,
      seguimiento_sugerido, estado_clasificacion, fila_origen_eleventa,
      posible_equivalencia, unidad_inventario, estatus, codigo_origen_eleventa,
      saldo_actual, saldo_inicial_origen, activo, actualizado_el
    ) VALUES (
      v_codigo, p_idempotencia, v_firma_actual,
      nullif(btrim(coalesce(p_datos->>'codigo_proveedor','')), ''),
      nullif(btrim(coalesce(p_datos->>'proveedor','')), ''),
      v_producto,
      nullif(btrim(coalesce(p_datos->>'departamento_origen','')), ''),
      (p_datos->>'p_costo')::numeric, (p_datos->>'p_venta')::numeric,
      (p_datos->>'p_mayoreo')::numeric,
      NULL, (p_datos->>'inv_minimo')::numeric, (p_datos->>'inv_maximo')::numeric,
      v_categoria, v_familia, v_pf, v_pc,
      nullif(btrim(coalesce(p_datos->>'seguimiento_sugerido','')), ''),
      nullif(btrim(coalesce(p_datos->>'estado_clasificacion','')), ''),
      NULL,
      nullif(btrim(coalesce(p_datos->>'posible_equivalencia','')), ''),
      nullif(btrim(coalesce(p_datos->>'unidad_inventario','')), ''),
      'Activo', NULL,
      0, 'ALTA_AXIA_SIN_EXISTENCIA', true, now()
    );
    RETURN pg_catalog.jsonb_build_object('codigo', v_codigo, 'repetido', false);
END;
$fn$;

REVOKE ALL ON FUNCTION public.axia_almacen_maestro_crear_producto(jsonb,uuid)
 FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.axia_almacen_maestro_crear_producto(jsonb,uuid)
 TO service_role;
COMMIT;

-- Solo consulta: verifica que la RPC existe (NO genera códigos).
SELECT to_regprocedure('public.axia_almacen_maestro_crear_producto(jsonb,uuid)')
       IS NOT NULL AS alta_automatica_disponible;
