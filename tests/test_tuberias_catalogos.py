from views.levantamientos.catalogos_canalizacion import (
    TIPOS_CANALIZACION,
    TIPOS_TUBOS,
)


def test_catalogos_centralizados_exponen_nomenclatura_actual_axia():
    for opcion in (
        "Pared delgada (EMT)",
        "Conduit metálico de pared intermedia (IMC)",
        "Metálico de pared gruesa (RMC)",
        "Policloruro de Vinilo (PVC)",
        "Liquidtight",
    ):
        assert opcion in TIPOS_TUBOS


def test_canalizacion_conserva_opciones_complementarias():
    for opcion in ("Canaleta", "Charola", "Charofil", "Escalerilla", "Existente"):
        assert opcion in TIPOS_CANALIZACION
