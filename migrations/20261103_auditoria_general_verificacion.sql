-- CONSULTAS DE SOLO LECTURA: ejecutarlas tras la migración.
-- 1. Verificar que ambos disparadores estén habilitados.
SELECT event_object_table AS tabla,trigger_name,action_timing,
       event_manipulation,action_statement
FROM information_schema.triggers
WHERE trigger_schema = 'public'
  AND trigger_name IN ('axia_rrhh_log_general_v1','axia_admin_log_general_v1')
ORDER BY event_object_table;

-- 2. Revisar movimientos recientes en el registro general sin datos sensibles.
SELECT fecha_hora,usuario,modulo,accion,descripcion,registro_afectado
FROM public.db_bitacora_mov
WHERE modulo IN ('RECURSOS_HUMANOS','LEVANTAMIENTOS','ACOS',
                 'ORDENES_TRABAJO','ORDENES_SERVICIO','BITACORAS_OPERATIVAS')
ORDER BY fecha_hora DESC LIMIT 50;
