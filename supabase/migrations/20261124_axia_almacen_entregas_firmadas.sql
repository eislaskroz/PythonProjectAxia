-- AXIA: recepción firmada móvil. Ejecutar UNA VEZ desde SQL Editor en un entorno de PRUEBA.
-- El descuento de existencias y la prueba de recepción se confirman en la MISMA transacción.
CREATE TABLE IF NOT EXISTS public.axia_almacen_recepciones_firmadas (
  idempotencia uuid PRIMARY KEY,
  movimiento_tipo text NOT NULL CHECK (movimiento_tipo IN ('SALIDA','SALIDA_OT')),
  responsable_id text NOT NULL,
  receptor_nombre text NOT NULL CHECK (length(btrim(receptor_nombre)) BETWEEN 3 AND 120),
  notas text NOT NULL DEFAULT '' CHECK (length(notas) <= 1000),
  firma_png_base64 text NOT NULL CHECK (length(firma_png_base64) BETWEEN 100 AND 180000),
  referencia text NOT NULL,
  registrado_el timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.axia_almacen_recepciones_firmadas ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.axia_almacen_recepciones_firmadas FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.axia_almacen_recepciones_firmadas TO service_role;
GRANT INSERT ON public.axia_almacen_recepciones_firmadas TO service_role;

CREATE OR REPLACE FUNCTION public.axia_almacen_field_salida_firmada(
 p_codigo text, p_cantidad numeric, p_motivo text, p_referencia text,
 p_destinatario text, p_responsable_id text, p_responsable text,
 p_idempotencia uuid, p_receptor_nombre text, p_notas text, p_firma_png_base64 text
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $fn$
DECLARE result jsonb; previo public.axia_almacen_recepciones_firmadas%ROWTYPE;
BEGIN
 IF length(btrim(coalesce(p_receptor_nombre,''))) NOT BETWEEN 3 AND 120
 OR length(coalesce(p_notas,'')) > 1000
 OR length(coalesce(p_firma_png_base64,'')) NOT BETWEEN 100 AND 180000
 OR left(coalesce(p_firma_png_base64,''),8) <> 'iVBORw0K'
 THEN RAISE EXCEPTION 'RECEPCION_INVALIDA'; END IF;
 -- No insertar un comprobante que no corresponda a la salida del mismo usuario.
 result := public.axia_almacen_maestro_registrar_movimiento(
   p_codigo,'SALIDA',p_cantidad,p_motivo,p_referencia,p_destinatario,
   p_responsable_id,p_responsable,p_idempotencia);
 SELECT * INTO previo FROM public.axia_almacen_recepciones_firmadas WHERE idempotencia=p_idempotencia;
 IF FOUND THEN
   IF previo.movimiento_tipo <> 'SALIDA' OR previo.responsable_id <> p_responsable_id
    OR previo.receptor_nombre <> btrim(p_receptor_nombre) OR previo.notas <> coalesce(p_notas,'')
    OR previo.firma_png_base64 <> p_firma_png_base64 OR previo.referencia <> coalesce(p_referencia,'')
   THEN RAISE EXCEPTION 'IDEMPOTENCIA_CON_DATOS_DISTINTOS'; END IF;
 ELSE
   INSERT INTO public.axia_almacen_recepciones_firmadas
   (idempotencia,movimiento_tipo,responsable_id,receptor_nombre,notas,firma_png_base64,referencia)
   VALUES(p_idempotencia,'SALIDA',p_responsable_id,btrim(p_receptor_nombre),
          coalesce(p_notas,''),p_firma_png_base64,coalesce(p_referencia,''));
 END IF;
 RETURN result;
END;$fn$;
REVOKE ALL ON FUNCTION public.axia_almacen_field_salida_firmada(text,numeric,text,text,text,text,text,uuid,text,text,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.axia_almacen_field_salida_firmada(text,numeric,text,text,text,text,text,uuid,text,text,text) TO service_role;

CREATE OR REPLACE FUNCTION public.axia_almacen_field_salida_ot_firmada(
 p_folio text,p_partidas jsonb,p_destinatario text,p_motivo text,
 p_responsable_id text,p_responsable text,p_idempotencia uuid,
 p_receptor_nombre text,p_notas text,p_firma_png_base64 text
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $fn$
DECLARE result jsonb; previo public.axia_almacen_recepciones_firmadas%ROWTYPE;
BEGIN
 IF length(btrim(coalesce(p_receptor_nombre,''))) NOT BETWEEN 3 AND 120
 OR length(coalesce(p_notas,'')) > 1000
 OR length(coalesce(p_firma_png_base64,'')) NOT BETWEEN 100 AND 180000
 OR left(coalesce(p_firma_png_base64,''),8) <> 'iVBORw0K'
 THEN RAISE EXCEPTION 'RECEPCION_INVALIDA'; END IF;
 result := public.axia_almacen_maestro_registrar_salida_ot(
  p_folio,p_partidas,p_destinatario,p_motivo,p_responsable_id,p_responsable,p_idempotencia);
 SELECT * INTO previo FROM public.axia_almacen_recepciones_firmadas WHERE idempotencia=p_idempotencia;
 IF FOUND THEN
   IF previo.movimiento_tipo <> 'SALIDA_OT' OR previo.responsable_id <> p_responsable_id
    OR previo.receptor_nombre <> btrim(p_receptor_nombre) OR previo.notas <> coalesce(p_notas,'')
    OR previo.firma_png_base64 <> p_firma_png_base64 OR previo.referencia <> upper(btrim(p_folio))
   THEN RAISE EXCEPTION 'IDEMPOTENCIA_CON_DATOS_DISTINTOS'; END IF;
 ELSE
   INSERT INTO public.axia_almacen_recepciones_firmadas
   (idempotencia,movimiento_tipo,responsable_id,receptor_nombre,notas,firma_png_base64,referencia)
   VALUES(p_idempotencia,'SALIDA_OT',p_responsable_id,btrim(p_receptor_nombre),
          coalesce(p_notas,''),p_firma_png_base64,upper(btrim(p_folio)));
 END IF;
 RETURN result;
END;$fn$;
REVOKE ALL ON FUNCTION public.axia_almacen_field_salida_ot_firmada(text,jsonb,text,text,text,text,uuid,text,text,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.axia_almacen_field_salida_ot_firmada(text,jsonb,text,text,text,text,uuid,text,text,text) TO service_role;
