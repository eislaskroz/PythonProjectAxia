from pathlib import Path
from security.permissions import (
    nombre_rol, obtener_tipo_usuario, puede_ver_usuarios,
    puede_administrar_usuarios, puede_administrar_registros,
    puede_editar_expedientes_rrhh, puede_ver_auditoria,
    puede_ver_clientes, puede_generar_levantamiento, matriz_permisos,
)


def test_roles_9_y_10_validos_y_sin_escalamiento():
    assert nombre_rol(9) == 'DG y Calidad'
    assert nombre_rol(10) == 'Recursos Humanos'
    assert obtener_tipo_usuario({'usu_tipo': 10}) == 10
    assert obtener_tipo_usuario({'usu_tipo': 99}) is None


def test_rrhh_puede_ver_usuarios_sin_administrar_accesos():
    hr = {'usu_tipo': 10}
    assert puede_ver_usuarios(hr)
    assert puede_editar_expedientes_rrhh(hr)
    assert not puede_administrar_usuarios(hr)
    assert not puede_administrar_registros(hr)
    assert not puede_ver_auditoria(hr)
    assert not puede_ver_clientes(hr)
    assert not puede_generar_levantamiento(hr)
    assert matriz_permisos()[10]['usuarios']
    assert not matriz_permisos()[10]['administrar_cuentas']


def test_roles_existentes_conservados():
    for i in (1,2):
        assert puede_administrar_usuarios({'usu_tipo':i})
    assert not puede_administrar_usuarios({'usu_tipo':3})


def test_sql_y_edge_no_aceptan_roles_ni_passwords():
    root=Path(__file__).resolve().parents[2]
    sql=(root/'migrations/20261103_rrhh_usuarios.sql').read_text()
    edge=(root/'supabase/functions/axia-rrhh-usuarios/index.ts').read_text()
    srv=(root/'services/rrhh_usuarios_service.py').read_text()
    assert "current_user <> 'service_role'" in sql
    assert "usu_tipo=10" in sql
    assert "GRANT EXECUTE" in sql
    assert "!FIELDS.includes(k)" in edge
    assert "Number(actor?.usu_tipo)!==10" in edge
    assert 'usu_password' not in srv.split('CAMPOS_RRHH = ',1)[1].split('))',1)[0]
    assert 'usu_tipo' not in srv.split('CAMPOS_RRHH = ',1)[1].split('))',1)[0]


def test_interfaz_bloquea_alta_y_controla_campos():
    ui=(Path(__file__).resolve().parents[2]/'views/usuarios_admin_view.py').read_text()
    assert 'btn_guardar.configure(state=\'disabled\'' in ui
    assert "campo in CAMPOS_RRHH" in ui
    assert 'solicitar_clave_rrhh' in ui
