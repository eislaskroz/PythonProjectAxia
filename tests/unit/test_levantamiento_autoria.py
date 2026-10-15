"""Regresiones: autoría original en PDF de todos los tipos de LEV."""
import json

import pytest

from services.levantamiento_autoria import autoria_desde_usuario, nombre_elaborador
from services.levantamiento_seguridad_pdf import generar_pdf_levantamiento_maestro


@pytest.mark.parametrize("contexto,esperado", [
    ({"nombre": " María  José ", "apellido": " Pérez  López "}, "María José Pérez López"),
    ({"usu_nombre": "José", "usu_apellido": "García"}, "José García"),
])
def test_usa_nombre_apellido_reales_de_login(contexto, esperado):
    assert nombre_elaborador({}, {"elaborado_por": autoria_desde_usuario(contexto)}) == esperado


def test_reimpresion_no_usa_operador_actual():
    assert nombre_elaborador(
        {"creado_por": "creador", "lev_tecnico": "Técnico auxiliar"},
        {"elaborado_por": {"usu_nombre": "Laura", "usu_apellido": "Hernández"}},
        buscar_usuario=lambda nickname: {"usu_nombre": "Otro", "usu_apellido": "Usuario"},
    ) == "Laura Hernández"


def test_registros_antiguos_recurre_a_autor_original_y_lev_tecnico():
    assert nombre_elaborador(
        {"creado_por": "legacy", "lev_tecnico": "Técnico anterior"}, {},
        buscar_usuario=lambda _nickname: {"usu_nombre": "Autor", "usu_apellido": "Antiguo"},
    ) == "Autor Antiguo"
    assert nombre_elaborador(
        {"creado_por": "legacy", "lev_tecnico": "Técnico anterior"}, {},
        buscar_usuario=lambda _nickname: None,
    ) == "Técnico anterior"


@pytest.mark.parametrize("tipo,modalidad", [
    ("Seguridad y Monitoreo", "Instalación"),
    ("Seguridad y Monitoreo", "Reparación"),
    ("Seguridad y Monitoreo", "Mantenimiento"),
    ("Redes Voz y Datos", "Instalación"),
    ("Control de Accesos", "Instalación"),
    ("Enlaces Inalámbricos", "Instalación"),
    ("Electricidad", "Instalación"),
    ("Paneles Solares", "Instalación"),
    ("Plantas de Energía", "Instalación"),
    ("Aires Acondicionados", "Instalación"),
    ("Tecnología, Equipos y Periféricos", "Instalación"),
    ("Obra Civil", "Instalación"),
])
def test_pdf_cierra_con_elaborado_por(tmp_path, tipo, modalidad):
    import fitz

    registro = {
        "lev_folio": "LEV-TEST-00001",
        "lev_tipo_levantamiento": tipo,
        "lev_modalidad_operativa": modalidad,
        "lev_cliente": "Cliente de prueba",
        "lev_descripcion": "Levantamiento de prueba",
        "lev_tecnico": "Técnico auxiliar",
        "creado_por": "nickname_antiguo",
        "lev_detalle_tecnico_json": json.dumps({
            "modalidad_operativa": modalidad,
            "elaborado_por": {"usu_nombre": "María José", "usu_apellido": "Pérez López"},
        }, ensure_ascii=False),
    }
    path = tmp_path / "levantamiento.pdf"
    generar_pdf_levantamiento_maestro(registro, ruta_salida=path)
    with fitz.open(path) as pdf:
        texto = "\n".join(page.get_text() for page in pdf)
        assert texto.count("ELABORADO POR:") == 1
        assert "María José Pérez López" in texto
        assert "Técnico auxiliar" not in texto
        assert "ELABORADO POR:" in pdf[-1].get_text()
