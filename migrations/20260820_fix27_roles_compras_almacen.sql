-- AXIA FIX27
-- Amplía formalmente db_usuarios.usu_tipo para los nuevos roles:
-- 7 = Compras
-- 8 = Almacén
--
-- Idempotencia práctica: elimina únicamente restricciones CHECK de db_usuarios
-- cuya definición haga referencia a usu_tipo y crea la restricción oficial 1..8.

DO $$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
        WHERE nsp.nspname = 'public'
          AND rel.relname = 'db_usuarios'
          AND con.contype = 'c'
          AND pg_get_constraintdef(con.oid) ILIKE '%usu_tipo%'
    LOOP
        EXECUTE format('ALTER TABLE public.db_usuarios DROP CONSTRAINT IF EXISTS %I', r.conname);
    END LOOP;
END $$;

ALTER TABLE public.db_usuarios
    ADD CONSTRAINT db_usuarios_usu_tipo_check
    CHECK (usu_tipo BETWEEN 1 AND 8);

COMMENT ON COLUMN public.db_usuarios.usu_tipo IS
'Rol AXIA: 1 Administrador, 2 Jefe de Operaciones, 3 Supervisor, 4 Operador, 5 Administrativo, 6 Especial/Ventas, 7 Compras, 8 Almacén.';
