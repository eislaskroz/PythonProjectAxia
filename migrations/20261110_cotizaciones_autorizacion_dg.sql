-- AXIA · Aprobación DG de cotizaciones (ejecutar una sola vez tras respaldo)
-- La columna cot_estatus ya existía. Nuevos estados: BORRADOR, PENDIENTE DG,
-- EN COMPRA X COTIZACIÓN, CONVERTIDA A OT.
ALTER TABLE public.db_cotizaciones
  ADD COLUMN IF NOT EXISTS cot_autorizado_dg_por text,
  ADD COLUMN IF NOT EXISTS cot_fecha_autorizacion_dg timestamptz;

-- VERIFICACIÓN: revisar restricciones CHECK existentes antes de introducir PENDIENTE DG.
SELECT conname, pg_get_constraintdef(oid) AS definicion
FROM pg_constraint
WHERE conrelid = 'public.db_cotizaciones'::regclass AND contype = 'c';

-- SEGURIDAD PENDIENTE: la transición DG debe protegerse por una función/RPC
-- verificada en servidor con identidad y rol autorizados; no basta una validación
-- del rol local en DESKTOP. No otorgar UPDATE irrestricto a anon.
