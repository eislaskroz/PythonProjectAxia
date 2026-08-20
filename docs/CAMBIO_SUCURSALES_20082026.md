# Cambio de sucursales operativas - 20/08/2026

## Nuevo modelo de dirección

La aplicación usa ahora los siguientes campos para `db_clientes_sucursales`:

- `suc_nombre`
- `suc_calle_numero`
- `suc_colonia`
- `suc_municipio`
- `suc_estado`
- `suc_codigo_postal`
- `suc_telefono`

El campo histórico `suc_domicilio` se conserva por compatibilidad y se sincroniza con la dirección completa.

## Migración requerida

Ejecutar en Supabase SQL Editor:

`migrations/20260820_sucursales_direccion_rancherita.sql`

La migración es idempotente: agrega las columnas faltantes, conserva direcciones históricas y crea/actualiza las 11 sucursales de Distribuidora de Lácteos La Rancherita SA de CV (`id_cliente = 7`).
