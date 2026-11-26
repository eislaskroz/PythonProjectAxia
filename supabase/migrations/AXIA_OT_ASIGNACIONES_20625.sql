BEGIN;
CREATE OR REPLACE FUNCTION public.axia_desktop_save_ot_assignments(p_actor bigint, p_ot bigint, p_expected bigint[], p_users bigint[])
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog AS $$
DECLARE v_current bigint[]; v_users bigint[]; v_ot public.db_ordenes_trabajo%ROWTYPE; v_count integer;
BEGIN
  PERFORM 1 FROM public.db_usuarios WHERE id_usuario=p_actor AND usu_tipo=1 AND usu_activo IS TRUE AND usu_acceso_habilitado IS TRUE AND usu_fecha_baja IS NULL FOR SHARE;
  IF NOT FOUND THEN RAISE EXCEPTION 'No autorizado' USING ERRCODE='42501'; END IF;
  IF p_users IS NULL OR p_expected IS NULL OR cardinality(p_users)>100 OR array_position(p_users,NULL) IS NOT NULL THEN RAISE EXCEPTION 'Selección inválida' USING ERRCODE='22023'; END IF;
  SELECT * INTO v_ot FROM public.db_ordenes_trabajo WHERE ot_id=p_ot FOR UPDATE;
  IF NOT FOUND OR v_ot.ot_estatus IS NULL OR v_ot.ot_estatus=3 THEN RAISE EXCEPTION 'OT no disponible' USING ERRCODE='22023'; END IF;
  SELECT coalesce(array_agg(id_asignacion ORDER BY id_asignacion),'{}'::bigint[]) INTO v_current FROM public.axia_ot_asignaciones WHERE ot_id=p_ot AND activo;
  IF v_current IS DISTINCT FROM p_expected THEN RAISE EXCEPTION 'Asignaciones modificadas; recarga' USING ERRCODE='40001'; END IF;
  SELECT coalesce(array_agg(DISTINCT x ORDER BY x),'{}'::bigint[]) INTO v_users FROM unnest(p_users) x;
  PERFORM 1 FROM public.db_usuarios WHERE id_usuario=ANY(v_users) ORDER BY id_usuario FOR SHARE;
  SELECT count(*) INTO v_count FROM public.db_usuarios WHERE id_usuario=ANY(v_users) AND usu_tipo IN (2,3,4) AND usu_activo IS TRUE AND usu_acceso_habilitado IS TRUE AND usu_fecha_baja IS NULL;
  IF v_count<>cardinality(v_users) THEN RAISE EXCEPTION 'Personal no autorizado' USING ERRCODE='22023'; END IF;
  IF (SELECT count(*) FROM public.db_usuarios WHERE id_usuario=ANY(v_users) AND usu_tipo=2)>1 OR (SELECT count(*) FROM public.db_usuarios WHERE id_usuario=ANY(v_users) AND usu_tipo=3)>1 THEN RAISE EXCEPTION 'Selecciona como máximo un jefe y un supervisor' USING ERRCODE='22023'; END IF;
  UPDATE public.axia_ot_asignaciones a SET activo=false, desactivado_en=clock_timestamp(), desactivado_por_id=p_actor WHERE a.ot_id=p_ot AND a.activo AND NOT EXISTS (SELECT 1 FROM public.db_usuarios u WHERE u.id_usuario=a.id_usuario AND u.id_usuario=ANY(v_users) AND a.rol_operativo=CASE u.usu_tipo WHEN 2 THEN 'JEFE_OPERACIONES' WHEN 3 THEN 'SUPERVISOR' WHEN 4 THEN 'TECNICO' END);
  INSERT INTO public.axia_ot_asignaciones(ot_id,id_usuario,rol_operativo,activo,asignado_por_id) SELECT p_ot,u.id_usuario,CASE u.usu_tipo WHEN 2 THEN 'JEFE_OPERACIONES' WHEN 3 THEN 'SUPERVISOR' ELSE 'TECNICO' END,true,p_actor FROM public.db_usuarios u WHERE u.id_usuario=ANY(v_users) AND NOT EXISTS (SELECT 1 FROM public.axia_ot_asignaciones a WHERE a.ot_id=p_ot AND a.id_usuario=u.id_usuario AND a.activo AND a.rol_operativo=CASE u.usu_tipo WHEN 2 THEN 'JEFE_OPERACIONES' WHEN 3 THEN 'SUPERVISOR' ELSE 'TECNICO' END);
  RETURN jsonb_build_object('ok',true);
END; $$;
REVOKE ALL ON FUNCTION public.axia_desktop_save_ot_assignments(bigint,bigint,bigint[],bigint[]) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.axia_desktop_save_ot_assignments(bigint,bigint,bigint[],bigint[]) TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.axia_ot_asignaciones_id_asignacion_seq TO service_role;
COMMIT;
