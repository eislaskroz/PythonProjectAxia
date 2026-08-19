# FIX10 - Cotizaciones de levantamientos

Antes de utilizar el módulo **Cotizaciones**, ejecutar en el SQL Editor de Supabase:

`migrations/20260819_cotizaciones_levantamientos.sql`

La migración agrega a `public.db_levantamientos`:

- `lev_validado_ventas` (`boolean`): marca la preautorización realizada por Operaciones (usu_tipo=5).
- `lev_validado_por` (`text`): usuario que preautorizó.
- `lev_fecha_validacion` (`timestamptz`): fecha/hora de preautorización.
- `lev_cotizacion_json` (`jsonb`): costos totales capturados por Ventas para cada partida.

## Flujo

1. Operaciones (usu_tipo=5) carga y revisa el levantamiento.
2. Pulsa **Validar Levantamiento**.
3. AXIA envía el PDF a `gte.ventas@axiacomunicaciones.mx`.
4. Si el correo fue confirmado, AXIA marca el levantamiento como preautorizado en Supabase.
5. Ventas (usu_tipo=6) abre **Cotizaciones** y solo ve levantamientos preautorizados.
6. Ventas captura el costo total de cada material/equipo/insumo y guarda.

El Administrador (usu_tipo=1) conserva acceso al módulo como superusuario.
