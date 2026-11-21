import unittest
from security.permissions import puede_editar_ordenes_operativas


class EdicionOrdenesPermisosTest(unittest.TestCase):
    def test_solo_tipos_dos_y_tres(self):
        for tipo in range(1, 11):
            with self.subTest(tipo=tipo):
                self.assertEqual(puede_editar_ordenes_operativas({"usu_tipo": tipo}), tipo in (2, 3))

    def test_identificador_usuario_no_otorga_permiso(self):
        self.assertFalse(puede_editar_ordenes_operativas({"id_usuario": 2, "usu_tipo": 4}))
        self.assertFalse(puede_editar_ordenes_operativas({"id_usuario": 3, "usu_tipo": 9}))

    def test_usuario_sin_tipo(self):
        self.assertFalse(puede_editar_ordenes_operativas({"id_usuario": 42}))
        self.assertFalse(puede_editar_ordenes_operativas(None))

    def test_tipo_como_cadena(self):
        self.assertTrue(puede_editar_ordenes_operativas({"usu_tipo": "2"}))
        self.assertTrue(puede_editar_ordenes_operativas({"usu_tipo": "3"}))


if __name__ == "__main__":
    unittest.main()
