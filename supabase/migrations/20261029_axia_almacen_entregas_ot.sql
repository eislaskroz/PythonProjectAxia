-- AXIA ALMACÉN · Entregas por Orden de Trabajo (OT) · 2026-10-29.
-- Revisar en entorno de pruebas; respaldar antes de ejecutar.
-- NO habilita movimientos ni configura el catálogo real de producción.
-- Requiere las migraciones de almacén anteriores y la tabla db_ordenes_trabajo.
BEGIN;

-- Laboratorio aislado (sin afectar inventario real)
CREATE TABLE IF NOT EXISTS public.axia_almacen_lab_ot_entregas (
  idempotencia uuid PRIMARY KEY,
  ot_folio text NOT NULL,
  firma text NOT NULL,
  responsable_id text NOT NULL,
  resultado jsonb NOT NULL DEFAULT '{}'::jsonb,
  fecha timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.axia_almacen_lab_ot_entregas ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.axia_almacen_lab_ot_entregas FROM PUBLIC, anon, authenticated;
GRANT ALL ON public.axia_almacen_lab_ot_entregas TO service_role;

CREATE OR REPLACE FUNCTION public.axia_almacen_lab_registrar_salida_ot(
    p_folio text, p_partidas jsonb, p_destinatario text,
    p_motivo text, p_responsable_id text, p_responsable text,
    p_idempotencia uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $fn$
DECLARE
    r record;
    producto public.axia_almacen_lab_productos%ROWTYPE;
    v_folio text := upper(btrim(coalesce(p_folio,'')));
    v_destinatario text := btrim(coalesce(p_destinatario,''));
    v_motivo text := btrim(coalesce(p_motivo,''));
    v_usuario text := btrim(coalesce(p_responsable_id,''));
    v_firma text;
    v_anterior public.axia_almacen_lab_ot_entregas%ROWTYPE;
    v_nuevo numeric(16,3);
    v_mov record;
    v_movimientos jsonb := '[]'::jsonb;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.axia_almacen_lab_config WHERE id=1 AND movimientos_habilitados = true) THEN
        RAISE EXCEPTION 'LAB_NO_HABILITADO';
    END IF;
    IF p_idempotencia IS NULL OR length(v_folio) NOT BETWEEN 1 AND 120
       OR length(v_destinatario) NOT BETWEEN 1 AND 120
       OR length(v_motivo) NOT BETWEEN 1 AND 250 OR v_usuario = ''
       OR p_partidas IS NULL OR jsonb_typeof(p_partidas) <> 'array'
       OR jsonb_array_length(p_partidas) NOT BETWEEN 1 AND 80 THEN
        RAISE EXCEPTION 'ENTREGA_OT_INVALIDA';
    END IF;
    -- Solo acepta folios de OT reales, no un número inventado por el cliente.
    IF NOT EXISTS (SELECT 1 FROM public.db_ordenes_trabajo WHERE ot_folio = v_folio) THEN
        RAISE EXCEPTION 'OT_NO_ENCONTRADA';
    END IF;
    -- Consolidamos códigos y validamos cantidades (un movimiento por artículo).
    FOR r IN
        SELECT btrim(x.codigo) AS codigo, SUM(x.cantidad) AS cantidad
        FROM jsonb_to_recordset(p_partidas) AS x(codigo text, cantidad numeric)
        GROUP BY btrim(x.codigo)
        ORDER BY btrim(x.codigo)
    LOOP
        IF length(coalesce(r.codigo,'')) NOT BETWEEN 1 AND 120 OR r.cantidad IS NULL
           OR r.cantidad <= 0 OR r.cantidad > 1000000
           OR r.cantidad <> trunc(r.cantidad,3) THEN
            RAISE EXCEPTION 'PARTIDA_OT_INVALIDA';
        END IF;
    END LOOP;
    SELECT md5(v_folio || '|' || v_destinatario || '|' || v_motivo || '|' || v_usuario
        || '|' || (SELECT coalesce(jsonb_agg(jsonb_build_object('codigo',q.codigo,'cantidad',q.cantidad)
                       ORDER BY q.codigo)::text,'[]')
                 FROM (SELECT btrim(x.codigo) codigo, sum(x.cantidad) cantidad
                       FROM jsonb_to_recordset(p_partidas) AS x(codigo text,cantidad numeric)
                       GROUP BY btrim(x.codigo)) q)) INTO v_firma;
    -- La llave única serializa peticiones concurrentes con la misma idempotencia.
    INSERT INTO public.axia_almacen_lab_ot_entregas(idempotencia,ot_folio,firma,responsable_id)
    VALUES(p_idempotencia,v_folio,v_firma,v_usuario)
    ON CONFLICT (idempotencia) DO NOTHING;
    IF NOT FOUND THEN
        SELECT * INTO v_anterior FROM public.axia_almacen_lab_ot_entregas WHERE idempotencia=p_idempotencia;
        IF v_anterior.firma IS DISTINCT FROM v_firma THEN
            RAISE EXCEPTION 'IDEMPOTENCIA_CON_DATOS_DISTINTOS';
        END IF;
        RETURN v_anterior.resultado || jsonb_build_object('repetido',true);
    END IF;
    -- Se ejecuta una única transacción. Cualquier partida inválida deshace TODO.
    -- Código ordenado para minimizar bloqueos cruzados.
    FOR r IN
        SELECT btrim(x.codigo) AS codigo, SUM(x.cantidad) AS cantidad
        FROM jsonb_to_recordset(p_partidas) AS x(codigo text,cantidad numeric)
        GROUP BY btrim(x.codigo)
        ORDER BY btrim(x.codigo)
    LOOP
        SELECT * INTO producto FROM public.axia_almacen_lab_productos
        WHERE codigo=r.codigo AND activo=true FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'PRODUCTO_NO_ENCONTRADO: %', r.codigo; END IF;
        IF producto.saldo < r.cantidad THEN
            RAISE EXCEPTION 'EXISTENCIA_INSUFICIENTE: %', r.codigo;
        END IF;
        v_nuevo := producto.saldo-r.cantidad;
        UPDATE public.axia_almacen_lab_productos SET saldo=v_nuevo,actualizado_en=now() WHERE id=producto.id;
        INSERT INTO public.axia_almacen_lab_movimientos
         (idempotencia,producto_id,tipo,cantidad,saldo_anterior,saldo_nuevo,
          motivo,referencia,destinatario,responsable_id,responsable)
        VALUES(gen_random_uuid(),producto.id,'SALIDA',r.cantidad,producto.saldo,v_nuevo,
          v_motivo,v_folio,v_destinatario,v_usuario,btrim(coalesce(p_responsable,'')))
        RETURNING id,cantidad,saldo_nuevo INTO v_mov;
        v_movimientos := v_movimientos || jsonb_build_array(jsonb_build_object(
          'codigo',r.codigo,'cantidad',r.cantidad,'saldo_nuevo',v_nuevo,'id',v_mov.id));
    END LOOP;
    UPDATE public.axia_almacen_lab_ot_entregas SET resultado=jsonb_build_object('folio',v_folio,
      'cantidad_partidas',jsonb_array_length(v_movimientos), 'movimientos',v_movimientos,
      'repetido',false) WHERE idempotencia=p_idempotencia
      RETURNING resultado INTO v_movimientos;
    RETURN v_movimientos;
END;
$fn$;
REVOKE ALL ON FUNCTION public.axia_almacen_lab_registrar_salida_ot(text,jsonb,text,text,text,text,uuid)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.axia_almacen_lab_registrar_salida_ot(text,jsonb,text,text,text,text,uuid)
  TO service_role;

-- Inventario real (permanece bloqueado por configuración)
CREATE TABLE IF NOT EXISTS public.axia_almacen_ot_entregas (
  idempotencia uuid PRIMARY KEY,
  ot_folio text NOT NULL,
  firma text NOT NULL,
  responsable_id text NOT NULL,
  resultado jsonb NOT NULL DEFAULT '{}'::jsonb,
  fecha timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.axia_almacen_ot_entregas ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.axia_almacen_ot_entregas FROM PUBLIC, anon, authenticated;
GRANT ALL ON public.axia_almacen_ot_entregas TO service_role;

CREATE OR REPLACE FUNCTION public.axia_almacen_registrar_salida_ot(
    p_folio text, p_partidas jsonb, p_destinatario text,
    p_motivo text, p_responsable_id text, p_responsable text,
    p_idempotencia uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $fn$
DECLARE
    r record;
    producto public.axia_almacen_productos%ROWTYPE;
    v_folio text := upper(btrim(coalesce(p_folio,'')));
    v_destinatario text := btrim(coalesce(p_destinatario,''));
    v_motivo text := btrim(coalesce(p_motivo,''));
    v_usuario text := btrim(coalesce(p_responsable_id,''));
    v_firma text;
    v_anterior public.axia_almacen_ot_entregas%ROWTYPE;
    v_nuevo numeric(16,3);
    v_mov record;
    v_movimientos jsonb := '[]'::jsonb;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.axia_almacen_config WHERE id=1 AND catalogo_autorizado = true AND movimientos_habilitados = true) THEN
        RAISE EXCEPTION 'ALMACEN_NO_HABILITADO';
    END IF;
    IF p_idempotencia IS NULL OR length(v_folio) NOT BETWEEN 1 AND 120
       OR length(v_destinatario) NOT BETWEEN 1 AND 120
       OR length(v_motivo) NOT BETWEEN 1 AND 250 OR v_usuario = ''
       OR p_partidas IS NULL OR jsonb_typeof(p_partidas) <> 'array'
       OR jsonb_array_length(p_partidas) NOT BETWEEN 1 AND 80 THEN
        RAISE EXCEPTION 'ENTREGA_OT_INVALIDA';
    END IF;
    -- Solo acepta folios de OT reales, no un número inventado por el cliente.
    IF NOT EXISTS (SELECT 1 FROM public.db_ordenes_trabajo WHERE ot_folio = v_folio) THEN
        RAISE EXCEPTION 'OT_NO_ENCONTRADA';
    END IF;
    -- Consolidamos códigos y validamos cantidades (un movimiento por artículo).
    FOR r IN
        SELECT btrim(x.codigo) AS codigo, SUM(x.cantidad) AS cantidad
        FROM jsonb_to_recordset(p_partidas) AS x(codigo text, cantidad numeric)
        GROUP BY btrim(x.codigo)
        ORDER BY btrim(x.codigo)
    LOOP
        IF length(coalesce(r.codigo,'')) NOT BETWEEN 1 AND 120 OR r.cantidad IS NULL
           OR r.cantidad <= 0 OR r.cantidad > 1000000
           OR r.cantidad <> trunc(r.cantidad,3) THEN
            RAISE EXCEPTION 'PARTIDA_OT_INVALIDA';
        END IF;
    END LOOP;
    SELECT md5(v_folio || '|' || v_destinatario || '|' || v_motivo || '|' || v_usuario
        || '|' || (SELECT coalesce(jsonb_agg(jsonb_build_object('codigo',q.codigo,'cantidad',q.cantidad)
                       ORDER BY q.codigo)::text,'[]')
                 FROM (SELECT btrim(x.codigo) codigo, sum(x.cantidad) cantidad
                       FROM jsonb_to_recordset(p_partidas) AS x(codigo text,cantidad numeric)
                       GROUP BY btrim(x.codigo)) q)) INTO v_firma;
    -- La llave única serializa peticiones concurrentes con la misma idempotencia.
    INSERT INTO public.axia_almacen_ot_entregas(idempotencia,ot_folio,firma,responsable_id)
    VALUES(p_idempotencia,v_folio,v_firma,v_usuario)
    ON CONFLICT (idempotencia) DO NOTHING;
    IF NOT FOUND THEN
        SELECT * INTO v_anterior FROM public.axia_almacen_ot_entregas WHERE idempotencia=p_idempotencia;
        IF v_anterior.firma IS DISTINCT FROM v_firma THEN
            RAISE EXCEPTION 'IDEMPOTENCIA_CON_DATOS_DISTINTOS';
        END IF;
        RETURN v_anterior.resultado || jsonb_build_object('repetido',true);
    END IF;
    -- Se ejecuta una única transacción. Cualquier partida inválida deshace TODO.
    -- Código ordenado para minimizar bloqueos cruzados.
    FOR r IN
        SELECT btrim(x.codigo) AS codigo, SUM(x.cantidad) AS cantidad
        FROM jsonb_to_recordset(p_partidas) AS x(codigo text,cantidad numeric)
        GROUP BY btrim(x.codigo)
        ORDER BY btrim(x.codigo)
    LOOP
        SELECT * INTO producto FROM public.axia_almacen_productos
        WHERE codigo=r.codigo AND activo=true FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'PRODUCTO_NO_ENCONTRADO: %', r.codigo; END IF;
        IF producto.saldo < r.cantidad THEN
            RAISE EXCEPTION 'EXISTENCIA_INSUFICIENTE: %', r.codigo;
        END IF;
        v_nuevo := producto.saldo-r.cantidad;
        UPDATE public.axia_almacen_productos SET saldo=v_nuevo,actualizado_en=now() WHERE id=producto.id;
        INSERT INTO public.axia_almacen_movimientos
         (idempotencia,producto_id,tipo,cantidad,saldo_anterior,saldo_nuevo,
          motivo,referencia,destinatario,responsable_id,responsable)
        VALUES(gen_random_uuid(),producto.id,'SALIDA',r.cantidad,producto.saldo,v_nuevo,
          v_motivo,v_folio,v_destinatario,v_usuario,btrim(coalesce(p_responsable,'')))
        RETURNING id,cantidad,saldo_nuevo INTO v_mov;
        v_movimientos := v_movimientos || jsonb_build_array(jsonb_build_object(
          'codigo',r.codigo,'cantidad',r.cantidad,'saldo_nuevo',v_nuevo,'id',v_mov.id));
    END LOOP;
    UPDATE public.axia_almacen_ot_entregas SET resultado=jsonb_build_object('folio',v_folio,
      'cantidad_partidas',jsonb_array_length(v_movimientos), 'movimientos',v_movimientos,
      'repetido',false) WHERE idempotencia=p_idempotencia
      RETURNING resultado INTO v_movimientos;
    RETURN v_movimientos;
END;
$fn$;
REVOKE ALL ON FUNCTION public.axia_almacen_registrar_salida_ot(text,jsonb,text,text,text,text,uuid)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.axia_almacen_registrar_salida_ot(text,jsonb,text,text,text,text,uuid)
  TO service_role;

COMMIT;
