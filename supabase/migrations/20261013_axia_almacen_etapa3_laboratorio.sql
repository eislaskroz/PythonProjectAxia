-- AXIA ALMACEN ETAPA 3: LABORATORIO PERSISTENTE INDEPENDIENTE.
-- NO CREA NI MODIFICA EXISTENCIAS REALES, db_usuarios, OT, ni tablas de produccion.
-- No ejecutarlo sin respaldo / validar en proyecto de pruebas si es posible.
-- Crea un entorno de 1886 codigos (semilla aparte) con saldos de apertura en cero.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.axia_almacen_lab_productos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  codigo text NOT NULL UNIQUE CHECK (length(btrim(codigo)) BETWEEN 1 AND 120),
  nombre text NOT NULL CHECK (length(btrim(nombre)) BETWEEN 1 AND 500),
  departamento text NOT NULL DEFAULT 'SIN DEPARTAMENTO',
  costo numeric(16,2) NOT NULL DEFAULT 0 CHECK (costo >= 0),
  precio_venta numeric(16,2) NOT NULL DEFAULT 0 CHECK (precio_venta >= 0),
  minimo numeric(16,3) NOT NULL DEFAULT 0 CHECK (minimo >= 0),
  maximo numeric(16,3) NOT NULL DEFAULT 0 CHECK (maximo >= 0),
  saldo_exportado numeric(16,3) NOT NULL DEFAULT 0 CHECK (saldo_exportado >= 0),
  saldo numeric(16,3) NOT NULL DEFAULT 0 CHECK (saldo >= 0),
  creado_en timestamptz NOT NULL DEFAULT now(),
  actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.axia_almacen_lab_config (
  id smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  movimientos_habilitados boolean NOT NULL DEFAULT false,
  modificado_en timestamptz NOT NULL DEFAULT now()
);
INSERT INTO public.axia_almacen_lab_config (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS public.axia_almacen_lab_movimientos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  idempotencia uuid NOT NULL UNIQUE,
  producto_id uuid NOT NULL REFERENCES public.axia_almacen_lab_productos(id),
  tipo text NOT NULL CHECK (tipo IN ('ENTRADA','SALIDA')),
  cantidad numeric(16,3) NOT NULL CHECK (cantidad > 0 AND cantidad <= 1000000),
  saldo_anterior numeric(16,3) NOT NULL CHECK (saldo_anterior >= 0),
  saldo_nuevo numeric(16,3) NOT NULL CHECK (saldo_nuevo >= 0),
  motivo varchar(250) NOT NULL CHECK (length(btrim(motivo)) > 0),
  referencia varchar(120) NOT NULL DEFAULT '',
  destinatario varchar(120) NOT NULL DEFAULT '',
  responsable_id text NOT NULL CHECK (length(btrim(responsable_id)) > 0),
  responsable text NOT NULL DEFAULT '',
  fecha timestamptz NOT NULL DEFAULT now(),
  CHECK (tipo <> 'SALIDA' OR length(btrim(destinatario)) > 0)
);
CREATE INDEX IF NOT EXISTS ix_axia_almacen_lab_movimientos_producto_fecha
  ON public.axia_almacen_lab_movimientos(producto_id, fecha DESC);

-- Control de intentos propio de la pasarela de Almacen. Sin cambios en el login general.
CREATE TABLE IF NOT EXISTS public.axia_almacen_lab_login_control (
  nickname text PRIMARY KEY,
  errores integer NOT NULL DEFAULT 0,
  bloqueado_hasta timestamptz,
  actualizado timestamptz NOT NULL DEFAULT now()
);

-- Denegar acceso al cliente publico incluso a lectura.
ALTER TABLE public.axia_almacen_lab_productos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.axia_almacen_lab_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.axia_almacen_lab_movimientos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.axia_almacen_lab_login_control ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.axia_almacen_lab_productos, public.axia_almacen_lab_config,
  public.axia_almacen_lab_movimientos, public.axia_almacen_lab_login_control
  FROM PUBLIC, anon, authenticated;
GRANT ALL ON public.axia_almacen_lab_productos, public.axia_almacen_lab_config,
  public.axia_almacen_lab_movimientos, public.axia_almacen_lab_login_control
  TO service_role;

CREATE OR REPLACE FUNCTION public.axia_almacen_lab_login_permitido(p_nickname text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_hasta timestamptz;
BEGIN
  IF p_nickname IS NULL OR length(btrim(p_nickname)) NOT BETWEEN 1 AND 120 THEN RETURN false; END IF;
  SELECT bloqueado_hasta INTO v_hasta FROM public.axia_almacen_lab_login_control
   WHERE nickname = lower(btrim(p_nickname));
  RETURN v_hasta IS NULL OR v_hasta <= now();
END;
$$;

-- Se invoca tras comprobar credenciales; solo fallos suman al bloqueo.
CREATE OR REPLACE FUNCTION public.axia_almacen_lab_registrar_login(p_nickname text, p_correcto boolean)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_registro public.axia_almacen_lab_login_control%ROWTYPE;
DECLARE v_errores integer;
BEGIN
  IF p_nickname IS NULL OR length(btrim(p_nickname)) NOT BETWEEN 1 AND 120 THEN RETURN false; END IF;
  INSERT INTO public.axia_almacen_lab_login_control(nickname) VALUES(lower(btrim(p_nickname)))
    ON CONFLICT DO NOTHING;
  SELECT * INTO v_registro FROM public.axia_almacen_lab_login_control
    WHERE nickname=lower(btrim(p_nickname)) FOR UPDATE;
  IF v_registro.bloqueado_hasta IS NOT NULL AND v_registro.bloqueado_hasta > now() THEN RETURN false; END IF;
  IF p_correcto THEN
    UPDATE public.axia_almacen_lab_login_control SET errores=0,bloqueado_hasta=NULL,actualizado=now()
      WHERE nickname=v_registro.nickname;
    RETURN true;
  END IF;
  v_errores := CASE WHEN (v_registro.bloqueado_hasta IS NOT NULL AND v_registro.bloqueado_hasta <= now())
                       OR v_registro.actualizado < now()-interval '15 minutes'
                     THEN 1 ELSE v_registro.errores+1 END;
  UPDATE public.axia_almacen_lab_login_control
    SET errores=v_errores,
        bloqueado_hasta=CASE WHEN v_errores>=5 THEN now()+interval '15 minutes' ELSE NULL END,
        actualizado=now() WHERE nickname=v_registro.nickname;
  RETURN false;
END;
$$;

CREATE OR REPLACE FUNCTION public.axia_almacen_lab_registrar_movimiento(
  p_codigo text, p_tipo text, p_cantidad numeric,
  p_motivo text, p_referencia text, p_destinatario text,
  p_responsable_id text, p_responsable text, p_idempotencia uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE p public.axia_almacen_lab_productos%ROWTYPE;
DECLARE prev public.axia_almacen_lab_movimientos%ROWTYPE;
DECLARE registrado public.axia_almacen_lab_movimientos%ROWTYPE;
DECLARE nuevo numeric(16,3);
BEGIN
  IF NOT EXISTS(SELECT 1 FROM public.axia_almacen_lab_config WHERE id=1 AND movimientos_habilitados=true) THEN
    RAISE EXCEPTION 'LAB_NO_HABILITADO';
  END IF;
  IF p_tipo IS NULL OR p_tipo NOT IN ('ENTRADA','SALIDA')
      OR p_cantidad IS NULL OR p_cantidad <= 0 OR p_cantidad > 1000000
      OR p_cantidad <> trunc(p_cantidad,3)
      OR p_codigo IS NULL OR length(btrim(p_codigo)) NOT BETWEEN 1 AND 120
      OR nullif(btrim(p_motivo),'') IS NULL OR length(p_motivo)>250
      OR length(coalesce(p_referencia,''))>120 OR length(coalesce(p_destinatario,''))>120
      OR nullif(btrim(p_responsable_id),'') IS NULL OR p_idempotencia IS NULL
      OR (p_tipo='SALIDA' AND nullif(btrim(p_destinatario),'') IS NULL) THEN
    RAISE EXCEPTION 'MOVIMIENTO_INVALIDO';
  END IF;
  -- Serializar por producto (elimina carreras para salidas simultaneas).
  SELECT * INTO p FROM public.axia_almacen_lab_productos WHERE codigo=btrim(p_codigo) FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'PRODUCTO_NO_ENCONTRADO'; END IF;
  SELECT * INTO prev FROM public.axia_almacen_lab_movimientos WHERE idempotencia=p_idempotencia;
  IF FOUND THEN
    IF prev.producto_id<>p.id OR prev.tipo<>p_tipo OR prev.cantidad<>p_cantidad
       OR prev.motivo<>btrim(p_motivo) OR prev.referencia<>btrim(coalesce(p_referencia,''))
       OR prev.destinatario<>btrim(coalesce(p_destinatario,''))
       OR prev.responsable_id<>btrim(p_responsable_id) THEN
      RAISE EXCEPTION 'IDEMPOTENCIA_CON_DATOS_DISTINTOS';
    END IF;
    RETURN to_jsonb(prev)||jsonb_build_object('repetido',true);
  END IF;
  nuevo := p.saldo + CASE WHEN p_tipo='ENTRADA' THEN p_cantidad ELSE -p_cantidad END;
  IF nuevo < 0 THEN RAISE EXCEPTION 'EXISTENCIA_INSUFICIENTE'; END IF;
  UPDATE public.axia_almacen_lab_productos SET saldo=nuevo, actualizado_en=now() WHERE id=p.id;
  INSERT INTO public.axia_almacen_lab_movimientos
   (idempotencia,producto_id,tipo,cantidad,saldo_anterior,saldo_nuevo,motivo,referencia,destinatario,responsable_id,responsable)
  VALUES(p_idempotencia,p.id,p_tipo,p_cantidad,p.saldo,nuevo,btrim(p_motivo),
      btrim(coalesce(p_referencia,'')),btrim(coalesce(p_destinatario,'')),
      btrim(p_responsable_id),btrim(coalesce(p_responsable,'')))
  RETURNING * INTO registrado;
  RETURN to_jsonb(registrado)||jsonb_build_object('repetido',false);
END;
$$;

REVOKE ALL ON FUNCTION public.axia_almacen_lab_login_permitido(text),
  public.axia_almacen_lab_registrar_login(text,boolean),
  public.axia_almacen_lab_registrar_movimiento(text,text,numeric,text,text,text,text,text,uuid)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.axia_almacen_lab_login_permitido(text),
  public.axia_almacen_lab_registrar_login(text,boolean),
  public.axia_almacen_lab_registrar_movimiento(text,text,numeric,text,text,text,text,text,uuid)
TO service_role;

-- ETAPA MANUAL tras revisar la semilla + Edge Function (NO incluido en esta migracion):
-- UPDATE public.axia_almacen_lab_config SET movimientos_habilitados=true,modificado_en=now() WHERE id=1;
-- Para detener de inmediato: UPDATE public.axia_almacen_lab_config SET movimientos_habilitados=false WHERE id=1;
