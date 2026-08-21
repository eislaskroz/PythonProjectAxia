"""Catálogo común de herramientas operativas AXIA para levantamientos.

El catálogo es deliberadamente transversal: el técnico puede seleccionar
herramientas de cualquier especialidad cuando el alcance real del servicio lo
requiera. No representa inventario ni disponibilidad de almacén.
"""
from __future__ import annotations

CATALOGO_HERRAMIENTAS = {
    "General": [
        "Flexómetro / cinta métrica", "Nivel de burbuja", "Nivel láser", "Linterna",
        "Escalera de tijera", "Escalera de extensión", "Andamio", "Juego de desarmadores",
        "Juego de llaves combinadas", "Juego de dados y matraca", "Llave ajustable",
        "Pinzas universales", "Pinzas de punta", "Pinzas de corte", "Martillo",
        "Taladro / rotomartillo", "Atornillador inalámbrico", "Brocas y puntas",
        "Aspiradora / sopladora", "Extensión eléctrica", "Generador portátil de apoyo",
        "Etiquetadora", "Cámara / teléfono para evidencia", "Laptop de servicio",
    ],
    "Electricidad": [
        "Multímetro digital", "Pinza amperimétrica", "Detector de voltaje sin contacto",
        "Probador de contactos", "Megóhmetro", "Telurómetro", "Medidor de secuencia de fases",
        "Analizador de calidad de energía", "Pelacables", "Ponchadora de terminales eléctricas",
        "Cortacables", "Dobladora de tubo conduit", "Guía jalacables", "Sonda pasacables",
        "Torquímetro / llave dinamométrica", "Prensa terminal hidráulica",
    ],
    "Seguridad y Monitoreo": [
        "Monitor de prueba CCTV", "Probador CCTV / video", "Tester PoE",
        "Crimpadora RJ45", "Pelador UTP/coaxial", "Ponchadora BNC", "Probador de cable de red",
        "Generador de tonos y sonda", "Laptop de configuración", "Monitor portátil HDMI/VGA",
        "Fuente de alimentación de prueba", "Probador de continuidad",
    ],
    "Control de Accesos": [
        "Multímetro digital", "Probador de continuidad", "Fuente de alimentación de prueba",
        "Crimpadora RJ45", "Probador de cable de red", "Laptop de configuración",
        "Plantilla / guía de perforación", "Remachadora", "Machuelos / tarrajas",
        "Medidor de fuerza / alineación de puerta",
    ],
    "Redes de Voz y Datos": [
        "Certificador de cableado estructurado", "Probador de cable de red",
        "Generador de tonos y sonda", "Crimpadora RJ45", "Herramienta de impacto 110/Krone",
        "Pelador de cable UTP", "Fusionadora de fibra óptica", "Cortadora de precisión de fibra",
        "Peladora de fibra óptica", "OTDR", "Medidor de potencia óptica", "Fuente de luz óptica",
        "Localizador visual de fallas (VFL)", "Microscopio / inspector de conectores de fibra",
        "Kit de limpieza de fibra óptica", "Laptop de configuración", "Tester PoE",
    ],
    "Enlaces Inalámbricos": [
        "Laptop de configuración", "Analizador Wi‑Fi / espectro", "GPS",
        "Brújula", "Inclinómetro", "Binoculares", "Medidor láser de distancia",
        "Tester PoE", "Probador de cable de red", "Crimpadora RJ45",
        "Torquímetro / llave dinamométrica", "Arnés para trabajo en altura",
    ],
    "Paneles Solares": [
        "Multímetro solar / DC", "Pinza amperimétrica DC", "Medidor de irradiancia solar",
        "Megóhmetro", "Cámara termográfica", "Crimpadora MC4", "Llaves para conectores MC4",
        "Pelacables solar", "Torquímetro / llave dinamométrica", "Probador de continuidad",
        "Medidor de puesta a tierra", "Nivel láser", "Taladro / rotomartillo",
    ],
    "Plantas de Energía": [
        "Multímetro digital", "Pinza amperimétrica", "Medidor de secuencia de fases",
        "Analizador de calidad de energía", "Megóhmetro", "Telurómetro", "Tacómetro",
        "Termómetro infrarrojo", "Cámara termográfica", "Banco de carga",
        "Torquímetro / llave dinamométrica", "Juego de dados y matraca", "Manómetro",
        "Densímetro / probador de batería", "Cargador / arrancador de batería",
    ],
    "Aires Acondicionados": [
        "Manifold de refrigeración", "Bomba de vacío", "Vacuómetro / micron gauge",
        "Báscula para refrigerante", "Detector electrónico de fugas", "Termómetro digital",
        "Termómetro infrarrojo", "Pinza amperimétrica", "Multímetro digital",
        "Cortatubos de cobre", "Abocardador / flaring", "Expansor de tubo",
        "Dobladora de tubo", "Llave dinamométrica para flare", "Recuperadora de refrigerante",
        "Cilindro de recuperación", "Nitrógeno y regulador de prueba", "Peine para aletas",
    ],
    "Obra Civil": [
        "Rotomartillo", "Martillo demoledor", "Esmeril angular", "Cortadora de concreto",
        "Revolvedora / mezcladora", "Vibrador de concreto", "Nivel láser", "Nivel de burbuja",
        "Plomada", "Regla de aluminio", "Cuchara de albañil", "Llana",
        "Pala", "Pico", "Barreta", "Carretilla", "Marro", "Cincel",
        "Sierra circular", "Caladora", "Pistola de clavos / fijación",
    ],
    "Tecnología, Equipos y Periféricos": [
        "Kit de desarmadores de precisión", "Pulsera antiestática (ESD)", "Tapete antiestático",
        "Sopladora / aire eléctrico", "Multímetro digital", "Probador de fuente ATX",
        "Adaptador USB a SATA/NVMe", "Dock de discos", "Memoria USB de servicio",
        "Pasta térmica y aplicador", "Pinzas de precisión", "Spudger / herramientas plásticas",
        "Laptop de diagnóstico", "Probador USB", "Cable/conversor de video de prueba",
    ],
}

CATEGORIAS_HERRAMIENTAS = tuple(CATALOGO_HERRAMIENTAS.keys())


def herramientas_por_categoria(categoria: str) -> list[str]:
    return list(CATALOGO_HERRAMIENTAS.get(str(categoria or "").strip(), CATALOGO_HERRAMIENTAS["General"]))
