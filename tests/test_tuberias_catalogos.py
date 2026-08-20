from views.levantamientos.catalogos_canalizacion import (
    TIPOS_CANALIZACION,
    TIPOS_TUBOS,
)


def test_catalogos_centralizados_exponen_nomenclatura_actual_axia():
    for opcion in (
        "Pared delgada (EMT)",
        "Conduit metálico de pared intermedia (IMC)",
        "Metálico de pared gruesa (RMC)",
        "PVC Pesado",
        "Liquidtight /Licuatite",
    ):
        assert opcion in TIPOS_TUBOS


def test_canalizacion_conserva_opciones_complementarias():
    for opcion in ("Canaleta", "Charola", "Charofil", "Escalerilla", "Existente"):
        assert opcion in TIPOS_CANALIZACION


def test_accesorios_usan_medidas_de_tuberia_y_calibres_ampliados():
    from views.levantamientos.catalogos_canalizacion import (
        TAMANOS_TUBOS, CALIBRES_CABLE_ELECTRICO, especificaciones_por_categoria
    )
    for categoria in ("Cople", "Registro", "Conector", "Abrazadera"):
        assert especificaciones_por_categoria(categoria) == TAMANOS_TUBOS
    for calibre in ("6 AWG", "4 AWG", "2 AWG", "1/0 AWG", "2/0 AWG", "3/0 AWG", "4/0 AWG", "250 AWG", "350 AWG"):
        assert calibre in CALIBRES_CABLE_ELECTRICO
