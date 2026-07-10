# =====================================================
# TEMA GLOBAL AXIA
# =====================================================
"""Compatibilidad para llamadas existentes del proyecto.

La lógica real ahora vive en ui/theme_manager.py para que todos los
colores, fuentes y escalas estén centralizados en un solo lugar.
"""

from ui.theme_manager import ThemeManager


def aplicar_tema_global():
    """Aplica el tema global de AXIA antes de crear ventanas."""
    ThemeManager.apply_global_theme()


def aplicar_fuente_tk(root=None):
    """Aplica fuente y estilo nativo Tk/ttk a una ventana existente."""
    ThemeManager.apply_native_tk_theme(root)


def aplicar_estilo_ventana(root=None, min_width=None, min_height=None):
    """Aplica ajustes visuales comunes a una ventana concreta."""
    ThemeManager.apply_window_defaults(root, min_width=min_width, min_height=min_height)
