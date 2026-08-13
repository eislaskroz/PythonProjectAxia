-- AXIA: homologación del flujo operativo vigente
-- LEVANTAMIENTO -> ACO -> ORDEN DE TRABAJO -> BITÁCORA OPERATIVA -> ORDEN DE SERVICIO
-- Idempotente: puede ejecutarse nuevamente sin borrar información.

BEGIN;

-- Trazabilidad Levantamiento -> OT
ALTER TABLE public.db_ordenes_trabajo
    ADD COLUMN IF NOT EXISTS id_levantamiento bigint,
    ADD COLUMN IF NOT EXISTS ot_folio_levantamiento text;

-- Trazabilidad Bitácora -> OT
ALTER TABLE public.db_bitacoras
    ADD COLUMN IF NOT EXISTS ot_id bigint,
    ADD COLUMN IF NOT EXISTS bit_ot_folio text;

-- Trazabilidad OT/Bitácora -> OS final
ALTER TABLE public.db_ordenes_servicio
    ADD COLUMN IF NOT EXISTS ot_id bigint,
    ADD COLUMN IF NOT EXISTS os_folio_ot text,
    ADD COLUMN IF NOT EXISTS os_folio_bitacora text;

CREATE INDEX IF NOT EXISTS idx_ot_id_levantamiento
    ON public.db_ordenes_trabajo (id_levantamiento);
CREATE INDEX IF NOT EXISTS idx_ot_folio_levantamiento
    ON public.db_ordenes_trabajo (ot_folio_levantamiento);
CREATE INDEX IF NOT EXISTS idx_bit_ot_folio
    ON public.db_bitacoras (bit_ot_folio);
CREATE INDEX IF NOT EXISTS idx_bit_ot_id
    ON public.db_bitacoras (ot_id);
CREATE INDEX IF NOT EXISTS idx_os_folio_ot
    ON public.db_ordenes_servicio (os_folio_ot);
CREATE INDEX IF NOT EXISTS idx_os_ot_id
    ON public.db_ordenes_servicio (ot_id);

COMMIT;

-- Verificación rápida
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (
      (table_name = 'db_ordenes_trabajo' AND column_name IN ('id_levantamiento','ot_folio_levantamiento'))
   OR (table_name = 'db_bitacoras' AND column_name IN ('ot_id','bit_ot_folio'))
   OR (table_name = 'db_ordenes_servicio' AND column_name IN ('ot_id','os_folio_ot','os_folio_bitacora'))
  )
ORDER BY table_name, column_name;
