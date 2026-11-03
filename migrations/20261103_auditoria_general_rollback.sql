-- REVERSIÓN del puente de auditoría general RH y Admin.
-- Elimina SOLO los dos triggers instalados por la migración.
-- NO borra registros, historiales ni movimientos existentes.
BEGIN;
DROP TRIGGER IF EXISTS axia_rrhh_log_general_v1 ON public.axia_rrhh_historial;
DROP TRIGGER IF EXISTS axia_admin_log_general_v1 ON public.axia_admin_registros_historial;
DROP FUNCTION IF EXISTS public.axia_auditoria_puente_movimientos();
COMMIT;
