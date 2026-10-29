-- AXIA Almacén - Catálogo administrable, sin eliminación física.
-- RESPALDAR antes de ejecutar. Compatible con las tablas de Etapas 2 y 3.
-- NO habilita inventario real, no modifica saldos ni ELEVENTA.
BEGIN;

ALTER TABLE public.axia_almacen_lab_productos
  ADD COLUMN IF NOT EXISTS activo boolean NOT NULL DEFAULT true;
-- Producción de Etapa 2 ya tiene activo; cubrir instalaciones previas.
ALTER TABLE public.axia_almacen_productos
  ADD COLUMN IF NOT EXISTS activo boolean NOT NULL DEFAULT true;

-- El borrado lógico se serializa con los movimientos por producto mediante FOR UPDATE.
CREATE OR REPLACE FUNCTION public.axia_almacen_lab_desactivar_producto(p_codigo text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE p public.axia_almacen_lab_productos%ROWTYPE;
BEGIN
  SELECT * INTO p FROM public.axia_almacen_lab_productos
    WHERE codigo=btrim(p_codigo) AND activo=true FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'PRODUCTO_NO_ENCONTRADO'; END IF;
  IF p.saldo <> 0 THEN RAISE EXCEPTION 'SALDO_NO_CERO'; END IF;
  UPDATE public.axia_almacen_lab_productos SET activo=false, actualizado_en=now()
    WHERE id=p.id;
  RETURN true;
END;
$$;
CREATE OR REPLACE FUNCTION public.axia_almacen_desactivar_producto(p_codigo text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE p public.axia_almacen_productos%ROWTYPE;
BEGIN
  SELECT * INTO p FROM public.axia_almacen_productos
    WHERE codigo=btrim(p_codigo) AND activo=true FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'PRODUCTO_NO_ENCONTRADO'; END IF;
  IF p.saldo <> 0 THEN RAISE EXCEPTION 'SALDO_NO_CERO'; END IF;
  UPDATE public.axia_almacen_productos SET activo=false, actualizado_en=now()
    WHERE id=p.id;
  RETURN true;
END;
$$;
REVOKE ALL ON FUNCTION public.axia_almacen_lab_desactivar_producto(text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.axia_almacen_desactivar_producto(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.axia_almacen_lab_desactivar_producto(text),
  public.axia_almacen_desactivar_producto(text) TO service_role;

-- Blindaje servidor: ni siquiera una RPC antigua puede mover existencias de
-- un producto inactivo; se revierte toda la transacción si se intenta.
CREATE OR REPLACE FUNCTION public.axia_almacen_validar_movimiento_activo()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE disponible boolean;
BEGIN
  IF TG_TABLE_NAME='axia_almacen_lab_movimientos' THEN
    SELECT activo INTO disponible FROM public.axia_almacen_lab_productos WHERE id=NEW.producto_id;
  ELSE
    SELECT activo INTO disponible FROM public.axia_almacen_productos WHERE id=NEW.producto_id;
  END IF;
  IF disponible IS DISTINCT FROM true THEN
    RAISE EXCEPTION 'PRODUCTO_INACTIVO';
  END IF;
  RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS tr_axia_almacen_lab_producto_activo ON public.axia_almacen_lab_movimientos;
CREATE TRIGGER tr_axia_almacen_lab_producto_activo
  BEFORE INSERT ON public.axia_almacen_lab_movimientos FOR EACH ROW
  EXECUTE FUNCTION public.axia_almacen_validar_movimiento_activo();
DROP TRIGGER IF EXISTS tr_axia_almacen_producto_activo ON public.axia_almacen_movimientos;
CREATE TRIGGER tr_axia_almacen_producto_activo
  BEFORE INSERT ON public.axia_almacen_movimientos FOR EACH ROW
  EXECUTE FUNCTION public.axia_almacen_validar_movimiento_activo();
REVOKE ALL ON FUNCTION public.axia_almacen_validar_movimiento_activo() FROM PUBLIC, anon, authenticated;

COMMIT;
-- A continuación, publicar la versión actualizada de la Edge Function axia-almacen.
-- Para PRODUCCIÓN, catalogo_autorizado debe habilitarse únicamente tras autorización formal.
-- No cambiar movimientos_habilitados ni importar existencias con este script.
