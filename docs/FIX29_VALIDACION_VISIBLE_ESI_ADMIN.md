# FIX29 - Validación visible y ESI para Administrador

- La pantalla de Cotizaciones muestra el motivo exacto por el que Preview/Guardar continúan bloqueados.
- Para Administrador (usu_tipo=1), ESI se selecciona de usuarios tipo 6 (Ventas).
- Al elegir ESI se precargan correo corporativo y teléfono desde db_usuarios.
- Usuario tipo 6 conserva asociación automática consigo mismo.
- No cambia Supabase: usa usu_correo y usu_telefono existentes.
