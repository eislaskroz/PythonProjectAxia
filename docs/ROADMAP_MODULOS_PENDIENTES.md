# Roadmap de módulos pendientes AXIA

## Módulos prioritarios por implementar

### 1. Dashboard ejecutivo
Indicadores rápidos:
- Levantamientos abiertos/cerrados.
- Órdenes de servicio abiertas/cerradas.
- Órdenes de trabajo pendientes.
- Bitácoras recientes.
- ACOs activos.
- Actividad por técnico o responsable.

### 2. Mantenimiento
Actualmente el flujo ya contempla Instalación / Reparación / Mantenimiento, pero falta definir y construir el formulario completo de Mantenimiento.
Debe incluir:
- Tipo de mantenimiento.
- Checklist técnico.
- Estado antes/después.
- Evidencia fotográfica.
- Recomendaciones.
- Próxima fecha sugerida.

### 3. Evidencias fotográficas centralizadas
Módulo para adjuntar, consultar y relacionar imágenes con:
- Levantamientos.
- Órdenes de servicio.
- Órdenes de trabajo.
- Bitácoras.
- Obra civil.

### 4. Catálogo de sucursales / ubicaciones
Aunque existe `sucursales_service.py`, conviene tener pantalla administrativa completa para:
- Alta.
- Edición.
- Búsqueda.
- Relación cliente-sucursal.
- Dirección y contacto local.

### 5. Catálogo de técnicos / cuadrillas
Administrar:
- Técnicos.
- Especialidad.
- Zona.
- Teléfono.
- Correo.
- Estatus.
- Relación con órdenes y bitácoras.

### 6. Inventario / equipos
Catálogo para:
- Cámaras.
- DVR/NVR.
- Discos duros.
- Switches.
- Fuentes.
- UPS.
- Series, marcas, modelos y estatus.

### 7. Reportes avanzados
Ampliar `reportes_view.py` con:
- Filtros por fecha.
- Cliente.
- Técnico.
- Estatus.
- Exportación a Excel/PDF.
- Indicadores mensuales.

### 8. Configuración del sistema
Pantalla para administrar:
- Rutas de guardado de PDFs.
- Datos de empresa.
- Logo institucional.
- Parámetros de folios.
- Variables no sensibles de operación.

### 9. Gestión de permisos por rol
Actualmente existe base en `security/permissions.py`, pero conviene crecerlo a:
- Roles configurables.
- Permisos por módulo.
- Permisos por acción: crear, editar, eliminar, exportar, ver.

### 10. Historial/auditoría más visible
Ya existe vista de auditoría, pero puede crecer a:
- Filtros por usuario.
- Acción.
- Fecha.
- Módulo.
- Exportación.

## Módulos futuros deseables

### 11. Notificaciones internas
Alertas para:
- Órdenes vencidas.
- Levantamientos pendientes.
- Bitácoras sin cierre.
- Cambios importantes.

### 12. Cotizaciones / seguimiento comercial
A partir de levantamientos o reparaciones:
- Generar solicitud de cotización.
- Relacionar equipos dañados.
- Estatus comercial.

### 13. Instalador formal
Cuando la beta sea estable:
- Inno Setup.
- Acceso directo.
- Desinstalador.
- Versión.
- Carpeta de documentos AXIA.
