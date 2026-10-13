BEGIN;

ALTER TABLE public.db_ordenes_trabajo
    ADD COLUMN IF NOT EXISTS ot_folio_levantamiento text;

ALTER TABLE public.db_bitacoras
    ADD COLUMN IF NOT EXISTS bit_ot_folio text;

ALTER TABLE public.db_ordenes_servicio
    ADD COLUMN IF NOT EXISTS os_folio_ot text,
    ADD COLUMN IF NOT EXISTS os_folio_bitacora text;

COMMIT;