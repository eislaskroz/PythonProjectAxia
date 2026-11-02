"""Regresiones del formulario de alta ACO: autollenado y responsables."""
from pathlib import Path

from services.aco_form_helpers import datos_contacto_aco

ROOT = Path(__file__).resolve().parents[2]


def test_contacto_operativo_completo_tiene_prioridad():
    datos = datos_contacto_aco(
        {"cli_contacto": "Principal", "cli_telefono": "CLIENTE", "cli_correo": "cliente@ejemplo.mx"},
        {"suc_telefono": "SUCURSAL", "suc_correo": "sucursal@ejemplo.mx"},
        {"con_nombre": "Operativo", "con_telefono": "CONTACTO", "con_correo": "contacto@ejemplo.mx"},
    )
    assert datos == {"nombre": "Operativo", "telefono": "CONTACTO", "correo": "contacto@ejemplo.mx"}


def test_contacto_sin_correo_ni_telefono_recupera_datos_de_sucursal_y_cliente():
    datos = datos_contacto_aco(
        {"cli_contacto": "Principal", "cli_telefono": "CLIENTE", "cli_correo": "cliente@ejemplo.mx"},
        {"suc_telefono": "SUCURSAL"},
        {"con_nombre": "Operativo", "con_telefono": "", "con_correo": None},
    )
    assert datos == {"nombre": "Operativo", "telefono": "SUCURSAL", "correo": "cliente@ejemplo.mx"}


def test_sin_sucursal_usa_datos_maestros_y_nunca_inventa_un_valor():
    cliente = {"cli_contacto": "Principal", "cli_telefono": "CLIENTE", "cli_correo": "cliente@ejemplo.mx"}
    assert datos_contacto_aco(cliente) == {
        "nombre": "Principal", "telefono": "CLIENTE", "correo": "cliente@ejemplo.mx",
    }
    assert datos_contacto_aco({}) == {"nombre": "", "telefono": "", "correo": ""}


def test_aco_selector_responsable_todas_las_areas_y_validacion():
    vista = (ROOT / "views" / "inicio_aco_view.py").read_text(encoding="utf-8")
    assert 'obtener_usuarios_por_tipos(TIPOS_VALIDOS, limite=3000)' in vista
    assert 'selector_responsable = NativeComboBox(' in vista
    assert 'if responsable not in seleccion_operativa["responsables_por_nombre"]:' in vista
    assert '"aco_responsable": responsable' in vista
    assert 'datos_contacto_aco(cliente_db, sucursal_db, contacto_db)' in vista
    assert 'OPCION_SUCURSAL_PRINCIPAL = "Principal / datos del cliente"' in vista


def test_consulta_responsables_pagina_y_no_pide_password():
    servicio = (ROOT / "services" / "usuarios_service.py").read_text(encoding="utf-8")
    fragmento = servicio.split('def obtener_usuarios_por_tipos(', 1)[1].split('def obtener_nombres_usuarios_por_tipos(', 1)[0]
    assert '.range(inicio, fin)' in fragmento
    assert '.in_("usu_tipo", tipos_validos)' in fragmento
    assert '.order("id_usuario")' in fragmento
    assert 'usu_password' not in fragmento
