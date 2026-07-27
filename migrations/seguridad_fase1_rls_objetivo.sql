-- AXIA FASE 1: OBJETIVO RLS. NO EJECUTAR hasta migrar el cliente a Supabase Auth
-- y completar db_usuarios.usu_auth_id para todos los usuarios activos.
BEGIN;
DO $$ DECLARE t text; BEGIN
  FOREACH t IN ARRAY ARRAY['db_usuarios','db_clientes','db_acos','db_levantamientos','db_ordenes_servicio','db_bitacoras','db_login','db_bitacora_mov','db_clientes_sucursales','db_clientes_sucursal_contactos','db_obras_civiles','db_ordenes_trabajo']
  LOOP
    IF to_regclass('public.'||t) IS NOT NULL THEN
      EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
      EXECUTE format('REVOKE ALL ON public.%I FROM anon', t);
    END IF;
  END LOOP;
END $$;
-- Ejemplo mínimo de lectura del propio perfil. Las políticas de negocio por tabla
-- deben crearse después de definir propiedad (created_by/auth_id) y alcance por rol.
DROP POLICY IF EXISTS usuario_lee_su_perfil ON public.db_usuarios;
CREATE POLICY usuario_lee_su_perfil ON public.db_usuarios FOR SELECT TO authenticated
USING (usu_auth_id = auth.uid());
COMMIT;
