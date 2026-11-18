# =====================================================
# TEMA GLOBAL AXIA
# =====================================================
from ui.theme_manager import ThemeManager


def aplicar_tema_global():
    ThemeManager.apply_global_theme()


def aplicar_fuente_tk(root=None):
    ThemeManager.apply_native_tk_theme(root)


def aplicar_estilo_ventana(root=None, min_width=None, min_height=None):
    ThemeManager.apply_window_defaults(root, min_width=min_width, min_height=min_height)
