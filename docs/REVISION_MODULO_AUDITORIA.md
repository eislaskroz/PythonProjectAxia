# Sprint de revisión del módulo de auditoría

## Resultado

AXIA ya contaba con dos mecanismos complementarios:

1. `db_login`: registra intentos correctos y fallidos, usuario, fecha/hora, IP local, nombre del equipo y geolocalización opcional.
2. `db_bitacora_mov`: registra operaciones funcionales por usuario, módulo, acción, descripción, registro afectado, IP local y equipo.

La vista administrativa anterior solo consultaba `db_bitacora_mov`, por lo que la información de `db_login` existía pero no estaba integrada en la pantalla Auditoría.

## Mejoras aplicadas

- Vista Auditoría unificada con selector entre movimientos e inicios de sesión.
- Visualización de accesos fallidos y correctos.
- Filtros independientes por fecha, usuario, estado/módulo, equipo e IP.
- Detalle y exportación de registros.
- Métricas dinámicas para cada fuente.
- Consultas con columnas específicas en lugar de `select('*')`.
- Eliminación de un movimiento duplicado `LOGIN_VALIDADO` que se registraba antes de establecer el usuario activo y podía quedar como `DESCONOCIDO`.
- Migración opcional de índices para acelerar búsquedas históricas.

## Qué significa “dónde se conecta”

Sin geolocalización externa, AXIA conserva:

- Nombre del equipo.
- Dirección IP local.
- Fecha y hora.
- Usuario y resultado.

La ciudad, región, país, latitud y longitud solo se completan cuando se configura:

```env
AXIA_ENABLE_IP_GEOLOCATION=1
```

La geolocalización por IP es aproximada y depende de un tercero; no representa GPS ni una ubicación física exacta.

## Riesgos pendientes

- Mientras RLS no esté activo, la inmutabilidad de las bitácoras depende de los permisos actuales de Supabase.
- La aplicación de escritorio no puede garantizar por sí sola que un administrador no modifique registros directamente en la base.
- Para una auditoría con valor probatorio se recomienda, después de Supabase Auth, impedir UPDATE y DELETE sobre ambas tablas mediante políticas RLS y funciones controladas.
- La búsqueda actual trabaja sobre una ventana de 500 registros recientes. Para historiales muy grandes convendrá implementar filtros del lado servidor y paginación.
