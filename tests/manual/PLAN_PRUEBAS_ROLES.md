# Plan de aceptación por rol

Ejecutar en **staging** con seis usuarios de prueba, uno por cada `usu_tipo`.
Registrar evidencia (captura, fecha, versión y resultado) para cada caso.

| Función | 1 Admin | 2 Jefe Ops | 3 Supervisor | 4 Operador | 5 Administrativo | 6 Especial |
|---|---:|---:|---:|---:|---:|---:|
| Agregar levantamiento | Sí | Sí | Sí | Sí | Sí | Sí |
| Consultar procesos | Sí | Sí | Sí | No | Sí | Sí |
| Órdenes y bitácoras | Sí | Sí | Sí | No | Sí | Sí |
| Reportes operativos | Sí | Sí | Sí | No | Sí | Sí |
| Usuarios | Sí | Sí | No | No | No | No |
| Clientes | Sí | Sí | No | No | No | No |
| Auditoría login/movimientos | Sí | No | No | No | No | No |

Además, intentar acceder a cada vista restringida mediante navegación normal y llamada directa. Debe bloquearse en ambos casos.
