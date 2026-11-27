from core.logger import configurar_logger
from services.desktop_secure_reads import listar

logger = configurar_logger(__name__)


def _texto(valor):
    return str(valor or "").strip().lower()


def _coincide(registro, termino, campos):
    termino = _texto(termino)
    if not termino:
        return True
    return any(termino in _texto(registro.get(campo)) for campo in campos)


def buscar_movimientos_auditoria(termino="", limite=200):
    registros = listar("desktop-audit", "movimientos", max(int(limite or 200), 500))
    campos = ("fecha_hora", "usuario", "modulo", "accion", "descripcion", "registro_afectado", "ip_local", "equipo", "latitud", "longitud", "ciudad", "region", "pais")
    return [r for r in registros if _coincide(r, termino, campos)][:limite]


def buscar_accesos_auditoria(termino="", limite=200):
    registros = listar("desktop-audit", "accesos", max(int(limite or 200), 500))
    campos = ("fecha_hora", "usu_nickname", "estatus", "descripcion", "direccion_ip", "nombre_equipo", "latitud", "longitud", "ciudad", "region", "pais")
    return [r for r in registros if _coincide(r, termino, campos)][:limite]


def resumen_registros(registros, tipo):
    registros = registros or []
    if tipo == "accesos":
        usuarios = len({_texto(r.get("usu_nickname")) for r in registros if r.get("usu_nickname")})
        fallidos = sum(1 for r in registros if _texto(r.get("estatus")) not in {"correcto", "exitoso", "ok"})
        return len(registros), usuarios, fallidos

    usuarios = len({_texto(r.get("usuario")) for r in registros if r.get("usuario")})
    modulos = len({_texto(r.get("modulo")) for r in registros if r.get("modulo")})
    return len(registros), usuarios, modulos