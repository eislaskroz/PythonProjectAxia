-- AXIA DESKTOP FIX26
-- Flujo Cotización -> Compras. Ejecutar UNA SOLA VEZ.
-- No genera órdenes de trabajo.

alter table public.db_cotizaciones
    add column if not exists cot_finalizado_por text,
    add column if not exists cot_fecha_finalizacion timestamptz;

create index if not exists idx_db_cotizaciones_estatus_finalizacion
    on public.db_cotizaciones (cot_estatus, cot_fecha_finalizacion desc);

comment on column public.db_cotizaciones.cot_estatus is
    'Estado comercial. FIX26 usa BORRADOR y EN COMPRA X COTIZACIÓN.';
comment on column public.db_cotizaciones.cot_fecha_finalizacion is
    'Momento en que Ventas finaliza la cotización y la entrega a Compras.';
comment on column public.db_cotizaciones.cot_finalizado_por is
    'Usuario de Ventas/Administrador que finalizó la cotización.';
