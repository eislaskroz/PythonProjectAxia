create table if not exists public.axia_solicitudes_edicion_lev (
    id uuid primary key default gen_random_uuid(),
    id_levantamiento bigint not null,
    lev_folio text not null,
    solicitante_id bigint not null,
    motivo text not null check (char_length(trim(motivo)) between 12 and 1000),
    estado text not null default 'PENDIENTE' check (estado in ('PENDIENTE','APROBADA','RECHAZADA','UTILIZADA','EXPIRADA','CANCELADA')),
    autorizador_id bigint,
    comentario_resolucion text,
    creado_en timestamptz not null default now(),
    resuelto_en timestamptz,
    expira_en timestamptz,
    utilizado_en timestamptz,
    nuevo_folio text,
    constraint solicitud_lev_tiempo check (expira_en is null or resuelto_en is not null)
);
create index if not exists axia_sol_lev_folio_idx on public.axia_solicitudes_edicion_lev(id_levantamiento, estado);
create index if not exists axia_sol_lev_sol_idx on public.axia_solicitudes_edicion_lev(solicitante_id, creado_en desc);
create unique index if not exists axia_sol_lev_un_pendiente on public.axia_solicitudes_edicion_lev(id_levantamiento, solicitante_id) where estado='PENDIENTE';
create table if not exists public.axia_auditoria_edicion_lev (
    id uuid primary key default gen_random_uuid(),
    solicitud_id uuid not null references public.axia_solicitudes_edicion_lev(id),
    folio_original text not null,
    folio_nuevo text not null,
    solicitante_id bigint not null,
    autorizador_id bigint not null,
    datos_anteriores jsonb not null,
    datos_nuevos jsonb not null,
    creado_en timestamptz not null default now()
);
create unique index if not exists axia_auditoria_lev_solicitud_idx on public.axia_auditoria_edicion_lev(solicitud_id);
alter table public.axia_solicitudes_edicion_lev enable row level security;
alter table public.axia_auditoria_edicion_lev enable row level security;
revoke all on public.axia_solicitudes_edicion_lev from anon, authenticated;
revoke all on public.axia_auditoria_edicion_lev from anon, authenticated;
grant all on public.axia_solicitudes_edicion_lev to service_role;
grant all on public.axia_auditoria_edicion_lev to service_role;
