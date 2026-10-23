-- AXIA DESKTOP | Obra Civil | 2026-10-23
-- Ejecutar EN SUPABASE SQL EDITOR ANTES de publicar DESKTOP.
-- Cambios: consecutivo OBC atómico + token idempotente para reconexiones.
-- No desactiva RLS, NO crea políticas públicas ni cambia obras existentes.
BEGIN;

-- El bloqueo impide que aparezcan nuevos folios durante la inicialización.
LOCK TABLE public.db_obras_civiles IN ACCESS EXCLUSIVE MODE;
ALTER TABLE public.db_obras_civiles
    ADD COLUMN IF NOT EXISTS obc_request_id uuid;
CREATE UNIQUE INDEX IF NOT EXISTS ux_axia_obc_request_id
    ON public.db_obras_civiles (obc_request_id)
    WHERE obc_request_id IS NOT NULL;

CREATE SEQUENCE IF NOT EXISTS public.axia_obc_folio_seq
    AS bigint START WITH 1 INCREMENT BY 1 MINVALUE 1 NO CYCLE;

-- Sincronizar la secuencia sin retroceder si la migración se reejecuta.
DO $do$
DECLARE
    max_folio bigint;
    ultimo_seq bigint;
    ya_usada boolean;
    ultimo_seguro bigint;
BEGIN
    SELECT COALESCE(MAX(substring(obc_folio from '^OBC-([0-9]+)$')::bigint), 0)
      INTO max_folio
      FROM public.db_obras_civiles
      WHERE obc_folio ~ '^OBC-[0-9]+$';
    SELECT last_value, is_called INTO ultimo_seq, ya_usada
      FROM public.axia_obc_folio_seq;
    ultimo_seguro := GREATEST(max_folio, CASE WHEN ya_usada THEN ultimo_seq ELSE ultimo_seq - 1 END);
    IF ultimo_seguro > 0 THEN
        PERFORM setval('public.axia_obc_folio_seq'::regclass, ultimo_seguro, true);
    ELSE
        PERFORM setval('public.axia_obc_folio_seq'::regclass, 1, false);
    END IF;
END
$do$;

-- Ignorar un posible OBC-0001 enviado desde un ejecutable anterior.
-- Únicamente los INSERT nuevos reciben el folio; registros existentes intactos.
CREATE OR REPLACE FUNCTION public.axia_obc_asignar_folio()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public
AS $function$
BEGIN
    NEW.obc_folio := 'OBC-' || lpad(nextval('public.axia_obc_folio_seq'::regclass)::text, 4, '0');
    RETURN NEW;
END
$function$;

DROP TRIGGER IF EXISTS tr_axia_obc_asignar_folio ON public.db_obras_civiles;
CREATE TRIGGER tr_axia_obc_asignar_folio
    BEFORE INSERT ON public.db_obras_civiles
    FOR EACH ROW EXECUTE FUNCTION public.axia_obc_asignar_folio();
REVOKE ALL ON FUNCTION public.axia_obc_asignar_folio() FROM PUBLIC;

-- Permite confirmar un INSERT cuyo resultado se perdió por corte de red.
-- No entrega contenido de la Obra Civil, solo ID + folio a quien posea el UUID.
-- El UUID aleatorio NO sustituye la autenticación de empleados.
CREATE OR REPLACE FUNCTION public.axia_obc_consultar_solicitud(p_solicitud uuid)
RETURNS TABLE (id_obra_civil text, obc_folio text)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, public
AS $function$
    SELECT oc.id_obra_civil::text, oc.obc_folio::text
    FROM public.db_obras_civiles AS oc
    WHERE oc.obc_request_id = p_solicitud
    LIMIT 1;
$function$;
REVOKE ALL ON FUNCTION public.axia_obc_consultar_solicitud(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.axia_obc_consultar_solicitud(uuid) TO anon, authenticated;

COMMIT;

-- IMPORTANTE:
-- Esta migración no corrige por sí sola la autenticación RLS.
-- Las políticas temporales 2026-10-22 para anon expiran 2026-10-24.
-- NO extenderlas silenciosamente ni agregar WITH CHECK (true) permanente.
-- Para una solución de seguridad definitiva, migrar a Supabase Auth
-- o un endpoint privado que verifique sesiones AXIA en el servidor.
