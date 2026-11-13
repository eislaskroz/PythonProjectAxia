-- ETAPA 1: almacenamiento de borradores; ejecutar solo tras respaldar y revisar.
-- La API accede exclusivamente mediante service_role; ninguna escritura anónima.
create table if not exists public.axia_borradores_compartidos (
  id uuid primary key default gen_random_uuid(),
  usuario_id bigint not null,
  modulo text not null check (modulo in ('LEVANTAMIENTO','BITACORA','ORDEN_SERVICIO','REPORTE_FOTOGRAFICO')),
  clave_cliente uuid not null,
  origen text not null check (origen in ('DESKTOP','FIELD')),
  esquema integer not null default 1 check (esquema = 1),
  datos jsonb not null default '{}'::jsonb,
  revision bigint not null default 1 check (revision >= 1),
  creado_en timestamptz not null default now(),
  actualizado_en timestamptz not null default now(),
  eliminado_en timestamptz,
  unique (usuario_id, modulo, clave_cliente)
);
create index if not exists axia_borradores_usuario_activos_idx
  on public.axia_borradores_compartidos(usuario_id, modulo, actualizado_en desc)
  where eliminado_en is null;
alter table public.axia_borradores_compartidos enable row level security;
revoke all on public.axia_borradores_compartidos from public, anon, authenticated;
-- La Edge Function usa SUPABASE_SERVICE_ROLE_KEY solo del lado del servidor.
-- Los borrados son lógicos: permite resolver conflictos y realizar auditorías.
