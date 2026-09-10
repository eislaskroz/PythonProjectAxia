-- AXIA DESKTOP 02/09/2026
-- Habilita los tipos de archivo que el formulario de Levantamientos permite adjuntar.
-- Ejecutar una sola vez en Supabase > SQL Editor.

update storage.buckets
set allowed_mime_types = array[
  'image/jpeg',
  'image/png',
  'image/webp',
  'application/pdf',
  'image/vnd.dwg',
  'image/vnd.dxf',
  'application/octet-stream'
]::text[]
where id = 'bitacoras-evidencias';

select id, name, allowed_mime_types
from storage.buckets
where id = 'bitacoras-evidencias';
