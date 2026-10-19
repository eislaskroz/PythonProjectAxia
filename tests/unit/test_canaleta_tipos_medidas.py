"""Homologación de Canaleta: catálogo propio y limpieza de selecciones cruzadas."""

from pathlib import Path

import pytest

from views.levantamientos.catalogos_canalizacion import (
    MEDIDAS_CANALETA_POR_TIPO,
    TAMANOS_TUBOS,
    TIPOS_CANALETA,
    TIPOS_TUBOS,
    especificaciones_por_categoria,
    normalizar_opciones_canalizacion,
)
from views.levantamientos.canalizacion_aproximado import (
    texto_aproximado_canalizacion,
    unidad_forzada_canalizacion,
)


def test_existen_cinco_tipos_independientes_de_emt():
    assert TIPOS_CANALETA == [
        "Canaleta PVC", "Canaleta PVC autoadherible", "Canaleta ranurada",
        "Canaleta metálica", "Canaleta de piso",
    ]
    assert not set(TIPOS_CANALETA).intersection(TIPOS_TUBOS)


@pytest.mark.parametrize("tipo", TIPOS_CANALETA)
def test_cada_tipo_de_canaleta_tiene_medidas_especificas(tipo):
    opciones = especificaciones_por_categoria("Canaleta", tipo)
    assert len(opciones) >= 3
    assert "Por definir" in opciones
    assert set(MEDIDAS_CANALETA_POR_TIPO[tipo]).issubset(opciones)
    assert not set(TAMANOS_TUBOS).intersection(opciones)


def test_tubo_a_canaleta_limpiar_tipo_emt_y_medidas():
    tipo, medida, opciones = normalizar_opciones_canalizacion(
        "Canaleta", "Pared delgada (EMT)", '3/4" (19mm)', TIPOS_CANALETA
    )
    assert tipo == "Canaleta PVC"
    assert medida == "Por definir"  # Evitar asumir una medida al cambiar de categoría
    assert medida in opciones


def test_cambio_entre_tipos_de_canaleta_ajusta_medidas():
    tipo, medida, opciones = normalizar_opciones_canalizacion(
        "Canaleta", "Canaleta ranurada", "20 × 10 mm", TIPOS_CANALETA
    )
    assert tipo == "Canaleta ranurada"
    assert medida == "Por definir"  # El técnico debe elegir la nueva medida
    assert medida in opciones


def test_medida_compatible_se_conserva_y_otras_categorias_no_cambian():
    tipo, medida, _ = normalizar_opciones_canalizacion(
        "Canaleta", "Canaleta PVC autoadherible", "20 × 10 mm", TIPOS_CANALETA
    )
    assert (tipo, medida) == ("Canaleta PVC autoadherible", "20 × 10 mm")
    tipo, medida, _ = normalizar_opciones_canalizacion(
        "Tubo", "Pared delgada (EMT)", '3/4" (19mm)', TIPOS_TUBOS
    )
    assert (tipo, medida) == ("Pared delgada (EMT)", '3/4" (19mm)')


def test_unidad_y_conversion_original_siguen_iguales():
    assert unidad_forzada_canalizacion("Canaleta", "Metro(s)") == "Pieza(s)"
    assert texto_aproximado_canalizacion("Canaleta", "25.00", "Pieza(s)") == "50 metros"
    assert texto_aproximado_canalizacion("Tubo", "25.00", "Pieza(s)") == "75 metros"
    assert texto_aproximado_canalizacion("Patch cord", "15", "Pieza(s)") == "15 Pieza(s)"


@pytest.mark.parametrize("archivo", ["views/levantamiento_view.py", "views/obra_civil_view.py"])
def test_ambas_vistas_actualizan_tipo_antes_que_medidas(archivo):
    codigo = Path(archivo).read_text(encoding="utf-8")
    assert 'if categoria == "Canaleta": return list(TIPOS_CANALETA)' in codigo
    assert "normalizar_opciones_canalizacion(" in codigo
    assert "actualizando_catalogos = False" in codigo
    assert "trace_add(\"write\", actualizar_catalogos)" in codigo
