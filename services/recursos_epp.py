"""Cantidades de equipo de protección básico según personal estimado.

No altera los catálogos ni requiere cambiar los campos persistidos. Los
formularios validan el número de personas antes de autorizar el guardado.
"""

EPP_BASICO = (
    "Casco de seguridad",
    "Botas de seguridad",
    "Chaleco reflejante / alta visibilidad",
    "Lentes de seguridad",
)


def personas_para_epp(valor):
    """Devuelve un entero positivo. Antes de la validación, usa 1 como vista previa."""
    try:
        cantidad = int(str(valor or "").strip())
    except (TypeError, ValueError):
        return 1
    return cantidad if cantidad > 0 else 1


def partidas_epp_basico(personas):
    """Genera partidas independientes, una por tipo, sin duplicados de personal."""
    cantidad = str(personas_para_epp(personas))
    return [{"epp": nombre, "cantidad": cantidad, "observaciones": ""}
            for nombre in EPP_BASICO]
