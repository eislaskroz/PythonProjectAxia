# Sistema de actualizaciones de AXIA Desktop

A partir de AXIA 2.02.0, una instalación existente puede actualizarse sin desinstalarla.

## Arquitectura

1. AXIA consulta `public.db_actualizaciones` en Supabase al iniciar la aplicación.
2. Si existe una versión activa superior a la instalada, muestra un aviso.
3. El usuario puede actualizar en ese momento o posponerla cuando la versión sea opcional.
4. AXIA descarga el instalador publicado en `act_url` dentro de `%LOCALAPPDATA%\\AXIA\\updates`.
5. Si se publicó `act_sha256`, AXIA verifica la integridad del instalador antes de ejecutarlo.
6. AXIA se cierra y un proceso externo ejecuta el instalador Inno Setup silenciosamente.
7. Como el instalador conserva el mismo `AppId`, actualiza la instalación existente en lugar de crear otra.
8. Al finalizar, AXIA vuelve a abrirse.

## Primera activación

Ejecutar en Supabase una sola vez:

`migrations/20260821_actualizaciones_axia.sql`

Los equipos que todavía tengan una versión anterior a 2.02.0 necesitarán instalar manualmente 2.02.0 una última vez. A partir de ahí recibirán las siguientes versiones mediante el actualizador.

## Publicar una versión

1. Incrementar `APP_VERSION` en `core/version.py` y `MyAppVersion` en `installer/AXIA.iss`.
2. Generar el instalador con `scripts/build_release.ps1`.
3. Subir `AXIA_Setup_X.Y.Z.exe` a una ubicación HTTPS estable.
4. Calcular SHA-256 en PowerShell:

```powershell
(Get-FileHash .\\release\\AXIA_Setup_2.02.1.exe -Algorithm SHA256).Hash.ToLower()
```

5. Insertar la versión en Supabase:

```sql
insert into public.db_actualizaciones
    (act_version, act_url, act_sha256, act_obligatoria, act_notas, act_canal)
values
    ('2.02.1',
     'https://http://www.axiacomunicaciones.com/sftwr//AXIA_Setup_2.02.1.exe',
     '56f4e01eda89f327cedc99b87364194852eb3ec1fcbc6ee45cdbae5c6c854c04',
     true,
     'Primera versión auto actualizable.',
     'stable');
```

`act_obligatoria = true` elimina la opción **Más tarde**. Si el usuario no acepta actualizar, AXIA se cierra para evitar trabajar con una versión incompatible.

## Seguridad

- El cliente de escritorio solo tiene permiso de lectura sobre `db_actualizaciones`.
- Nunca se distribuye una `service_role` key.
- Se recomienda publicar siempre `act_sha256`.
- Las migraciones de Supabase continúan ejecutándose manualmente por administración; los equipos cliente no ejecutan `ALTER TABLE` automáticamente.
