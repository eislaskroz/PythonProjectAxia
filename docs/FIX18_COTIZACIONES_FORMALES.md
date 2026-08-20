# FIX18 - Cotizaciones comerciales formales

## Migración obligatoria
Ejecutar `migrations/20260820_cotizaciones_formales.sql` una sola vez en Supabase.

La migración crea:
- `public.db_cotizaciones`.
- secuencia `public.seq_cotizaciones_folio`.
- RPC `public.generar_folio_cotizacion()`.
- folios `COT-XXXXX` centralizados para evitar duplicados concurrentes.

## Flujo
1. Operaciones preautoriza el levantamiento.
2. Ventas abre Cotizaciones y carga el LEV.
3. AXIA precarga cliente, contacto, sucursal y personal/datos operativos existentes.
4. Ventas captura proveedor, SKU, precios, utilidad, observaciones, plan de pagos, vigencia, descuento e IVA.
5. Guardar asigna `COT-XXXXX` la primera vez y persiste en `db_cotizaciones`.
6. PDF Cotización genera el formato corporativo horizontal basado en `COTIZACIÓN.pdf`.

El `lev_cotizacion_json` histórico se conserva sólo como compatibilidad/semilla de datos y ya no es la fuente principal de la cotización formal.
