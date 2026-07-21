"""Prepara e importa usuarios a Supabase de forma segura.

Uso recomendado desde la raíz del proyecto:
  python tools/importar_usuarios_seguro.py listaoperadores.csv --preparar
  python tools/importar_usuarios_seguro.py listaoperadores.csv --preparar --generar-passwords-temporales
  python tools/importar_usuarios_seguro.py listaoperadores.csv --aplicar --generar-passwords-temporales

La herramienta:
- lee CSV separado por punto y coma;
- valida roles 1..6;
- normaliza fechas DD/MM/AAAA -> AAAA-MM-DD;
- vuelve únicos los nicknames duplicados;
- genera bcrypt para contraseñas;
- cifra campos sensibles con la AXIA_DATA_KEY del .env;
- crea respaldo antes de aplicar;
- actualiza por id_usuario cuando el registro ya existe;
- inserta usuarios nuevos dejando que PostgreSQL genere su identidad;
- verifica el resultado sin intentar sobrescribir columnas GENERATED ALWAYS.

Nunca imprime AXIA_DATA_KEY ni contraseñas en consola.
"""
from __future__ import annotations

from core.logger import configurar_logger

logger = configurar_logger(__name__)

import argparse
import csv
import json
import os
import re
import secrets
import string
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.environment import cargar_entorno
from security.data_encryption import cifrar_diccionario, validar_configuracion_cifrado
from security.passwords import generar_hash_password, validar_fortaleza_password
from security.permissions import TIPOS_VALIDOS

CAMPOS = [
    "id_usuario", "usu_nickname", "usu_password", "usu_nombre", "usu_apellido",
    "usu_rfc", "usu_curp", "usu_imss", "usu_ine", "usu_fechanac", "usu_calle",
    "usu_numero", "usu_colonia", "usu_municipio", "usu_estado", "usu_cp",
    "usu_telefono", "usu_depto", "usu_puesto", "usu_regimen", "created_at",
    "usu_tipo", "usu_correo",
]

CAMPOS_SENSIBLES = [
    "usu_rfc", "usu_curp", "usu_imss", "usu_ine", "usu_fechanac",
    "usu_telefono", "usu_calle", "usu_numero", "usu_colonia",
    "usu_municipio", "usu_estado", "usu_cp", "usu_regimen",
]


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _slug(valor: str) -> str:
    limpio = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]", "", limpio)


def _primer_apellido(apellidos: str) -> str:
    partes = _texto(apellidos).split()
    return partes[0].title() if partes else "Usuario"


def _normalizar_fecha(valor: str) -> str:
    valor = _texto(valor)
    if not valor:
        return ""
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(valor, formato).date().isoformat()
        except ValueError:
            logger.debug("Excepción recuperable controlada.", exc_info=True)
    raise ValueError(f"Fecha inválida: {valor!r}. Usa DD/MM/AAAA o AAAA-MM-DD.")


def _password_temporal(longitud: int = 16) -> str:
    # Garantiza la política mínima y mezcla el resultado.
    chars = string.ascii_letters + string.digits + "!@#$%&*_-+"
    base = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%&*_-+"),
    ]
    base.extend(secrets.choice(chars) for _ in range(longitud - len(base)))
    secrets.SystemRandom().shuffle(base)
    return "".join(base)


def leer_csv(ruta: Path) -> list[dict[str, str]]:
    with ruta.open("r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo, delimiter=";")
        encabezados = lector.fieldnames or []
        faltantes = [campo for campo in CAMPOS if campo not in encabezados]
        if faltantes:
            raise ValueError("Faltan columnas requeridas: " + ", ".join(faltantes))
        return [{campo: _texto(fila.get(campo)) for campo in CAMPOS} for fila in lector]


def normalizar_nicknames(filas: list[dict[str, str]]) -> list[dict[str, str]]:
    conteo: dict[str, int] = {}
    for fila in filas:
        clave = _texto(fila["usu_nickname"]).casefold()
        conteo[clave] = conteo.get(clave, 0) + 1

    usados: set[str] = set()
    cambios: list[dict[str, str]] = []
    for fila in filas:
        original = _texto(fila["usu_nickname"])
        candidato = _slug(original) or "Usuario"
        if conteo.get(original.casefold(), 0) > 1:
            candidato = f"{candidato}{_slug(_primer_apellido(fila['usu_apellido']))}"
        base = candidato
        n = 2
        while candidato.casefold() in usados:
            candidato = f"{base}{n}"
            n += 1
        usados.add(candidato.casefold())
        fila["usu_nickname"] = candidato
        if candidato != original:
            cambios.append({"id_usuario": fila["id_usuario"], "anterior": original, "nuevo": candidato})
    return cambios


def preparar(
    filas: list[dict[str, str]],
    generar_temporales: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[str], list[dict[str, str]]]:
    errores: list[str] = []
    credenciales: list[dict[str, str]] = []
    cambios_nickname = normalizar_nicknames(filas)
    ids: set[int] = set()
    preparados: list[dict[str, Any]] = []

    for numero, fila in enumerate(filas, start=2):
        try:
            id_usuario = int(fila["id_usuario"])
            if id_usuario <= 0 or id_usuario in ids:
                raise ValueError("id_usuario repetido o inválido")
            ids.add(id_usuario)

            usu_tipo = int(fila["usu_tipo"])
            if usu_tipo not in TIPOS_VALIDOS:
                raise ValueError("usu_tipo debe estar entre 1 y 6")

            if not fila["usu_nickname"]:
                raise ValueError("usu_nickname está vacío")
            if not fila["usu_nombre"]:
                raise ValueError("usu_nombre está vacío")
            if not fila["usu_apellido"]:
                raise ValueError("usu_apellido está vacío")

            password = fila["usu_password"]
            valida, motivo = validar_fortaleza_password(password)
            fue_generada = False
            if not valida:
                if not generar_temporales:
                    raise ValueError(
                        f"contraseña débil ({motivo}) Usa --generar-passwords-temporales."
                    )
                password = _password_temporal()
                fue_generada = True

            registro: dict[str, Any] = dict(fila)
            registro["id_usuario"] = id_usuario
            registro["usu_tipo"] = usu_tipo
            registro["usu_fechanac"] = _normalizar_fecha(registro["usu_fechanac"])
            registro["usu_password"] = generar_hash_password(password)
            registro["usu_rfc"] = registro["usu_rfc"].upper()
            registro["usu_curp"] = registro["usu_curp"].upper()
            registro["usu_imss"] = registro["usu_imss"].replace("¨", "").strip()

            # Deja que PostgreSQL use su default cuando created_at viene vacío.
            if not registro.get("created_at"):
                registro.pop("created_at", None)

            registro = cifrar_diccionario(registro, CAMPOS_SENSIBLES)
            preparados.append(registro)

            if fue_generada:
                credenciales.append({
                    "id_usuario": str(id_usuario),
                    "usu_nickname": fila["usu_nickname"],
                    "password_temporal": password,
                    "cambio_obligatorio": "SI",
                })
        except Exception as exc:
            errores.append(f"Fila {numero}, ID {fila.get('id_usuario') or '?'}: {exc}")

    return preparados, credenciales, errores, cambios_nickname


def guardar_csv(ruta: Path, filas: list[dict[str, Any]], campos: list[str] | None = None) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not filas:
        ruta.write_text("", encoding="utf-8")
        return
    campos = campos or list(filas[0].keys())
    with ruta.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos, delimiter=";", extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(filas)


def guardar_json(ruta: Path, contenido: Any) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8")


def aplicar_supabase(preparados: list[dict[str, Any]], salida: Path) -> None:
    """Aplica la importación respetando columnas IDENTITY GENERATED ALWAYS.

    Estrategia:
    - si el id_usuario del CSV ya existe, actualiza ese registro sin enviar el ID;
    - si no existe, intenta localizarlo por nickname normalizado;
    - si tampoco existe, inserta el registro sin id_usuario y deja que PostgreSQL
      asigne la identidad automáticamente.

    Esto evita el error PostgreSQL 428C9 y conserva la capacidad de actualizar
    una tabla que ya contenga parte de los usuarios.
    """
    from supabase_config import supabase, TABLA_USUARIOS

    print("Creando respaldo de db_usuarios...")
    existentes = supabase.table(TABLA_USUARIOS).select("*").execute().data or []
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    respaldo = salida / f"respaldo_db_usuarios_{marca}.json"
    guardar_json(respaldo, existentes)

    por_id = {int(r["id_usuario"]): r for r in existentes if r.get("id_usuario") is not None}
    por_nickname = {
        str(r.get("usu_nickname") or "").strip().casefold(): r
        for r in existentes
        if str(r.get("usu_nickname") or "").strip()
    }

    ids_resultantes: list[int] = []
    acciones: list[dict[str, Any]] = []

    for numero, registro_preparado in enumerate(preparados, start=1):
        registro = dict(registro_preparado)
        id_origen = int(registro.pop("id_usuario"))
        nickname = str(registro.get("usu_nickname") or "").strip()

        existente = por_id.get(id_origen)
        criterio = "id_usuario"
        if existente is None:
            existente = por_nickname.get(nickname.casefold())
            criterio = "usu_nickname"

        try:
            if existente is not None:
                id_destino = int(existente["id_usuario"])
                respuesta = (
                    supabase.table(TABLA_USUARIOS)
                    .update(registro)
                    .eq("id_usuario", id_destino)
                    .execute()
                )
                if not (respuesta.data or []):
                    raise RuntimeError("Supabase no confirmó la actualización.")
                accion = "actualizado"
            else:
                respuesta = supabase.table(TABLA_USUARIOS).insert(registro).execute()
                datos = respuesta.data or []
                if not datos or datos[0].get("id_usuario") is None:
                    raise RuntimeError("Supabase no devolvió el ID generado para el usuario nuevo.")
                id_destino = int(datos[0]["id_usuario"])
                accion = "insertado"

            ids_resultantes.append(id_destino)
            acciones.append({
                "fila": numero,
                "id_csv": id_origen,
                "id_supabase": id_destino,
                "usu_nickname": nickname,
                "accion": accion,
                "coincidencia": criterio if existente is not None else "nuevo",
            })
        except Exception as exc:
            guardar_json(salida / f"resultado_parcial_{marca}.json", acciones)
            raise RuntimeError(
                f"Falló la fila {numero} ({nickname!r}, ID CSV {id_origen}): {exc}. "
                f"El respaldo está en {respaldo}."
            ) from exc

    verificados: list[dict[str, Any]] = []
    for inicio in range(0, len(ids_resultantes), 25):
        bloque = ids_resultantes[inicio:inicio + 25]
        datos = (
            supabase.table(TABLA_USUARIOS)
            .select("id_usuario,usu_nickname,usu_tipo,usu_password")
            .in_("id_usuario", bloque)
            .execute()
            .data or []
        )
        verificados.extend(datos)

    if len(verificados) != len(set(ids_resultantes)):
        raise RuntimeError(
            f"Verificación incompleta: esperados {len(set(ids_resultantes))}, "
            f"encontrados {len(verificados)}. El respaldo está en {respaldo}."
        )

    hashes_invalidos = [
        r["id_usuario"] for r in verificados
        if not str(r.get("usu_password", "")).startswith(("$2a$", "$2b$", "$2y$"))
    ]
    if hashes_invalidos:
        raise RuntimeError(f"Contraseñas sin bcrypt después de importar: {hashes_invalidos}")

    guardar_json(salida / f"resultado_importacion_{marca}.json", acciones)
    insertados = sum(1 for a in acciones if a["accion"] == "insertado")
    actualizados = sum(1 for a in acciones if a["accion"] == "actualizado")
    print(f"Importación verificada: {len(verificados)} usuarios únicos.")
    print(f"Actualizados: {actualizados} | Insertados: {insertados}")
    print(f"Respaldo local: {respaldo}")
    print(f"Relación ID CSV / ID Supabase: {salida / f'resultado_importacion_{marca}.json'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Importación segura de db_usuarios para AXIA")
    parser.add_argument("csv", type=Path, help="Ruta de listaoperadores.csv")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--preparar", action="store_true", help="Genera archivos sin modificar Supabase")
    grupo.add_argument("--aplicar", action="store_true", help="Prepara y ejecuta UPSERT en Supabase")
    parser.add_argument(
        "--generar-passwords-temporales",
        action="store_true",
        help="Reemplaza únicamente contraseñas que incumplen la política por claves fuertes aleatorias",
    )
    parser.add_argument("--si", action="store_true", help="Confirma la importación sin pregunta interactiva")
    parser.add_argument("--salida", type=Path, default=ROOT / "importacion_usuarios" / "salida")
    args = parser.parse_args()

    cargar_entorno()
    validar_configuracion_cifrado()

    if not args.csv.exists():
        print(f"ERROR: No existe {args.csv}", file=sys.stderr)
        return 2

    filas = leer_csv(args.csv)
    preparados, credenciales, errores, cambios = preparar(filas, args.generar_passwords_temporales)

    args.salida.mkdir(parents=True, exist_ok=True)
    guardar_json(args.salida / "usuarios_preparados_seguros.json", preparados)
    guardar_json(args.salida / "cambios_nickname.json", cambios)

    if credenciales:
        cred_path = args.salida / "CREDENCIALES_TEMPORALES_ELIMINAR_DESPUES.csv"
        guardar_csv(cred_path, credenciales, ["id_usuario", "usu_nickname", "password_temporal", "cambio_obligatorio"])
        try:
            os.chmod(cred_path, 0o600)
        except OSError:
            logger.debug("Excepción recuperable controlada.", exc_info=True)

    reporte = {
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "archivo_origen": str(args.csv.resolve()),
        "filas_leidas": len(filas),
        "filas_preparadas": len(preparados),
        "errores": errores,
        "nicknames_modificados": cambios,
        "passwords_temporales_generados": len(credenciales),
        "nota": "El archivo JSON contiene hashes bcrypt y campos cifrados; no contiene contraseñas legibles.",
    }
    guardar_json(args.salida / "reporte_validacion_usuarios.json", reporte)

    print(f"Leídos: {len(filas)} | Preparados: {len(preparados)} | Errores: {len(errores)}")
    if cambios:
        print(f"Nicknames ajustados para unicidad: {len(cambios)}")
    if credenciales:
        print(f"Contraseñas temporales generadas: {len(credenciales)}")
        print("IMPORTANTE: entrega ese archivo por un canal seguro y elimínalo después.")

    if errores:
        print("\nNo se modificó Supabase. Corrige los errores:", file=sys.stderr)
        for error in errores:
            print(f"- {error}", file=sys.stderr)
        return 3

    if args.preparar:
        print(f"Preparación terminada. Archivos en: {args.salida}")
        return 0

    if not args.si:
        confirmacion = input(
            f"Se hará UPSERT de {len(preparados)} usuarios en db_usuarios. "
            "Se creará un respaldo antes. Escribe IMPORTAR para continuar: "
        )
        if confirmacion.strip() != "IMPORTAR":
            print("Operación cancelada; Supabase no fue modificado.")
            return 1

    aplicar_supabase(preparados, args.salida)
    print("Importación segura completada.")
    print("Ejecuta migrations/sincronizar_secuencia_db_usuarios.sql en el SQL Editor de Supabase.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
