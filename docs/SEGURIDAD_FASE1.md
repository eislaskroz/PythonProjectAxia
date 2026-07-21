# Sprint Fase 1 — Seguridad

## Cambios aplicados al código
- `.env` y logs eliminados del paquete PyInstaller.
- Compilación se cancela si `AXIA.spec` vuelve a intentar incluir `.env`.
- Cifrado de datos sensibles en modo fail-closed (`AXIA_REQUIRE_ENCRYPTION=1`).
- Recuperación por nickname + RFC deshabilitada.
- Contraseñas en texto plano heredadas deshabilitadas por defecto.
- Política de contraseña: 10 caracteres, mayúscula, minúscula, número y símbolo.
- Bloqueo local tras intentos fallidos, configurable.
- Geolocalización IP deshabilitada por defecto.
- Rechazo explícito de `SUPABASE_SERVICE_ROLE_KEY` en escritorio.

## RLS: estado real
La aplicación actual usa autenticación propia en `db_usuarios` y una clave `anon`; por ello no existe un `auth.uid()` confiable para políticas RLS. Activar RLS total ahora rompería el programa.

Se entregan dos migraciones:
1. `seguridad_fase1_preparacion.sql`: preparación y retiro de escritura anónima en tablas nuevas. Validar primero en staging.
2. `seguridad_fase1_rls_objetivo.sql`: plantilla de cierre; NO ejecutar hasta migrar usuarios a Supabase Auth.

## Matriz objetivo
| Rol | Usuarios | Clientes/ACO | Levantamientos/órdenes/bitácoras | Reportes |
|---|---|---|---|---|
| Admin | CRUD | CRUD | CRUD | Lectura/exportación |
| Supervisor | Sin administración | Lectura | Crear/leer/actualizar asignados | Lectura |
| Técnico | Perfil propio | Lectura necesaria | Crear/leer/actualizar propios o asignados | Sin globales |
| Capturista | Perfil propio | Crear/actualizar autorizado | Captura autorizada | Sin globales |
| Consulta | Perfil propio | Solo lectura | Solo lectura autorizada | Lectura |

## Antes de producción
- Crear proyecto Supabase de staging.
- Migrar identidades a Supabase Auth y completar `usu_auth_id`.
- Añadir columnas de propiedad `created_by uuid`/`assigned_to uuid` donde corresponda.
- Crear y probar políticas por tabla y rol.
- Rotar claves que hayan estado en `.env` distribuido previamente.
