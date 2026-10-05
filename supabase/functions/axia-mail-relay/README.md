# AXIA Mail Relay

Esta Edge Function centraliza el correo de AXIA DESKTOP. **Las PCs no deben tener credenciales SMTP.**

## 1. Configurar secretos en Supabase (una sola vez)

Desde una terminal autenticada con Supabase CLI y vinculada al proyecto:

```bash
supabase secrets set \
  AXIA_SMTP_HOST="smtp.gmail.com" \
  AXIA_SMTP_PORT="587" \
  AXIA_SMTP_USER="CUENTA@DOMINIO" \
  AXIA_SMTP_PASSWORD="PASSWORD_DE_APLICACION" \
  AXIA_SMTP_SSL="0" \
  AXIA_MAIL_FROM="CUENTA@DOMINIO" \
  AXIA_MAIL_FROM_NAME="AXIA Comunicaciones" \
  AXIA_MAIL_ALLOWED_RECIPIENTS="coord.operaciones@axiacomunicaciones.mx" \
  AXIA_MAIL_BCC="CORREO_AUDITORIA@DOMINIO"
```

`SUPABASE_URL`, `SUPABASE_ANON_KEY` y `SUPABASE_SERVICE_ROLE_KEY` son secretos provistos por Supabase y no deben copiarse a este comando.

Para cambiar en el futuro la cuenta remitente sólo se actualizan `AXIA_SMTP_USER`, `AXIA_SMTP_PASSWORD` y `AXIA_MAIL_FROM` en Supabase. No se modifica ninguna PC.

## 2. Desplegar

```bash
supabase functions deploy axia-mail-relay --no-verify-jwt
```

La función hace su propia validación de la `apikey` pública del proyecto y, principalmente, evita convertirse en open relay mediante `AXIA_MAIL_ALLOWED_RECIPIENTS`. El remitente y BCC jamás son aceptados desde el cliente.

## 3. Cliente DESKTOP

DESKTOP sólo conserva `SUPABASE_URL`, `SUPABASE_KEY`, `AXIA_MAIL_ENABLED` y opcionalmente `AXIA_MAIL_RELAY_TIMEOUT`. No contiene contraseña SMTP ni cuenta remitente.

## Cambio de cuenta

```bash
supabase secrets set \
  AXIA_SMTP_USER="NUEVA_CUENTA@DOMINIO" \
  AXIA_SMTP_PASSWORD="NUEVO_PASSWORD_DE_APLICACION" \
  AXIA_MAIL_FROM="NUEVA_CUENTA@DOMINIO"
```

No es necesario recompilar ni reinstalar AXIA DESKTOP.
