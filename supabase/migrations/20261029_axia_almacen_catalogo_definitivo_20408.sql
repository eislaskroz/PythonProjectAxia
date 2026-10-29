-- AXIA DESKTOP 2.04.08 | CATALOGO UNICO + MOVIMIENTOS REALES
-- EJECUTAR UNA SOLA VEZ DESPUES DE RESPALDAR public.axia_almacen_catalogo_piloto.
-- No borra productos ni sobrescribe saldos ya inicializados.
-- El saldo inicial usa EXISTENCIA_ELEVENTA IMPORTADA como referencia PROVISIONAL.
-- Si NO corresponde al inventario físico, conciliar antes de entregar materiales.
-- La aplicación NO cambia las existencias en ELEVENTA.
BEGIN;
DO $m$
BEGIN
 IF to_regclass('public.axia_almacen_catalogo') IS NULL THEN
   IF to_regclass('public.axia_almacen_catalogo_piloto') IS NULL THEN
     RAISE EXCEPTION 'FALTA_CATALOGO: carga primero los 1886 productos del Excel';
   END IF;
   ALTER TABLE public.axia_almacen_catalogo_piloto RENAME TO axia_almacen_catalogo;
 END IF;
END $m$;
ALTER TABLE public.axia_almacen_catalogo
 ADD COLUMN IF NOT EXISTS saldo_actual numeric(20,3),
 ADD COLUMN IF NOT EXISTS activo boolean NOT NULL DEFAULT true,
 ADD COLUMN IF NOT EXISTS saldo_inicial_origen text,
 ADD COLUMN IF NOT EXISTS actualizado_el timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.axia_almacen_catalogo ALTER COLUMN fila_origen_eleventa DROP NOT NULL;
-- Inicialización una sola vez: nunca recalcular saldos después de los movimientos.
UPDATE public.axia_almacen_catalogo
 SET saldo_actual = greatest(0,round(coalesce(existencia_eleventa,0),3)),
     saldo_inicial_origen = 'ELEVENTA_IMPORTACION_20261029_SIN_CONCILIAR'
 WHERE saldo_actual IS NULL;
ALTER TABLE public.axia_almacen_catalogo ALTER COLUMN saldo_actual SET NOT NULL;
DO $m$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='axia_almacen_saldo_no_negativo') THEN
    ALTER TABLE public.axia_almacen_catalogo ADD CONSTRAINT axia_almacen_saldo_no_negativo CHECK(saldo_actual>=0);
  END IF;
END $m$;
CREATE TABLE IF NOT EXISTS public.axia_almacen_maestro_movimientos (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 idempotencia uuid NOT NULL UNIQUE,
 codigo_axia text NOT NULL REFERENCES public.axia_almacen_catalogo(codigo_axia),
 tipo text NOT NULL CHECK(tipo IN ('ENTRADA','SALIDA')),
 cantidad numeric(20,3) NOT NULL CHECK(cantidad>0 AND cantidad<=1000000),
 saldo_anterior numeric(20,3) NOT NULL CHECK(saldo_anterior>=0),
 saldo_nuevo numeric(20,3) NOT NULL CHECK(saldo_nuevo>=0),
 motivo text NOT NULL CHECK(length(btrim(motivo)) BETWEEN 1 AND 250),
 referencia text NOT NULL DEFAULT '',
 destinatario text NOT NULL DEFAULT '',
 responsable_id text NOT NULL,
 responsable text NOT NULL DEFAULT '',
 fecha timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT axia_almacen_maestro_salida_recibe CHECK(tipo <> 'SALIDA' OR length(btrim(destinatario))>0)
);
CREATE INDEX IF NOT EXISTS axia_almacen_maestro_mov_product_fecha
 ON public.axia_almacen_maestro_movimientos(codigo_axia,fecha DESC);
CREATE INDEX IF NOT EXISTS axia_almacen_maestro_mov_referencia
 ON public.axia_almacen_maestro_movimientos(referencia);
CREATE TABLE IF NOT EXISTS public.axia_almacen_maestro_entregas_ot (
 idempotencia uuid PRIMARY KEY,
 ot_folio text NOT NULL,
 firma text NOT NULL,
 responsable_id text NOT NULL,
 resultado jsonb NOT NULL DEFAULT '{}'::jsonb,
 fecha timestamptz NOT NULL DEFAULT now()
);
-- La clave anon del escritorio no puede leer ni modificar estas tablas.
ALTER TABLE public.axia_almacen_catalogo ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.axia_almacen_maestro_movimientos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.axia_almacen_maestro_entregas_ot ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.axia_almacen_catalogo,public.axia_almacen_maestro_movimientos,
 public.axia_almacen_maestro_entregas_ot FROM PUBLIC,anon,authenticated;
GRANT ALL ON public.axia_almacen_catalogo,public.axia_almacen_maestro_movimientos,
 public.axia_almacen_maestro_entregas_ot TO service_role;

-- Límite de intentos del login de Almacén (no requiere tablas de laboratorio).
CREATE TABLE IF NOT EXISTS public.axia_almacen_sesion_intentos (
 nickname text PRIMARY KEY,
 errores integer NOT NULL DEFAULT 0,
 bloqueado_hasta timestamptz,
 actualizado timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.axia_almacen_sesion_intentos ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.axia_almacen_sesion_intentos FROM PUBLIC,anon,authenticated;
GRANT ALL ON public.axia_almacen_sesion_intentos TO service_role;
CREATE OR REPLACE FUNCTION public.axia_almacen_login_permitido(p_nickname text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $fn$
DECLARE v_hasta timestamptz;
BEGIN
 IF p_nickname IS NULL OR length(btrim(p_nickname)) NOT BETWEEN 1 AND 120 THEN RETURN false; END IF;
 SELECT bloqueado_hasta INTO v_hasta FROM public.axia_almacen_sesion_intentos
 WHERE nickname=lower(btrim(p_nickname));
 RETURN v_hasta IS NULL OR v_hasta <= now();
END;$fn$;
CREATE OR REPLACE FUNCTION public.axia_almacen_registrar_login(p_nickname text,p_correcto boolean)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $fn$
DECLARE registro public.axia_almacen_sesion_intentos%ROWTYPE; nuevos integer;
BEGIN
 IF p_nickname IS NULL OR length(btrim(p_nickname)) NOT BETWEEN 1 AND 120 THEN RETURN false; END IF;
 INSERT INTO public.axia_almacen_sesion_intentos(nickname) VALUES(lower(btrim(p_nickname))) ON CONFLICT DO NOTHING;
 SELECT * INTO registro FROM public.axia_almacen_sesion_intentos WHERE nickname=lower(btrim(p_nickname)) FOR UPDATE;
 IF registro.bloqueado_hasta IS NOT NULL AND registro.bloqueado_hasta>now() THEN RETURN false; END IF;
 IF p_correcto THEN
  UPDATE public.axia_almacen_sesion_intentos SET errores=0,bloqueado_hasta=NULL,actualizado=now()
  WHERE nickname=registro.nickname;
  RETURN true;
 END IF;
 nuevos:=CASE WHEN registro.actualizado<now()-interval '15 minutes' THEN 1 ELSE registro.errores+1 END;
 UPDATE public.axia_almacen_sesion_intentos SET errores=nuevos,
 bloqueado_hasta=CASE WHEN nuevos>=5 THEN now()+interval '15 minutes' ELSE NULL END,
 actualizado=now() WHERE nickname=registro.nickname;
 RETURN false;
END;$fn$;
REVOKE ALL ON FUNCTION public.axia_almacen_login_permitido(text),
 public.axia_almacen_registrar_login(text,boolean) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.axia_almacen_login_permitido(text),
 public.axia_almacen_registrar_login(text,boolean) TO service_role;

-- Operación única, atómica, contra el catálogo maestro.
CREATE OR REPLACE FUNCTION public.axia_almacen_maestro_registrar_movimiento(
 p_codigo text,p_tipo text,p_cantidad numeric,p_motivo text,p_referencia text,
 p_destinatario text,p_responsable_id text,p_responsable text,p_idempotencia uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $fn$
DECLARE p public.axia_almacen_catalogo%ROWTYPE; m public.axia_almacen_maestro_movimientos%ROWTYPE;
 v_tipo text:=upper(btrim(coalesce(p_tipo,''))); v_codigo text:=btrim(coalesce(p_codigo,''));
 v_motivo text:=btrim(coalesce(p_motivo,'')); v_ref text:=btrim(coalesce(p_referencia,''));
 v_dest text:=btrim(coalesce(p_destinatario,'')); v_usuario text:=btrim(coalesce(p_responsable_id,''));
 v_saldo numeric(20,3);
BEGIN
 IF p_idempotencia IS NULL OR length(v_codigo) NOT BETWEEN 1 AND 120
  OR v_tipo NOT IN ('ENTRADA','SALIDA') OR p_cantidad IS NULL
  OR p_cantidad<=0 OR p_cantidad>1000000 OR p_cantidad<>trunc(p_cantidad,3)
  OR length(v_motivo) NOT BETWEEN 1 AND 250 OR length(v_ref)>120
  OR length(v_dest)>120 OR v_usuario='' OR (v_tipo='SALIDA' AND v_dest='')
 THEN RAISE EXCEPTION 'MOVIMIENTO_INVALIDO'; END IF;
 -- Serializa los reintentos de la misma solicitud, incluso entre clientes distintos.
 PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(p_idempotencia::text,11));
 SELECT * INTO m FROM public.axia_almacen_maestro_movimientos WHERE idempotencia=p_idempotencia;
 IF FOUND THEN
   IF m.codigo_axia<>v_codigo OR m.tipo<>v_tipo OR m.cantidad<>p_cantidad
    OR m.motivo<>v_motivo OR m.referencia<>v_ref OR m.destinatario<>v_dest OR m.responsable_id<>v_usuario
   THEN RAISE EXCEPTION 'IDEMPOTENCIA_CON_DATOS_DISTINTOS'; END IF;
   RETURN pg_catalog.jsonb_build_object('codigo',m.codigo_axia,'tipo',m.tipo,
    'cantidad',m.cantidad,'saldo_anterior',m.saldo_anterior,'saldo_nuevo',m.saldo_nuevo,'id',m.id,'repetido',true);
 END IF;
 SELECT * INTO p FROM public.axia_almacen_catalogo WHERE codigo_axia=v_codigo AND activo FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'PRODUCTO_NO_ENCONTRADO'; END IF;
 v_saldo:=p.saldo_actual+CASE WHEN v_tipo='ENTRADA' THEN p_cantidad ELSE -p_cantidad END;
 IF v_saldo<0 THEN RAISE EXCEPTION 'EXISTENCIA_INSUFICIENTE'; END IF;
 UPDATE public.axia_almacen_catalogo SET saldo_actual=v_saldo,actualizado_el=now() WHERE codigo_axia=v_codigo;
 INSERT INTO public.axia_almacen_maestro_movimientos
 (idempotencia,codigo_axia,tipo,cantidad,saldo_anterior,saldo_nuevo,motivo,referencia,destinatario,responsable_id,responsable)
 VALUES(p_idempotencia,v_codigo,v_tipo,p_cantidad,p.saldo_actual,v_saldo,v_motivo,v_ref,v_dest,v_usuario,btrim(coalesce(p_responsable,'')))
 RETURNING * INTO m;
 RETURN pg_catalog.jsonb_build_object('codigo',v_codigo,'tipo',v_tipo,'cantidad',p_cantidad,
  'saldo_anterior',m.saldo_anterior,'saldo_nuevo',m.saldo_nuevo,'id',m.id,'repetido',false);
END;$fn$;
REVOKE ALL ON FUNCTION public.axia_almacen_maestro_registrar_movimiento(text,text,numeric,text,text,text,text,text,uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.axia_almacen_maestro_registrar_movimiento(text,text,numeric,text,text,text,text,text,uuid) TO service_role;

-- Una entrega por OT contiene varias partidas. Si falla una, se revierten TODAS.
CREATE OR REPLACE FUNCTION public.axia_almacen_maestro_registrar_salida_ot(
 p_folio text,p_partidas jsonb,p_destinatario text,p_motivo text,
 p_responsable_id text,p_responsable text,p_idempotencia uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $fn$
DECLARE r record;p public.axia_almacen_catalogo%ROWTYPE;anterior public.axia_almacen_maestro_entregas_ot%ROWTYPE;
 v_folio text:=upper(btrim(coalesce(p_folio,'')));v_dest text:=btrim(coalesce(p_destinatario,''));
 v_motivo text:=btrim(coalesce(p_motivo,''));v_usuario text:=btrim(coalesce(p_responsable_id,''));
 v_firma text; v_nuevo numeric(20,3); v_mov uuid; v_lista jsonb:='[]'::jsonb;v_result jsonb;
BEGIN
 IF p_idempotencia IS NULL OR length(v_folio) NOT BETWEEN 1 AND 120
  OR length(v_dest) NOT BETWEEN 1 AND 120 OR length(v_motivo) NOT BETWEEN 1 AND 250
  OR v_usuario='' OR p_partidas IS NULL OR pg_catalog.jsonb_typeof(p_partidas)<>'array'
  OR pg_catalog.jsonb_array_length(p_partidas) NOT BETWEEN 1 AND 80
 THEN RAISE EXCEPTION 'ENTREGA_OT_INVALIDA'; END IF;
 IF NOT EXISTS (SELECT 1 FROM public.db_ordenes_trabajo WHERE ot_folio=v_folio)
 THEN RAISE EXCEPTION 'OT_NO_ENCONTRADA'; END IF;
 -- Validación por fila: impide cantidades malformadas, vacías o de precisión excesiva.
 FOR r IN SELECT * FROM pg_catalog.jsonb_to_recordset(p_partidas) AS x(codigo text,cantidad numeric) LOOP
  IF length(btrim(coalesce(r.codigo,''))) NOT BETWEEN 1 AND 120 OR r.cantidad IS NULL
   OR r.cantidad<=0 OR r.cantidad>1000000 OR r.cantidad<>trunc(r.cantidad,3)
  THEN RAISE EXCEPTION 'PARTIDA_OT_INVALIDA'; END IF;
 END LOOP;
 SELECT pg_catalog.md5(v_folio||'|'||v_dest||'|'||v_motivo||'|'||v_usuario||'|'||
  (SELECT coalesce(pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object('codigo',q.codigo,'cantidad',q.cantidad)
    ORDER BY q.codigo)::text,'[]') FROM
   (SELECT btrim(x.codigo) codigo,sum(x.cantidad) cantidad FROM
    pg_catalog.jsonb_to_recordset(p_partidas) AS x(codigo text,cantidad numeric)
    GROUP BY btrim(x.codigo)) q)) INTO v_firma;
 PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(p_idempotencia::text,17));
 SELECT * INTO anterior FROM public.axia_almacen_maestro_entregas_ot WHERE idempotencia=p_idempotencia;
 IF FOUND THEN
  IF anterior.firma IS DISTINCT FROM v_firma THEN RAISE EXCEPTION 'IDEMPOTENCIA_CON_DATOS_DISTINTOS'; END IF;
  RETURN anterior.resultado||pg_catalog.jsonb_build_object('repetido',true);
 END IF;
 INSERT INTO public.axia_almacen_maestro_entregas_ot(idempotencia,ot_folio,firma,responsable_id)
 VALUES(p_idempotencia,v_folio,v_firma,v_usuario);
 FOR r IN SELECT btrim(x.codigo) AS codigo,sum(x.cantidad) cantidad
    FROM pg_catalog.jsonb_to_recordset(p_partidas) AS x(codigo text,cantidad numeric)
    GROUP BY btrim(x.codigo) ORDER BY btrim(x.codigo)
 LOOP
  IF r.cantidad>1000000 THEN RAISE EXCEPTION 'PARTIDA_OT_INVALIDA'; END IF;
  SELECT * INTO p FROM public.axia_almacen_catalogo WHERE codigo_axia=r.codigo AND activo FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'PRODUCTO_NO_ENCONTRADO: %',r.codigo; END IF;
  IF p.saldo_actual<r.cantidad THEN RAISE EXCEPTION 'EXISTENCIA_INSUFICIENTE: %',r.codigo; END IF;
  v_nuevo:=p.saldo_actual-r.cantidad;
  UPDATE public.axia_almacen_catalogo SET saldo_actual=v_nuevo,actualizado_el=now() WHERE codigo_axia=r.codigo;
  INSERT INTO public.axia_almacen_maestro_movimientos
   (idempotencia,codigo_axia,tipo,cantidad,saldo_anterior,saldo_nuevo,motivo,referencia,destinatario,responsable_id,responsable)
  VALUES(gen_random_uuid(),r.codigo,'SALIDA',r.cantidad,p.saldo_actual,v_nuevo,v_motivo,v_folio,v_dest,v_usuario,btrim(coalesce(p_responsable,'')))
  RETURNING id INTO v_mov;
  v_lista:=v_lista||pg_catalog.jsonb_build_array(pg_catalog.jsonb_build_object('codigo',r.codigo,
   'cantidad',r.cantidad,'saldo_nuevo',v_nuevo,'id',v_mov));
 END LOOP;
 v_result:=pg_catalog.jsonb_build_object('folio',v_folio,'cantidad_partidas',pg_catalog.jsonb_array_length(v_lista),
  'movimientos',v_lista,'repetido',false);
 UPDATE public.axia_almacen_maestro_entregas_ot SET resultado=v_result WHERE idempotencia=p_idempotencia;
 RETURN v_result;
END;$fn$;
REVOKE ALL ON FUNCTION public.axia_almacen_maestro_registrar_salida_ot(text,jsonb,text,text,text,text,uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.axia_almacen_maestro_registrar_salida_ot(text,jsonb,text,text,text,text,uuid) TO service_role;

-- Desactivación segura: requiere saldo cero; no borra movimientos.
CREATE OR REPLACE FUNCTION public.axia_almacen_maestro_desactivar_producto(p_codigo text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $fn$
DECLARE p public.axia_almacen_catalogo%ROWTYPE;
BEGIN
 SELECT * INTO p FROM public.axia_almacen_catalogo WHERE codigo_axia=btrim(p_codigo) FOR UPDATE;
 IF NOT FOUND OR NOT p.activo THEN RAISE EXCEPTION 'PRODUCTO_NO_ENCONTRADO'; END IF;
 IF p.saldo_actual<>0 THEN RAISE EXCEPTION 'SALDO_NO_CERO'; END IF;
 UPDATE public.axia_almacen_catalogo SET activo=false,actualizado_el=now() WHERE codigo_axia=p.codigo_axia;
 RETURN true;
END;$fn$;
REVOKE ALL ON FUNCTION public.axia_almacen_maestro_desactivar_producto(text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.axia_almacen_maestro_desactivar_producto(text) TO service_role;
COMMIT;
-- Comprobación al concluir:
SELECT COUNT(*) AS productos,COUNT(DISTINCT codigo_axia) AS codigos_unicos,
 SUM(saldo_actual) AS piezas_equivalentes_iniciales
FROM public.axia_almacen_catalogo;
