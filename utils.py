# =====================================================
# IMPORTACIÓN DE LIBRERÍAS
# =====================================================

# =====================================================
# FUNCIÓN PARA CENTRAR VENTANAS
# =====================================================
def centrar_ventana(ventana, ancho=None, alto=None, padre=None):
    """Centra una ventana de Tk/CustomTkinter de forma consistente.

    Es compatible con las llamadas históricas ``centrar_ventana(win, w, h)``.
    Para ventanas secundarias conviene pasar ``padre``: se centran respecto a
    AXIA (también si la aplicación está en un segundo monitor). Si no hay padre
    utilizable, se usa el centro de la pantalla reportada por Tk.
    """
    try:
        ventana.update_idletasks()
    except Exception:
        pass

    try:
        ancho_real = int(ancho or max(1, ventana.winfo_reqwidth(), ventana.winfo_width()))
        alto_real = int(alto or max(1, ventana.winfo_reqheight(), ventana.winfo_height()))
    except Exception:
        ancho_real = int(ancho or 800)
        alto_real = int(alto or 600)

    # Si no se indicó padre explícito, intenta usar el master/toplevel.
    if padre is None:
        try:
            master = ventana.master
            if master is not None and master is not ventana:
                padre = master.winfo_toplevel()
        except Exception:
            padre = None

    usar_padre = False
    if padre is not None:
        try:
            padre.update_idletasks()
            pw, ph = padre.winfo_width(), padre.winfo_height()
            px, py = padre.winfo_rootx(), padre.winfo_rooty()
            usar_padre = pw > 1 and ph > 1
        except Exception:
            usar_padre = False

    if usar_padre:
        x = int(px + (pw - ancho_real) / 2)
        y = int(py + (ph - alto_real) / 2)
    else:
        pantalla_ancho = ventana.winfo_screenwidth()
        pantalla_alto = ventana.winfo_screenheight()
        x = int((pantalla_ancho - ancho_real) / 2)
        y = int((pantalla_alto - alto_real) / 2)

    # No forzamos x/y al monitor primario cuando existe padre, porque AXIA puede
    # estar abierto en un monitor secundario con coordenadas virtuales negativas.
    if not usar_padre:
        x = max(0, x)
        y = max(0, y)

    ventana.geometry(f"{ancho_real}x{alto_real}+{x}+{y}")
    return x, y


def centrar_ventana_renderizada(ventana, padre=None):
    """Centra una ventana usando el tamaño que obtuvo después de dibujarse."""
    try:
        ventana.update_idletasks()
        ancho = max(1, ventana.winfo_width(), ventana.winfo_reqwidth())
        alto = max(1, ventana.winfo_height(), ventana.winfo_reqheight())
        return centrar_ventana(ventana, ancho, alto, padre=padre)
    except Exception:
        return None


# =====================================================
# FUNCIÓN PARA ENCRIPTAR CONTRASEÑAS
# =====================================================
def encriptar_password(password):

    """
    Genera un hash seguro para una contraseña utilizando bcrypt.

    IMPORTANTE:
        El nombre de esta función se conserva para no romper
        archivos existentes que todavía la importan.

    Antes AXIA usaba SHA-256.
    A partir de esta versión, todas las contraseñas nuevas
    se guardan con bcrypt.
    """

    from security.passwords import generar_hash_password

    return generar_hash_password(password)
