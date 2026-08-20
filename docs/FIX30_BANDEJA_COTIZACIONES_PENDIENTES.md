# FIX30 · Bandeja de cotizaciones pendientes de Compras

La cabecera del módulo Cotizaciones queda dividida en dos bandejas equivalentes:

- **Cotizaciones realizadas · Pendientes de Compras**: muestra únicamente COT-XXXXX con `cot_estatus = BORRADOR`. Permite abrir una cotización guardada para consultar o entrar a Modificar.
- **Levantamientos preautorizados**: conserva los LEV disponibles para iniciar/continuar su cotización.

Al guardar una cotización, la bandeja izquierda se actualiza. Al finalizarla y cambiar a `EN COMPRA X COTIZACIÓN`, desaparece de esa bandeja y queda disponible para el módulo Compras.

No requiere cambios de Supabase.
