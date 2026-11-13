from services.borradores_compartidos_service import sobre_desktop, restaurar_desktop, nueva_clave, SCHEMA
import pytest

def test_preserva_datos_especializados_sin_eliminarlos():
    original = {"lev_cliente": "Cliente", "lev_detalle_tecnico_json": '{"e":1}',
                "lev_evidencias_json": '[{"ruta":"local"}]', "custom": [1, 2]}
    env = sobre_desktop("Tecnología", original)
    assert env['schema'] == SCHEMA
    assert env['media_transfer_complete'] is False
    tipo, vuelto = restaurar_desktop(env)
    assert tipo == "Tecnología" and vuelto == original

def test_no_convierte_field_sin_adaptador_que_preserve_evidencias():
    with pytest.raises(ValueError, match="requiere conversión"):
        restaurar_desktop({"schema": SCHEMA, "module": "LEVANTAMIENTO", "source": "FIELD", "native": {"field": {}}})

def test_claves_uuid_independientes():
    import uuid
    assert uuid.UUID(nueva_clave()) != uuid.UUID(nueva_clave())
