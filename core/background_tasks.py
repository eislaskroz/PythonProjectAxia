# =====================================================
# CORE: TAREAS EN SEGUNDO PLANO
# =====================================================
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
    if before:
        before()

    def worker() -> None:
        try:
            result = task()
        except Exception as exc:
            logger.exception("Error ejecutando tarea en segundo plano.")

            def handle_error(error=exc) -> None:
                if after:
                    after()
                if on_error:
                    on_error(error)

            try:
                if root is not None and root.winfo_exists():
                    root.after(0, handle_error)
            except Exception:
                logger.debug("Se descartó callback async de error porque la vista ya no existe.")
            return

        def handle_success() -> None:
            if after:
                after()
            if on_success:
                on_success(result)

        try:
            if root is not None and root.winfo_exists():
                root.after(0, handle_success)
        except Exception:
            logger.debug("Se descartó callback async de éxito porque la vista ya no existe.")

    Thread(
        target=worker,
        daemon=True
    ).start()
