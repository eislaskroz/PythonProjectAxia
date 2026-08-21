# FIX7 - Datos generales de levantamientos (21/08/2026)

Cambios aplicados a los formularios centralizados de levantamiento:

- Dirección operativa completa de sucursal concatenada y visible.
- Opción `Otros` al final del catálogo de clientes. Permite captura libre sin crear registros en `db_clientes`, `db_sucursales` ni contactos.
- Se retiran de la captura inicial Supervisor, Encargado de Proyecto y Técnico.
- Fecha de Levantamiento automática y bloqueada.
- Recursos proyectados dinámicos: `Un día` => horas + personas; `Varios días` => días + personas.
- Campo general `Notas`.
- PDF maestro actualizado para los nuevos datos generales.

## Supabase

Antes de usar esta versión ejecutar una sola vez:

`migrations/20260821_datos_generales_levantamientos.sql`

La migración es idempotente y agrega:

- `lev_direccion_sucursal`
- `lev_duracion_proyecto`
- `lev_horas_estimadas`
- `lev_notas`
