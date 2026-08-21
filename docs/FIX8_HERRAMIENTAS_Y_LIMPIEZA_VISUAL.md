# FIX8 – Herramientas y limpieza visual de levantamientos

Cambios aplicados el 21/08/2026:

- Se retiraron por completo los wallpapers temáticos de los formularios de levantamiento.
- El campo **Notas** quedó compacto y alineado a la derecha de **Fecha de Levantamiento**.
- Se añadió una sección común **Herramientas** antes de la descripción/observaciones finales.
- La sección permite agregar varias herramientas con categoría, herramienta, cantidad y observaciones.
- El catálogo cubre las especialidades de AXIA: General, Electricidad, Seguridad y Monitoreo, Control de Accesos, Redes de Voz y Datos, Enlaces Inalámbricos, Paneles Solares, Plantas de Energía, Aires Acondicionados, Obra Civil y Tecnología/Equipos/Periféricos.
- Las herramientas se guardan dentro de `lev_detalle_tecnico_json` bajo la clave `herramientas`, por lo que **no requiere migración de Supabase**.
- Al editar un levantamiento existente, la lista de herramientas se restaura automáticamente.
