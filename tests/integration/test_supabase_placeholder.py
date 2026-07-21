import os
import pytest

@pytest.mark.integration
def test_supabase_configuracion_disponible_solo_bajo_demanda():
    if os.getenv("AXIA_RUN_INTEGRATION_TESTS") != "1":
        pytest.skip("Activa AXIA_RUN_INTEGRATION_TESTS=1 para pruebas con Supabase.")
    assert os.getenv("SUPABASE_URL")
    assert os.getenv("SUPABASE_KEY")
