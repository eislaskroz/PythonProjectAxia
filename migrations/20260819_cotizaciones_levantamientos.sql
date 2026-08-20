-- AXIA DESKTOP FIX10
-- Persistencia del flujo Preautorización Operaciones -> Cotización Ventas.
-- Ejecutar en Supabase SQL Editor ANTES de utilizar el módulo Cotizaciones.

alter table public.db_levantamientos
    add column if not exists lev_validado_ventas boolean not null default false,
    add column if not exists lev_validado_por text,
    add column if not exists lev_fecha_validacion timestamptz,
    add column if not exists lev_cotizacion_json jsonb not null default '{}'::jsonb;

comment on column public.db_levantamientos.lev_validado_ventas is
    'Indica que el levantamiento fue preautorizado por Operaciones (usu_tipo=5) y enviado a Ventas.';
comment on column public.db_levantamientos.lev_validado_por is
    'Usuario que realizó la preautorización del levantamiento.';
comment on column public.db_levantamientos.lev_fecha_validacion is
    'Fecha/hora de la preautorización y envío a Ventas.';
comment on column public.db_levantamientos.lev_cotizacion_json is
    'Costos capturados por Ventas por cada material, insumo o equipo del levantamiento.';

create index if not exists idx_db_levantamientos_validado_ventas
    on public.db_levantamientos (lev_validado_ventas, fecha_registro desc);
