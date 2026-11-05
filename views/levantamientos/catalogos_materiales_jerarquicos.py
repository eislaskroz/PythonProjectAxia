"""Catálogo jerárquico AXIA a partir de PreviewCatálogo.xlsx (5/nov/2026).

El Excel proporciona familia, material, especialidad y unidad. Los tipos y
medidas NO se inventan: se reutilizan los catálogos preexistentes. Para un
material sin desgloses se ofrece «Por definir» hasta su catalogación.

Compatibilidad: el campo serializado ``categoria`` sigue guardando el antiguo
nombre del material, mientras ``familia`` identifica la nueva categoría padre.
"""
from __future__ import annotations

from views.levantamientos.catalogos_canalizacion import (
    TIPOS_TUBOS, TIPOS_COPLES, TIPOS_CAJAS, TIPOS_REGISTROS,
    TIPOS_CONECTORES, TIPOS_ABRAZADERAS, TIPOS_CANALETA,
    TIPOS_CABLE_ELECTRICO, TIPOS_CABLE_DATOS_CONTROL, TIPOS_CABLE_EXTERIOR,
    especificaciones_por_categoria,
)
from views.levantamientos.canalizacion_aproximado import unidad_fija_canalizacion

# Cuatro columnas originales: categoría, material, especialidad/uso y unidad.
CATALOGO_XLSX = [('Conductores y Canalización', 'Tubos', 'Eléctrico / Plomería / Datos', 'Tramo'),
 ('Conductores y Canalización', 'Canaletas', 'Eléctrico / Datos (Superficie)', 'Tramo'),
 ('Conductores y Canalización', 'Cable Eléctrico', 'Instalaciones Eléctricas / Potencia', 'Metro / Rollo'),
 ('Conductores y Canalización', 'Cable UTP (Cat 6 / 6A)', 'Redes de Voz, Datos y CCTV', 'Metro / Bobina'),
 ('Conductores y Canalización', 'Cable Coaxial', 'CCTV / Video analógico', 'Metro / Bobina'),
 ('Conductores y Canalización', 'Fibra Óptica', 'Enlaces de alta velocidad / Datos', 'Metro / Bobina'),
 ('Conductores y Canalización', 'Charofil (Malla) / Escalerrilla', 'Soporte masivo de cables (Redes/Energía)', 'Tramo'),
 ('Conexiones y Uniones', 'Codos', 'Cambio de dirección en tubos', 'Pieza'),
 ('Conexiones y Uniones', 'Coples', 'Unión lineal de tubos', 'Pieza'),
 ('Conexiones y Uniones', 'Conectores', 'Acoplar tubo a cajas de registro', 'Pieza'),
 ('Conexiones y Uniones', 'Plugs RJ45 / RJ11', 'Terminación de cables de red/telefonía', 'Pieza / Bolsa'),
 ('Conexiones y Uniones', 'Jacks y Placas (Faceplates)', 'Nodos terminales de red en pared', 'Pieza'),
 ('Conexiones y Uniones', 'Patch Panels', 'Organización de red en Racks', 'Pieza'),
 ('Conexiones y Uniones', 'Organizadores de Cable', 'Gestión estética de red en gabinetes', 'Pieza'),
 ('Fijación y Soporte', 'Abrazaderas', 'Sujeción de tubos a superficies', 'Pieza / Bolsa'),
 ('Fijación y Soporte', 'Unicanal (Riel)', 'Soporte de equipos (AA/Tableros/Plantas)', 'Tramo'),
 ('Fijación y Soporte', 'Varilla Roscada y Tuercas', 'Colgado de charolas y soportes', 'Pieza'),
 ('Fijación y Soporte', 'Estructuras de Aluminio', 'Montaje e inclinación de Paneles Solares', 'Kit / Tramo'),
 ('Fijación y Soporte', 'Taquetes y Tornillería Variada', 'Fijación general en concreto/tablaestaca', 'Pieza / Caja'),
 ('Cajas y Registros', 'Cajas (Chalupas/Square)', 'Alojamiento de apagadores/contactos/nodos', 'Pieza'),
 ('Cajas y Registros', 'Registros', 'Puntos de jalado, paso o inspección', 'Pieza'),
 ('Cajas y Registros', 'Tapas', 'Sello de protección para cajas/registros', 'Pieza'),
 ('Protección y Potencia', 'Pastillas Termomagnéticas / Fusibles', 'Protección contra sobrecargas y cortos', 'Pieza'),
 ('Protección y Potencia', 'Centros de Carga / Tableros', 'Distribución general de circuitos', 'Pieza'),
 ('Protección y Potencia',
  'Interruptores de Transferencia (ATS)',
  'Conmutación automática Plantas de Energía',
  'Pieza'),
 ('Protección y Potencia', 'Inversores / Combiner Boxes', 'Sistemas de Paneles Solares', 'Pieza'),
 ('Protección y Potencia', 'Varillas de Tierra / Conectores', 'Tierras físicas para equipos delicados', 'Pieza'),
 ('Consumibles y Empalmes',
  'Cinta Aislante / Vulcanizada / Termofit',
  'Aislamiento e impermeabilización de uniones',
  'Pieza / Rollo'),
 ('Consumibles y Empalmes', 'Zapatas Eléctricas / Bornes', 'Conexión de cables de gran calibre', 'Pieza'),
 ('Consumibles y Empalmes',
  'Capuchones / Conectores Wago',
  'Empalmes eléctricos rápidos en registros',
  'Pieza / Bolsa'),
 ('Específicos Aire Acondicionado', 'Tubería de Cobre Flexible', 'Líneas de gas refrigerante', 'Metro / Rollo'),
 ('Específicos Aire Acondicionado', 'Aislamiento Térmico (Armaflex)', 'Forro anticondensación para cobre', 'Tramo'),
 ('Específicos Aire Acondicionado', 'Manguera de Desagüe', 'Evacuación de agua condensada', 'Metro')]
ALIAS_MATERIAL_EXCEL = {'Tubos': 'Tubo',
 'Canaletas': 'Canaleta',
 'Coples': 'Cople',
 'Abrazaderas': 'Abrazadera',
 'Cajas (Chalupas/Square)': 'Cajas',
 'Registros': 'Registro',
 'Patch Panels': 'Patch panel',
 'Jacks y Placas (Faceplates)': 'Jacks y Placas (Faceplates)'}


# Se muestran exactamente las siete categorías de la fuente, sin mezclarlas.
MATERIALES_POR_FAMILIA = {}
DETALLE_MATERIAL = {}
for familia, etiqueta_excel, uso, unidad_excel in CATALOGO_XLSX:
    material = ALIAS_MATERIAL_EXCEL.get(etiqueta_excel, etiqueta_excel)
    MATERIALES_POR_FAMILIA.setdefault(familia, []).append(material)
    DETALLE_MATERIAL[material] = {"uso": uso, "unidad_excel": unidad_excel}

# Mantener los nombres utilizados por registros históricos y opciones anteriores.
MATERIALES_POR_FAMILIA["Conductores y Canalización"].append("Cable")
MATERIALES_POR_FAMILIA["Conexiones y Uniones"].extend(
    ["Jack RJ45", "Plug RJ45", "Faceplate", "Patch cord"]
)
FAMILIA_POR_MATERIAL = {
    material: familia
    for familia, materiales in MATERIALES_POR_FAMILIA.items()
    for material in materiales
}
ALIAS_ANTIGUOS = {"Canalización": "Canaleta", "Conector": "Conectores"}


def normalizar_material(material):
    texto = str(material or "").strip()
    return ALIAS_ANTIGUOS.get(texto, texto)


def familia_de_material(material):
    return FAMILIA_POR_MATERIAL.get(normalizar_material(material), "Conductores y Canalización")


def familias_materiales():
    return list(MATERIALES_POR_FAMILIA)


def materiales_de_familia(familia):
    return list(MATERIALES_POR_FAMILIA.get(familia, ()))


def tipos_de_material(material, especialidad=""):
    material = normalizar_material(material)
    tipos = {
        "Tubo": TIPOS_TUBOS,
        "Canaleta": TIPOS_CANALETA,
        "Cople": TIPOS_COPLES,
        "Cajas": TIPOS_CAJAS,
        "Registro": TIPOS_REGISTROS,
        "Conectores": TIPOS_CONECTORES,
        "Abrazadera": TIPOS_ABRAZADERAS,
        "Codos": ["45°", "90°", "Interior", "Exterior", "Plano"],
        "Tapas": ["Ciega", "Final", "Unión", "Para contacto", "Para datos"],
        "Cable Eléctrico": TIPOS_CABLE_ELECTRICO,
        "Cable Coaxial": ["Coaxial"],
        "Fibra Óptica": ["Fibra óptica", "Fibra óptica exterior"],
        "Cable UTP (Cat 6 / 6A)": ["UTP Cat6", "UTP Cat6A", "UTP Cat6 exterior", "UTP Cat6A exterior"],
        "Charofil (Malla) / Escalerrilla": ["Charofil", "Escalerilla"],
        "Jack RJ45": ["Cat5e", "Cat6", "Cat6A", "Blindado"],
        "Plug RJ45": ["Cat5e", "Cat6", "Cat6A", "Blindado"],
        "Faceplate": ["1 puerto", "2 puertos", "4 puertos", "Caja de superficie"],
        "Patch cord": ["Cat5e - 1 m", "Cat5e - 2 m", "Cat6 - 1 m", "Cat6 - 2 m", "Cat6A", "Fibra óptica"],
        "Patch panel": ["12 puertos Cat6", "24 puertos Cat6", "48 puertos Cat6", "Cat6A", "Fibra óptica"],
    }
    if material == "Cable":
        if especialidad == "Electricidad":
            return list(TIPOS_CABLE_ELECTRICO)
        if especialidad == "Enlaces Inalámbricos":
            return list(dict.fromkeys(TIPOS_CABLE_EXTERIOR + TIPOS_CABLE_ELECTRICO))
        return list(dict.fromkeys(TIPOS_CABLE_DATOS_CONTROL + TIPOS_CABLE_ELECTRICO +
                                  (TIPOS_CABLE_EXTERIOR if especialidad == "General" else [])))
    return list(tipos.get(material, ["Por definir"]))


def especificaciones_de_material(material, tipo=""):
    material = normalizar_material(material)
    if material == "Cable Eléctrico":
        from views.levantamientos.catalogos_canalizacion import CALIBRES_CABLE_ELECTRICO
        return list(CALIBRES_CABLE_ELECTRICO) + ["Por definir"]
    if material in {"Tubo", "Cople", "Registro", "Cajas", "Conectores", "Abrazadera",
                    "Codos", "Canaleta", "Cable"}:
        return especificaciones_por_categoria(material, tipo)
    return ["Por definir", "No aplica"]


def normalizar_seleccion_material(material, tipo_actual, especificacion_actual, tipos_disponibles):
    """Actualiza listas dependientes sin mezclar medidas de materiales distintos."""
    tipos = list(tipos_disponibles)
    tipo = str(tipo_actual or "").strip()
    if tipo not in tipos:
        tipo = tipos[0] if tipos else ""
    especificaciones = especificaciones_de_material(material, tipo)
    especificacion = str(especificacion_actual or "").strip()
    if especificacion not in especificaciones:
        especificacion = ("Por definir" if material == "Canaleta" and "Por definir" in especificaciones
                          else (especificaciones[0] if especificaciones else ""))
    return tipo, especificacion, especificaciones


def uso_de_material(material):
    return DETALLE_MATERIAL.get(normalizar_material(material), {}).get("uso", "")


UNIDADES_DISPONIBLES = [
    "Pieza(s)", "Metro(s)", "Tramo(s)", "Rollo(s)", "Bobina(s)",
    "Bolsa(s)", "Caja(s)", "Kit(s)", "Juego(s)",
]
UNIDAD_POR_TEXTO = {
    "pieza": "Pieza(s)", "metro": "Metro(s)", "tramo": "Tramo(s)",
    "rollo": "Rollo(s)", "bobina": "Bobina(s)", "bolsa": "Bolsa(s)",
    "caja": "Caja(s)", "kit": "Kit(s)", "juego": "Juego(s)",
}


def unidades_de_material(material):
    """Opciones del Excel primero; otras unidades se mantienen para compatibilidad."""
    material = normalizar_material(material)
    if unidad_fija_canalizacion(material):
        return ["Pieza(s)"]
    if material == "Cable":
        return ["Metro(s)", "Rollo(s)"] + [u for u in UNIDADES_DISPONIBLES if u not in {"Metro(s)", "Rollo(s)"}]
    raw = DETALLE_MATERIAL.get(material, {}).get("unidad_excel", "Pieza")
    propuestas = [UNIDAD_POR_TEXTO.get(p.strip().casefold()) for p in raw.split("/")]
    propuestas = [p for p in propuestas if p]
    return list(dict.fromkeys(propuestas + UNIDADES_DISPONIBLES))


def unidad_inicial_material(material):
    return unidades_de_material(material)[0]


def familia_de_partida(partida):
    """Lee nuevas y anteriores sin confundir material con categoría padre."""
    material = normalizar_material(partida.get("material") or partida.get("categoria"))
    familia = partida.get("familia") or familia_de_material(material)
    if material not in materiales_de_familia(familia):
        familia = familia_de_material(material)
    return familia
