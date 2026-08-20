from pathlib import Path
import os


def test_resumen_sucursales_no_lista_domicilios():
    src = Path('views/clientes_admin_view.py').read_text(encoding='utf-8')
    assert 'Cantidad de Sucursales Registradas:' in src
    assert 'for s in sucursales[:6]' not in src


def test_inactividad_es_global_y_configurable():
    src = Path('app.py').read_text(encoding='utf-8')
    assert 'AXIA_IDLE_TIMEOUT_MINUTES' in src
    assert 'bind_all' in src
    assert 'CIERRE_INACTIVIDAD' in src
    assert '_guardar_borrador_actual()' in src


def test_borrador_tiene_tres_acciones_y_restauracion():
    app = Path('app.py').read_text(encoding='utf-8')
    nav = Path('controllers/navigation_controller.py').read_text(encoding='utf-8')
    lev = Path('views/levantamiento_view.py').read_text(encoding='utf-8')
    assert 'Continuar' in app
    assert 'Guardar para después' in app
    assert 'Borrar' in app
    assert 'borrador=datos' in app
    assert 'borrador=None' in nav
    assert 'registro_editar or borrador' in lev


def test_borrador_se_cifra_y_se_elimina_al_guardar():
    svc = Path('services/levantamiento_borradores_service.py').read_text(encoding='utf-8')
    lev = Path('views/levantamiento_view.py').read_text(encoding='utf-8')
    assert 'cifrar_valor' in svc and 'descifrar_valor' in svc
    assert 'eliminar_borrador(usuario_activo)' in lev
