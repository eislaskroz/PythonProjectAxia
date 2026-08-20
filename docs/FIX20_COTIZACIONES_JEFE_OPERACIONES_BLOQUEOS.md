# FIX20 - Cotizaciones: layout, Jefe de Operaciones y campos protegidos

- La sección **Datos generales de cotización** se reorganizó a cinco columnas siguiendo la maqueta aprobada.
- **Jefe de Operaciones** ahora es un selector alimentado exclusivamente por usuarios con `usu_tipo = 2`.
- En las partidas comerciales quedan bloqueados para edición los campos que provienen del levantamiento: **Unidad / Tipo**, **Cantidad** y **Concepto**.
- Los valores bloqueados siguen formando parte del payload de la cotización y del PDF; sólo se evita su modificación accidental desde Ventas.
- No requiere cambios de esquema ni migraciones nuevas en Supabase.
