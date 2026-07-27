-- AXIA: catálogo oficial de roles para db_usuarios.usu_tipo
-- 1 Administrador | 2 Jefe de Operaciones | 3 Supervisor
-- 4 Operador | 5 Administrativo | 6 Especial
--
-- Ejecutar primero la consulta de diagnóstico. Si devuelve filas, corrige esos
-- valores antes de agregar/validar la restricción.

SELECT id_usuario, usu_nickname, usu_tipo
FROM public.db_usuarios
WHERE usu_tipo IS NULL OR usu_tipo NOT IN (1, 2, 3, 4, 5, 6);

ALTER TABLE public.db_usuarios
    DROP CONSTRAINT IF EXISTS db_usuarios_usu_tipo_valido;

ALTER TABLE public.db_usuarios
    ADD CONSTRAINT db_usuarios_usu_tipo_valido
    CHECK (usu_tipo IN (1, 2, 3, 4, 5, 6)) NOT VALID;

-- Ejecuta esta línea únicamente cuando la consulta de diagnóstico no devuelva
-- registros inválidos.
ALTER TABLE public.db_usuarios
    VALIDATE CONSTRAINT db_usuarios_usu_tipo_valido;
