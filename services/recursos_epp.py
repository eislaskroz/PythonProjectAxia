EPP_BASICO = (
    "Casco de seguridad",
    "Botas de seguridad",
    "Chaleco reflejante / alta visibilidad",
    "Lentes de seguridad",
)


def personas_para_epp(valor):
    try:
        cantidad = int(str(valor or "").strip())
    except (TypeError, ValueError):
        return 1
    return cantidad if cantidad > 0 else 1


def partidas_epp_basico(personas):
    cantidad = str(personas_para_epp(personas))
    return [{"epp": nombre, "cantidad": cantidad, "observaciones": ""}
            for nombre in EPP_BASICO]
