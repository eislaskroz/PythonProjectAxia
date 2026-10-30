-- AXIA Obra Civil 2.06.00 — cierre de permisos temporales
-- Ejecutar después de desplegar la Edge Function y confirmar una inserción.
-- No altera folios, obras existentes ni archivos.
BEGIN;
ALTER TABLE public.db_obras_civiles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS axia_obras_insert_temporal ON public.db_obras_civiles;
DROP POLICY IF EXISTS axia_obras_returning_temporal ON public.db_obras_civiles;
REVOKE ALL ON FUNCTION public.axia_obc_consultar_solicitud(uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.axia_obc_consultar_solicitud(uuid) TO service_role;
COMMIT;
SELECT policyname,cmd,roles,qual,with_check FROM pg_policies
WHERE schemaname='public' AND tablename='db_obras_civiles';
