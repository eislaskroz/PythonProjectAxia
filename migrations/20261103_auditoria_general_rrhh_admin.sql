-- AXIA DESKTOP 2.06.04 | Auditoría general de RH y consola administrativa.
-- Instalar en STAGING primero. No realiza altas, modificaciones ni bajas de empleados.
-- Requisitos: migraciones 20261103_rrhh_usuarios.sql,
-- 20261103_rrhh_altas_bajas.sql y 20261102_admin_registros.sql instaladas.
-- Las operaciones efectuadas DESPUÉS de instalar este puente se registran de forma
-- atómica en historial específico y db_bitacora_mov. No se duplican los eventos
-- ya registrados por los servicios habituales de ACO, LEV, OT, OS y BIT.
-- IMPORTANTE: los motivos libres y datos de expedientes NO se copian al log general.
BEGIN;

DO $preflight$
DECLARE
    v_tabla text;
    v_col text;
    v_requeridas text[] := ARRAY[
        'id_usuario','usuario','modulo','accion','descripcion',
        'registro_afectado','ip_local','equipo'
    ];
BEGIN
    FOREACH v_tabla IN ARRAY ARRAY[
        'db_bitacora_mov','axia_rrhh_historial','axia_admin_registros_historial'
    ] LOOP
        IF to_regclass(format('public.%I', v_tabla)) IS NULL THEN
            RAISE EXCEPTION 'Falta la tabla public.%. Instalación cancelada sin cambios', v_tabla;
        END IF;
    END LOOP;
    FOREACH v_col IN ARRAY v_requeridas LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_catalog.pg_attribute
            WHERE attrelid='public.db_bitacora_mov'::regclass
              AND attname=v_col AND attnum > 0 AND NOT attisdropped
        ) THEN
            RAISE EXCEPTION 'Falta la columna db_bitacora_mov.%. No se instaló el puente',v_col;
        END IF;
    END LOOP;
END;
$preflight$;

CREATE OR REPLACE FUNCTION public.axia_auditoria_puente_movimientos()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog, public
AS $fn$
DECLARE
    v_modulo text;
    v_accion text;
    v_descripcion text;
    v_registro text;
BEGIN
    -- Solo los historiales emitidos por las funciones autenticadas del servidor.
    -- Nunca aceptar llamadas directas desde Desktop o clientes con anon key.
    IF current_user <> 'service_role' THEN
        RAISE EXCEPTION 'El puente de auditoría es exclusivo del servicio' USING ERRCODE='42501';
    END IF;

    IF TG_TABLE_SCHEMA <> 'public' THEN
        RAISE EXCEPTION 'Origen de auditoría no permitido';
    END IF;

    IF TG_TABLE_NAME = 'axia_rrhh_historial' THEN
        v_modulo := 'RECURSOS_HUMANOS';
        v_accion := coalesce(nullif(upper(NEW.posterior->>'accion'), ''),
                            nullif(upper(NEW.anterior->>'accion'), ''),
                            'MODIFICAR');
        IF v_accion NOT IN ('ALTA','BAJA','MODIFICAR') THEN
            RAISE EXCEPTION 'Acción de historial RH desconocida: %',v_accion;
        END IF;
        v_descripcion := CASE v_accion
            WHEN 'ALTA' THEN 'Alta laboral registrada desde Recursos Humanos'
            WHEN 'BAJA' THEN 'Baja laboral registrada desde Recursos Humanos'
            ELSE 'Actualización de expediente desde Recursos Humanos'
        END;
        -- Solo un ID interno, sin CURP/RFC/INE/IMSS, correos o motivo libre.
        v_registro := 'EMPLEADO:' || NEW.empleado_id::text;

        INSERT INTO public.db_bitacora_mov
            (id_usuario,usuario,modulo,accion,descripcion,registro_afectado,ip_local,equipo)
        VALUES
            (NEW.actor_id,NEW.actor_usuario,v_modulo,v_accion,v_descripcion,
             v_registro,'NO_DISPONIBLE','SERVIDOR_SUPABASE');

    ELSIF TG_TABLE_NAME = 'axia_admin_registros_historial' THEN
        -- Agrupa los eventos administrativos bajo el módulo operativo afectado.
        v_modulo := CASE NEW.tabla
            WHEN 'db_acos' THEN 'ACOS'
            WHEN 'db_levantamientos' THEN 'LEVANTAMIENTOS'
            WHEN 'db_ordenes_trabajo' THEN 'ORDENES_TRABAJO'
            WHEN 'db_ordenes_servicio' THEN 'ORDENES_SERVICIO'
            WHEN 'db_bitacoras' THEN 'BITACORAS_OPERATIVAS'
            ELSE NULL
        END;
        IF v_modulo IS NULL OR NEW.accion NOT IN ('EDITAR','ELIMINAR') THEN
            RAISE EXCEPTION 'Origen/acción administrativa no autorizados';
        END IF;
        v_accion := 'ADMIN_' || NEW.accion;
        v_descripcion := CASE NEW.accion
            WHEN 'EDITAR' THEN 'Edición autorizada desde Administración de Registros'
            ELSE 'Eliminación autorizada desde Administración de Registros'
        END;
        v_registro := NEW.tabla || ':' || NEW.registro_id;

        INSERT INTO public.db_bitacora_mov
            (id_usuario,usuario,modulo,accion,descripcion,registro_afectado,ip_local,equipo)
        VALUES
            (NEW.actor_id,NEW.actor_usuario,v_modulo,v_accion,v_descripcion,
             v_registro,'NO_DISPONIBLE','SERVIDOR_SUPABASE');
    ELSE
        RAISE EXCEPTION 'Tabla no autorizada para puente de movimientos';
    END IF;
    -- Si la inserción general falla, también falla la operación original.
    -- La misma transacción evita operaciones confirmadas sin movimiento.
    RETURN NEW;
END;
$fn$;

REVOKE ALL ON FUNCTION public.axia_auditoria_puente_movimientos()
    FROM PUBLIC, anon, authenticated;

DROP TRIGGER IF EXISTS axia_rrhh_log_general_v1 ON public.axia_rrhh_historial;
CREATE TRIGGER axia_rrhh_log_general_v1
AFTER INSERT ON public.axia_rrhh_historial
FOR EACH ROW EXECUTE FUNCTION public.axia_auditoria_puente_movimientos();

DROP TRIGGER IF EXISTS axia_admin_log_general_v1 ON public.axia_admin_registros_historial;
CREATE TRIGGER axia_admin_log_general_v1
AFTER INSERT ON public.axia_admin_registros_historial
FOR EACH ROW EXECUTE FUNCTION public.axia_auditoria_puente_movimientos();

COMMIT;
