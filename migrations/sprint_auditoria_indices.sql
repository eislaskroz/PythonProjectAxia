-- AXIA | Sprint de revisión del módulo de auditoría
-- Índices recomendados para consultas recientes y filtros administrativos.
-- Puede ejecutarse varias veces. No modifica ni elimina información.

CREATE INDEX IF NOT EXISTS idx_db_bitacora_mov_fecha_hora
    ON public.db_bitacora_mov (fecha_hora DESC);
CREATE INDEX IF NOT EXISTS idx_db_bitacora_mov_usuario
    ON public.db_bitacora_mov (usuario);
CREATE INDEX IF NOT EXISTS idx_db_bitacora_mov_modulo
    ON public.db_bitacora_mov (modulo);
CREATE INDEX IF NOT EXISTS idx_db_bitacora_mov_equipo
    ON public.db_bitacora_mov (equipo);

CREATE INDEX IF NOT EXISTS idx_db_login_fecha_hora
    ON public.db_login (fecha_hora DESC);
CREATE INDEX IF NOT EXISTS idx_db_login_nickname
    ON public.db_login (usu_nickname);
CREATE INDEX IF NOT EXISTS idx_db_login_estatus
    ON public.db_login (estatus);
CREATE INDEX IF NOT EXISTS idx_db_login_equipo
    ON public.db_login (nombre_equipo);
