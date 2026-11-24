# Autorización de edición ESI — estado de implementación

## Incluido en AXIA DESKTOP

- Consulta general de levantamientos para ESI tipo 6, con PDF disponible en la pantalla existente.
- Solicitud de edición con motivo obligatorio, verificación de permiso vigente y bandeja de revisión para tipos 1, 2 y 3.
- El formulario original de Levantamientos se reutiliza cuando el servidor confirma un permiso; el guardado de una edición ESI se dirige a una operación protegida, **no** a la inserción directa.
- El rol ESI no recibe permisos generales de edición ni capacidad para aprobar solicitudes.

## Requisito imprescindible antes de utilizar en producción

**No se incluye una implementación operativa de la Edge Function `axia-edicion-levantamientos`.** El ZIP original tiene `supabase/functions/axia-almacen/index.ts` vacío; el servicio de identidad que emite las sesiones `login_levantamientos` no está incluido. No es posible verificar con seguridad una sesión AXIA en una nueva Edge Function sin el contrato o código del verificador existente. En consecuencia, las operaciones remotas permanecen bloqueadas por diseño hasta que se despliegue una función compatible y segura.

**No se ha aplicado la migración SQL a Supabase.** Se incluye `20261124_solicitudes_edicion_esi.sql` como punto de partida, no como confirmación de despliegue. Requiere validar los tipos de datos reales de `db_levantamientos.id_levantamiento` y `db_usuarios.id_usuario` antes de ejecutarla.

## Contrato necesario de la Edge Function

Endpoint `POST /functions/v1/axia-edicion-levantamientos`. Cabeceras: `apikey` pública, `Authorization` con clave pública para la puerta de enlace (con `verify_jwt=false` únicamente si la función hace validación estricta), `X-Axia-Almacen-Session` con sesión de catálogo obtenida tras login AXIA. El backend debe verificar criptográficamente esa sesión y derivar del servidor el ID y rol; nunca debe aceptar usuario o tipo enviados por la aplicación.

Acciones JSON:

- `solicitar`: `id_levantamiento`, `motivo`; solo tipo 6, verifica que no esté preautorizado ni tenga cotización iniciada, convertido a OT, ni versión sucesora vigente. Crea solicitud PENDIENTE.
- `listar_pendientes`: solo tipos 1, 2 y 3; consulta de solicitudes y motivos.
- `resolver`: `solicitud_id`, `aprobar`, `comentario`; solo tipos 1, 2 y 3, impide autoaprobación; al aprobar fija `expira_en=now()+interval '60 minutes'`, una sola decisión con bloqueo transaccional.
- `permiso_vigente`: `id_levantamiento`; tipo 6, verifica propietario de solicitud, APROBADA, sin caducar, sin documentos derivados; retorna `resultado: {"solicitud_id":"..."}`.
- `guardar_revision`: `id_levantamiento`, `solicitud_id`, `datos`; tipo 6, transacción atómica: bloquea solicitud y levantamiento, revalida flujo y vigencia, filtra datos al esquema autorizado, asigna nuevo folio con el generador oficial, inserta nueva fila sin sobreescribir original, registra auditoría y relación de versiones, consume solicitud y devuelve registro nuevo. Debe protegerse contra reintentos y colisiones de folio.

Formato de éxito `{"ok":true,"resultado":...}`. Fallo: HTTP 4xx/5xx `{"ok":false,"error":"..."}`.

## Faltantes de producción

- Implementar y desplegar la Edge Function con validador de sesión AXIA real y transacciones SQL, garantizando que los cambios no puedan hacerse por la API REST pública directa. Sin revisar las políticas de escritura existentes de `db_levantamientos`, este candado NO puede considerarse una frontera de seguridad completa.
- Confirmar cómo se representan la preautorización, la apertura de cotización y la cadena de revisiones, así como los vínculos con evidencias/Storage y PDFs.
- Añadir relación formal `folio_origen` / `folio_vigente` o tabla de versiones, y asegurar que la bandeja de Cotizaciones solo use la revisión vigente.
- Validar manualmente en Windows y probar sesiones/roles contra el backend real. No se han efectuado escrituras en Supabase.
