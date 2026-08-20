# FIX23 - Cotización: estructura documental y foco visible

- Se elimina el bloque redundante de folio/fecha/levantamiento debajo del título del PDF.
- La retícula de cotización sigue el orden del formato comercial de referencia: Fecha de Cotización, No. Cotización, No. Levantamiento, Cliente, Contacto, Sucursal y Asunto.
- Plan de Pagos y Vigencia de Cotización permanecen en un bloque lateral independiente.
- Se corrige la navegación global por TAB dentro de `CTkScrollableFrame`: al cambiar el foco, el canvas desplaza automáticamente el viewport para mantener visible el campo activo.
- No requiere cambios en Supabase.
