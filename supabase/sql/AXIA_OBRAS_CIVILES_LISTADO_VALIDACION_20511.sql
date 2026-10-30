-- AXIA 2.05.11: validación independiente de Obra Civil en listado universal.
-- NO duplica obras en db_levantamientos ni habilita acceso público a Obra Civil.
BEGIN;
ALTER TABLE public.db_obras_civiles
  ADD COLUMN IF NOT EXISTS obc_validado_ventas boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS obc_validado_por text,
  ADD COLUMN IF NOT EXISTS obc_fecha_validacion timestamptz;
CREATE INDEX IF NOT EXISTS idx_axia_obras_consulta_recientes
  ON public.db_obras_civiles (fecha_registro DESC);
COMMIT;
