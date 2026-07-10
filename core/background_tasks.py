# =====================================================
# CORE: TAREAS EN SEGUNDO PLANO
# =====================================================
"""
Utilidad central para ejecutar operaciones lentas sin congelar la interfaz.

Problema que resuelve:
    CustomTkinter/Tkinter trabaja en un solo hilo principal.
    Si en ese hilo hacemos una consulta HTTP a Supabase, una petición externa
    o una operación pesada, la ventana puede quedarse congelada.

Solución:
    Ejecutamos la tarea pesada en un hilo secundario y regresamos el resultado
    al hilo principal usando root.after().

Regla importante:
    NUNCA actualices widgets directamente desde el hilo secundario.
    Todas las operaciones visuales deben ir en on_success, on_error o after,
    porque esas funciones se ejecutan de regreso en el hilo principal.
"""

from __future__ import annotations

from threading import Thread
from typing import Any, Callable, Optional

from core.logger import get_logger

logger = get_logger(__name__)


def run_async(
    root,
    task: Callable[[], Any],
    on_success: Optional[Callable[[Any], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
    before: Optional[Callable[[], None]] = None,
    after: Optional[Callable[[], None]] = None,
) -> None:
    """
    Ejecuta una tarea en segundo plano y devuelve el resultado a la UI.

    Parámetros:
        root:
            Ventana principal o Toplevel de Tkinter/CustomTkinter.
            Se usa para ejecutar callbacks seguros con root.after().

        task:
            Función pesada que se ejecutará en un hilo secundario.
            Aquí van consultas a Supabase, requests, validaciones externas,
            generación de reportes, etc.

        on_success:
            Función que recibe el resultado de task cuando todo sale bien.
            Se ejecuta en el hilo principal, por lo tanto puede modificar UI.

        on_error:
            Función que recibe la excepción si task falla.
            Se ejecuta en el hilo principal, por lo tanto puede mostrar messagebox.

        before:
            Función opcional ejecutada antes de iniciar el hilo.
            Útil para cambiar cursor, deshabilitar botones o mostrar carga.

        after:
            Función opcional ejecutada siempre al final.
            Útil para restaurar cursor, habilitar botones o quitar carga.
    """

    if before:
        before()

    def worker() -> None:
        """Trabajo real que corre fuera del hilo principal de la interfaz."""
        try:
            result = task()
        except Exception as exc:  # noqa: BLE001 - Queremos capturar y reportar cualquier fallo controlado.
            logger.exception("Error ejecutando tarea en segundo plano.")

            def handle_error(error=exc) -> None:
                """Ejecuta el callback de error dentro del hilo principal."""
                if after:
                    after()
                if on_error:
                    on_error(error)

            root.after(0, handle_error)
            return

        def handle_success() -> None:
            if after:
                after()
            if on_success:
                on_success(result)

        root.after(0, handle_success)

    Thread(
        target=worker,
        daemon=True
    ).start()
