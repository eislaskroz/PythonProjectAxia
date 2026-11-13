"""Regresión del catálogo jerárquico y compatibilidad de registros anteriores."""
from pathlib import Path
import pytest

from views.levantamientos.catalogos_materiales_jerarquicos import (
    CATALOGO_XLSX, CATALOGO_NOVIEMBRE_2026, FAMILIA_POR_MATERIAL,
    MATERIALES_POR_FAMILIA, familia_de_material, familia_de_partida,
    familias_materiales, materiales_de_familia, normalizar_material,
    tipos_de_material, normalizar_seleccion_material, unidad_inicial_material,
    unidades_de_material,
)
from views.levantamientos.canalizacion_aproximado import texto_aproximado_canalizacion


def test_excel_noviembre_261_combinaciones_39_materiales_7_categorias():
    assert len(CATALOGO_XLSX) == 261
    assert len(familias_materiales()) == 7
    assert len(FAMILIA_POR_MATERIAL) == 39
    assert len({(f, m, t) for f, m, t in CATALOGO_XLSX}) == 261
    assert all(f and m and t for f, m, t in CATALOGO_XLSX)
    assert all(m in FAMILIA_POR_MATERIAL for grupo in MATERIALES_POR_FAMILIA.values() for m in grupo)
    assert all(len(tipos) == len(set(tipos)) for mats in CATALOGO_NOVIEMBRE_2026.values() for tipos in mats.values())


def test_materiales_activos_catalogo_2026():
    assert familia_de_material("Tubo") == "Conductores y Canalización"
    assert familia_de_material("Conectores") == "Conexiones y Uniones"
    assert familia_de_material("Abrazadera") == "Fijación y Soporte"
    assert "Canaleta" in materiales_de_familia("Conductores y Canalización")
    assert "Patch cord" in materiales_de_familia("Conexiones y Uniones")
    assert "Plugs RJ" in materiales_de_familia("Conexiones y Uniones")
    assert "Tubería de Cobre Flexible" in materiales_de_familia("Específicos Aire Acondirionado")
    assert "Varilla Roscada" in materiales_de_familia("Fijación y Soporte")
    assert "Aislamiento Térmico" in materiales_de_familia("Específicos Aire Acondirionado")
    assert "Pastillas Termomagnéticas" in materiales_de_familia("Protección y Potencia")


def test_tipos_activados_nuevos_y_eliminaciones_respetadas():
    assert "Helicoidal metálico / Flexible ZAPA" in tipos_de_material("Tubo")
    assert "Corrugado no metálico (ENT)" in tipos_de_material("Tubo")
    assert "Vorrugado no metálico (ENT)" not in tipos_de_material("Tubo")
    assert "Conector ZAPA" in tipos_de_material("Conectores")
    assert "Conector de ZAPA" not in tipos_de_material("Conectores")
    assert "12 puertos Cat6" in tipos_de_material("Patch panel")
    assert "Varilla roscada de cobre o bronce" in tipos_de_material("Varilla Roscada")
    assert tipos_de_material("Plugs RJ45 / RJ11") == []
    assert "Plugs RJ45 / RJ11" not in materiales_de_familia("Conexiones y Uniones")


def test_compatibilidad_de_partidas_historicas_sin_reintroducir_tipos():
    assert normalizar_material("Conector") == "Conectores"
    assert normalizar_material("Canalización") == "Canaleta"
    assert familia_de_partida({"categoria":"Tubo", "tipo":"Pared delgada (EMT)"}) == "Conductores y Canalización"
    assert familia_de_partida({"familia":"Específicos Aire Acondicionado", "material":"Aislamiento Térmico (Armaflex)"}) == "Específicos Aire Acondicionado"
    assert familia_de_partida({"categoria":"Varilla Roscada y Tuercas"}) == "Fijación y Soporte"


def test_abrazadera_para_viga_tiene_dos_medidas():
    assert "Para Viga" in tipos_de_material("Abrazadera")
    tipo, medida, opciones = normalizar_seleccion_material("Abrazadera", "Para Viga", "", tipos_de_material("Abrazadera"))
    assert tipo == "Para Viga"
    assert opciones == ['1" (25mm)', '3/4" (19mm)']
    assert medida in opciones


def test_canaleta_no_mezcla_medidas_de_tubo():
    tipo, medida, opciones = normalizar_seleccion_material("Canaleta", "Pared delgada (EMT)", '3/4" (19mm)', tipos_de_material("Canaleta"))
    assert tipo in tipos_de_material("Canaleta")
    assert medida == "Por definir"
    assert '3/4" (19mm)' not in opciones


def test_legacy_de_unidades_y_calibres_mantiene_reglas_existentes():
    _, medida, calibres = normalizar_seleccion_material("Cable Eléctrico", "THHN / THWN", "", tipos_de_material("Cable Eléctrico"))
    assert "14 AWG (Hasta 15A)" in calibres
    assert medida in calibres
    assert unidad_inicial_material("Tubo") == "Pieza(s)"
    assert unidad_inicial_material("Canaleta") == "Pieza(s)"
    assert unidad_inicial_material("Cable Eléctrico") == "Metro(s)"
    assert unidad_inicial_material("Unicanal (Riel)") == "Tramo(s)"
    assert "Bobina(s)" in unidades_de_material("Cable UTP (Cat 6 / 6A )")
    assert texto_aproximado_canalizacion("Tubo", "2", "Pieza(s)") == "6 metros"
    assert texto_aproximado_canalizacion("Canaleta", "2", "Pieza(s)") == "4 metros"


@pytest.mark.parametrize('tipo', [
    'Helicoidal metálico / Flexible ZAPA', 'Liquidtight / Licuatite',
    'Poliducto corrugado (Ligero)', 'Corrugado no metálico (ENT)',
])
def test_tubos_flexibles_noviembre_se_cuentan_por_metro(tipo):
    assert tipo in tipos_de_material("Tubo")
    assert unidades_de_material("Tubo", tipo) == ["Metro(s)"]
    assert texto_aproximado_canalizacion("Tubo", "4", "Metro(s)", tipo) == "4 metros"


@pytest.mark.parametrize('archivo', ['views/levantamiento_view.py','views/obra_civil_view.py'])
def test_ambos_formularios_comparten_catalogo_y_respetan_legacy(archivo):
    code=Path(archivo).read_text(encoding='utf-8')
    assert 'tipos_de_material(' in code
    assert 'materiales_de_familia(' in code
    assert 'historico=True' in code
    assert '"familia":' in code and '"material":' in code
