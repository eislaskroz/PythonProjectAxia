"""Importador controlado de la Base de Clientes AXIA 2026.

Diseñado para cargar el archivo normalizado incluido en:
    data_importacion_clientes_2026/

Flujo recomendado:
    python tools/importar_clientes_2026.py --preparar
    python tools/importar_clientes_2026.py --aplicar --confirmar CARGAR_CLIENTES_2026

Características de seguridad:
- no escribe nada en modo --preparar;
- crea respaldo JSON de clientes, sucursales y contactos antes de aplicar;
- usa services.clientes_service.crear_cliente(), conservando el cifrado AXIA;
- usa services.sucursales_service para sucursales/contactos;
- evita duplicados por RFC/razón social, nombre de sucursal y datos de contacto;
- no importa contactos de pago automáticamente: quedan en un CSV pendiente;
- genera un reporte detallado de INSERTADO / EXISTENTE / CONFLICTO / ERROR.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "data_importacion_clientes_2026"
OUT_DIR = ROOT / "importacion_clientes_2026_salida"
CONFIRMACION = "CARGAR_CLIENTES_2026"


def texto(v: Any) -> str:
    return str(v or "").strip()


def texto_mayusculas(v: Any) -> str:
    """Normaliza texto de negocio a MAYÚSCULAS antes de persistirlo."""
    return texto(v).upper()


def correo_minusculas(v: Any) -> str:
    """Normaliza correos a minúsculas; es la única excepción de capitalización."""
    return texto(v).lower()


def clave(v: Any) -> str:
    s = unicodedata.normalize("NFKD", texto(v)).encode("ascii", "ignore").decode("ascii").casefold()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def leer_csv(nombre: str) -> list[dict[str, str]]:
    ruta = DATA_DIR / nombre
    if not ruta.is_file():
        raise FileNotFoundError(f"No se encontró {ruta}")
    with ruta.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f, delimiter=";")]


def guardar_json(ruta: Path, contenido: Any) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def guardar_csv(ruta: Path, filas: list[dict[str, Any]]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not filas:
        ruta.write_text("", encoding="utf-8-sig")
        return
    campos: list[str] = []
    for fila in filas:
        for campo in fila:
            if campo not in campos:
                campos.append(campo)
    with ruta.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)


def cargar_fuente():
    return (
        leer_csv("clientes.csv"),
        leer_csv("sucursales.csv"),
        leer_csv("contactos_operativos.csv"),
        leer_csv("contactos_pago_pendientes.csv"),
        leer_csv("incidencias.csv"),
    )


def preparar() -> int:
    clientes, sucursales, contactos, pagos, incidencias = cargar_fuente()
    print("\nAXIA - PREPARACIÓN IMPORTACIÓN CLIENTES 2026")
    print("=" * 52)
    print(f"Clientes normalizados:          {len(clientes)}")
    print(f"Sucursales normalizadas:        {len(sucursales)}")
    print(f"Contactos operativos:           {len(contactos)}")
    print(f"Contactos de pago pendientes:   {len(pagos)}")
    print(f"Incidencias para revisión:      {len(incidencias)}")
    print("\nEste modo NO realizó cambios en Supabase.")
    print("Regla de escritura: textos en MAYÚSCULAS; correos electrónicos en minúsculas.")
    print("Teléfonos, C.P. y valores numéricos se conservan sin transformación de mayúsculas/minúsculas.")
    print("Los contactos de pago NO se importan automáticamente por seguridad de modelo.")
    print(f"Revisa: {DATA_DIR / 'incidencias.csv'}")
    return 0


def _backup_tablas(supabase, tablas: list[str], destino: Path) -> None:
    for tabla in tablas:
        try:
            filas = supabase.table(tabla).select("*").execute().data or []
        except Exception as exc:
            filas = [{"_backup_error": str(exc)}]
        guardar_json(destino / f"{tabla}.json", filas)


def aplicar(confirmacion: str) -> int:
    if confirmacion != CONFIRMACION:
        print("Importación cancelada: falta confirmación explícita.")
        print(f"Usa: --confirmar {CONFIRMACION}")
        return 2

    from core.environment import cargar_entorno
    cargar_entorno()
    from security.data_encryption import validar_configuracion_cifrado
    validar_configuracion_cifrado()
    from supabase_config import (
        supabase, TABLA_CLIENTES, TABLA_SUCURSALES, TABLA_CONTACTOS_SUCURSAL,
    )
    from services.clientes_service import buscar_clientes, crear_cliente
    from services.sucursales_service import (
        obtener_sucursales_por_cliente,
        obtener_contactos_por_sucursal,
        crear_sucursal,
        crear_contacto_sucursal,
    )

    clientes, sucursales, contactos, pagos, incidencias = cargar_fuente()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUT_DIR / marca
    backup_dir = run_dir / "respaldo_antes_de_importar"
    print(f"Creando respaldo en {backup_dir} ...")
    _backup_tablas(supabase, [TABLA_CLIENTES, TABLA_SUCURSALES, TABLA_CONTACTOS_SUCURSAL], backup_dir)

    reporte: list[dict[str, Any]] = []
    existentes = buscar_clientes("", limite=5000)
    por_rfc = {texto(x.get("cli_rfc")).upper(): x for x in existentes if texto(x.get("cli_rfc"))}
    por_razon = {clave(x.get("cli_razonsocial")): x for x in existentes if texto(x.get("cli_razonsocial"))}
    client_ids: dict[str, Any] = {}

    # 1) CLIENTES
    for c in clientes:
        ck = c["client_key"]
        rfc = texto(c.get("cli_rfc")).upper()
        razon = texto(c.get("cli_razonsocial"))
        by_rfc = por_rfc.get(rfc) if rfc and rfc not in {"PENDIENTE", "NA", "N/A"} else None
        by_razon = por_razon.get(clave(razon))
        existente = by_rfc or by_razon
        if by_rfc and by_razon and by_rfc.get("id_cliente") != by_razon.get("id_cliente"):
            reporte.append({"tipo":"CLIENTE","clave":razon,"accion":"CONFLICTO","detalle":"RFC y razón social apuntan a clientes distintos"})
            continue
        if existente:
            client_ids[ck] = existente.get("id_cliente")
            reporte.append({"tipo":"CLIENTE","clave":razon,"accion":"EXISTENTE","id":existente.get("id_cliente"),"detalle":"No se sobrescribió"})
            continue
        # Regla AXIA de capitalización para altas masivas:
        # - texto de negocio en MAYÚSCULAS;
        # - correos electrónicos en minúsculas;
        # - teléfonos, C.P. y otros identificadores numéricos se conservan sin alterar.
        payload = {
            "cli_tipo": texto_mayusculas(c.get("cli_tipo")),
            "cli_estatus": texto_mayusculas(c.get("cli_estatus")),
            "cli_razonsocial": texto_mayusculas(c.get("cli_razonsocial")),
            "cli_rfc": texto_mayusculas(c.get("cli_rfc")),
            "cli_contacto": texto_mayusculas(c.get("cli_contacto")),
            "cli_telefono": texto(c.get("cli_telefono")),
            "cli_correo": correo_minusculas(c.get("cli_correo")),
            "cli_calle": texto_mayusculas(c.get("cli_calle")),
            "cli_numero": texto_mayusculas(c.get("cli_numero")),
            "cli_colonia": texto_mayusculas(c.get("cli_colonia")),
            "cli_municipio": texto_mayusculas(c.get("cli_municipio")),
            "cli_estado": texto_mayusculas(c.get("cli_estado")),
            "cli_cp": texto(c.get("cli_cp")),
            "cli_notas": texto_mayusculas(c.get("cli_notas")),
        }
        ok, msg, nuevo = crear_cliente(payload)
        if ok and nuevo:
            cid = nuevo.get("id_cliente")
            client_ids[ck] = cid
            por_razon[clave(razon)] = nuevo
            if rfc: por_rfc[rfc] = nuevo
            reporte.append({"tipo":"CLIENTE","clave":razon,"accion":"INSERTADO","id":cid,"detalle":msg})
        else:
            reporte.append({"tipo":"CLIENTE","clave":razon,"accion":"ERROR","detalle":msg})

    # 2) SUCURSALES
    suc_ids: dict[tuple[str, str], Any] = {}
    suc_cache: dict[Any, list[dict[str, Any]]] = {}
    for s in sucursales:
        ck = s["client_key"]
        cid = client_ids.get(ck)
        sn = texto(s.get("suc_nombre"))
        if not cid:
            reporte.append({"tipo":"SUCURSAL","clave":sn,"accion":"OMITIDO","detalle":"Cliente padre no disponible"})
            continue
        if cid not in suc_cache:
            suc_cache[cid] = obtener_sucursales_por_cliente(cid, page_size=500) or []
        existentes_s = suc_cache[cid]
        ex = next((x for x in existentes_s if clave(x.get("suc_nombre")) == clave(sn)), None)
        if ex:
            sid = ex.get("suc_id") or ex.get("id_sucursal")
            suc_ids[(ck, clave(sn))] = sid
            reporte.append({"tipo":"SUCURSAL","clave":sn,"accion":"EXISTENTE","id":sid,"detalle":"No se sobrescribió"})
            continue
        payload = {
            "id_cliente": cid,
            "suc_nombre": texto_mayusculas(sn),
            "suc_calle_numero": texto_mayusculas(s.get("suc_calle_numero")),
            "suc_colonia": texto_mayusculas(s.get("suc_colonia")),
            "suc_municipio": texto_mayusculas(s.get("suc_municipio")),
            "suc_estado": texto_mayusculas(s.get("suc_estado")),
            "suc_codigo_postal": texto(s.get("suc_codigo_postal")),
            "suc_telefono": texto(s.get("suc_telefono")),
            "suc_correo": correo_minusculas(s.get("suc_correo")),
            "suc_estatus": 1,
        }
        ok, msg, nueva = crear_sucursal(payload)
        if ok and nueva:
            sid = nueva.get("suc_id") or nueva.get("id_sucursal")
            suc_ids[(ck, clave(sn))] = sid
            suc_cache[cid].append(nueva)
            reporte.append({"tipo":"SUCURSAL","clave":sn,"accion":"INSERTADO","id":sid,"detalle":msg})
        else:
            reporte.append({"tipo":"SUCURSAL","clave":sn,"accion":"ERROR","detalle":msg})

    # 3) CONTACTOS OPERATIVOS
    con_cache: dict[Any, list[dict[str, Any]]] = {}
    for c in contactos:
        ck = c["client_key"]
        sn = texto(c.get("suc_nombre"))
        sid = suc_ids.get((ck, clave(sn)))
        nombre = texto(c.get("con_nombre"))
        if not sid:
            reporte.append({"tipo":"CONTACTO","clave":nombre,"accion":"OMITIDO","detalle":f"Sucursal destino no disponible: {sn}"})
            continue
        if sid not in con_cache:
            con_cache[sid] = obtener_contactos_por_sucursal(sid, page_size=500) or []
        em = texto(c.get("con_correo")).casefold()
        tel = re.sub(r"\D", "", texto(c.get("con_telefono")))
        def mismo(x):
            if clave(x.get("con_nombre")) != clave(nombre): return False
            xem = texto(x.get("con_correo")).casefold()
            xt = re.sub(r"\D", "", texto(x.get("con_telefono")))
            return (em and xem == em) or (tel and xt == tel) or (not em and not tel)
        ex = next((x for x in con_cache[sid] if mismo(x)), None)
        if ex:
            reporte.append({"tipo":"CONTACTO","clave":nombre,"accion":"EXISTENTE","id":ex.get("con_id") or ex.get("id_contacto"),"detalle":sn})
            continue
        payload = {
            "suc_id": sid,
            "con_nombre": texto_mayusculas(nombre),
            "con_puesto": texto_mayusculas(c.get("con_puesto")),
            "con_correo": correo_minusculas(c.get("con_correo")),
            "con_telefono": texto(c.get("con_telefono")),
            "con_estatus": 1,
        }
        ok, msg, nuevo = crear_contacto_sucursal(payload)
        if ok and nuevo:
            con_cache[sid].append(nuevo)
            reporte.append({"tipo":"CONTACTO","clave":nombre,"accion":"INSERTADO","id":nuevo.get("con_id") or nuevo.get("id_contacto"),"detalle":sn})
        else:
            reporte.append({"tipo":"CONTACTO","clave":nombre,"accion":"ERROR","detalle":msg})

    guardar_csv(run_dir / "resultado_importacion.csv", reporte)
    guardar_json(run_dir / "resumen_importacion.json", {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "totales_fuente": {"clientes":len(clientes),"sucursales":len(sucursales),"contactos_operativos":len(contactos)},
        "contactos_pago_no_importados": len(pagos),
        "incidencias_fuente": len(incidencias),
        "acciones": {a: sum(1 for r in reporte if r.get("accion") == a) for a in sorted({r.get("accion") for r in reporte})},
    })
    print("\nImportación finalizada.")
    print(f"Reporte: {run_dir / 'resultado_importacion.csv'}")
    print(f"Resumen: {run_dir / 'resumen_importacion.json'}")
    print(f"Contactos de pago NO importados: {len(pagos)}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Importación segura de la Base de Clientes AXIA 2026")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--preparar", action="store_true", help="Valida y resume sin tocar Supabase")
    g.add_argument("--aplicar", action="store_true", help="Carga clientes/sucursales/contactos operativos")
    p.add_argument("--confirmar", default="", help="Confirmación obligatoria para --aplicar")
    args = p.parse_args()
    if args.preparar:
        return preparar()
    return aplicar(args.confirmar)

if __name__ == "__main__":
    raise SystemExit(main())
