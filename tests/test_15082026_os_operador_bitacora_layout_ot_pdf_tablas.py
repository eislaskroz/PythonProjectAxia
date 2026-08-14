from pathlib import Path


def read(path):
    return Path(path).read_text(encoding='utf-8')


def test_operador_puede_capturar_orden_servicio_sin_abrir_ot():
    permissions = read('security/permissions.py')
    sidebar = read('ui/app_sidebar.py')
    os_view = read('views/orden_servicio_view.py')
    assert 'def puede_generar_orden_servicio' in permissions
    assert 'return obtener_tipo_usuario(usuario_activo) in ROLES_TODOS' in permissions
    assert 'callbacks["orden_servicio"]' in sidebar
    assert 'if tipo_usuario == OPERADOR' in sidebar
    assert 'puede_generar_orden_servicio(usuario_activo)' in os_view


def test_bitacora_usa_rejilla_de_seis_columnas_y_orden_solicitado():
    source = read('views/bitacora_avance_view.py')
    assert 'for col in range(6)' in source
    assert 'entry("Nombre del Cliente", var_cliente, "Autollenado por ACO", 1, 3' in source
    assert 'combo_sucursal = option("Sucursal operativa", var_sucursal' in source
    assert 'entry("Nombre del encargado del proyecto", var_encargado' in source
    assert 'entry("Dirección de la sucursal", var_direccion' in source and 'colspan=3' in source
    assert 'fila_operativa.grid_columnconfigure(0, weight=3)' in source
    assert 'fila_operativa.grid_columnconfigure(1, weight=1)' in source
    assert 'fila_operativa.grid_columnconfigure(2, weight=1)' in source
    assert 'campo_operativo("Técnico en sitio", 0)' in source
    assert 'campo_operativo("Estatus", 1)' in source
    assert 'campo_operativo("Porcentaje de avance", 2)' in source


def test_pdf_ot_separa_materiales_equipos_y_miscelaneos():
    schema = read('services/ordenes_trabajo_schema.py')
    contract = read('services/operational_document_pdf.py')
    renderer = read('views/formato_helpers.py')
    assert 'grupo="Materiales"' in schema
    assert 'grupo="Equipos"' in schema
    assert 'grupo="Misceláneos"' in schema
    assert 'secciones.append(("Materiales"' in contract
    assert 'secciones.append(("Equipos"' in contract
    assert 'secciones.append(("Misceláneos / consumibles"' in contract
    assert 'for section_title_text, normalized_rows in sections_render' in renderer
