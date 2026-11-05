"""Cobertura de jerarquía, opciones existentes y compatibilidad de partidas AXIA."""
from pathlib import Path
import pytest

from views.levantamientos.catalogos_materiales_jerarquicos import (
    CATALOGO_XLSX, FAMILIA_POR_MATERIAL, MATERIALES_POR_FAMILIA,
    familia_de_material, familia_de_partida, familias_materiales,
    materiales_de_familia, normalizar_material, tipos_de_material,
    normalizar_seleccion_material, unidad_inicial_material,
    unidades_de_material, uso_de_material,
)
from views.levantamientos.canalizacion_aproximado import texto_aproximado_canalizacion


def test_excel_tiene_33_materiales_en_siete_familias():
    assert len(CATALOGO_XLSX) == 33
    assert len(familias_materiales()) == 7
    assert all(f and m and uso and unidad for f,m,uso,unidad in CATALOGO_XLSX)
    assert all(mat in FAMILIA_POR_MATERIAL for grupo in MATERIALES_POR_FAMILIA.values() for mat in grupo)


def test_materiales_existentes_se_preservan_y_ubican_en_sus_familias():
    assert familia_de_material("Tubo") == "Conductores y Canalización"
    assert familia_de_material("Conectores") == "Conexiones y Uniones"
    assert familia_de_material("Abrazadera") == "Fijación y Soporte"
    assert familia_de_material("Cajas") == "Cajas y Registros"
    assert "Cable" in materiales_de_familia("Conductores y Canalización")
    assert "Patch cord" in materiales_de_familia("Conexiones y Uniones")
    assert "Canaleta" in materiales_de_familia("Conductores y Canalización")


def test_nuevos_materiales_excel_cubiertos():
    assert "Tubería de Cobre Flexible" in materiales_de_familia("Específicos Aire Acondicionado")
    assert "Centros de Carga / Tableros" in materiales_de_familia("Protección y Potencia")
    assert "Varilla Roscada y Tuercas" in materiales_de_familia("Fijación y Soporte")
    assert "Cable UTP (Cat 6 / 6A)" in materiales_de_familia("Conductores y Canalización")
    assert "Aislamiento Térmico (Armaflex)" in materiales_de_familia("Específicos Aire Acondicionado")
    assert "Montaje" in uso_de_material("Estructuras de Aluminio")


def test_antiguas_partidas_sin_familia_se_pueden_restaurar():
    assert normalizar_material("Conector") == "Conectores"
    assert normalizar_material("Canalización") == "Canaleta"
    assert familia_de_partida({"categoria": "Tubo", "tipo": "Pared delgada (EMT)"}) == "Conductores y Canalización"
    assert familia_de_partida({"categoria": "Conectores", "tipo": "Conector de ZAPA"}) == "Conexiones y Uniones"
    assert familia_de_partida({"familia": "Fijación y Soporte", "material": "Abrazadera"}) == "Fijación y Soporte"


def test_abrazadera_para_viga_conserva_solo_dos_tamanos():
    assert "Para Viga" in tipos_de_material("Abrazadera")
    tipo, medida, opciones = normalizar_seleccion_material("Abrazadera", "Para Viga", "", tipos_de_material("Abrazadera"))
    assert tipo == "Para Viga"
    assert opciones == ['1" (25mm)', '3/4" (19mm)']
    assert medida in opciones


def test_tubo_y_conector_zapa_y_medidas_independientes():
    assert "Helicoidal metálico / Flexible ZAPA" in tipos_de_material("Tubo")
    assert "Conector de ZAPA" in tipos_de_material("Conectores")
    assert normalizar_seleccion_material("Tubo", "Pared delgada (EMT)", '3/4" (19mm)', tipos_de_material("Tubo"))[1] == '3/4" (19mm)'
    tipo, medida, opciones = normalizar_seleccion_material("Canaleta", "Pared delgada (EMT)", '3/4" (19mm)', tipos_de_material("Canaleta"))
    assert tipo == "Canaleta PVC"
    assert medida == "Por definir"
    assert '3/4" (19mm)' not in opciones


def test_calibres_electricos_y_nuevos_sin_especificacion_no_se_inventan():
    _, medida, calibres = normalizar_seleccion_material("Cable Eléctrico", "THHN / THWN", "", tipos_de_material("Cable Eléctrico"))
    assert "14 AWG (Hasta 15A)" in calibres
    assert medida in calibres
    assert tipos_de_material("Pastillas Termomagnéticas / Fusibles") == ["Por definir"]
    assert normalizar_seleccion_material("Pastillas Termomagnéticas / Fusibles", "", "", ["Por definir"])[1] == "Por definir"


def test_unidades_compatibles_y_conversion_metros():
    assert unidad_inicial_material("Tubo") == "Pieza(s)"
    assert unidad_inicial_material("Canaleta") == "Pieza(s)"
    assert unidad_inicial_material("Cable Eléctrico") == "Metro(s)"
    assert unidad_inicial_material("Unicanal (Riel)") == "Tramo(s)"
    assert "Bobina(s)" in unidades_de_material("Cable UTP (Cat 6 / 6A)")
    assert texto_aproximado_canalizacion("Tubo", "2", "Pieza(s)") == "6 metros"
    assert texto_aproximado_canalizacion("Canaleta", "2", "Pieza(s)") == "4 metros"


@pytest.mark.parametrize('archivo', ['views/levantamiento_view.py', 'views/obra_civil_view.py'])
def test_ambos_formularios_muestran_ocho_columnas_y_guardan_familia(archivo):
    code = Path(archivo).read_text(encoding='utf-8')
    assert '"Categoría", "Material", "Tipo"' in code
    assert 'normalizar_seleccion_material(' in code
    assert '"familia":' in code
    assert '"material":' in code
    assert 'familia_de_partida(' in code
    assert 'column=7' in code
