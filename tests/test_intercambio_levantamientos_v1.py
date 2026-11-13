import pytest
from services.levantamiento_intercambio_v1 import (
    desktop_a_sobre, field_a_vista_desktop, restaurar_desktop_nativo, IntercambioNoSeguro,
)

def test_desktop_roundtrip_preserva_claves_extra():
    original = {'lev_cliente': 'AXIA', 'lev_descripcion': 'Servicio', 'lev_detalle_tecnico_json': '{"x": 1}', 'otro': [1, 2]}
    envelope = desktop_a_sobre('Redes Voz y Datos', original)
    tipo, restored = restaurar_desktop_nativo(envelope)
    assert tipo == 'Redes Voz y Datos'
    assert restored == original
    assert envelope['common']['description'] == 'Servicio'

def test_no_pasa_fotografias_locales():
    with pytest.raises(IntercambioNoSeguro):
        desktop_a_sobre('Redes', {'__evidencias_locales': ['C:/foto.jpg']})

def test_no_pasa_plano_embebido():
    with pytest.raises(IntercambioNoSeguro):
        desktop_a_sobre('Redes', {'lev_anotacion_plano_json': '{"habilitado": true, "imagen_base64":"abc"}'})

def test_field_comunes():
    envelope = {'schema': 'axia.draft.v1', 'module': 'LEVANTAMIENTO', 'source': 'FIELD',
                'native': {'field': {'formValues': {}}},
                'common': {'client': 'Cliente', 'description': 'Instalación'}}
    result = field_a_vista_desktop(envelope)
    assert result['lev_cliente'] == 'Cliente'
    assert result['lev_descripcion'] == 'Instalación'

def test_no_descarta_respuestas_tecnicas():
    envelope = {'schema': 'axia.draft.v1', 'module': 'LEVANTAMIENTO', 'source': 'FIELD',
                'native': {'field': {'formValues': {'cctv': 'Sí'}}}, 'common': {'client': 'A'}}
    with pytest.raises(IntercambioNoSeguro):
        field_a_vista_desktop(envelope)

def test_no_descarta_firma():
    envelope = {'schema': 'axia.draft.v1', 'module': 'LEVANTAMIENTO', 'source': 'FIELD',
                'native': {'field': {'signatureData': 'base64'}}, 'common': {'client': 'A'}}
    with pytest.raises(IntercambioNoSeguro):
        field_a_vista_desktop(envelope)
