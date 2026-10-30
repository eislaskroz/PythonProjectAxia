-- AXIA DESKTOP | Edición integral de Obra Civil | 2026-10-30
-- EJECUTAR UNA SOLA VEZ EN SUPABASE SQL EDITOR ANTES DE DESPLEGAR EDGE FUNCTION.
-- Mantiene obc_id y todos los adjuntos. SOLO cambia el folio si hay cambios
-- efectivos. La nueva numeración utiliza la misma secuencia que los INSERT.
-- El folio anterior queda auditado; no se crea un segundo registro de Obra Civil.
BEGIN;

CREATE TABLE IF NOT EXISTS public.axia_obc_historial_ediciones (
    solicitud uuid PRIMARY KEY,
    obc_id bigint NOT NULL,
    folio_anterior text NOT NULL UNIQUE,
    folio_nuevo text NOT NULL UNIQUE,
    editado_por text NOT NULL,
    campos_modificados text[] NOT NULL,
    cambios_confirmados jsonb NOT NULL,
    fecha_edicion timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_axia_obc_historial_id
    ON public.axia_obc_historial_ediciones(obc_id, fecha_edicion DESC);
REVOKE ALL ON TABLE public.axia_obc_historial_ediciones FROM PUBLIC, anon, authenticated;

CREATE OR REPLACE FUNCTION public.axia_obc_actualizar_versionada(
    p_folio_anterior text, p_cambios jsonb, p_usuario text, p_solicitud uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public
AS $fn$
DECLARE
    v_actual public.db_obras_civiles%ROWTYPE;
    v_id bigint;
    v_anterior text;
    v_nuevo text;
    v_clave text;
    v_tipo text;
    v_sql text;
    v_resultado jsonb;
    v_registrada public.axia_obc_historial_ediciones%ROWTYPE;
    v_permitidos text[] := ARRAY[
        'obc_fecha','obc_cliente','obc_contacto','obc_sucursal','obc_direccion',
        'obc_responsable_axia','obc_supervisor','obc_dias_trabajo','obc_personas_considerar',
        'obc_tipo_giro','obc_nombre_proyecto','obc_superficie_disponible','obc_superficie_adecuada',
        'obc_planos_arquitectonicos','obc_requiere_maquinaria','obc_permisos',
        'obc_observaciones_iniciales','obc_ejecucion_json','obc_planos_acabados',
        'obc_generacion_planos','obc_etapa_acabados','obc_obra_blanca',
        'obc_observaciones_finales','obc_anotacion_plano_json',
        'obc_evidencias_json','obc_archivos_adjuntos_json'];
BEGIN
    IF p_solicitud IS NULL OR p_folio_anterior !~ '^OBC-[0-9]{4,}$'
       OR p_usuario IS NULL OR length(trim(p_usuario))=0 THEN
        RAISE EXCEPTION 'SOLICITUD_INVALIDA';
    END IF;
    -- Reintento idempotente (red desconectada después del COMMIT).
    SELECT * INTO v_registrada
      FROM public.axia_obc_historial_ediciones WHERE solicitud=p_solicitud;
    IF FOUND THEN
        IF v_registrada.folio_anterior IS DISTINCT FROM p_folio_anterior OR
           v_registrada.editado_por IS DISTINCT FROM p_usuario OR
           v_registrada.cambios_confirmados IS DISTINCT FROM p_cambios THEN
            RAISE EXCEPTION 'SOLICITUD_NO_COINCIDE';
        END IF;
        SELECT to_jsonb(t) INTO v_resultado
          FROM public.db_obras_civiles t WHERE t.obc_id=v_registrada.obc_id;
        RETURN v_resultado;
    END IF;

    IF p_cambios IS NULL OR jsonb_typeof(p_cambios) <> 'object' OR p_cambios='{}'::jsonb THEN
        RAISE EXCEPTION 'SIN_CAMBIOS';
    END IF;
    FOR v_clave IN SELECT jsonb_object_keys(p_cambios) LOOP
        IF NOT v_clave=ANY(v_permitidos) THEN
            RAISE EXCEPTION 'CAMPO_NO_AUTORIZADO: %',v_clave;
        END IF;
        IF jsonb_typeof(p_cambios->v_clave)='null' THEN
            RAISE EXCEPTION 'VALOR_NULO_NO_PERMITIDO: %',v_clave;
        END IF;
    END LOOP;

    -- Bloqueo de fila para impedir dos ediciones simultáneas del mismo folio.
    SELECT * INTO v_actual FROM public.db_obras_civiles
     WHERE obc_folio=p_folio_anterior FOR UPDATE;
    IF NOT FOUND THEN
        -- Se pudo completar un reintento paralelo antes de adquirir el bloqueo.
        SELECT * INTO v_registrada FROM public.axia_obc_historial_ediciones
        WHERE solicitud=p_solicitud;
        IF FOUND AND v_registrada.editado_por=p_usuario AND
           v_registrada.folio_anterior=p_folio_anterior AND
           v_registrada.cambios_confirmados=p_cambios THEN
            SELECT to_jsonb(t) INTO v_resultado FROM public.db_obras_civiles t
             WHERE t.obc_id=v_registrada.obc_id;
            RETURN v_resultado;
        END IF;
        RAISE EXCEPTION 'FOLIO_DESACTUALIZADO';
    END IF;
    IF v_actual.obc_validado_ventas THEN
        RAISE EXCEPTION 'OBRA_VALIDADA_NO_EDITABLE';
    END IF;

    -- Evita consumir otro folio por reenviar valores que ya estaban guardados.
    IF NOT EXISTS (
        SELECT 1 FROM jsonb_each(p_cambios) e
        WHERE (to_jsonb(v_actual)->e.key) IS DISTINCT FROM e.value
    ) THEN
        RETURN to_jsonb(v_actual);
    END IF;

    -- Misma secuencia de altas, garantiza nuevo folio global sin colisión.
    v_nuevo := 'OBC-' || lpad(nextval('public.axia_obc_folio_seq'::regclass)::text,4,'0');
    v_sql := 'UPDATE public.db_obras_civiles SET obc_folio=$2';
    FOR v_clave IN SELECT jsonb_object_keys(p_cambios) LOOP
        SELECT pg_catalog.format_type(a.atttypid,a.atttypmod) INTO v_tipo
          FROM pg_catalog.pg_attribute a
          WHERE a.attrelid='public.db_obras_civiles'::regclass
            AND a.attname=v_clave AND a.attnum>0 AND NOT a.attisdropped;
        IF v_tipo IS NULL THEN RAISE EXCEPTION 'COLUMNA_INEXISTENTE: %',v_clave; END IF;
        v_sql := v_sql || format(', %I = ($1->>%L)::%s',v_clave,v_clave,v_tipo);
    END LOOP;
    v_sql := v_sql || ' WHERE obc_id=$3 AND obc_folio=$4 '
                  || 'AND obc_validado_ventas=false RETURNING to_jsonb(db_obras_civiles)';
    EXECUTE v_sql INTO v_resultado USING p_cambios,v_nuevo,v_actual.obc_id,p_folio_anterior;
    IF v_resultado IS NULL THEN RAISE EXCEPTION 'EDICION_CONFLICTO'; END IF;
    INSERT INTO public.axia_obc_historial_ediciones(
        solicitud,obc_id,folio_anterior,folio_nuevo,editado_por,campos_modificados,cambios_confirmados)
    VALUES (p_solicitud,v_actual.obc_id,p_folio_anterior,v_nuevo,p_usuario,
        ARRAY(SELECT jsonb_object_keys(p_cambios)),p_cambios);
    RETURN v_resultado;
END;
$fn$;
REVOKE ALL ON FUNCTION public.axia_obc_actualizar_versionada(text,jsonb,text,uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.axia_obc_actualizar_versionada(text,jsonb,text,uuid) TO service_role;
COMMIT;

-- Verificar posteriormente:
-- SELECT obc_id, obc_folio FROM public.db_obras_civiles ORDER BY obc_id DESC LIMIT 5;
-- SELECT obc_id, folio_anterior, folio_nuevo, editado_por, fecha_edicion
-- FROM public.axia_obc_historial_ediciones ORDER BY fecha_edicion DESC LIMIT 10;
