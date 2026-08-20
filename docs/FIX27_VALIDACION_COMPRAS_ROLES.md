# FIX27 — Validación de cotización + Compras + roles 7/8

## Cotizaciones
- PDF Preview y Guardar permanecen deshabilitados mientras la captura esté incompleta.
- Se validan datos generales, condiciones comerciales y partidas.
- Por partida se exige Unidad/Tipo, Cantidad, Proveedor, Modelo, SKU, Marca, Concepto, P. Lista y Utilidad %.
- Cuando un dato no aplica, Ventas puede registrar `N/A` en los campos de texto.
- La validación también se repite en `cotizaciones_service.py` antes de persistir en Supabase.

## Nuevos roles
- 7 = Compras.
- 8 = Almacén.
- Los roles 7 y 8 no heredan automáticamente permisos operativos de los roles 1-6.
- Administrador conserva acceso al módulo de Compras.

## Compras
- Nuevo módulo lateral `Compras` para Administrador y rol 7.
- Muestra las cotizaciones cuyo estado es `EN COMPRA X COTIZACIÓN`.
- No genera Orden de Trabajo.
- Esta primera versión es una bandeja de pendientes; el proceso de compra se incorporará después.

## Supabase
Ejecutar una vez `migrations/20260820_fix27_roles_compras_almacen.sql` para garantizar que `db_usuarios.usu_tipo` acepte 1..8.
