import pytest
from core.deployment import DeploymentConfigurationError, extract_project_ref, load_deployment_config

REF = "abcdefghijklmnopqrst"

def test_extract_project_ref():
    assert extract_project_ref(f"https://{REF}.supabase.co") == REF

@pytest.mark.parametrize("url", ["https://example.com", "", "https://short.supabase.co"])
def test_rechaza_url_invalida(url):
    with pytest.raises(DeploymentConfigurationError):
        extract_project_ref(url)

def test_staging_exige_ref_esperado(monkeypatch):
    monkeypatch.setenv("AXIA_ENV", "staging")
    monkeypatch.setenv("SUPABASE_URL", f"https://{REF}.supabase.co")
    monkeypatch.delenv("AXIA_EXPECTED_SUPABASE_PROJECT_REF", raising=False)
    with pytest.raises(DeploymentConfigurationError):
        load_deployment_config()

def test_proyecto_equivocado_falla_cerrado(monkeypatch):
    monkeypatch.setenv("AXIA_ENV", "production")
    monkeypatch.setenv("SUPABASE_URL", f"https://{REF}.supabase.co")
    monkeypatch.setenv("AXIA_EXPECTED_SUPABASE_PROJECT_REF", "zyxwvutsrqponmlkjihg")
    with pytest.raises(DeploymentConfigurationError):
        load_deployment_config()
