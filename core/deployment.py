"""Validaciones de despliegue y separación de ambientes de AXIA."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

VALID_ENVIRONMENTS = frozenset({"development", "staging", "production"})
_PROJECT_REF_RE = re.compile(r"^[a-z0-9]{20}$")


class DeploymentConfigurationError(RuntimeError):
    """Configuración de ambiente inválida o peligrosa."""


@dataclass(frozen=True)
class DeploymentConfig:
    environment: str
    supabase_url: str
    project_ref: str
    expected_project_ref: str | None


def extract_project_ref(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    suffix = ".supabase.co"
    if not host.endswith(suffix):
        raise DeploymentConfigurationError("SUPABASE_URL no corresponde a un proyecto Supabase válido.")
    project_ref = host[: -len(suffix)]
    if not _PROJECT_REF_RE.fullmatch(project_ref):
        raise DeploymentConfigurationError("No fue posible identificar el project ref de Supabase.")
    return project_ref


def load_deployment_config() -> DeploymentConfig:
    environment = os.getenv("AXIA_ENV", "development").strip().lower()
    if environment not in VALID_ENVIRONMENTS:
        raise DeploymentConfigurationError(
            f"AXIA_ENV inválido: {environment!r}. Usa development, staging o production."
        )
    url = (os.getenv("SUPABASE_URL") or "").strip()
    if not url:
        raise DeploymentConfigurationError("Falta SUPABASE_URL.")
    project_ref = extract_project_ref(url)
    expected = (os.getenv("AXIA_EXPECTED_SUPABASE_PROJECT_REF") or "").strip().lower() or None
    if environment in {"staging", "production"} and not expected:
        raise DeploymentConfigurationError(
            "AXIA_EXPECTED_SUPABASE_PROJECT_REF es obligatorio en staging y production."
        )
    if expected and expected != project_ref:
        raise DeploymentConfigurationError(
            "El proyecto Supabase configurado no coincide con el ambiente esperado."
        )
    return DeploymentConfig(environment, url, project_ref, expected)


def require_non_production(action: str) -> DeploymentConfig:
    config = load_deployment_config()
    if config.environment == "production":
        raise DeploymentConfigurationError(
            f"La acción '{action}' está bloqueada en producción sin autorización explícita."
        )
    return config
