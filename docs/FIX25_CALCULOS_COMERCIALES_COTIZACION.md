# FIX25 - Cálculos comerciales automáticos de cotización

En cada partida de Cotizaciones, Ventas captura manualmente únicamente **P. Lista** y **Utilidad %** para la parte económica.

Campos calculados y bloqueados:

- `Costo = P. Lista × (Utilidad / 100)`
- `P. Venta = P. Lista + Costo`
- `P. Unitario = P. Venta`
- `Importe = P. Unitario × Cantidad`

También permanecen bloqueados Unidad / Tipo, Cantidad y Concepto porque provienen del levantamiento.

Los cálculos se realizan en tiempo real en la interfaz y se vuelven a calcular en `cotizaciones_service.py` al guardar, evitando confiar en valores derivados enviados desde la UI. No requiere migración de Supabase.
