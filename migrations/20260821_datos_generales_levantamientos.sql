-- AXIA 21/08/2026 - Datos generales de levantamientos
-- Ejecutar una sola vez en Supabase SQL Editor. Es idempotente.

alter table public.db_levantamientos
    add column if not exists lev_direccion_sucursal text,
    add column if not exists lev_duracion_proyecto text,
    add column if not exists lev_horas_estimadas numeric,
    add column if not exists lev_notas text;

comment on column public.db_levantamientos.lev_direccion_sucursal is 'Domicilio operativo concatenado de la sucursal seleccionada';
comment on column public.db_levantamientos.lev_duracion_proyecto is 'Un día o Varios días';
comment on column public.db_levantamientos.lev_horas_estimadas is 'Horas estimadas cuando el proyecto es de un día';
comment on column public.db_levantamientos.lev_notas is 'Notas generales capturadas durante el levantamiento';
