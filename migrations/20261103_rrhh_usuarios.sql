-- AXIA Recursos Humanos (rol 10). Ejecutar en STAGING primero y con respaldo.
-- Esta migración NO cambia datos de usuarios ni concede permisos a anon.
BEGIN;

CREATE TABLE IF NOT EXISTS public.axia_rrhh_historial (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  fecha timestamptz NOT NULL DEFAULT now(),
  actor_id bigint NOT NULL,
  actor_usuario text NOT NULL,
  empleado_id bigint NOT NULL,
  motivo text NOT NULL,
  anterior jsonb NOT NULL,
  posterior jsonb NOT NULL
);
ALTER TABLE public.axia_rrhh_historial ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.axia_rrhh_historial FROM PUBLIC, anon, authenticated;
GRANT INSERT, SELECT ON public.axia_rrhh_historial TO service_role;
REVOKE ALL ON SEQUENCE public.axia_rrhh_historial_id_seq FROM PUBLIC, anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.axia_rrhh_historial_id_seq TO service_role;

CREATE OR REPLACE FUNCTION public.axia_rrhh_actualizar_usuario(
    p_id bigint, p_actor_id bigint, p_actor_usuario text, p_motivo text,
    p_antes jsonb, p_cambios jsonb
) RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public
AS $$
DECLARE
  v_actual jsonb;
  v_posterior jsonb;
  v_col text;
  v_set text := '';
  v_campos text[] := ARRAY[
    'usu_nombre','usu_apellido','usu_rfc','usu_curp','usu_imss','usu_ine',
    'usu_fechanac','usu_telefono','usu_correo','usu_depto','usu_puesto',
    'usu_calle','usu_numero','usu_colonia','usu_municipio','usu_estado',
    'usu_cp','usu_regimen'
  ];
BEGIN
  IF current_user <> 'service_role' THEN
    RAISE EXCEPTION 'Servicio RRHH exclusivo';
  END IF;
  IF NOT EXISTS(SELECT 1 FROM public.db_usuarios WHERE id_usuario=p_actor_id AND usu_tipo=10) THEN
    RAISE EXCEPTION 'El actor no tiene rol Recursos Humanos';
  END IF;
  IF p_id IS NULL OR p_actor_id IS NULL OR length(trim(coalesce(p_motivo,'')))<8
    OR jsonb_typeof(p_antes)<>'object' OR jsonb_typeof(p_cambios)<>'object'
    OR p_cambios='{}'::jsonb THEN
    RAISE EXCEPTION 'Solicitud incompleta o sin cambios';
  END IF;
  SELECT to_jsonb(t) INTO v_actual FROM public.db_usuarios t WHERE t.id_usuario=p_id FOR UPDATE;
  IF v_actual IS NULL THEN RAISE EXCEPTION 'Empleado no encontrado'; END IF;
  FOR v_col IN SELECT jsonb_object_keys(p_cambios) LOOP
    IF NOT v_col=ANY(v_campos) THEN RAISE EXCEPTION 'Campo no autorizado para RRHH'; END IF;
    IF NOT p_antes ? v_col OR (v_actual->v_col IS DISTINCT FROM p_antes->v_col) THEN
       RAISE EXCEPTION 'El registro fue modificado; vuelve a buscar al empleado';
    END IF;
    IF v_actual->v_col IS DISTINCT FROM p_cambios->v_col THEN
      v_set := v_set || CASE WHEN v_set<>'' THEN ', ' ELSE '' END ||
        format('%I=(SELECT %I FROM jsonb_populate_record(NULL::public.db_usuarios,$2))',v_col,v_col);
    END IF;
  END LOOP;
  IF v_set='' THEN RAISE EXCEPTION 'No hay cambios reales'; END IF;
  EXECUTE format('UPDATE public.db_usuarios SET %s WHERE id_usuario=$1 RETURNING to_jsonb(db_usuarios)',v_set)
    INTO v_posterior USING p_id,p_cambios;
  INSERT INTO public.axia_rrhh_historial(actor_id,actor_usuario,empleado_id,motivo,anterior,posterior)
    VALUES(p_actor_id,trim(p_actor_usuario),p_id,trim(p_motivo),
      (SELECT jsonb_object_agg(k,v_actual->k) FROM unnest(v_campos) AS k WHERE p_cambios ? k),
      (SELECT jsonb_object_agg(k,v_posterior->k) FROM unnest(v_campos) AS k WHERE p_cambios ? k));
  RETURN jsonb_build_object('id_usuario',p_id,'actualizado',true);
END; $$;
REVOKE ALL ON FUNCTION public.axia_rrhh_actualizar_usuario(bigint,bigint,text,text,jsonb,jsonb)
  FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.axia_rrhh_actualizar_usuario(bigint,bigint,text,text,jsonb,jsonb)
  TO service_role;

COMMIT;
-- Si db_usuarios.usu_tipo tiene CHECK/FK que excluya 9 y 10, revisar la restricción
-- existente antes de crear usuarios de estos roles. No se cambia automáticamente.
