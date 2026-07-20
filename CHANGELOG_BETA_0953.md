# AXIA Beta 0.95.3

## Correcciones

- Restaurado el buscador por número de ACO como contenido predeterminado de **Inicio ACO**.
- El campo de número de ACO recibe el foco al abrir la vista y permite validar con `Enter`.
- Conservados los accesos **Sí, tengo ACO** y **No tengo ACO**.
- Reemplazado el posicionamiento absoluto del encabezado ACO por un layout adaptable, evitando que desaparezca con distintas resoluciones o escalas de Windows.
- Corregido un error de sintaxis en el botón **Guardar ACO** que podía impedir cargar el módulo desde el código fuente.
- Actualizada la versión central y el instalador a `0.95.3`.

## Validaciones realizadas

- Compilación de todos los archivos Python sin errores de sintaxis.
- Auditoría estructural ejecutada con `tools/auditar_proyecto.py`.
- Conservada la navegación hacia Levantamientos, Órdenes de Servicio, Órdenes de Trabajo y Bitácoras después de validar un ACO.

## Prueba recomendada

1. Abrir **Inicio ACO**.
2. Confirmar que el buscador aparezca inmediatamente.
3. Capturar un ACO y presionar `Enter`.
4. Validar que se muestren las opciones operativas correspondientes.
5. Probar **No tengo ACO** y guardar un registro de prueba.
