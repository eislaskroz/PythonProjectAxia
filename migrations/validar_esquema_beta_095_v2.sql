-- AXIA Beta 0.95 - Validación de esquema V2
-- Distingue claramente tablas inexistentes de columnas faltantes.

WITH tablas_requeridas(tabla) AS (
VALUES
('db_clientes_sucursales'),
('db_usuarios'),
('db_obras_civiles'),
('db_ordenes_trabajo')
),
tablas_faltantes AS (
SELECT tr.tabla
FROM tablas_requeridas tr
LEFT JOIN information_schema.tables t
  ON t.table_schema='public' AND t.table_name=tr.tabla
WHERE t.table_name IS NULL
),
columnas_requeridas(tabla,columna) AS (
VALUES
('db_clientes_sucursales','suc_estado'),('db_clientes_sucursales','suc_municipio'),
('db_usuarios','usu_correo'),
('db_obras_civiles','id_aco'),('db_obras_civiles','id_sucursal'),('db_obras_civiles','id_contacto'),
('db_obras_civiles','obc_folio'),('db_obras_civiles','obc_fecha'),('db_obras_civiles','obc_aco_numero'),
('db_obras_civiles','obc_cliente'),('db_obras_civiles','obc_contacto'),('db_obras_civiles','obc_sucursal'),
('db_obras_civiles','obc_direccion'),('db_obras_civiles','obc_responsable_axia'),('db_obras_civiles','obc_supervisor'),
('db_obras_civiles','obc_tipo_giro'),('db_obras_civiles','obc_nombre_proyecto'),('db_obras_civiles','obc_superficie_disponible'),
('db_obras_civiles','obc_superficie_adecuada'),('db_obras_civiles','obc_planos_arquitectonicos'),
('db_obras_civiles','obc_requiere_maquinaria'),('db_obras_civiles','obc_permisos'),('db_obras_civiles','obc_observaciones_iniciales'),
('db_obras_civiles','obc_ejecucion_json'),('db_obras_civiles','obc_pruebas_resultado'),('db_obras_civiles','obc_pruebas_observaciones'),
('db_obras_civiles','obc_planos_acabados'),('db_obras_civiles','obc_generacion_planos'),('db_obras_civiles','obc_etapa_acabados'),
('db_obras_civiles','obc_obra_blanca'),('db_obras_civiles','obc_evidencias_json'),('db_obras_civiles','obc_preentrega_resultado'),
('db_obras_civiles','obc_preentrega_observaciones'),('db_obras_civiles','obc_entrega_formal'),('db_obras_civiles','obc_fecha_entrega'),
('db_obras_civiles','obc_observaciones_finales'),('db_obras_civiles','obc_firma_cliente_base64'),
('db_obras_civiles','obc_firma_tecnico_base64'),('db_obras_civiles','obc_estatus'),('db_obras_civiles','creado_por'),
('db_obras_civiles','fecha_registro'),
('db_ordenes_trabajo','id_aco'),('db_ordenes_trabajo','id_sucursal'),('db_ordenes_trabajo','id_contacto'),
('db_ordenes_trabajo','ot_aco_numero'),('db_ordenes_trabajo','ot_asunto'),('db_ordenes_trabajo','ot_cliente'),
('db_ordenes_trabajo','ot_contacto'),('db_ordenes_trabajo','ot_descripcion'),('db_ordenes_trabajo','ot_esi'),
('db_ordenes_trabajo','ot_estatus'),('db_ordenes_trabajo','ot_fecha'),('db_ordenes_trabajo','ot_folio'),
('db_ordenes_trabajo','ot_jefe_operacion'),('db_ordenes_trabajo','ot_numero_dias'),('db_ordenes_trabajo','ot_numero_personas'),
('db_ordenes_trabajo','ot_partidas_json'),('db_ordenes_trabajo','ot_prioridad'),('db_ordenes_trabajo','ot_sucursal'),
('db_ordenes_trabajo','ot_supervisor'),('db_ordenes_trabajo','creado_por'),('db_ordenes_trabajo','fecha_registro')
)
SELECT 'TABLA_FALTANTE' AS tipo, tf.tabla AS table_name, NULL::text AS elemento
FROM tablas_faltantes tf
UNION ALL
SELECT 'COLUMNA_FALTANTE', cr.tabla, cr.columna
FROM columnas_requeridas cr
JOIN information_schema.tables t ON t.table_schema='public' AND t.table_name=cr.tabla
LEFT JOIN information_schema.columns c
  ON c.table_schema='public' AND c.table_name=cr.tabla AND c.column_name=cr.columna
WHERE c.column_name IS NULL
ORDER BY 1,2,3;
