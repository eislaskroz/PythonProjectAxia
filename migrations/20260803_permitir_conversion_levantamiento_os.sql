-- Permite que el cliente actual actualice levantamientos al convertirlos en OS.
-- Ejecutar en Supabase solo si RLS está habilitado y no existe una política UPDATE equivalente.
ALTER TABLE public.db_levantamientos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Permitir actualizar levantamientos" ON public.db_levantamientos;
CREATE POLICY "Permitir actualizar levantamientos"
ON public.db_levantamientos
FOR UPDATE
TO public
USING (true)
WITH CHECK (true);

-- La verificación posterior al UPDATE requiere SELECT.
DROP POLICY IF EXISTS "Permitir consultar levantamientos" ON public.db_levantamientos;
CREATE POLICY "Permitir consultar levantamientos"
ON public.db_levantamientos
FOR SELECT
TO public
USING (true);
