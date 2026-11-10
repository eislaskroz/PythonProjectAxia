"""Comprobaciones de la integración de RH, sin conexión a Supabase."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

from security.permissions import (
    puede_ver_usuarios,
    puede_editar_expedientes_rrhh,
    puede_administrar_usuarios,
    puede_administrar_registros,
    puede_ver_auditoria,
    puede_generar_levantamiento,
)

ROOT = Path(__file__).resolve().parents[2]


def _load_service(monkeypatch, actor_tipo=10, response=None):
    """Aísla un cliente RH sin cargar secretos ni llamar a la red."""
    supa = types.ModuleType("supabase_config")
    supa.SUPABASE_URL = "https://example.supabase.co"
    supa.SUPABASE_KEY = "anon-ficticia-de-prueba"
    monkeypatch.setitem(sys.modules, "supabase_config", supa)
    usuarios = types.ModuleType("services.usuarios_service")
    class UsuarioServiceError(Exception):
        pass
    usuarios.UsuarioServiceError = UsuarioServiceError
    monkeypatch.setitem(sys.modules, "services.usuarios_service", usuarios)
    spec = importlib.util.spec_from_file_location(
        "_rrhh_integracion_prueba", ROOT / "services/rrhh_usuarios_service.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.obtener_usuario_actual = lambda: {
        "usu_tipo": actor_tipo, "usuario": "PERSONA_PRUEBA", "id_usuario": 99
    }
    # La prueba inspecciona el contrato de campos sin procesar información real.
    module.cifrar_diccionario = lambda values, fields: dict(values)
    module.descifrar_diccionario = lambda values, fields: dict(values)
    sent = []
    class Response:
        ok = True
        def json(self):
            return response or {"resultado": {"actualizado": True}, "registros": []}
    def post(url, **kw):
        sent.append((url, kw))
        return Response()
    monkeypatch.setattr(module.requests, "post", post)
    return module, sent


@pytest.mark.parametrize("tipo", [3, 4, 5, 6, 7, 8, 9])
def test_rh_exclusivo_sin_escalamiento(tipo):
    u = {"usu_tipo": tipo}
    assert not puede_editar_expedientes_rrhh(u)
    assert not puede_ver_usuarios(u)


def test_rol_10_no_crea_cuentas_ni_otros_registros():
    u = {"usu_tipo": 10}
    assert puede_ver_usuarios(u)
    assert puede_editar_expedientes_rrhh(u)
    assert not puede_administrar_usuarios(u)
    assert not puede_administrar_registros(u)
    assert not puede_ver_auditoria(u)
    assert not puede_generar_levantamiento(u)


def test_cliente_no_envia_rol_password_ni_nickname(monkeypatch):
    module, sent = _load_service(monkeypatch)
    empleado = {"id_usuario": 123, "usu_nombre": "Ana", "usu_apellido": "Prueba",
                "usu_tipo": 4, "usu_nickname": "ana"}
    empleado["_axia_original_cifrado"] = {"usu_nombre": "Ana"}
    datos = {**empleado, "usu_nombre": "Ana María", "usu_tipo": "1",
             "usu_password": "NO_DEBE_ENVIARSE", "usu_nickname": "ADMIN"}
    ok, _, _ = module.actualizar_usuario_rrhh(
        123, datos, empleado, "clave-ficticia", "Corrección de nombre"
    )
    assert ok
    assert len(sent) == 1
    url, request = sent[0]
    payload = request["json"]
    assert url.endswith("/functions/v1/axia-rrhh-usuarios")
    assert payload["accion"] == "actualizar"
    assert payload["cambios"] == {"usu_nombre": "Ana María"}
    assert set(payload["cambios"]).isdisjoint({"usu_password", "usu_tipo", "usu_nickname"})
    assert request["allow_redirects"] is False


def test_servicio_bloquea_roles_distintos(monkeypatch):
    module, sent = _load_service(monkeypatch, actor_tipo=4)
    with pytest.raises(module.UsuarioServiceError, match="rol 10"):
        module.buscar_usuarios_rrhh("empleado", "clave-ficticia")
    assert not sent


def test_nombres_obligatorios_y_campos_protegidos(monkeypatch):
    module, sent = _load_service(monkeypatch)
    seleccionado = {"id_usuario": 123, "usu_nombre": "Ana", "usu_apellido": "Prueba",
                    "_axia_original_cifrado": {"usu_nombre": "Ana"}}
    ok, msg, _ = module.actualizar_usuario_rrhh(
        123, {"usu_nombre": "", "usu_apellido": "Prueba"},
        seleccionado, "clave-ficticia", "Corrección de expediente")
    assert not ok and "Nombre" in msg
    assert not sent


def test_pantalla_rh_omite_campo_password_sin_ocultar_roles():
    text = (ROOT / "views/usuarios_admin_view.py").read_text(encoding="utf-8")
    assert 'if not (solo_rrhh and dato[0] == "usu_password")' in text
    assert '"Expediente de personal" if solo_rrhh' in text
    assert "campo in CAMPOS_RRHH" in text


def test_version_del_proyecto_no_se_retrocede():
    ver = (ROOT / "core/version.py").read_text(encoding="utf-8")
    installer = (ROOT / "installer/AXIA.iss").read_text(encoding="utf-8")
    assert 'APP_VERSION = "2.06.15"' in ver
    assert 'MyAppVersion "2.06.15"' in installer
