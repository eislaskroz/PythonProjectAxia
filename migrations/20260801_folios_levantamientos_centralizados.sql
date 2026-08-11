-- AXIA Desktop / AXIA Field
-- Migración: folios centralizados para db_levantamientos
-- Formato oficial: LEV-XXXXX
-- Fecha: 2026-08-01

BEGIN;

-- 1) Crear la secuencia central si todavía no existe.
CREATE SEQUENCE IF NOT EXISTS public.levantamientos_folio_seq
    AS bigint
    INCREMENT BY 1
    MINVALUE 1
    START WITH 1
    NO MAXVALUE
    CACHE 1;

-- 2) Sincronizar la secuencia con los folios existentes.
--    Solo considera folios con el formato LEV- seguido de números.
--    Si la secuencia ya estaba más adelantada, no la retrocede.
DO $$
DECLARE
    v_max_folio bigint := 0;
    v_seq_last bigint := 0;
    v_seq_called boolean := false;
    v_target bigint := 0;
BEGIN
    SELECT COALESCE(
        MAX((substring(upper(trim(lev_folio)) FROM '^LEV-([0-9]+)$'))::bigint),
        0
    )
    INTO v_max_folio
    FROM public.db_levantamientos
    WHERE lev_folio IS NOT NULL
      AND upper(trim(lev_folio)) ~ '^LEV-[0-9]+$';

    SELECT last_value, is_called
    INTO v_seq_last, v_seq_called
    FROM public.levantamientos_folio_seq;

    IF NOT v_seq_called THEN
        v_seq_last := 0;
    END IF;

    v_target := GREATEST(v_max_folio, v_seq_last);

    IF v_target > 0 THEN
        PERFORM setval('public.levantamientos_folio_seq', v_target, true);
    ELSE
        PERFORM setval('public.levantamientos_folio_seq', 1, false);
    END IF;
END;
$$;

-- 3) Crear la función RPC que usarán Desktop y Mobile.
CREATE OR REPLACE FUNCTION public.generar_folio_levantamiento()
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_numero bigint;
BEGIN
    v_numero := nextval('public.levantamientos_folio_seq');
    RETURN 'LEV-' || lpad(v_numero::text, 5, '0');
END;
$$;

-- 4) Restringir la función y conceder únicamente ejecución.
REVOKE ALL ON FUNCTION public.generar_folio_levantamiento() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.generar_folio_levantamiento() TO anon;
GRANT EXECUTE ON FUNCTION public.generar_folio_levantamiento() TO authenticated;
GRANT EXECUTE ON FUNCTION public.generar_folio_levantamiento() TO service_role;

COMMENT ON SEQUENCE public.levantamientos_folio_seq IS
'Secuencia central para folios LEV-XXXXX compartidos por AXIA Desktop y AXIA Field.';

COMMENT ON FUNCTION public.generar_folio_levantamiento() IS
'Genera de forma atómica el siguiente folio de levantamiento con formato LEV-XXXXX.';

COMMIT;

-- ============================================================
-- PRUEBAS MANUALES (ejecutar después, una por una; no dentro de
-- la migración si no deseas consumir folios de prueba)
-- ============================================================

-- Ver el folio numéricamente más alto que ya existe:
-- SELECT lev_folio
-- FROM public.db_levantamientos
-- WHERE upper(trim(lev_folio)) ~ '^LEV-[0-9]+$'
-- ORDER BY (substring(upper(trim(lev_folio)) FROM '^LEV-([0-9]+)$'))::bigint DESC
-- LIMIT 1;

-- Solicitar un nuevo folio (ESTO CONSUME UN NÚMERO):
-- SELECT public.generar_folio_levantamiento();

-- Ver el estado actual de la secuencia:
-- SELECT last_value, is_called
-- FROM public.levantamientos_folio_seq;
