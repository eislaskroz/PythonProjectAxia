-- AXIA DESKTOP - 20/08/2026
-- Amplía db_clientes_sucursales al nuevo modelo de dirección operativa
-- y carga las 11 sucursales de Distribuidora de Lácteos La Rancherita SA de CV (id_cliente=7).

BEGIN;

ALTER TABLE public.db_clientes_sucursales
    ADD COLUMN IF NOT EXISTS suc_calle_numero text,
    ADD COLUMN IF NOT EXISTS suc_colonia text,
    ADD COLUMN IF NOT EXISTS suc_codigo_postal text;

-- Conserva direcciones históricas: si sólo existe suc_domicilio, úsalo como
-- Calle y Número hasta que el registro sea actualizado desde AXIA.
UPDATE public.db_clientes_sucursales
SET suc_calle_numero = suc_domicilio
WHERE COALESCE(BTRIM(suc_calle_numero), '') = ''
  AND COALESCE(BTRIM(suc_domicilio), '') <> '';

WITH rancherita(id_cliente, suc_nombre, suc_calle_numero, suc_colonia, suc_municipio, suc_estado, suc_codigo_postal, suc_telefono) AS (
    VALUES
    (7, 'ERMITA', 'CALZ. ERMITA IZTAPALAPA #3490', 'SANTA MARÍA AZTAHUACAN', 'IZTAPALAPA', 'CIUDAD DE MÉXICO', '09500', '*'),
    (7, 'REYES', 'CALLE 9 MZ. 76 LT. 26-A', 'VALLE DE LOS REYES', 'LOS REYES LA PAZ', 'ESTADO DE MÉXICO', '56430', '*'),
    (7, 'GUSTAVO BAZ', 'GUSTAVO BAZ #21', 'BENITO JUÁREZ', 'NEZAHUALCÓYOTL', 'ESTADO DE MÉXICO', '57000', '*'),
    (7, 'F-620', 'NAVE F BODEGA 620', 'SANTA CRUZ (VENTA DE CARPIO)', 'ECATEPEC', 'ESTADO DE MÉXICO', '55065', '*'),
    (7, 'D-406', 'NAVE D BODEGA 406', 'SANTA CRUZ (VENTA DE CARPIO)', 'ECATEPEC', 'ESTADO DE MÉXICO', '55065', '*'),
    (7, 'D-401', 'NAVE D BODEGA 401', 'SANTA CRUZ (VENTA DE CARPIO)', 'ECATEPEC', 'ESTADO DE MÉXICO', '55065', '*'),
    (7, 'C-309', 'NAVE C BODEGA 309', 'SANTA CRUZ (VENTA DE CARPIO)', 'ECATEPEC', 'ESTADO DE MÉXICO', '55065', '*'),
    (7, 'TEXCOCO', 'COLÓN #210', 'TEXCOCO DE MORA CENTRO', 'TEXCOCO', 'ESTADO DE MÉXICO', '56100', '*'),
    (7, 'A-45', 'NAVE A BODEGA 45', 'CAMINO VIEJO A CHIMALHUACAN S/N (BARRIO EL VERGEL)', 'SAN VICENTE CHICOLOAPAN', 'ESTADO DE MÉXICO', '56370', '*'),
    (7, 'C-19', 'NAVE C BODEGA 19', 'CAMINO VIEJO A CHIMALHUACAN S/N (BARRIO EL VERGEL)', 'SAN VICENTE CHICOLOAPAN', 'ESTADO DE MÉXICO', '56370', '*'),
    (7, 'CARPIO', 'RANCHERÍA DE  ATLAUTENCO #38 BODEGA 10', 'SANTA CRUZ (VENTA DE CARPIO)', 'ECATEPEC', 'ESTADO DE MÉXICO', '55065', '*')
), actualizados AS (
    UPDATE public.db_clientes_sucursales s
    SET
        suc_calle_numero = r.suc_calle_numero,
        suc_colonia = r.suc_colonia,
        suc_municipio = r.suc_municipio,
        suc_estado = r.suc_estado,
        suc_codigo_postal = r.suc_codigo_postal,
        suc_telefono = r.suc_telefono,
        suc_domicilio = CONCAT_WS(', ', r.suc_calle_numero, r.suc_colonia, r.suc_municipio, r.suc_estado, 'C.P. ' || r.suc_codigo_postal),
        suc_estatus = 1
    FROM rancherita r
    WHERE s.id_cliente = r.id_cliente
      AND UPPER(BTRIM(s.suc_nombre)) = UPPER(BTRIM(r.suc_nombre))
    RETURNING s.suc_id
)
INSERT INTO public.db_clientes_sucursales (
    id_cliente, suc_nombre, suc_calle_numero, suc_colonia, suc_municipio,
    suc_estado, suc_codigo_postal, suc_telefono, suc_domicilio, suc_estatus
)
SELECT
    r.id_cliente, r.suc_nombre, r.suc_calle_numero, r.suc_colonia, r.suc_municipio,
    r.suc_estado, r.suc_codigo_postal, r.suc_telefono,
    CONCAT_WS(', ', r.suc_calle_numero, r.suc_colonia, r.suc_municipio, r.suc_estado, 'C.P. ' || r.suc_codigo_postal),
    1
FROM rancherita r
WHERE NOT EXISTS (
    SELECT 1
    FROM public.db_clientes_sucursales s
    WHERE s.id_cliente = r.id_cliente
      AND UPPER(BTRIM(s.suc_nombre)) = UPPER(BTRIM(r.suc_nombre))
);

COMMIT;
