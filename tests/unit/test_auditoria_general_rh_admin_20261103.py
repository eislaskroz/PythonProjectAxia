"""Pruebas estructurales del puente de auditoría (sin conexión a producción)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SQL = (ROOT / 'migrations' / '20261103_auditoria_general_rrhh_admin.sql').read_text(encoding='utf-8')


def test_instalacion_transaccional_e_idempotente():
    assert re.search(r'\bBEGIN\s*;', SQL)
    assert re.search(r'\bCOMMIT\s*;', SQL)
    for name in ('axia_rrhh_log_general_v1', 'axia_admin_log_general_v1'):
        assert f'DROP TRIGGER IF EXISTS {name}' in SQL
        assert f'CREATE TRIGGER {name}' in SQL


def test_historiales_y_movimientos_en_misma_transaccion():
    assert 'AFTER INSERT ON public.axia_rrhh_historial' in SQL
    assert 'AFTER INSERT ON public.axia_admin_registros_historial' in SQL
    assert SQL.count('INSERT INTO public.db_bitacora_mov') == 2
    assert 'EXCEPTION WHEN' not in SQL
    assert 'SECURITY INVOKER' in SQL


def test_no_expone_datos_sensibles_en_registro_general():
    # Ninguno de los campos sensibles aparece en instrucciones VALUES/descripcion.
    assert 'NEW.anterior::text' not in SQL
    assert 'NEW.posterior::text' not in SQL
    assert 'NEW.motivo' not in SQL
    assert 'NEW.empleado_id::text' in SQL
    assert "v_modulo := 'RECURSOS_HUMANOS'" in SQL


def test_solo_fuentes_previstas_y_roles_de_servidor():
    assert "current_user <> 'service_role'" in SQL
    assert "TG_TABLE_NAME = 'axia_rrhh_historial'" in SQL
    assert "TG_TABLE_NAME = 'axia_admin_registros_historial'" in SQL
    assert 'REVOKE ALL ON FUNCTION public.axia_auditoria_puente_movimientos()' in SQL


def test_modulos_operativos_existentes_siguen_registrando_movimientos():
    modulos = (
        'acos_service.py','levantamientos_service.py',
        'ordenes_trabajo_service.py','ordenes_servicio_service.py',
        'bitacoras_service.py',
    )
    for modulo in modulos:
        codigo = (ROOT/'services'/modulo).read_text(encoding='utf-8')
        assert 'registrar_movimiento_seguro' in codigo, modulo
    # Evita crear triggers sobre esos módulos: generarían registros duplicados.
    for tabla in ('db_acos','db_levantamientos','db_ordenes_trabajo',
                  'db_ordenes_servicio','db_bitacoras'):
        assert f'AFTER INSERT ON public.{tabla}' not in SQL
