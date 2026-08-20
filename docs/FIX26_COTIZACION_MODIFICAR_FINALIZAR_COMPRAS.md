# FIX26 — Modificar / Finalizar Cotización → Compras

## Flujo

- Una cotización nueva se captura y se guarda con estado `BORRADOR`.
- Al guardar, queda en modo consulta para evitar cambios accidentales.
- **Modificar cotización** vuelve a cargar desde Supabase la última versión y habilita exactamente los campos comerciales editables de generación.
- **Finalizar cotización** exige que no existan cambios pendientes, solicita confirmación y cambia el estado a `EN COMPRA X COTIZACIÓN`.
- Finalizar **no crea ni convierte una Orden de Trabajo**.
- Una cotización finalizada queda bloqueada en Ventas; su PDF continúa disponible.
- `obtener_cotizaciones_en_compra()` deja preparado el contrato de lectura para el futuro módulo de Compras.

## Supabase

Ejecutar una sola vez:

`migrations/20260820_fix26_cotizacion_en_compra.sql`

La migración conserva la tabla existente y agrega auditoría del handoff:

- `cot_finalizado_por`
- `cot_fecha_finalizacion`
- índice por `cot_estatus` + fecha de finalización

No se modifica ni se elimina ninguna migración histórica.
