-- AXIA ALMACÉN: esquema preparado, SIN IMPORTACIÓN y CON MOVIMIENTOS DESHABILITADOS.
-- Ejecutar en Supabase SQL Editor sólo después de respaldar el proyecto.
-- Las escrituras se realizan EXCLUSIVAMENTE desde la Edge Function (service_role).
-- El rol y la identidad son verificados por la Edge Function antes de usar la RPC.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.axia_almacen_productos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  codigo text NOT NULL UNIQUE CHECK (length(trim(codigo)) BETWEEN 1 AND 120),
  nombre text NOT NULL CHECK (length(trim(nombre)) BETWEEN 1 AND 500),
  departamento text NOT NULL DEFAULT 'SIN DEPARTAMENTO',
  unidad text NOT NULL DEFAULT 'Pieza(s)',
  costo numeric(16,2) NOT NULL DEFAULT 0 CHECK (costo >= 0),
  precio_venta numeric(16,2) NOT NULL DEFAULT 0 CHECK (precio_venta >= 0),
  minimo numeric(16,3) NOT NULL DEFAULT 0 CHECK (minimo >= 0),
  maximo numeric(16,3) NOT NULL DEFAULT 0 CHECK (maximo >= 0),
  saldo numeric(16,3) NOT NULL DEFAULT 0 CHECK (saldo >= 0),
  activo boolean NOT NULL DEFAULT true,
  creado_en timestamptz NOT NULL DEFAULT now(),
  actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.axia_almacen_config (
  id smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  catalogo_autorizado boolean NOT NULL DEFAULT false,
  movimientos_habilitados boolean NOT NULL DEFAULT false,
  fecha_corte timestamptz,
  autorizado_por text,
  observaciones text
);
INSERT INTO public.axia_almacen_config (id)
VALUES (1) ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS public.axia_almacen_movimientos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  idempotencia uuid NOT NULL UNIQUE,
  producto_id uuid NOT NULL REFERENCES public.axia_almacen_productos(id),
  tipo text NOT NULL CHECK (tipo IN ('ENTRADA','SALIDA')),
  cantidad numeric(16,3) NOT NULL CHECK (cantidad > 0 AND cantidad <= 1000000),
  saldo_anterior numeric(16,3) NOT NULL CHECK (saldo_anterior >= 0),
  saldo_nuevo numeric(16,3) NOT NULL CHECK (saldo_nuevo >= 0),
  motivo varchar(250) NOT NULL CHECK (length(trim(motivo)) > 0),
  referencia varchar(120) NOT NULL DEFAULT '',
  destinatario varchar(120) NOT NULL DEFAULT '',
  responsable_id text NOT NULL CHECK (length(trim(responsable_id)) > 0),
  responsable text NOT NULL DEFAULT '',
  fecha timestamptz NOT NULL DEFAULT now(),
  CHECK (tipo <> 'SALIDA' OR length(trim(destinatario)) > 0)
);
CREATE INDEX IF NOT EXISTS ix_axia_almacen_movimientos_producto_fecha
  ON public.axia_almacen_movimientos (producto_id, fecha DESC);

CREATE TABLE IF NOT EXISTS public.axia_almacen_login_intentos (
  nickname text PRIMARY KEY,
  errores integer NOT NULL DEFAULT 0,
  bloqueado_hasta timestamptz,
  actualizado timestamptz NOT NULL DEFAULT now()
);

-- RLS cerrada: ni el anon key del escritorio ni las sesiones de Auth
-- pueden leer o modificar inventarios directamente.
ALTER TABLE public.axia_almacen_productos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.axia_almacen_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.axia_almacen_movimientos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.axia_almacen_login_intentos ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.axia_almacen_productos, public.axia_almacen_config,
  public.axia_almacen_movimientos, public.axia_almacen_login_intentos
  FROM PUBLIC, anon, authenticated;
GRANT ALL ON public.axia_almacen_productos, public.axia_almacen_config,
  public.axia_almacen_movimientos, public.axia_almacen_login_intentos TO service_role;

-- Retorna true si el usuario puede intentar autenticarse.
CREATE OR REPLACE FUNCTION public.axia_almacen_intento_login(
  p_nickname text, p_correcto boolean DEFAULT false
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE intento public.axia_almacen_login_intentos%ROWTYPE;
BEGIN
  IF p_nickname IS NULL OR length(trim(p_nickname)) < 1 OR length(p_nickname) > 120 THEN
    RETURN false;
  END IF;
  INSERT INTO public.axia_almacen_login_intentos (nickname)
  VALUES (lower(trim(p_nickname))) ON CONFLICT DO NOTHING;
  SELECT * INTO intento FROM public.axia_almacen_login_intentos
    WHERE nickname = lower(trim(p_nickname)) FOR UPDATE;
  IF intento.bloqueado_hasta IS NOT NULL AND intento.bloqueado_hasta > now() THEN
    RETURN false;
  END IF;
  IF p_correcto THEN
    UPDATE public.axia_almacen_login_intentos
      SET errores = 0, bloqueado_hasta = NULL, actualizado = now()
      WHERE nickname = intento.nickname;
    RETURN true;
  END IF;
  -- p_correcto=false es llamado antes de comprobar la contraseña. Mantiene
  -- la cuota en 5 intentos por 15 minutos, aunque haya fallos concurrentes.
  UPDATE public.axia_almacen_login_intentos
    SET errores = CASE WHEN actualizado < now() - interval '15 minutes' THEN 1 ELSE errores + 1 END,
        bloqueado_hasta = CASE WHEN (CASE WHEN actualizado < now() - interval '15 minutes'
                                          THEN 1 ELSE errores + 1 END) >= 5
                                THEN now() + interval '15 minutes' ELSE NULL END,
        actualizado = now()
    WHERE nickname = intento.nickname;
  RETURN true;
END;
$$;
REVOKE ALL ON FUNCTION public.axia_almacen_intento_login(text,boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.axia_almacen_intento_login(text,boolean) TO service_role;

-- RPC ATÓMICA con bloqueo de producto para evitar carreras de existencias.
-- El caller autorizado está autenticado por la Edge Function, nunca se
-- acepta identidad ni saldo proporcionados por una clave pública cliente.
CREATE OR REPLACE FUNCTION public.axia_almacen_registrar_movimiento(
  p_codigo text, p_tipo text, p_cantidad numeric,
  p_motivo text, p_referencia text, p_destinatario text,
  p_responsable_id text, p_responsable text, p_idempotencia uuid
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  cfg public.axia_almacen_config%ROWTYPE;
  producto public.axia_almacen_productos%ROWTYPE;
  previo public.axia_almacen_movimientos%ROWTYPE;
  saldo_final numeric(16,3);
  movimiento public.axia_almacen_movimientos%ROWTYPE;
BEGIN
  SELECT * INTO cfg FROM public.axia_almacen_config WHERE id = 1;
  IF NOT FOUND OR NOT cfg.catalogo_autorizado OR NOT cfg.movimientos_habilitados THEN
    RAISE EXCEPTION 'ALMACEN_NO_HABILITADO';
  END IF;
  IF p_tipo NOT IN ('ENTRADA','SALIDA') OR p_cantidad IS NULL OR
     p_cantidad <= 0 OR p_cantidad > 1000000 OR p_cantidad <> trunc(p_cantidad,3) OR
     nullif(trim(p_motivo),'') IS NULL OR length(p_motivo) > 250 OR
     length(coalesce(p_referencia,'')) > 120 OR length(coalesce(p_destinatario,'')) > 120 OR
     nullif(trim(p_responsable_id),'') IS NULL OR p_idempotencia IS NULL OR
     (p_tipo = 'SALIDA' AND nullif(trim(p_destinatario),'') IS NULL) THEN
    RAISE EXCEPTION 'MOVIMIENTO_INVALIDO';
  END IF;
  SELECT * INTO producto FROM public.axia_almacen_productos
    WHERE codigo = p_codigo AND activo = true FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'PRODUCTO_NO_ENCONTRADO'; END IF;
  SELECT * INTO previo FROM public.axia_almacen_movimientos WHERE idempotencia = p_idempotencia;
  IF FOUND THEN
    IF previo.producto_id <> producto.id OR previo.tipo <> p_tipo OR previo.cantidad <> p_cantidad OR
       previo.motivo <> trim(p_motivo) OR previo.referencia <> coalesce(trim(p_referencia),'') OR
       previo.destinatario <> coalesce(trim(p_destinatario),'') OR
       previo.responsable_id <> trim(p_responsable_id) THEN
      RAISE EXCEPTION 'IDEMPOTENCIA_CON_DATOS_DISTINTOS';
    END IF;
    RETURN to_jsonb(previo) || jsonb_build_object('repetido',true);
  END IF;
  saldo_final := producto.saldo + CASE WHEN p_tipo='ENTRADA' THEN p_cantidad ELSE -p_cantidad END;
  IF saldo_final < 0 THEN RAISE EXCEPTION 'EXISTENCIA_INSUFICIENTE'; END IF;
  UPDATE public.axia_almacen_productos
    SET saldo = saldo_final, actualizado_en = now() WHERE id = producto.id;
  INSERT INTO public.axia_almacen_movimientos
    (idempotencia, producto_id, tipo, cantidad, saldo_anterior, saldo_nuevo,
     motivo, referencia, destinatario, responsable_id, responsable)
  VALUES (p_idempotencia, producto.id, p_tipo, p_cantidad, producto.saldo, saldo_final,
     trim(p_motivo), coalesce(trim(p_referencia),''), coalesce(trim(p_destinatario),''),
     trim(p_responsable_id), coalesce(trim(p_responsable),''))
  RETURNING * INTO movimiento;
  RETURN to_jsonb(movimiento) || jsonb_build_object('repetido',false);
END;
$$;
REVOKE ALL ON FUNCTION public.axia_almacen_registrar_movimiento(
  text,text,numeric,text,text,text,text,text,uuid
) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.axia_almacen_registrar_movimiento(
  text,text,numeric,text,text,text,text,text,uuid
) TO service_role;

-- IMPORTANTE: no ejecutar migraciones o cambios de configuración de esta
-- tabla desde la aplicación. No habilitar la operación antes de la firma
-- del responsable, verificación de conteo físico e importación de saldos.
