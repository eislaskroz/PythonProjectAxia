# AXIA DESKTOP - Correo automático de levantamientos

Al guardar **o actualizar** cualquier formato de levantamiento, AXIA genera el PDF definitivo y después intenta enviarlo por correo.

## Destinatarios configurados

- Remitente: `levantamientos@axiacomunicaciones.mx`
- Para: `mmachuca@axiacomunicaciones.mx`
- CC: `desarrollo.01@axiacomunicaciones.mx`

## Datos que faltan del hosting

Por seguridad, la contraseña nunca va dentro del código ni de `.env.example`.
Copia las variables de correo de `.env.example` a tu archivo `.env` real y completa:

- `AXIA_SMTP_HOST`: servidor SMTP indicado por el hosting.
- `AXIA_SMTP_PORT`: normalmente 465 (SSL) o 587 (STARTTLS), según tu hosting.
- `AXIA_SMTP_PASSWORD`: contraseña real de `levantamientos@axiacomunicaciones.mx`.
- Seguridad:
  - Para SSL directo (normalmente puerto 465): `AXIA_SMTP_SSL=1` y `AXIA_SMTP_STARTTLS=0`.
  - Para STARTTLS (normalmente puerto 587): `AXIA_SMTP_SSL=0` y `AXIA_SMTP_STARTTLS=1`.

## Comportamiento ante una falla de correo

El levantamiento y su PDF **sí quedan guardados** aunque falle Internet, autenticación o SMTP. AXIA muestra el estado del envío al usuario y registra el detalle técnico en el log.
