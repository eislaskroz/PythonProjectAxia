# FIX22 - Cotización homologada al AXIA PDF Engine

- Se eliminó el render visual aislado de Cotizaciones.
- La cotización ahora reutiliza `BasePdfGenerator` para fondo, título, metadatos, paginación y pie corporativo.
- Se agregó `assets/FormatoFondoHorizontal.png`, adaptación horizontal de la plantilla corporativa para Letter landscape sin deformar el fondo vertical.
- Datos generales, partidas y totales usan la misma paleta, bordes, encabezados y jerarquía visual de Levantamientos, Órdenes de Trabajo, Órdenes de Servicio y Bitácoras.
- Las partidas usan `LongTable` con encabezado repetible para permitir cotizaciones multipágina.
- El formato se compactó para que una cotización típica de 13 partidas pueda permanecer en una sola hoja horizontal.
- No requiere cambios en Supabase.
