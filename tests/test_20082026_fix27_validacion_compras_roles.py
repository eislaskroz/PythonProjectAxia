from pathlib import Path


def test_roles_compras_y_almacen_estan_registrados():
    texto = Path('security/permissions.py').read_text(encoding='utf-8')
    assert 'COMPRAS = 7' in texto
    assert 'ALMACEN = 8' in texto
    assert 'COMPRAS: "Compras"' in texto
    assert 'ALMACEN: "Almacén"' in texto
    assert 'def puede_ver_compras' in texto


def test_formulario_usuarios_acepta_1_a_8():
    vista = Path('views/usuarios_admin_view.py').read_text(encoding='utf-8')
    servicio = Path('services/usuarios_service.py').read_text(encoding='utf-8')
    assert 'Tipo de usuario (1-8)' in vista
    assert 'entre 1 y 8' in servicio


def test_preview_y_guardado_dependen_de_validacion_completa():
    texto = Path('views/cotizaciones_view.py').read_text(encoding='utf-8')
    assert 'def validar_captura_completa' in texto
    assert 'btn_pdf.configure(state="normal" if valida else "disabled")' in texto
    assert 'btn_guardar.configure(state="normal" if (modo and valida and not finalizada) else "disabled")' in texto
    assert 'P. Lista debe ser mayor que cero' in texto
    assert 'Usa N/A cuando no aplique' in texto


def test_servicio_impide_persistir_cotizacion_incompleta():
    texto = Path('services/cotizaciones_service.py').read_text(encoding='utf-8')
    assert 'Falta completar correctamente' in texto
    assert 'La cotización no contiene partidas comerciales' in texto
    assert 'Precio de lista, lote {i}' in texto


def test_modulo_compras_lista_cotizaciones_en_compra_y_no_crea_ot():
    vista = Path('views/compras_view.py').read_text(encoding='utf-8')
    assert 'obtener_cotizaciones_en_compra' in vista
    assert 'Pendientes de compra' in vista
    assert 'todavía no se genera una Orden de Trabajo' in vista
    sidebar = Path('ui/app_sidebar.py').read_text(encoding='utf-8')
    assert '"🛒 Compras"' in sidebar
    nav = Path('controllers/navigation_controller.py').read_text(encoding='utf-8')
    assert 'def mostrar_compras' in nav
