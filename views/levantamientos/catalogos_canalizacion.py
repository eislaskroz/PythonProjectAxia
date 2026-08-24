"""Catálogos homologados para canalización, infraestructura y cableado.

Los valores se conservan con la nomenclatura operativa proporcionada por AXIA.
"""

TIPOS_COPLES = [
    "Opresor", "Compresión", "Roscado", "Combinación", "PVC Rígido",
    "Polietileno", "Ducto Polietileno Alta Densidad",
]

TIPOS_TUBOS = [
    "Pared delgada (EMT)",
    "Conduit metálico de pared intermedia (IMC)",
    "Metálico de pared gruesa (RMC)",
    "Helicoidal metálico",
    "PVC Pesado",
    "Poliducto corrugado (Ligero)",
    "Vorrugado no metálico (ENT)",
    "Liquidtight /Licuatite",
    "Resina termoendurecible reforzada (RTRC)",
]

TAMANOS_TUBOS = [
    '1/2" (13mm)', '3/4" (19mm)', '1" (25mm)', '1 1/4" (32mm)',
    '1 1/2" (38mm)', '2" (51mm)', '2" 1/2" (63mm)',
]

# Compatibilidad con registros/versiones anteriores. Los formularios nuevos usan
# selectores independientes para tipo y tamaño.
TIPOS_TUBOS_CON_TAMANO = [
    f"{tipo} — {tamano}" for tipo in TIPOS_TUBOS for tamano in TAMANOS_TUBOS
]

TIPOS_REGISTROS = [
    "Empotrados o de pared", "Superficiales", "Piso", "Metálicos", "Plástico",
    "Concreto", "Cajas Cuadrados o Rectangulares",
    "Cajas Octagonales (Chalupas u Octagonales)",
    "Cajas Condulets (LB, LL, LR, C, T)", "Cajas Estancas",
]

TIPOS_CONECTORES = [
    "Regletas o clemas de conexión", "Torsión (Capuchones)",
    "Presión o empalme rápido (Wago)", "Anillo y Horquilla", "Pala y Bala",
    "Mecánicos y de compresión (C y H)", "Cilíndricos e impermeables",
]

TIPOS_ABRAZADERAS = [
    "Tipo Omega", "Uña", "Unicanal", "Tipo U", "Tipo P", "Plástico o PVC", "De Clip",
]

TIPOS_CABLE_ELECTRICO = [
    "THW / THHW", "THHN / THWN", "SPT (Cable dúplex)", "SJT (Uso rudo)",
]

CALIBRES_CABLE_ELECTRICO = [
    "14 AWG (Hasta 15A)", "12 AWG (Hasta 20A)",
    "10 AWG (Hasta 30A)", "8 AWG (Hasta 40A)",
    "6 AWG", "4 AWG", "2 AWG", "1/0 AWG", "2/0 AWG",
    "3/0 AWG", "4/0 AWG", "250 AWG", "350 AWG",
]

CATEGORIAS_CON_MEDIDA_TUBO = {"Tubo", "Cople", "Registro", "Conector", "Conectores", "Abrazadera", "Codos"}


def especificaciones_por_categoria(categoria, tipo=""):
    """Devuelve las medidas/calibres válidos para la partida de canalización."""
    categoria = str(categoria or "").strip()
    tipo = str(tipo or "").strip()
    if categoria in CATEGORIAS_CON_MEDIDA_TUBO:
        return list(TAMANOS_TUBOS)
    if categoria == "Cable":
        # Mantiene opciones abiertas para cableado de datos/control, pero expone
        # todos los calibres eléctricos disponibles cuando el levantamiento lo requiere.
        return list(CALIBRES_CABLE_ELECTRICO) + ["No aplica", "Por definir"]
    if categoria in ("Canalización", "Canaleta") and tipo in TIPOS_TUBOS:
        return list(TAMANOS_TUBOS)
    return ["No aplica", "Por definir"]


def normalizar_tipo_canalizacion(tipo):
    """Compatibilidad de lectura con levantamientos guardados con nombres anteriores."""
    aliases = {
        "Policloruro de Vinilo (PVC)": "PVC Pesado",
        "Liquidtight": "Liquidtight /Licuatite",
        "Canalización": "Canaleta",
        "Conector": "Conectores",
    }
    valor = str(tipo or "").strip()
    return aliases.get(valor, valor)


TIPOS_CABLE_DATOS_CONTROL = [
    "UTP Cat5e", "UTP Cat6", "UTP Cat6A", "STP Cat6", "STP Cat6A",
    "Fibra óptica", "Coaxial", "Control 4 hilos", "Control 6 hilos",
] + TIPOS_CABLE_ELECTRICO

TIPOS_CABLE_EXTERIOR = [
    "UTP Cat5e exterior", "UTP Cat6 exterior", "UTP Cat6A exterior",
    "Fibra óptica exterior", "Cable de control exterior",
] + TIPOS_CABLE_ELECTRICO

TIPOS_CANALIZACION = [
    "Canaleta", "Charola", "Charofil", "Escalerilla", "Existente",
] + TIPOS_TUBOS
