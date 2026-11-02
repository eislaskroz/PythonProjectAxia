-- AXIA DESKTOP | Corrección de P0001 en axia_admin_mutar_registro
-- 2026-11-02
-- Ejecutar con rol propietario (Supabase SQL Editor), idealmente después de respaldo.
-- NO modifica ni borra registros de negocio. NO cambia los permisos de usuarios.
-- NO altera reglas de relaciones, auditoría ni eliminación en cascada.
-- La función sigue SECURITY INVOKER y su EXECUTE queda limitado a service_role.
-- La Edge Function continúa validando contraseña y rol 1 del Administrador AXIA.

BEGIN;

DO $axia_patch$
DECLARE
    v_funcion regprocedure := to_regprocedure(
        'public.axia_admin_mutar_registro(text,text,jsonb,jsonb,text,bigint,text,text)'
    );
    v_definicion text;
    v_original text := $guard_anterior$IF coalesce(current_setting('request.jwt.claim.role', true),'') <> 'service_role' THEN$guard_anterior$;
    v_corregido text := $guard_nuevo$IF current_user <> 'service_role' THEN$guard_nuevo$;
    v_security_definer boolean;
BEGIN
    IF v_funcion IS NULL THEN
        RAISE EXCEPTION 'No existe axia_admin_mutar_registro con la firma esperada; no se realizaron cambios';
    END IF;

    SELECT prosecdef INTO v_security_definer FROM pg_proc WHERE oid = v_funcion;
    IF v_security_definer IS DISTINCT FROM FALSE THEN
        RAISE EXCEPTION 'La función no es SECURITY INVOKER; revisión manual necesaria';
    END IF;

    SELECT pg_get_functiondef(v_funcion) INTO v_definicion;

    IF position(v_original IN v_definicion) > 0 THEN
        -- Modifica solo la comprobación de rol; preserva íntegro el resto del SQL.
        EXECUTE replace(v_definicion, v_original, v_corregido);
        RAISE NOTICE 'Guard de la función corregido: comprobación con current_user';
    ELSIF position(v_corregido IN v_definicion) > 0 THEN
        RAISE NOTICE 'Corrección ya aplicada anteriormente; sin cambios en el cuerpo';
    ELSE
        RAISE EXCEPTION 'La validación actual difiere de la versión AXIA conocida; no se aplicaron cambios';
    END IF;
END;
$axia_patch$;

-- Protección explícita. No dar EXECUTE a anon, authenticated ni PUBLIC.
REVOKE ALL ON FUNCTION public.axia_admin_mutar_registro(text,text,jsonb,jsonb,text,bigint,text,text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.axia_admin_mutar_registro(text,text,jsonb,jsonb,text,bigint,text,text)
    TO service_role;

DO $axia_check$
DECLARE
    v_funcion regprocedure := to_regprocedure(
        'public.axia_admin_mutar_registro(text,text,jsonb,jsonb,text,bigint,text,text)'
    );
    v_security_definer boolean;
BEGIN
    SELECT prosecdef INTO v_security_definer FROM pg_proc WHERE oid = v_funcion;
    IF v_security_definer IS DISTINCT FROM FALSE
       OR has_function_privilege('anon', v_funcion, 'EXECUTE')
       OR has_function_privilege('authenticated', v_funcion, 'EXECUTE')
       OR NOT has_function_privilege('service_role', v_funcion, 'EXECUTE') THEN
        RAISE EXCEPTION 'No se cumplen las restricciones administrativas; cambios revertidos';
    END IF;
    RAISE NOTICE 'AXIA OK: SECURITY INVOKER y ejecución restringida a service_role';
END;
$axia_check$;

COMMIT;

-- NOTA: el mensaje P0001 no prueba que el registro sea eliminable.
-- Si tiene relaciones con otros registros, la función seguirá rechazando su baja.
-- No realices una eliminación de prueba sobre información real de producción.
