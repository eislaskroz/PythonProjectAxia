# AXIA DESKTOP 2.06.34 — piloto de lectura privada

- Desplegar `supabase/functions/desktop-operational-evidence-access-v3/index.ts` con Legacy JWT OFF. Usa los secretos existentes `AXIA_MOBILE_JWT_SECRET` y `AXIA_DESKTOP_EVIDENCE_GRANTS` (además de la configuración Supabase del servidor).
- No reactivar ningún piloto de escritura. El endpoint solo permite lectura de BIT-00024 y OS-00005, a un administrador activo con grant corporativo registrado. Requiere la sesión AXIA compartida ya utilizada por DESKTOP.
- Abrir y generar los PDF desde las consultas de Bitácoras y Órdenes de Servicio. Ambas fotos de cada documento deben estar visibles. Se verifica SHA-256, tamaño, tipo y origen HTTPS antes de renderizar. Si falla la consulta no se usa el bucket histórico ni se genera el PDF del piloto sin sus fotos.
- No se reutiliza el artefacto PDF local para los folios piloto. Las copias PDF que se guardan o abren contienen imágenes y requieren protección local conforme a las políticas de AXIA. No se garantiza revocación de una copia PDF ya generada.
- No se modifican las cargas históricas, FIELD, TICKETS ni las políticas existentes. Las demás OT y otros roles requieren integración posterior. No se usa la API de escritura ni se limpia el almacenamiento.
- Pruebas locales: `python -m pytest -q tests/test_operational_evidence_v3.py` (15 casos simulados); `python scripts/check_version_sync.py`. Prueba de interfaz, PDF real de Supabase, caducidad de URL, roles y compilación Windows pendientes.
