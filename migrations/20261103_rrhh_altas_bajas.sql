-- AXIA RRHH — Alta y baja NO destructivas. Instalar con copia de seguridad y probar antes en STAGING.
-- Dependencia: migracion 20261103_rrhh_usuarios.sql (tabla axia_rrhh_historial).
BEGIN;

ALTER TABLE public.db_usuarios
  ADD COLUMN IF NOT EXISTS usu_activo boolean NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS usu_acceso_habilitado boolean NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS usu_fecha_baja timestamptz;

-- Para cuentas anteriores, los defaults preservan el acceso preexistente.
-- RH NO puede decidir el rol ni establecer/recuperar contraseñas.
CREATE OR REPLACE FUNCTION public.axia_rrhh_alta_usuario(
  p_actor_id bigint, p_actor_usuario text, p_nickname text,
  p_hash_inutilizable text, p_datos jsonb, p_motivo text
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $$
DECLARE
  v_id bigint;
  v_nombre text;
  v_apellido text;
  v_col text;
  v_allowed text[] := ARRAY[
    'usu_nombre','usu_apellido','usu_rfc','usu_curp','usu_imss','usu_ine',
    'usu_fechanac','usu_telefono','usu_correo','usu_depto','usu_puesto',
    'usu_calle','usu_numero','usu_colonia','usu_municipio','usu_estado',
    'usu_cp','usu_regimen'
  ];
  v_prepared public.db_usuarios%ROWTYPE;
BEGIN
  IF current_user <> 'service_role' THEN RAISE EXCEPTION 'Servicio RRHH exclusivo'; END IF;
  IF NOT EXISTS (SELECT 1 FROM public.db_usuarios
     WHERE id_usuario=p_actor_id AND usu_tipo=10 AND usu_activo IS TRUE AND usu_acceso_habilitado IS TRUE)
  THEN RAISE EXCEPTION 'Actor RRHH no autorizado'; END IF;
  IF length(trim(coalesce(p_motivo,''))) < 8
     OR length(trim(coalesce(p_nickname,''))) < 3
     OR length(trim(coalesce(p_nickname,''))) > 40
     OR p_nickname !~ '^[A-Za-z0-9._-]+$'
     OR p_hash_inutilizable !~ '^\$2[aby]\$' OR length(p_hash_inutilizable) < 50
     OR jsonb_typeof(p_datos) IS DISTINCT FROM 'object'
  THEN RAISE EXCEPTION 'Datos de alta inválidos'; END IF;
  FOR v_col IN SELECT jsonb_object_keys(p_datos) LOOP
    IF NOT v_col=ANY(v_allowed) THEN RAISE EXCEPTION 'Campo de alta no autorizado'; END IF;
  END LOOP;
  v_nombre := trim(p_datos->>'usu_nombre');
  v_apellido := trim(p_datos->>'usu_apellido');
  IF coalesce(v_nombre,'')='' OR coalesce(v_apellido,'')=''
  THEN RAISE EXCEPTION 'Nombre y apellido son obligatorios'; END IF;
  -- Serializa la verificación de nicknames iguales (sin cambiar restricciones existentes).
  PERFORM pg_advisory_xact_lock(hashtext(lower(trim(p_nickname)))::bigint);
  IF EXISTS (SELECT 1 FROM public.db_usuarios
             WHERE lower(usu_nickname)=lower(trim(p_nickname)))
  THEN RAISE EXCEPTION 'El nombre de usuario ya está registrado'; END IF;
  SELECT * INTO v_prepared FROM jsonb_populate_record(NULL::public.db_usuarios,p_datos);
  INSERT INTO public.db_usuarios (
    usu_nickname,usu_password,usu_tipo,usu_activo,usu_acceso_habilitado,
    usu_nombre,usu_apellido,usu_rfc,usu_curp,usu_imss,usu_ine,
    usu_fechanac,usu_telefono,usu_correo,usu_depto,usu_puesto,
    usu_calle,usu_numero,usu_colonia,usu_municipio,usu_estado,usu_cp,usu_regimen
  ) VALUES (
    trim(p_nickname),p_hash_inutilizable,4,true,false,
    v_prepared.usu_nombre,v_prepared.usu_apellido,v_prepared.usu_rfc,
    v_prepared.usu_curp,v_prepared.usu_imss,v_prepared.usu_ine,
    v_prepared.usu_fechanac,v_prepared.usu_telefono,v_prepared.usu_correo,
    v_prepared.usu_depto,v_prepared.usu_puesto,v_prepared.usu_calle,
    v_prepared.usu_numero,v_prepared.usu_colonia,v_prepared.usu_municipio,
    v_prepared.usu_estado,v_prepared.usu_cp,v_prepared.usu_regimen
  ) RETURNING id_usuario INTO v_id;
  INSERT INTO public.axia_rrhh_historial (actor_id,actor_usuario,empleado_id,motivo,anterior,posterior)
  VALUES (p_actor_id,trim(p_actor_usuario),v_id,trim(p_motivo),'{}'::jsonb,
    jsonb_build_object('accion','ALTA','usu_nickname',trim(p_nickname),'usu_tipo',4,
      'usu_activo',true,'usu_acceso_habilitado',false));
  RETURN jsonb_build_object('id_usuario',v_id,'alta',true,'acceso_habilitado',false);
END; $$;

CREATE OR REPLACE FUNCTION public.axia_rrhh_baja_usuario(
  p_id bigint,p_actor_id bigint,p_actor_usuario text,p_motivo text,
  p_hash_revocado text,p_estado_esperado boolean
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $$
DECLARE v_usuario public.db_usuarios%ROWTYPE;
BEGIN
  IF current_user <> 'service_role' THEN RAISE EXCEPTION 'Servicio RRHH exclusivo'; END IF;
  IF NOT EXISTS (SELECT 1 FROM public.db_usuarios
      WHERE id_usuario=p_actor_id AND usu_tipo=10 AND usu_activo IS TRUE AND usu_acceso_habilitado IS TRUE)
  THEN RAISE EXCEPTION 'Actor RRHH no autorizado'; END IF;
  IF p_id IS NULL OR p_id=p_actor_id OR length(trim(coalesce(p_motivo,''))) < 8
     OR p_hash_revocado !~ '^\$2[aby]\$' OR length(p_hash_revocado)<50
     OR p_estado_esperado IS DISTINCT FROM true
  THEN RAISE EXCEPTION 'Solicitud de baja inválida'; END IF;
  SELECT * INTO v_usuario FROM public.db_usuarios WHERE id_usuario=p_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Empleado no encontrado'; END IF;
  IF v_usuario.usu_activo IS DISTINCT FROM p_estado_esperado
  THEN RAISE EXCEPTION 'Estado actualizado por otro usuario: vuelve a consultar'; END IF;
  IF v_usuario.usu_tipo IN (1,10)
  THEN RAISE EXCEPTION 'RH no puede dar de baja Administradores ni cuentas de RH'; END IF;
  UPDATE public.db_usuarios
     SET usu_activo=false,usu_acceso_habilitado=false,
         usu_password=p_hash_revocado,usu_fecha_baja=now()
   WHERE id_usuario=p_id;
  INSERT INTO public.axia_rrhh_historial (actor_id,actor_usuario,empleado_id,motivo,anterior,posterior)
  VALUES (p_actor_id,trim(p_actor_usuario),p_id,trim(p_motivo),
    jsonb_build_object('accion','BAJA','usu_activo',true,'usu_tipo',v_usuario.usu_tipo),
    jsonb_build_object('accion','BAJA','usu_activo',false,'usu_acceso_habilitado',false));
  RETURN jsonb_build_object('id_usuario',p_id,'baja',true);
END; $$;

REVOKE ALL ON FUNCTION public.axia_rrhh_alta_usuario(bigint,text,text,text,jsonb,text)
 FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.axia_rrhh_alta_usuario(bigint,text,text,text,jsonb,text) TO service_role;
REVOKE ALL ON FUNCTION public.axia_rrhh_baja_usuario(bigint,bigint,text,text,text,boolean)
 FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.axia_rrhh_baja_usuario(bigint,bigint,text,text,text,boolean) TO service_role;
COMMIT;
