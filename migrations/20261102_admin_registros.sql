-- AXIA DESKTOP | Consola de Registros - preparación única.
-- Ejecutar en SQL Editor con una cuenta propietaria del esquema, primero en staging.
-- NUNCA otorgar acceso a esta función a anon/authenticated/PUBLIC.
CREATE TABLE IF NOT EXISTS public.axia_admin_registros_historial (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha timestamptz NOT NULL DEFAULT now(),
    actor_id bigint NOT NULL,
    actor_usuario text NOT NULL,
    tabla text NOT NULL,
    registro_id text NOT NULL,
    accion text NOT NULL CHECK (accion IN ('EDITAR','ELIMINAR')),
    motivo text NOT NULL,
    anterior jsonb NOT NULL,
    posterior jsonb
);
ALTER TABLE public.axia_admin_registros_historial ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.axia_admin_registros_historial FROM PUBLIC, anon, authenticated;
REVOKE ALL ON SEQUENCE public.axia_admin_registros_historial_id_seq FROM PUBLIC, anon, authenticated;

CREATE OR REPLACE FUNCTION public.axia_admin_mutar_registro(
    p_tabla text, p_id text, p_antes jsonb, p_cambios jsonb,
    p_accion text, p_actor_id bigint, p_actor_usuario text, p_motivo text
) RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public
AS $$
DECLARE
    v_pk text; v_folio text; v_campos text[]; v_actual jsonb; v_despues jsonb;
    v_col text; v_set text := ''; v_sql text; v_ref record; v_existe boolean;
    v_valor text; v_revision text; v_tabla text; v_campo text;
BEGIN
    -- Defensa redundante: únicamente puede ser llamada con el JWT service_role.
    IF coalesce(current_setting('request.jwt.claim.role', true),'') <> 'service_role' THEN
        RAISE EXCEPTION 'Operación reservada al servicio administrativo';
    END IF;
    IF p_accion NOT IN ('EDITAR','ELIMINAR') OR length(trim(coalesce(p_motivo,''))) < 8
       OR p_actor_id IS NULL OR length(trim(coalesce(p_actor_usuario,''))) < 1 THEN
        RAISE EXCEPTION 'Acción, actor o motivo inválidos';
    END IF;
    CASE p_tabla
        WHEN 'db_acos' THEN
            v_pk:='id_aco'; v_folio:='aco_numero';
            v_campos:=ARRAY['aco_cliente','aco_descripcion','aco_observaciones','aco_responsable','aco_fecha_inicio','aco_fecha_compromiso','aco_estatus'];
        WHEN 'db_levantamientos' THEN
            v_pk:='id_levantamiento'; v_folio:='lev_folio';
            v_campos:=ARRAY['lev_cliente','lev_tipo','lev_estatus','lev_prioridad','lev_contacto','lev_telefono','lev_correo','lev_direccion','lev_direccion_sucursal','lev_ubicacion','lev_descripcion','lev_requerimientos','lev_observaciones','lev_tecnico','lev_supervisor','lev_duracion_proyecto','lev_horas_estimadas','lev_dias_trabajo','lev_personas_considerar','lev_notas','lev_fecha_programada','lev_fecha_realizacion','lev_modalidad_operativa','lev_descripcion_fallas','lev_detalle_tecnico_json','lev_equipos_danados_json'];
        WHEN 'db_ordenes_trabajo' THEN
            v_pk:='ot_id'; v_folio:='ot_folio';
            v_campos:=ARRAY['ot_cliente','ot_contacto','ot_sucursal','ot_jefe_operacion','ot_supervisor','ot_esi','ot_numero_dias','ot_numero_personas','ot_asunto','ot_descripcion','ot_estatus','ot_prioridad','ot_fecha','ot_partidas_json'];
        WHEN 'db_ordenes_servicio' THEN
            v_pk:='id_orden'; v_folio:='os_folio';
            v_campos:=ARRAY['os_cliente','os_tipo','os_estatus','os_prioridad','os_contacto','os_telefono','os_correo','os_direccion','os_ubicacion','os_descripcion','os_actividades','os_materiales','os_observaciones','os_tecnico','os_supervisor','os_fecha_programada','os_fecha_inicio','os_fecha_cierre','os_sucursal','os_encargado','os_hora_llegada','os_hora_salida'];
        WHEN 'db_bitacoras' THEN
            v_pk:='id_bitacora'; v_folio:='bit_folio';
            v_campos:=ARRAY['bit_cliente','bit_descripcion','bit_direccion_sucursal','bit_encargado_proyecto_axia','bit_estatus','bit_fecha','bit_hora_llegada','bit_hora_salida','bit_observaciones','bit_porcentaje_avance','bit_tecnico','bit_tecnico_sitio'];
        ELSE RAISE EXCEPTION 'Tipo de registro no autorizado';
    END CASE;
    IF p_id IS NULL OR length(p_id)>128 OR jsonb_typeof(p_antes) <> 'object' THEN
        RAISE EXCEPTION 'Referencia de registro incorrecta';
    END IF;
    EXECUTE format('SELECT to_jsonb(t) FROM public.%I t WHERE t.%I::text = $1 FOR UPDATE',p_tabla,v_pk)
        INTO v_actual USING p_id;
    IF v_actual IS NULL THEN RAISE EXCEPTION 'El registro ya no existe'; END IF;
    IF v_actual IS DISTINCT FROM p_antes THEN
        RAISE EXCEPTION 'El registro cambió desde que se abrió. Actualiza la búsqueda antes de guardar.';
    END IF;

    IF p_accion='EDITAR' THEN
        IF jsonb_typeof(p_cambios) <> 'object' OR p_cambios='{}'::jsonb THEN
            RAISE EXCEPTION 'No hay cambios para guardar';
        END IF;
        FOR v_col IN SELECT jsonb_object_keys(p_cambios) LOOP
            IF NOT (v_col=ANY(v_campos)) THEN RAISE EXCEPTION 'Campo protegido o desconocido: %',v_col; END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_attribute a
                           WHERE a.attrelid=format('public.%I',p_tabla)::regclass
                           AND a.attname=v_col AND a.attnum>0 AND NOT a.attisdropped) THEN
                RAISE EXCEPTION 'La columna % no existe en el esquema actual',v_col;
            END IF;
            IF v_actual->v_col IS DISTINCT FROM p_cambios->v_col THEN
                v_set:=v_set || CASE WHEN v_set<>'' THEN ', ' ELSE '' END ||
                  format('%I=(SELECT %I FROM jsonb_populate_record(NULL::public.%I,$2) AS v)',v_col,v_col,p_tabla);
            END IF;
        END LOOP;
        IF v_set='' THEN RAISE EXCEPTION 'No hay cambios reales'; END IF;
        EXECUTE format('UPDATE public.%I SET %s WHERE %I::text=$1 RETURNING to_jsonb(%I)',
                       p_tabla,v_set,v_pk,p_tabla) INTO v_despues USING p_id,p_cambios;
    ELSE
        -- Relaciones por ID y folio, incluidos enlaces antiguos sin FK explícita.
        -- No se permite eliminación en cascada desde este módulo.
        FOR v_ref IN
            SELECT * FROM (VALUES
              ('db_acos','db_levantamientos','id_aco','id'),('db_acos','db_levantamientos','lev_aco_numero','folio'),
              ('db_acos','db_ordenes_trabajo','id_aco','id'),('db_acos','db_ordenes_trabajo','ot_aco_numero','folio'),
              ('db_acos','db_ordenes_servicio','id_aco','id'),('db_acos','db_ordenes_servicio','os_aco_numero','folio'),
              ('db_acos','db_bitacoras','bit_aco_numero','folio'),('db_acos','db_obras_civiles','obc_aco_numero','folio'),
              ('db_levantamientos','db_ordenes_trabajo','id_levantamiento','id'),('db_levantamientos','db_ordenes_trabajo','ot_folio_levantamiento','folio'),
              ('db_levantamientos','db_ordenes_servicio','id_levantamiento','id'),('db_levantamientos','db_ordenes_servicio','os_folio_levantamiento','folio'),
              ('db_levantamientos','db_cotizaciones','id_levantamiento','id'),('db_levantamientos','db_cotizaciones','lev_folio','folio'),
              ('db_ordenes_trabajo','db_bitacoras','ot_id','id'),('db_ordenes_trabajo','db_bitacoras','bit_ot_folio','folio'),
              ('db_ordenes_trabajo','db_ordenes_servicio','ot_id','id'),('db_ordenes_trabajo','db_ordenes_servicio','os_folio_ot','folio'),
              ('db_ordenes_servicio','db_ordenes_trabajo','ot_folio_os','folio'),
              ('db_bitacoras','db_ordenes_servicio','os_folio_bitacora','folio')
            ) AS x(padre,hija,columna,tipo) WHERE padre=p_tabla
        LOOP
            IF to_regclass(format('public.%I',v_ref.hija)) IS NULL OR NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name=v_ref.hija AND column_name=v_ref.columna
            ) THEN CONTINUE; END IF;
            v_valor := CASE WHEN v_ref.tipo='id' THEN p_id ELSE v_actual->>v_folio END;
            IF nullif(v_valor,'') IS NULL THEN CONTINUE; END IF;
            EXECUTE format('SELECT EXISTS(SELECT 1 FROM public.%I WHERE %I::text=$1 LIMIT 1)',v_ref.hija,v_ref.columna)
                INTO v_existe USING v_valor;
            IF v_existe THEN RAISE EXCEPTION 'No se puede eliminar: existen registros relacionados en %',v_ref.hija; END IF;
        END LOOP;
        EXECUTE format('DELETE FROM public.%I WHERE %I::text=$1',p_tabla,v_pk) USING p_id;
        v_despues:=NULL;
    END IF;

    INSERT INTO public.axia_admin_registros_historial(actor_id,actor_usuario,tabla,registro_id,accion,motivo,anterior,posterior)
    VALUES(p_actor_id,p_actor_usuario,p_tabla,p_id,p_accion,trim(p_motivo),v_actual,v_despues);
    RETURN jsonb_build_object('accion',p_accion,'folio',v_actual->>v_folio,'registro',v_despues);
END; $$;
REVOKE ALL ON FUNCTION public.axia_admin_mutar_registro(text,text,jsonb,jsonb,text,bigint,text,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.axia_admin_mutar_registro(text,text,jsonb,jsonb,text,bigint,text,text) TO service_role;
GRANT SELECT,INSERT ON public.axia_admin_registros_historial TO service_role;
GRANT USAGE,SELECT ON SEQUENCE public.axia_admin_registros_historial_id_seq TO service_role;
