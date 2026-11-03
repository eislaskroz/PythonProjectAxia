-- CONSULTA DE DIAGNÓSTICO, NO MODIFICA SUPABASE.
-- Verifica restricciones relacionadas con db_usuarios antes de usar usu_tipo=9/10.
SELECT c.conname AS restriccion, c.contype AS tipo, pg_get_constraintdef(c.oid) AS definicion
FROM pg_constraint c
WHERE c.conrelid = 'public.db_usuarios'::regclass
ORDER BY c.conname;

SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema='public' AND table_name='db_usuarios'
  AND column_name IN ('id_usuario','usu_tipo','usu_nombre','usu_apellido',
    'usu_rfc','usu_curp','usu_imss','usu_ine','usu_fechanac')
ORDER BY column_name;
