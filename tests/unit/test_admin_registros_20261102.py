"""Regresiones estáticas y de permisos para la consola administrativa AXIA.

No requieren acceso a la base real ni credenciales; las operaciones de escritura
solo pueden verificarse extremo a extremo después de desplegar SQL y Edge.
"""
from pathlib import Path
import ast
import re

BASE=Path(__file__).resolve().parents[2]

def test_rol_administrador_exclusivo():
    from security.permissions import puede_administrar_registros
    for rol in range(1,9):
        assert puede_administrar_registros({'usu_tipo':rol}) is (rol==1)
    assert not puede_administrar_registros(None)
    assert not puede_administrar_registros({'usu_tipo':'desconocido'})

def test_las_cinco_tablas_estan_en_el_contrato():
    src=(BASE/'services/admin_registros_service.py').read_text(encoding='utf-8')
    for t in ('db_acos','db_levantamientos','db_ordenes_trabajo','db_ordenes_servicio','db_bitacoras'):
        assert t in src
        assert t in (BASE/'supabase/functions/axia-admin-registros/index.ts').read_text()
        assert t in (BASE/'migrations/20261102_admin_registros.sql').read_text()

def test_credenciales_no_se_guardan_y_sin_service_role_cliente():
    src=(BASE/'services/admin_registros_service.py').read_text()
    assert 'SERVICE_ROLE_KEY' not in src
    assert 'https://' in src
    assert '.post(' in src
    assert 'obtener_usuario_actual' in src

def test_sin_acceso_publico_al_rpc():
    sql=(BASE/'migrations/20261102_admin_registros.sql').read_text()
    assert 'REVOKE ALL ON FUNCTION' in sql
    assert 'FROM PUBLIC,anon,authenticated' in sql
    assert 'GRANT EXECUTE ON FUNCTION' in sql
    assert 'TO service_role' in sql
    assert 'FOR UPDATE' in sql
    assert 'IS DISTINCT FROM p_antes' in sql
    assert 'No se puede eliminar: existen registros relacionados' in sql
    assert 'INSERT INTO public.axia_admin_registros_historial' in sql

def test_server_valida_password_y_tipo_1():
    src=(BASE/'supabase/functions/axia-admin-registros/index.ts').read_text()
    assert 'bcrypt.compare(password,hash)' in src
    assert "Number(actor?.usu_tipo)!==1" in src
    assert "accion==='eliminar'" in src
    assert "accion==='auditoria'" in src

def test_menu_y_navegacion_protegidos():
    menu=(BASE/'ui/app_sidebar.py').read_text()
    nav=(BASE/'controllers/navigation_controller.py').read_text()
    app=(BASE/'app.py').read_text()
    assert 'if puede_administrar_registros(usuario_activo)' in menu
    assert 'callbacks["admin_registros"]' in menu
    assert 'self._verificar_permiso(' in nav.split('def mostrar_admin_registros',1)[1].split('def mostrar_auditoria',1)[0]
    assert '"admin_registros": self.navigation.mostrar_admin_registros' in app

def test_codigo_compilable_y_campos_protegidos():
    for rel in ('views/admin_registros_view.py','services/admin_registros_service.py','ui/app_sidebar.py','controllers/navigation_controller.py'):
        ast.parse((BASE/rel).read_text(encoding='utf-8'))
    src=(BASE/'services/admin_registros_service.py').read_text(encoding='utf-8')
    allowed=src.split('EDITABLES = {',1)[1].split('EDITABLES = {k:',1)[0]
    for clave in ('"aco_numero"','"lev_folio"','"ot_folio"','"os_folio"','"bit_folio"',
                  '"id_aco"','"id_levantamiento"','"os_fotos"'):
        assert clave not in allowed
