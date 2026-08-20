# FIX19 — Correo electrónico de empresa en usuarios

- Se expone en Administración de Usuarios el campo existente `db_usuarios.usu_correo`.
- No se crea una columna duplicada en Supabase: `usu_correo` ya existía y ya era consumida por Cotizaciones para el ESI.
- El formulario permite alta y edición del correo empresarial.
- La búsqueda administrativa también considera el correo.
- El correo se normaliza a minúsculas y, si se captura, se valida con una comprobación básica de formato.
- En Mi Usuario la etiqueta se homologa a “Correo electrónico de empresa”.
- No requiere migración de Supabase.
