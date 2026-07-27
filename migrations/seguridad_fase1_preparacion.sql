-- AXIA FASE 1: preparación NO disruptiva para Supabase Auth + RLS
-- Esta migración no activa RLS ni revoca permisos porque el cliente actual aún
-- utiliza autenticación propia. Puede ejecutarse primero en staging.
BEGIN;
ALTER TABLE IF EXISTS public.db_usuarios ADD COLUMN IF NOT EXISTS usu_auth_id uuid UNIQUE;
CREATE INDEX IF NOT EXISTS idx_db_usuarios_auth_id ON public.db_usuarios(usu_auth_id);
COMMENT ON COLUMN public.db_usuarios.usu_auth_id IS 'Vinculación futura con auth.users.id. Debe completarse antes de activar RLS.';
COMMIT;
