from __future__ import annotations
from services import levantamiento_borradores_service as storage


def test_borrador_reusa_identificador_y_revision(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, '_base_dir', lambda: tmp_path)
    monkeypatch.setattr(storage, 'cifrar_valor', lambda s: s)
    monkeypatch.setattr(storage, 'descifrar_valor', lambda s: s)
    user = {'id_usuario': 42}
    storage.guardar_borrador(user, 'General', {'lev_descripcion': 'Primera captura'})
    first = storage.cargar_borrador(user)
    key = first['sincronizacion']['clave_cliente']
    assert first['sincronizacion']['revision'] == 0
    assert storage.confirmar_sincronizacion(user, key, 1, first['guardado_en'])
    storage.guardar_borrador(user, 'General', {'lev_descripcion': 'Segunda captura'})
    second = storage.cargar_borrador(user)
    assert second['sincronizacion']['clave_cliente'] == key
    assert second['sincronizacion']['revision'] == 1
    assert second['sincronizacion']['estado'] == 'pendiente'
    assert storage.confirmar_sincronizacion(user, key, 2, first['guardado_en']) is False
    final = storage.cargar_borrador(user)
    assert final['sincronizacion']['revision'] == 2
    assert final['sincronizacion']['estado'] == 'pendiente' 
