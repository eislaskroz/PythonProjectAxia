# Estatus general AXIA - revisión 09/07/2026

## Limpieza aplicada
- Se eliminaron carpetas `__pycache__` y archivos compilados `.pyc`.
- Se agregó `.gitignore` para evitar subir `.env`, `.venv`, `build`, `dist`, logs y archivos generados.
- Se agregaron `__init__.py` faltantes para mantener paquetes consistentes.
- Se agregó `requirements-dev.txt` para dependencias de desarrollo.
- Se agregó `scripts/build_exe.ps1` para generar el ejecutable con PyInstaller.
- Se agregó `scripts/limpiar_proyecto.py` para limpiar basura generada sin tocar código fuente.

## Validación técnica rápida
- Archivos Python revisados: 62.
- Resultado de compilación sintáctica: sin errores detectados.
- No se movieron módulos funcionales principales para no romper imports ni flujo actual.

## Estructura recomendada actual

```text
assets/          Recursos visuales: logo, ícono, imágenes.
controllers/     Controladores de navegación y coordinación.
core/            Utilidades centrales: logger, cache, tareas, fechas.
docs/            Documentación técnica y roadmap.
migrations/      SQL y notas de cambios de base de datos.
modules/         Capa de módulos/abstracciones por proceso.
security/        Permisos, cifrado y contraseñas.
services/        Lógica de negocio y comunicación con Supabase.
tools/           Herramientas de diagnóstico/desarrollo.
ui/              Tema visual, fuentes, colores y componentes reutilizables.
views/           Pantallas y formularios.
scripts/         Automatizaciones locales: limpieza/build.
```

## Observaciones
El proyecto ya tiene una separación correcta entre vistas, servicios, controladores, seguridad y UI. 
Por seguridad, esta limpieza fue conservadora: se quitó basura y se agregaron herramientas, pero no se reubicaron archivos grandes como `levantamiento_view.py`, `orden_servicio_view.py` u otros, porque moverlos sin una ronda completa de pruebas podría romper imports, PDFs o flujos existentes.

## Siguiente mejora recomendada
Refactorizar gradualmente vistas grandes en componentes reutilizables, por ejemplo:
- Secciones de formularios.
- Botones de guardado/vista previa PDF.
- Helpers de PDF.
- Componentes de tablas.
- Componentes de captura de evidencias.
