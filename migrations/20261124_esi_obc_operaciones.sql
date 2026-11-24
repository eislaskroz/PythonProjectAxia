create table if not exists public.axia_solicitudes_edicion_obc (
 id uuid primary key default gen_random_uuid(),
 obc_id text not null,
 obc_folio text not null,
 solicitante_id bigint not null,
 motivo text not null check (char_length(btrim(motivo)) between 12 and 1000),
 estado text not null default 'PENDIENTE' check (estado in ('PENDIENTE','APROBADA','RECHAZADA','UTILIZADA','EXPIRADA','CANCELADA')),
 autorizador_id bigint,
 comentario_resolucion text,
 creado_en timestamptz not null default now(),
 resuelto_en timestamptz,
 expira_en timestamptz,
 utilizado_en timestamptz,
 nuevo_folio text
);
create index if not exists axia_sol_obc_estado on public.axia_solicitudes_edicion_obc(estado, creado_en);
create index if not exists axia_sol_obc_origen on public.axia_solicitudes_edicion_obc(obc_id, solicitante_id);
create table if not exists public.axia_auditoria_edicion_obc (
 id uuid primary key default gen_random_uuid(),
 solicitud_id uuid not null unique references public.axia_solicitudes_edicion_obc(id),
 folio_original text not null unique,
 folio_nuevo text not null unique,
 solicitante_id bigint not null,
 autorizador_id bigint not null,
 datos_anteriores jsonb not null,
 datos_nuevos jsonb not null,
 creado_en timestamptz not null default now()
);
alter table public.axia_solicitudes_edicion_obc enable row level security;
alter table public.axia_auditoria_edicion_obc enable row level security;
revoke all on public.axia_solicitudes_edicion_obc, public.axia_auditoria_edicion_obc from public,anon,authenticated;
grant all on public.axia_solicitudes_edicion_obc, public.axia_auditoria_edicion_obc to service_role;

create or replace function public.axia_esi_obc_operacion_segura(
 p_accion text, p_actor bigint, p_rol integer, p_entrada jsonb default '{}'::jsonb
) returns jsonb language plpgsql security definer set search_path=pg_catalog,public as $$
declare
 v_id text;
 v_obra public.db_obras_civiles%rowtype;
 v_solicitud public.axia_solicitudes_edicion_obc%rowtype;
 v_nueva public.db_obras_civiles%rowtype;
 v_motivo text;
 v_request uuid;
 v_folio text;
 v_doc jsonb;
 v_columnas text;
 v_campos text[];
 v_rol integer;
 v_permitidos text[] := array[
  'obc_fecha','obc_cliente','obc_contacto','obc_sucursal','obc_direccion',
  'obc_responsable_axia','obc_supervisor','obc_dias_trabajo','obc_personas_considerar',
  'obc_tipo_giro','obc_nombre_proyecto','obc_superficie_disponible','obc_superficie_adecuada',
  'obc_planos_arquitectonicos','obc_requiere_maquinaria','obc_permisos',
  'obc_observaciones_iniciales','obc_ejecucion_json','obc_planos_acabados',
  'obc_generacion_planos','obc_etapa_acabados','obc_obra_blanca',
  'obc_observaciones_finales','obc_anotacion_plano_json',
  'obc_evidencias_json','obc_archivos_adjuntos_json'
 ];
begin
 select usu_tipo into v_rol from public.db_usuarios where id_usuario=p_actor;
 if v_rol is null or v_rol <> p_rol then raise exception 'SESION_SIN_PERMISO' using errcode='42501'; end if;
 if p_accion='listar_pendientes_obc' then
  if p_rol not in (1,2,3) then raise exception 'ROL_NO_AUTORIZADO' using errcode='42501'; end if;
  return (select coalesce(jsonb_agg(to_jsonb(x) order by x.creado_en),'[]'::jsonb) from (
   select id,obc_id,obc_folio,solicitante_id,motivo,estado,creado_en
   from public.axia_solicitudes_edicion_obc where estado='PENDIENTE' order by creado_en limit 200
  ) x);
 end if;
 if p_accion='resolver_obc' then
  if p_rol not in (1,2,3) then raise exception 'ROL_NO_AUTORIZADO' using errcode='42501'; end if;
  v_request := (p_entrada->>'solicitud_id')::uuid;
  select * into v_solicitud from public.axia_solicitudes_edicion_obc where id=v_request for update;
  if not found then raise exception 'SOLICITUD_NO_ENCONTRADA'; end if;
  if v_solicitud.estado<>'PENDIENTE' then raise exception 'SOLICITUD_YA_RESUELTA'; end if;
  if v_solicitud.solicitante_id=p_actor then raise exception 'AUTOAUTORIZACION_PROHIBIDA' using errcode='42501'; end if;
  if p_entrada->>'aprobar'='true' then
   select * into v_obra from public.db_obras_civiles where obc_id::text=v_solicitud.obc_id for update;
   perform public.axia_esi_obc_validar_origen(v_solicitud.obc_id);
   update public.axia_solicitudes_edicion_obc set estado='APROBADA',autorizador_id=p_actor,
    comentario_resolucion=left(coalesce(p_entrada->>'comentario',''),1000),resuelto_en=now(),
    expira_en=now()+interval '60 minutes' where id=v_request;
   return jsonb_build_object('estado','APROBADA','expira_en',now()+interval '60 minutes');
  end if;
  if not length(btrim(coalesce(p_entrada->>'comentario',''))) between 5 and 1000 then raise exception 'MOTIVO_RECHAZO_OBLIGATORIO'; end if;
  update public.axia_solicitudes_edicion_obc set estado='RECHAZADA',autorizador_id=p_actor,
   comentario_resolucion=left(p_entrada->>'comentario',1000),resuelto_en=now() where id=v_request;
  return jsonb_build_object('estado','RECHAZADA');
 end if;
 if p_rol<>6 then raise exception 'SOLO_ESI' using errcode='42501'; end if;
 v_id := btrim(coalesce(p_entrada->>'obc_id',''));
 if length(v_id)<1 or length(v_id)>120 then raise exception 'OBC_INVALIDA'; end if;
 if p_accion='solicitar_obc' then
  select * into v_obra from public.db_obras_civiles where obc_id::text=v_id for update;
  perform public.axia_esi_obc_validar_origen(v_id);
  v_motivo := btrim(coalesce(p_entrada->>'motivo',''));
  if length(v_motivo) not between 12 and 1000 then raise exception 'MOTIVO_INVALIDO'; end if;
  if exists(select 1 from public.axia_solicitudes_edicion_obc where obc_id=v_id and solicitante_id=p_actor
    and (estado='PENDIENTE' or (estado='APROBADA' and expira_en>now()))) then
   raise exception 'SOLICITUD_ACTIVA_EXISTENTE';
  end if;
  update public.axia_solicitudes_edicion_obc set estado='EXPIRADA' where obc_id=v_id and solicitante_id=p_actor
    and estado='APROBADA' and expira_en<=now();
  insert into public.axia_solicitudes_edicion_obc(obc_id,obc_folio,solicitante_id,motivo)
   values(v_id,v_obra.obc_folio,p_actor,v_motivo) returning id into v_request;
  return jsonb_build_object('solicitud_id',v_request,'estado','PENDIENTE');
 end if;
 if p_accion='permiso_vigente_obc' then
  perform public.axia_esi_obc_validar_origen(v_id);
  select * into v_solicitud from public.axia_solicitudes_edicion_obc where obc_id=v_id and solicitante_id=p_actor
   and estado='APROBADA' and expira_en>now() order by resuelto_en desc limit 1;
  if not found then raise exception 'SIN_AUTORIZACION_VIGENTE' using errcode='42501'; end if;
  return jsonb_build_object('solicitud_id',v_solicitud.id,'expira_en',v_solicitud.expira_en);
 end if;
 if p_accion='guardar_revision_obc' then
  v_request := (p_entrada->>'solicitud_id')::uuid;
  select * into v_solicitud from public.axia_solicitudes_edicion_obc where id=v_request for update;
  if not found or v_solicitud.solicitante_id<>p_actor or v_solicitud.obc_id<>v_id
   or v_solicitud.estado<>'APROBADA' or v_solicitud.expira_en<=now() then
   raise exception 'SIN_AUTORIZACION_VIGENTE' using errcode='42501';
  end if;
  select * into v_obra from public.db_obras_civiles where obc_id::text=v_id for update;
  perform public.axia_esi_obc_validar_origen(v_id);
  if jsonb_typeof(p_entrada->'datos')<>'object' or p_entrada->'datos'='{}'::jsonb then raise exception 'DATOS_INVALIDOS'; end if;
  if pg_column_size(p_entrada->'datos')>8000000 then raise exception 'DATOS_DEMASIADO_GRANDES'; end if;
  select array_agg(k) into v_campos from jsonb_object_keys(p_entrada->'datos') k where not k=any(v_permitidos);
  if array_length(v_campos,1)>0 then raise exception 'CAMPOS_NO_AUTORIZADOS'; end if;
  v_doc := to_jsonb(v_obra)
   || (select coalesce(jsonb_object_agg(k,v),'{}'::jsonb) from jsonb_each(p_entrada->'datos') x(k,v) where k=any(v_permitidos))
   || jsonb_build_object('obc_request_id',gen_random_uuid(),'obc_estatus',1,'obc_validado_ventas',false,
    'obc_validado_por',null,'obc_fecha_validacion',null,'creado_por',
     (select usu_nickname from public.db_usuarios where id_usuario=p_actor),'fecha_registro',now());
  select string_agg(format('%I',attname),', ' order by attnum) into v_columnas from pg_attribute
   where attrelid='public.db_obras_civiles'::regclass and attnum>0 and not attisdropped
    and attname not in ('obc_id','obc_folio') and attgenerated='';
  execute format('insert into public.db_obras_civiles (%s) select %s from jsonb_populate_record(null::public.db_obras_civiles,$1) returning *',v_columnas,v_columnas)
   into v_nueva using v_doc;
  if v_nueva.obc_id is null or v_nueva.obc_folio is null or v_nueva.obc_folio=v_obra.obc_folio then
   raise exception 'FOLIO_OBC_NO_GENERADO';
  end if;
  insert into public.axia_auditoria_edicion_obc(solicitud_id,folio_original,folio_nuevo,solicitante_id,autorizador_id,datos_anteriores,datos_nuevos)
   values(v_request,v_obra.obc_folio,v_nueva.obc_folio,p_actor,v_solicitud.autorizador_id,to_jsonb(v_obra),to_jsonb(v_nueva));
  update public.axia_solicitudes_edicion_obc set estado='UTILIZADA',utilizado_en=now(),nuevo_folio=v_nueva.obc_folio where id=v_request;
  return to_jsonb(v_nueva);
 end if;
 raise exception 'ACCION_DESCONOCIDA';
end;
$$;

create or replace function public.axia_esi_obc_validar_origen(p_id text)
returns void language plpgsql security definer set search_path=pg_catalog,public as $$
declare v_obra public.db_obras_civiles%rowtype;
begin
 select * into v_obra from public.db_obras_civiles where obc_id::text=p_id;
 if not found then raise exception 'OBC_NO_ENCONTRADA'; end if;
 if coalesce(v_obra.obc_validado_ventas,false) or v_obra.obc_fecha_validacion is not null then
  raise exception 'OBC_YA_VALIDADA';
 end if;
 if exists(select 1 from public.db_cotizaciones where lev_folio=v_obra.obc_folio) then
  raise exception 'OBC_EN_COTIZACION';
 end if;
 if exists(select 1 from public.axia_auditoria_edicion_obc where folio_original=v_obra.obc_folio) then
  raise exception 'OBC_TIENE_VERSION_POSTERIOR';
 end if;
end;
$$;
revoke all on function public.axia_esi_obc_operacion_segura(text,bigint,integer,jsonb) from public,anon,authenticated;
revoke all on function public.axia_esi_obc_validar_origen(text) from public,anon,authenticated;
grant execute on function public.axia_esi_obc_operacion_segura(text,bigint,integer,jsonb) to service_role;
grant execute on function public.axia_esi_obc_validar_origen(text) to service_role;
