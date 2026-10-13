# AXIA DESKTOP — Almacén / Etapa 2
**Versión de desarrollo: 13/10/2026**

## Qué se entrega

- Pantalla con pestañas **Catálogo**, **Entrada**, **Salida** y **Kardex**.
- Selección de producto y captura de código (compatible con lectores USB que escriben como teclado).
- Validación de cantidad mayor a cero, máximo tres decimales, motivo obligatorio y destinatario obligatorio en salidas.
- Confirmación previa y registro de usuario, referencia, saldo anterior y posterior.
- Bloqueo de salidas con saldo insuficiente.
- En el cliente: protección de reintentos con UUID de operación para no duplicar movimientos si falla la conexión.
- En el servidor: SQL preparado con bloqueo transaccional de producto, transacción atómica, registro de Kardex, permisos restringidos y bloqueo de operación hasta aprobación.

## ¿Cómo probar HOY sin afectar la base de datos?

1. Conserva una copia de tu versión estable de AXIA DESKTOP.
2. Descomprime el ZIP de esta etapa en una carpeta nueva. **No sustituyas tu versión de producción sin probarla.**
3. Ejecuta normalmente AXIA DESKTOP con un usuario **Administrador (tipo 1)** o **Almacén (tipo 8)**.
4. Abre `📦 Almacén` y observa el mensaje amarillo **PRUEBAS EN MEMORIA**.
5. En **Catálogo**, busca un código y selecciona su fila. Sus existencias ELEVENTA son sólo una referencia histórica.
6. En **Entrada**, escribe una cantidad (p. ej., 5), referencia y motivo. Confirma. Verás el saldo simulado 5.
7. En **Salida**, indica una cantidad inferior (p. ej., 2), motivo y **quién recibe**. Confirma. El saldo simulado quedará 3.
8. En **Kardex**, consulta el código seleccionado y verifica responsable, saldos, referencias y fecha.
9. Prueba una salida mayor al saldo: **debe rechazarla**.
10. Cierra el módulo y ábrelo otra vez: las entradas y salidas de prueba **desaparecen**. Eso es intencional. Ninguna existencia real se modificó.

> **Aviso importante:** el simulador inicia todos los saldos en cero, aunque el Excel muestre existencias históricas. No hay persistencia local ni sincronización por defecto.

## Qué NO se ha hecho

- **NO** se ejecutó ninguna migración SQL en Supabase.
- **NO** se desplegó la Edge Function.
- **NO** se importó el catálogo aprobado ni las cantidades reales de ELEVENTA.
- **NO** se habilitaron entradas/salidas en el inventario real.
- **NO** se alteraron órdenes de trabajo ni otros módulos.
- **NO** se asegura todavía el funcionamiento visual real en Windows: la validación disponible es sintáctica y de lógica con pruebas automáticas.

## Preparación de Supabase (para el área técnica, NO ejecutar aún en producción)

Archivo: `supabase/migrations/20261013_axia_almacen_etapa2.sql`.

Crea 4 tablas:

1. `axia_almacen_productos` — catálogo y saldo por código.
2. `axia_almacen_movimientos` — movimientos/Kardex inmutables desde el cliente.
3. `axia_almacen_config` — interruptores de autorización del catálogo y movimientos, inicialmente en `false`.
4. `axia_almacen_login_intentos` — protección de intentos de acceso al nuevo servicio.

Las operaciones se ejecutan vía la función PostgreSQL `axia_almacen_registrar_movimiento`, que bloquea el producto mientras calcula y actualiza saldo + registra Kardex **en una misma transacción**. No permite saldos negativos, ni que el cliente cambie saldos arbitrariamente.

**IMPORTANTE**: El SQL se incluye como preparativo técnico. No ejecutes aún la migración sin revisar tipos y políticas reales de tu proyecto, hacer respaldo y probarla en una instancia de ensayo.

Archivo Edge Function: `supabase/functions/axia-almacen/index.ts`.

- Verifica usuario y contraseña con bcrypt desde el servidor contra `db_usuarios`; exige nivel 1 u 8.
- La verificación NO acepta contraseñas heredadas SHA-256 o texto plano. El usuario debe iniciar normalmente sesión en AXIA primero para migrar a bcrypt, cuando corresponda.
- Emite una sesión firmada de 15 minutos; verifica el rol vigente en cada operación.
- Usa la **service role key exclusivamente en el entorno privado de la Edge Function**; jamás en `.env` del escritorio.
- Requiere el secreto privado `AXIA_ALMACEN_JWT_SECRET` de al menos 32 caracteres aleatorios, configurado solamente en Supabase.
- Despliegue contemplado con `supabase functions deploy axia-almacen --no-verify-jwt`. El servicio maneja su autenticación AXIA con controles de intentos en base de datos; el JWT de Supabase Auth del cliente no sustituye esta validación.
- La operación de movimientos permanece bloqueada en `axia_almacen_config` hasta que se autoricen el catálogo y los saldos de apertura.

**Posteriormente**, una vez auditado el catálogo:

1. Conciliar conteo físico, claves repetidas y fechas de corte.
2. Cargar productos en tablas de ensayo (sin sumar ambos Excel y sin eliminar códigos sin autorización).
3. Definir y ejecutar una carga de apertura **auditada** para saldos iniciales (NO incluida en esta etapa).
4. Probar SQL/RPC y permisos con usuarios tipo 1, 8 y un usuario no autorizado.
5. Activar catálogo e inventario sólo después de aceptación formal de Almacén.
6. En `.env` del equipo cliente, incorporar `AXIA_ALMACEN_MODO=remoto` **únicamente cuando el backend esté probado**. Si se omite, el sistema permanece en modo `simulador`.

## Pruebas realizadas

Pruebas unitarias en `tests/unit/test_almacen_etapa2.py`:
- Inicialización con saldo cero sin usar existencia histórica.
- Entrada / salida y consulta de Kardex.
- Rechazo de salidas con existencia insuficiente.
- Idempotencia: dos solicitudes con mismo UUID no producen dos entradas.
- Validación de permisos, cantidades y códigos duplicados.

Comando: `python -m pytest tests/unit/test_almacen_etapa2.py -q`

## Pendientes para una implementación completa

- Obtener aprobación del catálogo, cantidades y fecha de corte.
- Ejecutar y validar una migración **en entorno de pruebas**, incluidas políticas RLS y la Edge Function.
- Probar la UI de Windows, el instalador y el ejecutable PyInstaller.
- Implementar carga auditable de saldos de apertura, devoluciones, ajustes autorizados, reportes y vínculo definitivo con OT.
- Definir quién puede autorizar salidas, ajustes y acceso a información de costos.
