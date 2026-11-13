"""Catálogo maestro de canalización y materiales, noviembre 2026.

Fuente: «Catálogo de Materiales Noviembre 2026.xlsx», hoja NOV2026,
261 combinaciones explícitas Categoría/Material/Tipo. Las capturas nuevas
utilizan este listado como lista cerrada; las opciones retiradas no reaparecen.

El Excel NO contiene columnas de tamaño, unidad ni uso. Esas listas se
conservan de las reglas anteriores donde existen; los materiales sin regla
particular usan «Por definir» para especificación y Pieza(s) por defecto.
Los registros históricos no se eliminan de Supabase.

ATENCIÓN: se respeta la denominación literal «Específicos Aire Acondirionado»
que figura en el Excel proporcionado; ajustar primero la fuente si se desea
corregirla para una publicación posterior.
"""
from __future__ import annotations

from views.levantamientos.catalogos_canalizacion import (
    CALIBRES_CABLE_ELECTRICO, especificaciones_por_categoria,
)
from views.levantamientos.canalizacion_aproximado import unidad_fija_canalizacion, tubo_por_metro

CATALOGO_NOVIEMBRE_2026 = {'Conexiones y Uniones': {'Faceplate': ['1 puerto', '2 puertos', '4 puertos', 'Caja de superficie'],
                          'Patch panel': ['12 puertos Cat6',
                                          '24 puertos Cat6',
                                          '48 puertos Cat6',
                                          'Cat6A',
                                          'Fibra óptica'],
                          'Codos': ['45"', '90"', 'Exterior', 'Interior', 'Plano'],
                          'Conectores': ['Anillo y Horquilla',
                                         'Cilíndricos e impermeables',
                                         'Conduit galvanizado',
                                         'Conduit PVC',
                                         'Conector ZAPA',
                                         'Liquidtight / Licuatite',
                                         'Mecánicos y de compresión (C y H)',
                                         'Pala y Bala',
                                         'Presión o empalme rápido (Wago)',
                                         'Regletas o clemas de conexión',
                                         'Torsión (Capuchones)'],
                          'Organizadores de Cable': ['Bandejas y redes de gestión (bajo escritorio)',
                                                     'Cajas organizadoras de cables',
                                                     'Canaletas o cubre-cables',
                                                     'Cinchos y bridas (de plástico o velcro)',
                                                     'Clips y soportes adhesivos',
                                                     'Tubos o mangas flexibles (espirales y de neopreno)'],
                          'Jack RJ45': ['Blindado', 'Cat5e', 'Cat6', 'Cat6A'],
                          'Plug RJ45': ['Blindado', 'Cat5e', 'Cat6', 'Cat6A'],
                          'Patch cord': ['Cat5e - 1 m',
                                         'Cat5e - 2 m',
                                         'Cat6 - 1 m',
                                         'Cat6 - 2 m',
                                         'Cat6A',
                                         'Fibra óptica'],
                          'Cople': ['Combinación',
                                    'Compresión',
                                    'Conduit',
                                    'Confuit Galvanizado',
                                    'Counduit PD',
                                    'Counduit PG',
                                    'Ducto Polietileno Alta Densidad',
                                    'Opresor',
                                    'Polietileno',
                                    'PVC Rígido',
                                    'Roscado'],
                          'Plugs RJ': ['RJ10 / RJ22 (4P2C / 4P4C)',
                                       'RJ11 (6P2C / 6P4C)',
                                       'RJ12 (6P6C)',
                                       'RJ14 (6P4C con dos líneas)',
                                       'RJ25 (6P6C con tres líneas)',
                                       'RJ61 (8P4C)']},
 'Consumibles y Empalmes': {'Capuchones / Conectores': ['Amarillo',
                                                        'Azul / P2',
                                                        'Gris / P1',
                                                        'Naranja / P3',
                                                        'Rojo / P5'],
                            'Cinta Aislante / Vulcanizada': ['Cinta de vinilo (PVC)',
                                                             'Cinta de goma / caucho',
                                                             'Cinta de tela (o algodón / acetato',
                                                             'Cinta de mástique (masilla)',
                                                             'Cinta de tela de vidrio / barnizada '
                                                             '(batista)',
                                                             'Cinta líquida'],
                            'Zapatas Eléctricas': ['Zapatas de compresión (mecánicas o hidráulicas)',
                                                   'Zapatas mecánicas (o de tornillo)',
                                                   'Tipo Anillo (Ojo)',
                                                   'Tipo Horquilla (Herradura o Espada)',
                                                   'Tipo Recta / Punta (Pin)',
                                                   'De Cobre (Electrolítico / Estañado)',
                                                   'De Aluminio (o Bimetálicas)',
                                                   'De Bronce o Aleaciones especiales']},
 'Conductores y Canalización': {'Cable': ['Cable de control exterior',
                                          'Coaxial',
                                          'Control 4 hilos',
                                          'Control 6 hilos',
                                          'Fibra óptica',
                                          'Fibra óptica exterior',
                                          'SJT (Uso rudo)',
                                          'SPT (Cable dúplex)',
                                          'THHN / THWN',
                                          'THW / THHW',
                                          'UTP Cat5e',
                                          'UTP Cat5e exterior',
                                          'UTP Cat6',
                                          'UTP Cat6 exterior',
                                          'UTP Cat6A',
                                          'UTP Cat6A exterior'],
                                'Canaleta': ['Canaleta de piso',
                                             'Canaleta metálica',
                                             'Canaleta PVC',
                                             'Canaleta PVC autoadherible',
                                             'Canaleta ranurada'],
                                'Charofil (Malla) / Escalerilla': ['Charofil', 'Escalerilla'],
                                'Cable Coaxial': ['Coaxial'],
                                'Tubo': ['Conduit metálico de pared intermedia',
                                         'Corrugado no metálico (ENT)',
                                         'Helicoidal metálico / Flexible ZAPA',
                                         'Liquidtight / Licuatite',
                                         'Metálico de pared gruesa (RMC)',
                                         'Pared delgada (EMT)',
                                         'Poliducto corrugado (Ligero)',
                                         'PVC Pesado',
                                         'Resina termoendurecible reforzada'],
                                'Fibra Óptica': ['Fibra óptica', 'Fibra óptica exterior'],
                                'Cable Eléctrico': ['SJT (Uso rudo)',
                                                    'SPT (Cable dúplex)',
                                                    'THHN / THHW',
                                                    'THW / THHW'],
                                'Cable UTP (Cat 6 / 6A )': ['UTP Cat6',
                                                            'UTP Cat6 exterior',
                                                            'UTP Cat6A',
                                                            'UTP Cat6A exterior']},
 'Cajas y Registros': {'Registro': ['Cajas Condulets (LB, LL, LR, C, T)',
                                    'Cajas Cuadradas o Rectangulares',
                                    'Cajas Estancas',
                                    'Cajas Octagonales (Chalupas u Octagonales)',
                                    'Concreto',
                                    'Empotrados o de pared',
                                    'Metálicos',
                                    'Piso',
                                    'Plástico',
                                    'Superficiales'],
                       'Tapas': ['Ciega', 'Final', 'Para contacto', 'Para datos', 'Unión'],
                       'Cajas': ['Cuadradas',
                                 'FD',
                                 'FS',
                                 'FSC',
                                 'FSCC',
                                 'FSCD',
                                 'FSL',
                                 'FSR',
                                 'FSS',
                                 'FST',
                                 'Octagonales',
                                 'Rectangulares',
                                 'Tipo C',
                                 'Tipo L',
                                 'Tipo X']},
 'Fijación y Soporte': {'Abrazadera': ['De Clip',
                                       'Para Viga',
                                       'Plástico o PVC',
                                       'Tipo Omega',
                                       'Tipo P',
                                       'Tipo U',
                                       'Unicanal',
                                       'Uña'],
                        'Estructuras de Aluminio': ['Perfiles cuadrados',
                                                    'Perfiles rectangulares',
                                                    'Perfiles con formas especiales (U, L, T, planos y '
                                                    'tubulares)'],
                        'Taquetes y Tornillería Variada': ['De expansión (plástico o nylon)',
                                                           'Anti-giro / Con aletas',
                                                           'Para Tablaroca o superficies hueca',
                                                           'Metálicos o de expansión pesada',
                                                           'De impacto o golpe',
                                                           'Químicos',
                                                           'Pijas para madera / aglomerado',
                                                           'Pijas autorroscantes / autoperforantes',
                                                           'Tornillos métricos',
                                                           'Tornillos para Tablaroca'],
                        'Unicanal (Riel)': ['Sólido (Liso)',
                                            'Perforado',
                                            'Doble ranura (Unión de dos rieles)'],
                        'Varilla Roscada': ['Varilla roscada galvanizada',
                                            'Varilla roscada de acero inoxidable',
                                            'Varilla roscada de cobre o bronce',
                                            'Varilla roscada de nailon']},
 'Específicos Aire Acondirionado': {'Aislamiento Térmico': ['Poliestireno expandido (EPS / Porexpan)',
                                                            'Poliestireno extruido (XPS)',
                                                            'Espuma de poliuretano',
                                                            'Lana de roca',
                                                            'Lana de vidrio (o fibra de vidrio)',
                                                            'Corcho',
                                                            'Celulosa',
                                                            'Lana de oveja, cármano, lino o paja'],
                                    'Manguera de Desagüe': ['Mangueras corrugadas',
                                                            'Mangueras lisas',
                                                            'Mangueras reforzadas',
                                                            'PVC (Policloruro de vinilo)',
                                                            'Polipropileno (PP)',
                                                            'Caucho o hule termoplástico',
                                                            'Para lavadora automática',
                                                            'Extensiones de desagüe',
                                                            'Para fregaderos, lavabos o lavavajillas'],
                                    'Tubería de Cobre Flexible': ['Tubo de Cobre Tipo K',
                                                                  'Tubo de Cobre Tipo L',
                                                                  'Tubo de Cobre Tipo M',
                                                                  'Tubo de Cobre ACR',
                                                                  'Tubo de Cobre para Gas']},
 'Protección y Potencia': {'Apagadores': ['Apagador sencillo (1 vía)', 'Apagador de escalera (3 vías)', 'Apagador de paso (4 vías)', 'Pulsador (timbre)', 'Atenuador (dimmer)'],
                           'Contactos': ['Contacto sencillo o dúplex (NEMA 1-15)', 'Contacto dúplex aterrizado (NEMA 5-15 / 2P+T)', 'Contacto de 20 Amperes (NEMA 5-20)', 'Contacto GFCI (falla a tierra)', 'Contacto con puertos USB'],
                           'Centros de Carga / Tableros': ['Tablero de alumbrado',
                                                           'Tablero de fuerza',
                                                           'Tablero mixto',
                                                           'Monofásico',
                                                           'Bifásicos',
                                                           'Trifásicos',
                                                           'De empotrar',
                                                           'De sobreponer',
                                                           'Con zapata principal',
                                                           'Con interruptor principal',
                                                           'NEMA 1',
                                                           'NEMA 3R / IP65 o superior'],
                           'Interruptores de Transferencia': ['Manuales',
                                                              'Automáticos (ATS)',
                                                              'Transición abierta',
                                                              'Transición cerrada',
                                                              'Transición de carga suave',
                                                              'Clase PC',
                                                              'Bipolares',
                                                              'Tripolares / Tetrapolares',
                                                              'Baja tensión',
                                                              'Media tensión'],
                           'Inversores': ['Onda sinusoidal pura',
                                          'Onda sinusoidal modificada',
                                          'Onda cuadrada',
                                          'Inversores interconectados',
                                          'Inversores aislados',
                                          'Inversores híbridos',
                                          'Inversores de cadena',
                                          'Microinversores'],
                           'Pastillas Termomagnéticas': ['Monopolares (1 Polo / 1P)',
                                                         'Bipolares (2 Polos / 2P)',
                                                         'Tripolares (3 Polos / 3P)',
                                                         'Tetrapolares (4 Polos / 4P)',
                                                         'Riel DIN',
                                                         'Tipo QO',
                                                         'Caja moldeada',
                                                         'Curva B',
                                                         'Curva C',
                                                         'Curva D',
                                                         'Tipo GF',
                                                         'Tipo AFCI'],
                           'Varillas de Tierra': ['Varilla cobrizada (Copperweld)',
                                                  'Varilla de cobre puro',
                                                  'Varilla de acero inoxidable',
                                                  'Varillas roscadas y modulares',
                                                  'Varillas químicas']}}

CATALOGO_XLSX = [
    (familia, material, tipo)
    for familia, materiales in CATALOGO_NOVIEMBRE_2026.items()
    for material, tipos in materiales.items()
    for tipo in tipos
]

MATERIALES_HISTORICOS_POR_FAMILIA = {'Conductores y Canalización': ['Tubo',
                                'Canaleta',
                                'Cable Eléctrico',
                                'Cable UTP (Cat 6 / 6A)',
                                'Cable Coaxial',
                                'Fibra Óptica',
                                'Charofil (Malla) / Escalerrilla',
                                'Cable'],
 'Conexiones y Uniones': ['Codos',
                          'Cople',
                          'Conectores',
                          'Plugs RJ45 / RJ11',
                          'Jacks y Placas (Faceplates)',
                          'Patch panel',
                          'Organizadores de Cable',
                          'Jack RJ45',
                          'Plug RJ45',
                          'Faceplate',
                          'Patch cord'],
 'Fijación y Soporte': ['Abrazadera',
                        'Unicanal (Riel)',
                        'Varilla Roscada y Tuercas',
                        'Estructuras de Aluminio',
                        'Taquetes y Tornillería Variada'],
 'Cajas y Registros': ['Cajas', 'Registro', 'Tapas'],
 'Protección y Potencia': ['Pastillas Termomagnéticas / Fusibles',
                           'Centros de Carga / Tableros',
                           'Interruptores de Transferencia (ATS)',
                           'Inversores / Combiner Boxes',
                           'Varillas de Tierra / Conectores'],
 'Consumibles y Empalmes': ['Cinta Aislante / Vulcanizada / Termofit',
                            'Zapatas Eléctricas / Bornes',
                            'Capuchones / Conectores Wago'],
 'Específicos Aire Acondicionado': ['Tubería de Cobre Flexible',
                                    'Aislamiento Térmico (Armaflex)',
                                    'Manguera de Desagüe']}

DETALLE_MATERIAL_HISTORICO = {'Tubo': {'uso': 'Eléctrico / Plomería / Datos', 'unidad_excel': 'Tramo'},
 'Canaleta': {'uso': 'Eléctrico / Datos (Superficie)', 'unidad_excel': 'Tramo'},
 'Cable Eléctrico': {'uso': 'Instalaciones Eléctricas / Potencia', 'unidad_excel': 'Metro / Rollo'},
 'Cable UTP (Cat 6 / 6A)': {'uso': 'Redes de Voz, Datos y CCTV', 'unidad_excel': 'Metro / Bobina'},
 'Cable Coaxial': {'uso': 'CCTV / Video analógico', 'unidad_excel': 'Metro / Bobina'},
 'Fibra Óptica': {'uso': 'Enlaces de alta velocidad / Datos', 'unidad_excel': 'Metro / Bobina'},
 'Charofil (Malla) / Escalerrilla': {'uso': 'Soporte masivo de cables (Redes/Energía)',
                                     'unidad_excel': 'Tramo'},
 'Codos': {'uso': 'Cambio de dirección en tubos', 'unidad_excel': 'Pieza'},
 'Cople': {'uso': 'Unión lineal de tubos', 'unidad_excel': 'Pieza'},
 'Conectores': {'uso': 'Acoplar tubo a cajas de registro', 'unidad_excel': 'Pieza'},
 'Plugs RJ45 / RJ11': {'uso': 'Terminación de cables de red/telefonía', 'unidad_excel': 'Pieza / Bolsa'},
 'Jacks y Placas (Faceplates)': {'uso': 'Nodos terminales de red en pared', 'unidad_excel': 'Pieza'},
 'Patch panel': {'uso': 'Organización de red en Racks', 'unidad_excel': 'Pieza'},
 'Organizadores de Cable': {'uso': 'Gestión estética de red en gabinetes', 'unidad_excel': 'Pieza'},
 'Abrazadera': {'uso': 'Sujeción de tubos a superficies', 'unidad_excel': 'Pieza / Bolsa'},
 'Unicanal (Riel)': {'uso': 'Soporte de equipos (AA/Tableros/Plantas)', 'unidad_excel': 'Tramo'},
 'Varilla Roscada y Tuercas': {'uso': 'Colgado de charolas y soportes', 'unidad_excel': 'Pieza'},
 'Estructuras de Aluminio': {'uso': 'Montaje e inclinación de Paneles Solares',
                             'unidad_excel': 'Kit / Tramo'},
 'Taquetes y Tornillería Variada': {'uso': 'Fijación general en concreto/tablaestaca',
                                    'unidad_excel': 'Pieza / Caja'},
 'Cajas': {'uso': 'Alojamiento de apagadores/contactos/nodos', 'unidad_excel': 'Pieza'},
 'Registro': {'uso': 'Puntos de jalado, paso o inspección', 'unidad_excel': 'Pieza'},
 'Tapas': {'uso': 'Sello de protección para cajas/registros', 'unidad_excel': 'Pieza'},
 'Pastillas Termomagnéticas / Fusibles': {'uso': 'Protección contra sobrecargas y cortos',
                                          'unidad_excel': 'Pieza'},
 'Centros de Carga / Tableros': {'uso': 'Distribución general de circuitos', 'unidad_excel': 'Pieza'},
 'Interruptores de Transferencia (ATS)': {'uso': 'Conmutación automática Plantas de Energía',
                                          'unidad_excel': 'Pieza'},
 'Inversores / Combiner Boxes': {'uso': 'Sistemas de Paneles Solares', 'unidad_excel': 'Pieza'},
 'Varillas de Tierra / Conectores': {'uso': 'Tierras físicas para equipos delicados',
                                     'unidad_excel': 'Pieza'},
 'Cinta Aislante / Vulcanizada / Termofit': {'uso': 'Aislamiento e impermeabilización de uniones',
                                             'unidad_excel': 'Pieza / Rollo'},
 'Zapatas Eléctricas / Bornes': {'uso': 'Conexión de cables de gran calibre', 'unidad_excel': 'Pieza'},
 'Capuchones / Conectores Wago': {'uso': 'Empalmes eléctricos rápidos en registros',
                                  'unidad_excel': 'Pieza / Bolsa'},
 'Tubería de Cobre Flexible': {'uso': 'Líneas de gas refrigerante', 'unidad_excel': 'Metro / Rollo'},
 'Aislamiento Térmico (Armaflex)': {'uso': 'Forro anticondensación para cobre', 'unidad_excel': 'Tramo'},
 'Manguera de Desagüe': {'uso': 'Evacuación de agua condensada', 'unidad_excel': 'Metro'}}

ALIAS_MATERIAL_HISTORICO = {'Canalización': 'Canaleta',
 'Conector': 'Conectores',
 'Tubos': 'Tubo',
 'Canaletas': 'Canaleta',
 'Coples': 'Cople',
 'Registros': 'Registro',
 'Abrazaderas': 'Abrazadera',
 'Patch Panels': 'Patch panel',
 'Cajas (Chalupas/Square)': 'Cajas'}

EQUIVALENCIA_UNIDAD_LEGADA = {'Cable UTP (Cat 6 / 6A )': 'Cable UTP (Cat 6 / 6A)',
 'Charofil (Malla) / Escalerilla': 'Charofil (Malla) / Escalerrilla',
 'Plugs RJ': 'Plugs RJ45 / RJ11',
 'Capuchones / Conectores': 'Capuchones / Conectores Wago',
 'Cinta Aislante / Vulcanizada': 'Cinta Aislante / Vulcanizada / Termofit',
 'Zapatas Eléctricas': 'Zapatas Eléctricas / Bornes',
 'Aislamiento Térmico': 'Aislamiento Térmico (Armaflex)',
 'Varilla Roscada': 'Varilla Roscada y Tuercas',
 'Interruptores de Transferencia': 'Interruptores de Transferencia (ATS)',
 'Inversores': 'Inversores / Combiner Boxes',
 'Pastillas Termomagnéticas': 'Pastillas Termomagnéticas / Fusibles',
 'Varillas de Tierra': 'Varillas de Tierra / Conectores'}

MATERIALES_POR_FAMILIA = {
    familia: list(materiales)
    for familia, materiales in CATALOGO_NOVIEMBRE_2026.items()
}
FAMILIA_POR_MATERIAL = {
    material: familia
    for familia, materiales in MATERIALES_POR_FAMILIA.items()
    for material in materiales
}
FAMILIA_HISTORICA_POR_MATERIAL = {
    material: familia
    for familia, materiales in MATERIALES_HISTORICOS_POR_FAMILIA.items()
    for material in materiales
}
DETALLE_MATERIAL = dict(DETALLE_MATERIAL_HISTORICO)
for _actual, _anterior in EQUIVALENCIA_UNIDAD_LEGADA.items():
    if _anterior in DETALLE_MATERIAL_HISTORICO:
        DETALLE_MATERIAL[_actual] = DETALLE_MATERIAL_HISTORICO[_anterior].copy()


def normalizar_material(material):
    """Normalizar identificadores legados del mismo material (sin reactivar bajas)."""
    valor = str(material or "").strip()
    return ALIAS_MATERIAL_HISTORICO.get(valor, valor)


def familia_de_material(material):
    valor = normalizar_material(material)
    return (FAMILIA_POR_MATERIAL.get(valor)
            or FAMILIA_HISTORICA_POR_MATERIAL.get(valor)
            or "Conductores y Canalización")


def familias_materiales():
    """Solo las familias vigentes del Excel."""
    return list(MATERIALES_POR_FAMILIA)


def materiales_de_familia(familia):
    """Solo materiales vigentes: no reintroduce los retirados en nuevos LEV."""
    return list(MATERIALES_POR_FAMILIA.get(familia, ()))


def tipos_de_material(material, especialidad=""):
    """Solo tipos expresamente incluidos en el Excel de noviembre 2026.

    Los tipos históricos se agregan de forma local en el editor al abrir
    registros antiguos; nunca se incluyen en el catálogo de nueva captura.
    """
    material = normalizar_material(material)
    familia = FAMILIA_POR_MATERIAL.get(material)
    if familia:
        return list(CATALOGO_NOVIEMBRE_2026[familia][material])
    return []


def especificaciones_de_material(material, tipo=""):
    """El Excel no incluye calibres: conservar medidas verificadas existentes."""
    material = normalizar_material(material)
    if material == "Cable Eléctrico":
        return list(CALIBRES_CABLE_ELECTRICO) + ["Por definir"]
    if material in {"Tubo", "Cople", "Registro", "Cajas", "Conectores",
                    "Abrazadera", "Codos", "Canaleta", "Cable"}:
        return especificaciones_por_categoria(material, tipo)
    return ["Por definir", "No aplica"]


def normalizar_seleccion_material(material, tipo_actual, especificacion_actual, tipos_disponibles):
    """Actualiza tipo/tamaño dependientes sin mezclar dimensiones de otros materiales."""
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


def unidades_de_material(material, tipo=""):
    material = normalizar_material(material)
    if tubo_por_metro(material, tipo):
        return ["Metro(s)"]
    if unidad_fija_canalizacion(material, tipo):
        return ["Pieza(s)"]
    if material == "Cable":
        return ["Metro(s)", "Rollo(s)"] + [u for u in UNIDADES_DISPONIBLES if u not in {"Metro(s)", "Rollo(s)"}]
    raw = DETALLE_MATERIAL.get(material, {}).get("unidad_excel", "Pieza")
    propuestas = [UNIDAD_POR_TEXTO.get(p.strip().casefold()) for p in raw.split("/")]
    propuestas = [p for p in propuestas if p]
    return list(dict.fromkeys(propuestas + UNIDADES_DISPONIBLES))


def unidad_inicial_material(material, tipo=""):
    return unidades_de_material(material, tipo)[0]


def familia_de_partida(partida):
    """Mantener la familia original en registros legados, aunque ya no esté vigente."""
    material = normalizar_material(partida.get("material") or partida.get("categoria"))
    familia = str(partida.get("familia") or "").strip()
    if familia:
        return familia
    return familia_de_material(material)
