"""Validaciones de límite 50, fecha de interfaz, ACO y descripción, sin Supabase."""
from pathlib import Path
from uuid import uuid4
import pytest
from services import reportador_fotografico_service as rf
from services.reportador_fotografico_pdf import _validate_and_plan

ROOT = Path(__file__).resolve().parents[2]


def payload(activities: int):
    return dict(aco='ACO-0901', cliente='Cliente', sucursal='Sitio',
                nombre_servicio='Servicio', tecnico_responsable='Técnico',
                fecha_servicio='2026-11-09',
                actividades=[rf.nueva_actividad() | {'titulo': f'Actividad {i+1}',
                                                       'cantidad_fotos': 1}
                             for i in range(activities)])


@pytest.mark.parametrize('n', [1, 20, 21, 49, 50])
def test_los_limites_validan_50(n):
    rf.validar_captura(payload(n))


@pytest.mark.parametrize('n', [0, 51])
def test_no_permite_mas_de_50_o_menos_de_1(n):
    with pytest.raises(rf.ErrorReportador, match='1 a 50'):
        rf.validar_captura(payload(n))


def test_fecha_muestra_y_guarda_como_corresponde():
    assert rf.fecha_para_mostrar('2026-11-09') == '09-11-2026'
    assert rf.fecha_para_guardar('09-11-2026') == '2026-11-09'
    assert rf.fecha_para_mostrar('2024-02-29') == '29-02-2024'
    with pytest.raises(rf.ErrorReportador, match='DD-MM-AAAA'):
        rf.fecha_para_guardar('31-02-2026')
    with pytest.raises(rf.ErrorReportador, match='DD-MM-AAAA'):
        rf.fecha_para_guardar('2026-11-09')


def test_pdf_plan_acepta_50_actividades():
    data = payload(50)
    report = {k:v for k,v in data.items() if k!='actividades'}
    report.update(id_reporte=8, autor_nombre='Técnico 1', cantidad_os=1)
    acts = data['actividades']
    detail = dict(reporte=report, actividades=acts,
                  fotos=[{'clave_actividad':a['clave'], 'numero':1} for a in acts],
                  ordenes=[{'numero':1}])
    assert len(_validate_and_plan(detail)[1]) == 50


def test_consulta_aco_es_autenticada_y_los_campos_vienen_del_maestro():
    src = (ROOT/'supabase/functions/axia-reportador-desktop/index.ts').read_text()
    assert src.index('const actor=await session(body);') < src.index("if(op==='acos')")
    assert "db.from('db_acos')" in src
    assert 'aco_cliente,aco_descripcion,id_sucursal' in src
    assert "db.from('db_clientes_sucursales')" in src
    assert "if(op==='aco_detalle')" in src
    assert "db.from('db_ordenes_trabajo')" in src
    assert "db.from('db_ordenes_servicio')" in src
    assert "db.from('db_levantamientos')" in src
    assert '250_000' in src


def test_sql_incremental_ajusta_constraints_y_valida_aco():
    sql=(ROOT/'migrations/20261109_reportador_50_actividades_y_aco.sql').read_text()
    assert 'orden BETWEEN 1 AND 50' in sql
    assert 'NOT BETWEEN 1 AND 50' in sql
    assert 'SELECT 1 FROM public.db_acos WHERE aco_numero=' in sql
    assert 'CREATE OR REPLACE FUNCTION public.axia_rf_guardar' in sql


def test_descripcion_oculta_el_campo_en_tk():
    src=(ROOT/'views/reportador_fotografico_view.py').read_text()
    assert 'def actualizar_descripcion()' in src
    assert 'desc.pack_forget()' in src
    assert 'checkbox.configure(command=actualizar_descripcion)' in src
    assert "'descripcion': a['descripcion'].get('1.0','end-1c').strip() if a['enable'].get() else ''" in src
    assert "('fecha_servicio', 'Fecha (DD-MM-AAAA)')" in src
