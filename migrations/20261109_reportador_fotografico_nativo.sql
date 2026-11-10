-- AXIA DESKTOP 2.06.15 | Reportador fotográfico nativo | Migración nueva
-- Ejecutar una sola vez en Supabase SQL Editor, revisando antes el proyecto.
-- No modifica tablas existentes de AXIA; crea axia_rf_* y bucket privado.
BEGIN;
CREATE TABLE IF NOT EXISTS public.axia_rf_sesiones (
  token_hash text PRIMARY KEY CHECK (length(token_hash)=64),
  usuario_id bigint NOT NULL,
  expira_en timestamptz NOT NULL,
  creada_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_axia_rf_sesiones_expira ON public.axia_rf_sesiones(expira_en);

-- Rate limiting server-side por cuenta: protege el endpoint de inicio de sesión.
CREATE TABLE IF NOT EXISTS public.axia_rf_intentos_login (
  cuenta_hash text PRIMARY KEY CHECK(length(cuenta_hash)=64),
  intentos integer NOT NULL CHECK(intentos>=0),
  inicio timestamptz NOT NULL DEFAULT now()
);
CREATE OR REPLACE FUNCTION public.axia_rf_solicitud_login(p_cuenta_hash text)
RETURNS boolean LANGUAGE plpgsql SET search_path=public AS $$
DECLARE v_intentos int;
BEGIN
  IF length(p_cuenta_hash)<>64 THEN RETURN false; END IF;
  INSERT INTO public.axia_rf_intentos_login(cuenta_hash,intentos,inicio)
  VALUES(p_cuenta_hash,1,now())
  ON CONFLICT (cuenta_hash) DO UPDATE
  SET intentos=CASE
      WHEN public.axia_rf_intentos_login.inicio<now()-interval '15 minutes' THEN 1
      ELSE public.axia_rf_intentos_login.intentos+1 END,
      inicio=CASE
      WHEN public.axia_rf_intentos_login.inicio<now()-interval '15 minutes' THEN now()
      ELSE public.axia_rf_intentos_login.inicio END
  RETURNING intentos INTO v_intentos;
  RETURN v_intentos<=12;
END;$$;

CREATE TABLE IF NOT EXISTS public.axia_rf_reportes (
  id_reporte bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  aco varchar(60) NOT NULL,
  cliente varchar(200) NOT NULL,
  sucursal varchar(200) NOT NULL,
  nombre_servicio varchar(250) NOT NULL,
  tecnico_responsable varchar(150) NOT NULL,
  fecha_servicio date NOT NULL,
  observaciones varchar(5000) NOT NULL DEFAULT '',
  cantidad_os smallint NOT NULL DEFAULT 1 CHECK (cantidad_os BETWEEN 1 AND 4),
  estado varchar(12) NOT NULL DEFAULT 'BORRADOR' CHECK(estado IN ('BORRADOR','FINALIZADO')),
  usuario_creador_id bigint NOT NULL,
  autor_nombre varchar(220) NOT NULL DEFAULT '',
  creado_en timestamptz NOT NULL DEFAULT now(),
  actualizado_en timestamptz NOT NULL DEFAULT now(),
  finalizado_en timestamptz
);
CREATE INDEX IF NOT EXISTS ix_axia_rf_reportes_autor_fecha ON public.axia_rf_reportes(usuario_creador_id,actualizado_en DESC);
CREATE INDEX IF NOT EXISTS ix_axia_rf_reportes_fecha ON public.axia_rf_reportes(actualizado_en DESC);

CREATE TABLE IF NOT EXISTS public.axia_rf_actividades (
  id_actividad bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_reporte bigint NOT NULL REFERENCES public.axia_rf_reportes(id_reporte) ON DELETE CASCADE,
  clave uuid NOT NULL,
  orden smallint NOT NULL CHECK(orden BETWEEN 1 AND 20),
  titulo varchar(200) NOT NULL,
  descripcion varchar(3000) NOT NULL DEFAULT '',
  descripcion_habilitada boolean NOT NULL DEFAULT true,
  cantidad_fotos smallint NOT NULL DEFAULT 2 CHECK (cantidad_fotos BETWEEN 1 AND 5),
  UNIQUE(id_reporte,clave)
);
CREATE INDEX IF NOT EXISTS ix_axia_rf_actividades_orden ON public.axia_rf_actividades(id_reporte,orden);
CREATE TABLE IF NOT EXISTS public.axia_rf_fotos (
  id_reporte bigint NOT NULL,
  clave_actividad uuid NOT NULL,
  numero smallint NOT NULL CHECK(numero BETWEEN 1 AND 5),
  ruta text NOT NULL,
  nombre_original varchar(255) NOT NULL DEFAULT '',
  PRIMARY KEY(id_reporte,clave_actividad,numero),
  FOREIGN KEY(id_reporte,clave_actividad) REFERENCES public.axia_rf_actividades(id_reporte,clave) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS public.axia_rf_os (
  id_reporte bigint NOT NULL REFERENCES public.axia_rf_reportes(id_reporte) ON DELETE CASCADE,
  numero smallint NOT NULL CHECK(numero BETWEEN 1 AND 4),
  ruta text NOT NULL,
  nombre_original varchar(255) NOT NULL DEFAULT '',
  PRIMARY KEY(id_reporte,numero)
);
CREATE TABLE IF NOT EXISTS public.axia_rf_auditoria (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_reporte bigint NOT NULL REFERENCES public.axia_rf_reportes(id_reporte),
  usuario_id bigint NOT NULL,
  accion varchar(32) NOT NULL,
  estado_anterior varchar(12),
  estado_nuevo varchar(12),
  fecha timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.axia_rf_autoguardados (
  usuario_id bigint NOT NULL,
  clave uuid NOT NULL,
  reporte_id bigint,
  datos jsonb NOT NULL DEFAULT '{}'::jsonb,
  actualizado_en timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(usuario_id,clave)
);

-- Operación atómica (encabezado, actividades y eliminaciones).
CREATE OR REPLACE FUNCTION public.axia_rf_guardar(p_actor bigint,p_id bigint,p_datos jsonb)
RETURNS bigint LANGUAGE plpgsql SET search_path=public AS $$
DECLARE
  v_id bigint; v_estado text; v_autor bigint; v_autor_nombre text;
  v_act jsonb; v_n int:=0; v_claves uuid[]:=ARRAY[]::uuid[]; v_clave uuid;
BEGIN
  IF jsonb_typeof(p_datos->'actividades') IS DISTINCT FROM 'array' THEN
    RAISE EXCEPTION 'La lista de actividades debe ser un arreglo';
  END IF;
  IF jsonb_array_length(p_datos->'actividades') NOT BETWEEN 1 AND 20 THEN
    RAISE EXCEPTION 'El reporte debe contener entre 1 y 20 actividades';
  END IF;
  IF length(trim(coalesce(p_datos->>'aco',''))) NOT BETWEEN 1 AND 60 OR
     length(trim(coalesce(p_datos->>'cliente',''))) NOT BETWEEN 1 AND 200 OR
     length(trim(coalesce(p_datos->>'sucursal',''))) NOT BETWEEN 1 AND 200 OR
     length(trim(coalesce(p_datos->>'nombre_servicio',''))) NOT BETWEEN 1 AND 250 OR
     length(trim(coalesce(p_datos->>'tecnico_responsable',''))) NOT BETWEEN 1 AND 150 OR
     length(coalesce(p_datos->>'observaciones','')) > 5000 OR
     coalesce(p_datos->>'fecha_servicio','') !~ '^\d{4}-\d{2}-\d{2}$' THEN
    RAISE EXCEPTION 'Completa correctamente los datos generales';
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
    IF length(trim(coalesce(v_act->>'titulo',''))) NOT BETWEEN 1 AND 200 OR
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

CREATE OR REPLACE FUNCTION public.axia_rf_cambiar_estado(p_actor bigint,p_id bigint,p_accion text)
RETURNS text LANGUAGE plpgsql SET search_path=public AS $$
DECLARE v_estado text; v_autor bigint; v_cantidad int; v_esperadas int;
BEGIN
 SELECT estado,usuario_creador_id,cantidad_os INTO v_estado,v_autor,v_esperadas
 FROM public.axia_rf_reportes WHERE id_reporte=p_id FOR UPDATE;
 IF v_estado IS NULL THEN RAISE EXCEPTION 'Reporte no encontrado'; END IF;
 IF v_autor<>p_actor AND NOT EXISTS (SELECT 1 FROM public.db_usuarios WHERE id_usuario=p_actor AND usu_tipo=1) THEN
   RAISE EXCEPTION 'No tienes permiso para modificar el reporte'; END IF;
 IF p_accion='finalizar' THEN
   IF v_estado<>'BORRADOR' THEN RAISE EXCEPTION 'El reporte no es un borrador'; END IF;
   SELECT count(*) INTO v_cantidad FROM public.axia_rf_actividades WHERE id_reporte=p_id;
   IF v_cantidad<1 THEN RAISE EXCEPTION 'Agrega al menos una actividad'; END IF;
   IF EXISTS (SELECT 1 FROM public.axia_rf_actividades a LEFT JOIN
             (SELECT clave_actividad,count(*) AS cargadas FROM public.axia_rf_fotos WHERE id_reporte=p_id GROUP BY clave_actividad) f
             ON f.clave_actividad=a.clave
             WHERE a.id_reporte=p_id AND coalesce(f.cargadas,0)<>a.cantidad_fotos) THEN
      RAISE EXCEPTION 'Completa las fotografías requeridas en todas las actividades'; END IF;
   SELECT count(*) INTO v_cantidad FROM public.axia_rf_os WHERE id_reporte=p_id;
   IF v_cantidad<>v_esperadas THEN RAISE EXCEPTION 'Adjunta todas las Órdenes de Servicio seleccionadas'; END IF;
   UPDATE public.axia_rf_reportes SET estado='FINALIZADO',finalizado_en=now(),actualizado_en=now() WHERE id_reporte=p_id;
   INSERT INTO public.axia_rf_auditoria(id_reporte,usuario_id,accion,estado_anterior,estado_nuevo)
   VALUES(p_id,p_actor,'FINALIZAR',v_estado,'FINALIZADO');
   RETURN 'FINALIZADO';
 ELSIF p_accion='reabrir' THEN
   IF NOT EXISTS(SELECT 1 FROM public.db_usuarios WHERE id_usuario=p_actor AND usu_tipo=1) THEN
     RAISE EXCEPTION 'Solo Administrador puede reabrir reportes'; END IF;
   IF v_estado<>'FINALIZADO' THEN RAISE EXCEPTION 'El reporte no está finalizado'; END IF;
   UPDATE public.axia_rf_reportes SET estado='BORRADOR',finalizado_en=NULL,actualizado_en=now() WHERE id_reporte=p_id;
   INSERT INTO public.axia_rf_auditoria(id_reporte,usuario_id,accion,estado_anterior,estado_nuevo)
   VALUES(p_id,p_actor,'REABRIR',v_estado,'BORRADOR');
   RETURN 'BORRADOR';
 ELSE RAISE EXCEPTION 'Acción de estado inválida'; END IF;
END;$$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM storage.buckets WHERE id='axia-reportador') THEN
    INSERT INTO storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
    VALUES('axia-reportador','axia-reportador',false,12582912,ARRAY['image/jpeg']);
  END IF;
END $$;

-- Bloqueo en BD: las evidencias no se alteran mientras el reporte está FINALIZADO.
-- FOR UPDATE serializa la carga de imágenes con la finalización del reporte.
CREATE OR REPLACE FUNCTION public.axia_rf_validar_evidencia_editable()
RETURNS trigger LANGUAGE plpgsql SET search_path=public AS $$
DECLARE v_id bigint; v_estado text;
BEGIN
  v_id:=CASE WHEN TG_OP='DELETE' THEN OLD.id_reporte ELSE NEW.id_reporte END;
  SELECT estado INTO v_estado FROM public.axia_rf_reportes WHERE id_reporte=v_id FOR UPDATE;
  IF v_estado IS DISTINCT FROM 'BORRADOR' THEN
    RAISE EXCEPTION 'Las evidencias de un reporte finalizado son de solo lectura';
  END IF;
  IF TG_OP='DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END;$$;
DROP TRIGGER IF EXISTS trg_rf_foto_editable ON public.axia_rf_fotos;
CREATE TRIGGER trg_rf_foto_editable BEFORE INSERT OR UPDATE OR DELETE ON public.axia_rf_fotos
FOR EACH ROW EXECUTE FUNCTION public.axia_rf_validar_evidencia_editable();
DROP TRIGGER IF EXISTS trg_rf_os_editable ON public.axia_rf_os;
CREATE TRIGGER trg_rf_os_editable BEFORE INSERT OR UPDATE OR DELETE ON public.axia_rf_os
FOR EACH ROW EXECUTE FUNCTION public.axia_rf_validar_evidencia_editable();

-- Exclusivamente Edge Function con service_role. Ningún acceso directo con anon.
DO $$ DECLARE v_tab text; BEGIN
 FOREACH v_tab IN ARRAY ARRAY['axia_rf_sesiones','axia_rf_intentos_login','axia_rf_reportes','axia_rf_actividades','axia_rf_fotos','axia_rf_os','axia_rf_auditoria','axia_rf_autoguardados'] LOOP
   EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',v_tab);
   EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon,authenticated',v_tab);
   EXECUTE format('GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE public.%I TO service_role',v_tab);
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION public.axia_rf_validar_evidencia_editable() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.axia_rf_guardar(bigint,bigint,jsonb) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.axia_rf_solicitud_login(text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.axia_rf_solicitud_login(text) TO service_role;
REVOKE ALL ON FUNCTION public.axia_rf_cambiar_estado(bigint,bigint,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.axia_rf_guardar(bigint,bigint,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.axia_rf_cambiar_estado(bigint,bigint,text) TO service_role;
COMMIT;
