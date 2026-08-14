from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(path): return (ROOT/path).read_text(encoding='utf-8')

def test_os_fecha_aco_y_autollenados():
    s=read('views/orden_servicio_view.py')
    assert 'datetime.now().strftime("%d/%m/%Y")' in s
    assert 'obtener_contextos_aco_disponibles_cierre' in s
    assert 'option("ACO", var_aco, acos_disponibles' in s
    for campo in ['var_cliente.set', 'var_sucursal.set', 'var_domicilio.set', 'var_encargado_general.set', 'var_solicitante.set', 'var_correo.set', 'var_celular.set']:
        assert campo in s

def test_os_roles_combo_y_multitecnico():
    s=read('views/orden_servicio_view.py')
    assert 'obtener_nombres_usuarios_por_tipos([2, 3, 4])' in s
    assert 'obtener_nombres_usuarios_por_tipos([4])' in s
    assert 'option("Tipo de Servicio", var_tipo_servicio, TIPOS_SERVICIO' in s
    assert 'def agregar_tecnico()' in s
    assert '" | ".join(tecnicos_seleccionados)' in s
    assert 'seccion("Proveedor"' not in s

def test_os_fotos_migracion_y_pdf():
    view=read('views/orden_servicio_view.py')
    svc=read('services/ordenes_servicio_service.py')
    pdf=read('services/operational_document_pdf.py')
    mig=read('migrations/20260817_os_evidencias_fotograficas.sql')
    assert 'subir_evidencias_orden_servicio' in view
    assert '"os_fotos": []' in view
    assert 'os_fotos' in svc and 'os_fotos' in mig
    assert '"Evidencia Fotográfica": r.get("os_fotos") or []' in pdf

def test_bitacora_multitecnico_tipo4():
    s=read('views/bitacora_avance_view.py')
    assert 'obtener_nombres_usuarios_por_tipos([4])' in s
    assert 'def agregar_tecnico()' in s
    assert 'bit_tecnico_sitio' in s
