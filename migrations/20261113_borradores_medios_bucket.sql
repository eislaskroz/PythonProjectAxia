-- ETAPA 2C. Ejecutar SOLO en un entorno de pruebas tras respaldo y revisión.
-- Bucket privado: sin políticas SELECT/INSERT para anon/authenticated.
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'axia-borradores-medios', 'axia-borradores-medios', false,
  8388608, ARRAY['image/jpeg','image/png','image/webp','application/pdf']::text[]
)
ON CONFLICT (id) DO NOTHING;
-- Revisar la configuración existente si ya había un bucket con ese ID:
-- SELECT id, public, file_size_limit, allowed_mime_types FROM storage.buckets WHERE id='axia-borradores-medios';
-- La función server-side autorizada usa service_role. No publicar el bucket.
