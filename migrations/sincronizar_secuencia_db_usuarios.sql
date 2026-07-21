-- Ejecutar después de importar IDs explícitos en public.db_usuarios.
-- Ajusta la secuencia asociada a id_usuario al máximo ID existente.
DO $$
DECLARE
    seq_name text;
    max_id bigint;
BEGIN
    seq_name := pg_get_serial_sequence('public.db_usuarios', 'id_usuario');
    SELECT COALESCE(MAX(id_usuario), 0) INTO max_id FROM public.db_usuarios;

    IF seq_name IS NULL THEN
        RAISE NOTICE 'id_usuario no usa una secuencia serial/identity detectable. No se hizo ningún cambio.';
    ELSIF max_id = 0 THEN
        PERFORM setval(seq_name, 1, false);
    ELSE
        PERFORM setval(seq_name, max_id, true);
    END IF;
END $$;

SELECT MAX(id_usuario) AS max_id_actual FROM public.db_usuarios;
