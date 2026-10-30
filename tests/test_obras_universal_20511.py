import json
import unittest
from services.obras_civiles_universal import (
    es_obra_civil, transformar_obra_civil,
    cambios_obra_civil_desde_formulario,
)


class TestUniversalObraCivil(unittest.TestCase):
    def setUp(self):
        self.raw = {
            'obc_id': 7, 'obc_folio': 'OBC-0001',
            'obc_cliente': 'Cliente ejemplo', 'obc_nombre_proyecto': 'Obra civil prueba',
            'obc_contacto': 'Contacto', 'obc_sucursal': 'Sucursal',
            'obc_ejecucion_json': json.dumps({'_conceptos_obra': [{'tipo':'OTROS','concepto':'Partida manual','unidad':'m2'}],
                '_datos_generales_axia': {'tecnico':'Personal'}}),
            'obc_validado_ventas': False, 'obc_fecha': '2026-10-30',
        }

    def test_identidad_sin_id_de_levantamiento(self):
        item = transformar_obra_civil(self.raw)
        self.assertTrue(es_obra_civil(item))
        self.assertEqual(item['lev_folio'], 'OBC-0001')
        self.assertNotIn('id_levantamiento', item)
        self.assertEqual(item['lev_tipo'], 'Obra Civil')
        self.assertIn('Partida manual', item['lev_detalle_tecnico_json'])

    def test_edicion_no_pisa_folio_ni_anexos(self):
        item = transformar_obra_civil(self.raw)
        cambios = cambios_obra_civil_desde_formulario(item, {
            'lev_cliente':'Nuevo nombre', 'lev_contacto':'Nueva persona',
            'lev_direccion':'Dirección', 'lev_ubicacion':'Sucursal',
            'lev_supervisor':'Supervisor','lev_fecha_realizacion':'2026-10-30',
            'lev_tecnico':'Empleado', 'lev_telefono':'555', 'lev_correo':'a@b.mx',
        }, 'Nuevo proyecto', 'Giro', 'Nota', item['lev_detalle_tecnico_json'])
        self.assertNotIn('obc_folio', cambios)
        self.assertNotIn('obc_evidencias_json', cambios)
        self.assertNotIn('obc_archivos_adjuntos_json', cambios)
        self.assertNotIn('id_aco', cambios)
        self.assertEqual(cambios['obc_nombre_proyecto'], 'Nuevo proyecto')
        self.assertEqual(json.loads(cambios['obc_ejecucion_json'])['_datos_generales_axia']['tecnico'], 'Empleado')
        self.assertEqual(json.loads(cambios['obc_ejecucion_json'])['_conceptos_obra'][0]['concepto'], 'Partida manual')

    def test_detalle_json_invalido_no_aceptado(self):
        item = transformar_obra_civil(self.raw)
        with self.assertRaises(ValueError):
            cambios_obra_civil_desde_formulario(item, {}, 'Obra', '', '', '[]')

    def test_validado_queda_identificado(self):
        item = transformar_obra_civil({**self.raw,'obc_validado_ventas': True})
        self.assertEqual(item['lev_estatus'], 'Validado')
        self.assertTrue(item['lev_validado_ventas'])


if __name__ == '__main__':
    unittest.main()
