# AXIA FIELD + DESKTOP · Salidas firmadas con NOTAS (desarrollo)

## Alcance incluido

- Salida simple y salida vinculada a OT: **cantidad realmente entregada**, nombre de quien recibe (3–120 caracteres), firma manuscrita obligatoria y **NOTAS** (hasta 1000 caracteres).
- Ejemplo: OT solicita 100 m, se entregan 40 m, notas «Quedan pendientes 60 m». El movimiento disminuye **40**, no 100.
- Inventario y evidencia de recepción se guardan en una sola transacción SQL; si la firma no se puede guardar, no se confirma la salida.
- Comprobante PDF móvil listo para compartir por el selector de Android (correo, WhatsApp, etc.); reimpresión de PDF con firma y notas desde Kárdex de FIELD y DESKTOP, utilizando `comprobante_kardex`.
- Entradas mantienen su registro inmediato y posterior reimpresión de etiquetas por el personal de Almacén.
- El identificador de idempotencia permite reintentos sin duplicar el descuento. Si se pierde la conexión después de confirmar, consultar Kárdex antes de cambiar datos/reintentar.

## Instalación correcta (sin Terminal)

**No ejecutar directamente en producción**: hacer copia de seguridad de la base de datos y Edge Function y probar en un proyecto de staging.

1. **SQL Editor (Supabase):** abrir `supabase/migrations/20261124_axia_almacen_entregas_firmadas.sql`; ejecutar una vez. Crea `axia_almacen_recepciones_firmadas` y dos RPC nuevas. NO ejecutar de nuevo las migraciones históricas.
2. **Edge Functions → axia-almacen → Code:** respaldar `index.ts`, sustituir por `supabase/functions/axia-almacen/index.ts` de esta versión y pulsar **Deploy updates**. Mantener JWT y secretos existentes; no compartas su valor. La migración SQL debe aplicarse **antes** de desplegar esta función, porque Kárdex la consulta.
3. Abrir `AXIA FIELD` en Android Studio, sincronizar Gradle, compilar e instalar la nueva versión en un teléfono de prueba.
4. Sustituir `AXIA DESKTOP` con la versión entregada, también primero en un equipo de prueba. El generador de PDF usa la recepción firmada devuelta por Supabase.
5. Hacer pruebas con inventario de **prueba**, nunca con movimientos reales hasta validar:
   - OT con solicitud 100 m y entrega real 40 m, nota pendiente 60 m.
   - Firmar, confirmar, verificar descuento 40 en DESKTOP, comprobar nombre, notas y firma en PDF local, en Kárdex móvil y en reimpresión de DESKTOP.
   - Salida sin OT y entrada de material, comprobar sus respectivos comprobantes.
   - Reintento con el mismo UUID: no debe descontar dos veces.
   - Firma ausente: bloquear la operación sin descontar.
   - Error de Supabase: no generar confirmación falsa ni duplicados.
   - Usuarios tipo 8 y administrador tipo 1; rechazar otros roles.
   - Comprobar que AXIA DESKTOP conserva sus operaciones existentes de Almacén.

## Persistencia / alcance de seguridad

La tabla conserva la firma como PNG base64, junto con receptor, notas, responsable, idempotencia y fecha. La tabla no permite lecturas directas con `anon`/`authenticated`; sólo la función protegida con autorización devuelve la firma. Los datos firmados son inmutables desde estas rutas (no se incorporan rutas de edición/borrado). **No existe aún flujo de corrección auditada**.

El PDF se reconstruye desde los datos almacenados, no se almacena una copia PDF canónica en Storage. No se implementó un envío automático de correo; se utiliza el selector de compartir de Android. El formulario NO verifica automáticamente la cantidad solicitada en las partidas de la OT; la cantidad realmente entregada se captura y la diferencia se documenta en NOTAS.

## Validación efectuada / pendiente

- Generación Python de un PDF firmado de ejemplo con notas: **correcta**; inspección visual de la muestra: **correcta**.
- No hay Gradle disponible para ejecutar la compilación completa de Android en este entorno; **pendiente compilar FIELD**.
- No se ejecutó SQL ni se desplegó Edge Function contra Supabase; **pendientes pruebas de integración y permisos**.
- No se instaló APK ni se probó firma real táctil, WhatsApp, impresora ni sincronización en dispositivo.
