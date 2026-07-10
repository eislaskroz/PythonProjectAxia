# =====================================================
# IMPORTACIÓN DE LIBRERÍAS
# =====================================================

# =====================================================
# FUNCIÓN PARA CENTRAR VENTANAS
# =====================================================
def centrar_ventana(ventana, ancho, alto):

    """
    Centra una ventana automáticamente
    respecto a la resolución actual de pantalla.

    Parámetros:
        ventana:
            Objeto ventana de Tkinter o CustomTkinter.

        ancho (int):
            Ancho deseado de la ventana.

        alto (int):
            Alto deseado de la ventana.

    Esta función:
    - obtiene resolución de pantalla,
    - calcula coordenadas centrales,
    - posiciona la ventana automáticamente.
    """


    # =================================================
    # OBTENER RESOLUCIÓN DE PANTALLA
    # =================================================

    """
    winfo_screenwidth():
    Obtiene ancho total del monitor.
    """

    pantalla_ancho = ventana.winfo_screenwidth()


    """
    winfo_screenheight():
    Obtiene alto total del monitor.
    """

    pantalla_alto = ventana.winfo_screenheight()


    # =================================================
    # CALCULAR POSICIÓN CENTRAL
    # =================================================

    """
    Fórmula para centrar ventana:

    posición_x =
        ancho_pantalla / 2
        -
        ancho_ventana / 2

    posición_y =
        alto_pantalla / 2
        -
        alto_ventana / 2
    """

    x = int(
        (pantalla_ancho / 2)
        -
        (ancho / 2)
    )

    y = int(
        (pantalla_alto / 2)
        -
        (alto / 2)
    )


    # =================================================
    # APLICAR GEOMETRÍA A LA VENTANA
    # =================================================

    """
    geometry():
    Define:
    - tamaño
    - posición

    Formato:
        ancho x alto + x + y
    """

    ventana.geometry(
        f"{ancho}x{alto}+{x}+{y}"
    )


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
