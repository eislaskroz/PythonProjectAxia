"""Pruebas puras para los formularios de edición; no requieren servidor ni Tk."""
import ast
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
ARCHIVO = ROOT / 'views' / 'admin_registros_formularios.py'
SERVICIO = ROOT / 'services' / 'admin_registros_service.py'


def importar_logica_pura():
    # Extraer las funciones/métodos puros sin construir ventanas Tk en CI.
    arbol = ast.parse(ARCHIVO.read_text(encoding='utf8'))
    servicio = ast.parse(SERVICIO.read_text(encoding='utf8'))
    asignaciones = [n for n in servicio.body if isinstance(n, ast.Assign)
                     and any(isinstance(t,ast.Name) and t.id == 'EDITABLES' for t in n.targets)]
    ns = {'copy':copy,'json':json}
    exec(compile(ast.Module(body=asignaciones, type_ignores=[]), str(SERVICIO), 'exec'), ns)
    nombres = {'SECCIONES','NOMBRES','ENUMS','LARGOS','RELACIONES_PROTEGIDAS'}
    funciones = {'secciones_efectivas','_analizar_json','_serializar_json_editado','_convertir_hoja','_actualizar_ruta'}
    nodos=[]
    for n in arbol.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in nombres for t in n.targets):
            nodos.append(n)
        elif isinstance(n,ast.FunctionDef) and n.name in funciones:
            # Retirar anotaciones solo en prueba, sin alterar fuente real.
            n.returns=None
            for arg in n.args.args:
                arg.annotation=None
            nodos.append(n)
        elif isinstance(n,ast.ClassDef) and n.name=='FormularioSeccionado':
            metodo=next(m for m in n.body if isinstance(m,ast.FunctionDef) and m.name=='cambios')
            nodos.append(ast.ClassDef(name='FormularioDePrueba',bases=[],keywords=[],body=[metodo],decorator_list=[]))
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodos,type_ignores=[])),str(ARCHIVO),'exec'),ns)
    return ns


LOGICA=importar_logica_pura()


class PruebasFormularioAdministrativo(unittest.TestCase):
    def test_los_cinco_formatos_tienen_secciones_y_solo_campos_permitidos(self):
        for tabla,campos in LOGICA['EDITABLES'].items():
            registro={campo:'original' for campo in campos}
            secciones=LOGICA['secciones_efectivas'](tabla,registro)
            todos=[campo for _,c in secciones for campo in c]
            self.assertGreaterEqual(len(secciones),2)
            self.assertEqual(set(todos),set(campos))
            self.assertEqual(len(todos),len(set(todos)))

    def test_no_muestra_campos_no_autorizados(self):
        registro={'lev_cliente':'Demo','lev_folio':'LEV-001', 'id_aco':12,'lev_estatus':1}
        secciones=LOGICA['secciones_efectivas']('db_levantamientos',registro)
        todos=[c for _,filas in secciones for c in filas]
        self.assertEqual(set(todos),{'lev_cliente','lev_estatus'})

    def test_json_tecnico_reconstruye_tipo_y_preserva_datos_ocultos(self):
        original='{"elementos":[{"nombre":"Cámara","cantidad":2,"prueba":true}],"otros":13}'
        arbol,cadena=LOGICA['_analizar_json'](original)
        LOGICA['_actualizar_ruta'](arbol,('elementos',0,'cantidad'),4)
        convertido=LOGICA['_serializar_json_editado'](arbol,cadena)
        self.assertIsInstance(convertido,str)
        self.assertEqual(json.loads(convertido)['elementos'][0]['cantidad'],4)
        self.assertTrue(json.loads(convertido)['elementos'][0]['prueba'])
        self.assertEqual(json.loads(convertido)['otros'],13)

    def test_booleanos_y_numeros_preservan_tipo(self):
        fn=LOGICA['_convertir_hoja']
        self.assertIs(fn('No',True),False)
        self.assertEqual(fn('45',1),45)
        self.assertEqual(fn('5.75',2.3),5.75)
        with self.assertRaises(ValueError):fn('palabra',10)

    def test_sin_desbloquear_no_envia_nada(self):
        vista=LOGICA['FormularioDePrueba'].__new__(LOGICA['FormularioDePrueba'])
        vista.original={'aco_cliente':'A','aco_observaciones':'Antes'}
        vista.controles={'aco_cliente':SimpleNamespace(seccion='General',leer=lambda:'B'),
                        'aco_observaciones':SimpleNamespace(seccion='Notas',leer=lambda:'Nuevo')}
        vista.desbloqueadas={'General':False,'Notas':False}
        self.assertEqual(vista.cambios(),{})
        vista.desbloqueadas['Notas']=True
        self.assertEqual(vista.cambios(),{'aco_observaciones':'Nuevo'})

    def test_json_equivalente_no_consume_guardado(self):
        vista=LOGICA['FormularioDePrueba'].__new__(LOGICA['FormularioDePrueba'])
        vista.original={'ot_partidas_json':'[{"parte":"a","cantidad":2}]'}
        vista.controles={'ot_partidas_json':SimpleNamespace(seccion='Partidas',leer=lambda:'[{"cantidad": 2, "parte": "a"}]')}
        vista.desbloqueadas={'Partidas':True}
        self.assertEqual(vista.cambios(),{})

    def test_no_acepta_porcentaje_fuera_de_rango(self):
        vista=LOGICA['FormularioDePrueba'].__new__(LOGICA['FormularioDePrueba'])
        vista.original={'bit_porcentaje_avance':30}
        vista.controles={'bit_porcentaje_avance':SimpleNamespace(seccion='Avance',leer=lambda:120)}
        vista.desbloqueadas={'Avance':True}
        with self.assertRaises(ValueError):vista.cambios()


if __name__ == '__main__':
    unittest.main()
