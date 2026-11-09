-- AXIA REPORTADOR 2.06.14 | Actualización incremental 09/11/2026
-- SOLO después de la instalación inicial del Reportador; NO volver a
-- ejecutar el SQL inicial. Ejecutar completo en Supabase SQL Editor.
-- Cambia de 20 a 50 actividades y verifica que el ACO exista en db_acos.
BEGIN;
ALTER TABLE public.axia_rf_actividades
 DROP CONSTRAINT IF EXISTS axia_rf_actividades_orden_check;
ALTER TABLE public.axia_rf_actividades
 ADD CONSTRAINT axia_rf_actividades_orden_check CHECK (orden BETWEEN 1 AND 50);

CREATE OR REPLACE FUNCTION public.axia_rf_guardar(p_actor bigint,p_id bigint,p_datos jsonb)
RETURNS bigint LANGUAGE plpgsql SET search_path=public AS $$
DECLARE
  v_id bigint; v_estado text; v_autor bigint; v_autor_nombre text;
  v_act jsonb; v_n int:=0; v_claves uuid[]:=ARRAY[]::uuid[]; v_clave uuid;
BEGIN
  IF jsonb_typeof(p_datos->'actividades') IS DISTINCT FROM 'array' THEN
    RAISE EXCEPTION 'La lista de actividades debe ser un arreglo';
  END IF;
  IF jsonb_array_length(p_datos->'actividades') NOT BETWEEN 1 AND 50 THEN
    RAISE EXCEPTION 'El reporte debe contener entre 1 y 50 actividades';
  END IF;
  IF length(trim(coalesce(p_datos->>'aco',''))) NOT BETWEEN 1 AND 60 OR
     length(trim(coalesce(p_datos->>'cliente',''))) NOT BETWEEN 1 AND 500 OR
     length(trim(coalesce(p_datos->>'sucursal',''))) NOT BETWEEN 1 AND 500 OR
     length(trim(coalesce(p_datos->>'nombre_servicio',''))) NOT BETWEEN 1 AND 250 OR
     length(trim(coalesce(p_datos->>'tecnico_responsable',''))) NOT BETWEEN 1 AND 150 OR
     length(coalesce(p_datos->>'observaciones','')) > 5000 OR
     coalesce(p_datos->>'fecha_servicio','') !~ '^\d{4}-\d{2}-\d{2}$' THEN
    RAISE EXCEPTION 'Completa correctamente los datos generales';
  END IF;
  -- El ACO debe existir en el catálogo AXIA (no aceptar un texto inventado).
  IF NOT EXISTS (SELECT 1 FROM public.db_acos WHERE aco_numero=trim(p_datos->>'aco')) THEN
    RAISE EXCEPTION 'Selecciona un ACO existente en AXIA';
  END IF;
  IF p_id IS NULL THEN
    SELECT concat_ws(' ',usu_nombre,usu_apellido) INTO v_autor_nombre FROM public.db_usuarios WHERE id_usuario=p_actor;
    IF v_autor_nombre IS NULL THEN RAISE EXCEPTION 'Usuario AXIA no localizado'; END IF;
    INSERT INTO public.axia_rf_reportes(aco,cliente,sucursal,nombre_servicio,tecnico_responsable,fecha_servicio,observaciones,usuario_creador_id,autor_nombre)
      VALUES(trim(p_datos->>'aco'),trim(p_datos->>'cliente'),trim(p_datos->>'sucursal'),trim(p_datos->>'nombre_servicio'),
             trim(p_datos->>'tecnico_responsable'),(p_datos->>'fecha_servicio')::date,coalesce(p_datos->>'observaciones',''),p_actor,v_autor_nombre)
      RETURNING id_reporte INTO v_id;
  ELSE
    SELECT estado,usuario_creador_id INTO v_estado,v_autor FROM public.axia_rf_reportes WHERE id_reporte=p_id FOR UPDATE;
    IF v_estado IS NULL THEN RAISE EXCEPTION 'Reporte no encontrado'; END IF;
    IF v_estado<>'BORRADOR' THEN RAISE EXCEPTION 'El reporte está finalizado y es de solo lectura'; END IF;
    IF v_autor<>p_actor AND NOT EXISTS (SELECT 1 FROM public.db_usuarios WHERE id_usuario=p_actor AND usu_tipo=1) THEN
      RAISE EXCEPTION 'No tienes acceso a este reporte';
    END IF;
    v_id:=p_id;
    UPDATE public.axia_rf_reportes SET aco=trim(p_datos->>'aco'),cliente=trim(p_datos->>'cliente'),
      sucursal=trim(p_datos->>'sucursal'),nombre_servicio=trim(p_datos->>'nombre_servicio'),
      tecnico_responsable=trim(p_datos->>'tecnico_responsable'),fecha_servicio=(p_datos->>'fecha_servicio')::date,
      observaciones=coalesce(p_datos->>'observaciones',''),actualizado_en=now() WHERE id_reporte=v_id;
  END IF;
  FOR v_act IN SELECT value FROM jsonb_array_elements(p_datos->'actividades') LOOP
    v_n:=v_n+1;
    v_clave:=(v_act->>'clave')::uuid;
    IF v_clave=ANY(v_claves) THEN RAISE EXCEPTION 'Actividad duplicada'; END IF;
    v_claves:=array_append(v_claves,v_clave);
    IF length(trim(coalesce(v_act->>'titulo',''))) NOT BETWEEN 1 AND 500 OR
       length(coalesce(v_act->>'descripcion',''))>3000 OR
       coalesce((v_act->>'cantidad_fotos')::int,0) NOT BETWEEN 1 AND 5 THEN
      RAISE EXCEPTION 'Título, descripción o cantidad de fotos inválidos en actividad %',v_n;
    END IF;
    INSERT INTO public.axia_rf_actividades(id_reporte,clave,orden,titulo,descripcion,descripcion_habilitada,cantidad_fotos)
      VALUES(v_id,v_clave,v_n,trim(v_act->>'titulo'),
        CASE WHEN coalesce((v_act->>'descripcion_habilitada')::boolean,true) THEN coalesce(v_act->>'descripcion','') ELSE '' END,
        coalesce((v_act->>'descripcion_habilitada')::boolean,true),(v_act->>'cantidad_fotos')::smallint)
      ON CONFLICT(id_reporte,clave) DO UPDATE SET orden=excluded.orden,titulo=excluded.titulo,
        descripcion=excluded.descripcion,descripcion_habilitada=excluded.descripcion_habilitada,cantidad_fotos=excluded.cantidad_fotos;
    DELETE FROM public.axia_rf_fotos WHERE id_reporte=v_id AND clave_actividad=v_clave
      AND numero>(v_act->>'cantidad_fotos')::smallint;
  END LOOP;
  DELETE FROM public.axia_rf_actividades WHERE id_reporte=v_id AND NOT (clave=ANY(v_claves));
  RETURN v_id;
END;$$;

REVOKE ALL ON FUNCTION public.axia_rf_guardar(bigint,bigint,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.axia_rf_guardar(bigint,bigint,jsonb) TO service_role;
COMMIT;
