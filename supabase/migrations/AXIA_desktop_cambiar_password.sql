BEGIN;

CREATE FUNCTION public.axia_desktop_cambiar_password(
    p_usuario bigint,
    p_hash_anterior text,
    p_hash_nuevo text
) RETURNS boolean
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $fn$
DECLARE
    v_nickname text;
BEGIN
    IF p_usuario IS NULL OR p_usuario <= 0
       OR p_hash_anterior IS NULL OR p_hash_nuevo IS NULL
       OR p_hash_anterior !~ '^\$2[aby]\$[0-9]{2}\$[./A-Za-z0-9]{53}$'
       OR p_hash_nuevo !~ '^\$2[ab]\$12\$[./A-Za-z0-9]{53}$'
       OR p_hash_anterior = p_hash_nuevo THEN
        RETURN false;
    END IF;

    UPDATE public.db_usuarios
    SET usu_password = p_hash_nuevo
    WHERE id_usuario = p_usuario
      AND usu_password = p_hash_anterior
      AND usu_activo IS TRUE
      AND usu_acceso_habilitado IS TRUE
      AND usu_fecha_baja IS NULL
    RETURNING usu_nickname INTO v_nickname;

    IF NOT FOUND THEN
        RETURN false;
    END IF;

    INSERT INTO public.db_bitacora_mov
        (id_usuario, usuario, modulo, accion, descripcion, registro_afectado, fecha_hora)
    VALUES
        (p_usuario, v_nickname, 'MI_USUARIO', 'CAMBIAR_PASSWORD',
         'Cambio de contraseña propia verificado en servidor', p_usuario::text, clock_timestamp());

    RETURN true;
END;
$fn$;

REVOKE ALL ON FUNCTION public.axia_desktop_cambiar_password(bigint,text,text)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.axia_desktop_cambiar_password(bigint,text,text)
TO service_role;

COMMIT;
