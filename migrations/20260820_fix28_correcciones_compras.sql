-- AXIA DESKTOP FIX28
-- Correcciones de compatibilidad para Cotizaciones + Compras.
-- Esta migración es idempotente y puede ejecutarse aunque FIX26/FIX27 ya se hayan aplicado.

-- Campos requeridos por el flujo Cotización -> Compras.
alter table public.db_cotizaciones
    add column if not exists cot_finalizado_por text,
    add column if not exists cot_fecha_finalizacion timestamptz;

create index if not exists idx_db_cotizaciones_estatus_finalizacion
    on public.db_cotizaciones (cot_estatus, cot_fecha_finalizacion desc);

comment on column public.db_cotizaciones.cot_estatus is
    'Estado comercial. AXIA usa BORRADOR y EN COMPRA X COTIZACIÓN.';
comment on column public.db_cotizaciones.cot_fecha_finalizacion is
    'Momento en que Ventas finaliza la cotización y la entrega a Compras.';
comment on column public.db_cotizaciones.cot_finalizado_por is
    'Usuario de Ventas/Administrador que finalizó la cotización.';

-- Roles 7 = Compras y 8 = Almacén.
DO $$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
        WHERE nsp.nspname = 'public'
          AND rel.relname = 'db_usuarios'
          AND con.contype = 'c'
          AND pg_get_constraintdef(con.oid) ILIKE '%usu_tipo%'
    LOOP
        EXECUTE format('ALTER TABLE public.db_usuarios DROP CONSTRAINT IF EXISTS %I', r.conname);
    END LOOP;
END $$;

ALTER TABLE public.db_usuarios
    ADD CONSTRAINT db_usuarios_usu_tipo_check
    CHECK (usu_tipo BETWEEN 1 AND 8);

COMMENT ON COLUMN public.db_usuarios.usu_tipo IS
'Rol AXIA: 1 Administrador, 2 Jefe de Operaciones, 3 Supervisor, 4 Operador, 5 Administrativo, 6 Especial/Ventas, 7 Compras, 8 Almacén.';
