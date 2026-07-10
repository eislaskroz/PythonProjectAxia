"""Catálogo maestro escalable de equipos para levantamientos AXIA.

La clasificación estable (familia/subfamilia/características) vive en código.
La marca y el modelo se capturan de forma dinámica para evitar que AXIA dependa
cada vez que los fabricantes renuevan sus líneas de producto.
"""

MARCAS_COMUNES = [
    "Por definir", "Hikvision", "Dahua", "Axis", "Hanwha", "Bosch", "ZKTeco",
    "Ubiquiti", "MikroTik", "Cisco", "Aruba", "TP-Link", "Panduit", "Tripp Lite",
    "APC", "Schneider Electric", "Siemens", "ABB", "Eaton", "Generac", "Cummins",
    "Carrier", "York", "Daikin", "Midea", "LG", "Samsung", "Sungrow", "Huawei",
    "Canadian Solar", "Jinko Solar", "Otra"
]

CATALOGO_EQUIPOS = {
    "Seguridad y Monitoreo": [
        {"familia": "Cámara", "subfamilias": ["Bala", "Domo", "Turret", "PTZ", "Fisheye", "Térmica", "LPR"], "caracteristicas": "Tecnología, resolución, lente, IR, PoE, protección IP/IK"},
        {"familia": "Grabador", "subfamilias": ["DVR", "NVR", "Servidor de video"], "caracteristicas": "Canales, resolución, bahías, ancho de banda, RAID"},
        {"familia": "Almacenamiento", "subfamilias": ["Disco duro vigilancia", "NAS", "SAN"], "caracteristicas": "Capacidad, interfaz, carga de trabajo, redundancia"},
        {"familia": "Monitor", "subfamilias": ["Monitor operativo", "Videowall", "Pantalla profesional"], "caracteristicas": "Pulgadas, resolución, entradas, operación 24/7"},
        {"familia": "Switch", "subfamilias": ["PoE", "PoE+", "PoE++", "Industrial"], "caracteristicas": "Puertos, presupuesto PoE, uplinks, administración"},
    ],
    "Redes Voz y Datos": [
        {"familia": "Switch", "subfamilias": ["No administrable", "Administrable", "PoE", "PoE+", "Core", "Industrial"], "caracteristicas": "Puertos, velocidad, uplinks, PoE, capa L2/L3"},
        {"familia": "Router", "subfamilias": ["Empresarial", "SD-WAN", "Industrial", "LTE/5G"], "caracteristicas": "Throughput, interfaces WAN/LAN, VPN, redundancia"},
        {"familia": "Access Point", "subfamilias": ["Interior", "Exterior", "Alta densidad", "Mesh"], "caracteristicas": "Wi-Fi, bandas, MIMO, usuarios, PoE"},
        {"familia": "Rack", "subfamilias": ["Mural", "Piso", "Abierto", "Gabinete exterior"], "caracteristicas": "Unidades, fondo, carga, ventilación"},
        {"familia": "Telefonía", "subfamilias": ["PBX IP", "Teléfono IP", "Gateway", "ATA"], "caracteristicas": "Extensiones, troncales, protocolos, licencias"},
    ],
    "Aires Acondicionados": [
        {"familia": "Aire acondicionado", "subfamilias": ["Mini split", "Multi split", "Cassette", "Piso-techo", "Precisión", "Paquete"], "caracteristicas": "Capacidad BTU/TR, voltaje, inverter, refrigerante"},
        {"familia": "Condensadora", "subfamilias": ["Convencional", "Inverter", "Precisión"], "caracteristicas": "Capacidad, alimentación, refrigerante, distancia máxima"},
        {"familia": "Control", "subfamilias": ["Termostato", "Control remoto", "Control central", "BMS"], "caracteristicas": "Compatibilidad, comunicación, programación"},
        {"familia": "Bomba de drenaje", "subfamilias": ["Mini", "Tanque", "Peristáltica"], "caracteristicas": "Caudal, altura, voltaje, alarma"},
    ],
    "Plantas de Energía": [
        {"familia": "Planta de emergencia", "subfamilias": ["Diésel", "Gas LP", "Gas natural", "Gasolina"], "caracteristicas": "kW/kVA, fases, voltaje, autonomía, cabina"},
        {"familia": "Transferencia", "subfamilias": ["ATS", "Manual", "Transición cerrada", "Bypass"], "caracteristicas": "Amperaje, polos, voltaje, control"},
        {"familia": "Tablero", "subfamilias": ["Distribución", "Emergencia", "Sincronismo", "Control"], "caracteristicas": "Amperaje, interruptores, fases, gabinete"},
        {"familia": "Tanque de combustible", "subfamilias": ["Base", "Día", "Externo"], "caracteristicas": "Capacidad, material, contención, sensores"},
    ],
    "Electricidad": [
        {"familia": "Tablero eléctrico", "subfamilias": ["Alumbrado", "Distribución", "Fuerza", "Transferencia", "Control"], "caracteristicas": "Amperaje, fases, voltaje, capacidad interruptiva"},
        {"familia": "Transformador", "subfamilias": ["Seco", "Aceite", "Aislamiento", "Control"], "caracteristicas": "kVA, primario/secundario, fases, impedancia"},
        {"familia": "UPS", "subfamilias": ["Interactiva", "Online", "Modular", "Industrial"], "caracteristicas": "VA/W, autonomía, fases, voltaje, bypass"},
        {"familia": "Protección", "subfamilias": ["Interruptor", "Supresor", "Fusible", "Relé"], "caracteristicas": "Corriente, polos, curva, capacidad interruptiva"},
        {"familia": "Luminaria", "subfamilias": ["Interior", "Exterior", "Emergencia", "Industrial"], "caracteristicas": "Potencia, lúmenes, temperatura, IP"},
    ],
    "Control de Accesos": [
        {"familia": "Lector", "subfamilias": ["Tarjeta", "Biométrico", "Facial", "QR", "UHF"], "caracteristicas": "Credencial, protocolo, capacidad, IP/IK"},
        {"familia": "Controlador", "subfamilias": ["1 puerta", "2 puertas", "4 puertas", "IP", "Elevador"], "caracteristicas": "Puertas, usuarios, eventos, red, alimentación"},
        {"familia": "Cerradura", "subfamilias": ["Electromagnética", "Contrachapa", "Perno", "Torniquete", "Chapa inteligente"], "caracteristicas": "Fuerza, voltaje, fail-safe/fail-secure"},
        {"familia": "Botón/Sensor", "subfamilias": ["Salida", "Emergencia", "Contacto magnético", "REX"], "caracteristicas": "Tipo, contacto, voltaje, montaje"},
    ],
    "Enlaces Inalámbricos": [
        {"familia": "Radio", "subfamilias": ["Punto a punto", "Punto-multipunto", "Backhaul", "CPE"], "caracteristicas": "Frecuencia, throughput, ganancia, alcance"},
        {"familia": "Antena", "subfamilias": ["Parabólica", "Panel", "Sectorial", "Omnidireccional"], "caracteristicas": "Ganancia, frecuencia, apertura, polarización"},
        {"familia": "Protección", "subfamilias": ["Supresor Ethernet", "Pararrayos", "Tierra física"], "caracteristicas": "Categoría, descarga, conectores, puesta a tierra"},
        {"familia": "Estructura", "subfamilias": ["Mástil", "Torre", "Herraje", "Gabinete exterior"], "caracteristicas": "Altura, carga al viento, material, anclaje"},
    ],
    "Paneles Solares": [
        {"familia": "Panel fotovoltaico", "subfamilias": ["Monocristalino", "Bifacial", "Flexible"], "caracteristicas": "Wp, eficiencia, Voc, Isc, dimensiones"},
        {"familia": "Inversor", "subfamilias": ["String", "Microinversor", "Híbrido", "Central"], "caracteristicas": "kW, MPPT, fases, voltaje, comunicación"},
        {"familia": "Batería", "subfamilias": ["Litio", "AGM", "Gel", "Plomo-ácido"], "caracteristicas": "kWh/Ah, voltaje, ciclos, BMS"},
        {"familia": "Protección DC/AC", "subfamilias": ["Combiner box", "Seccionador", "SPD", "Interruptor"], "caracteristicas": "Voltaje, corriente, polos, capacidad"},
        {"familia": "Estructura", "subfamilias": ["Coplanar", "Inclinada", "Techo plano", "Suelo"], "caracteristicas": "Material, inclinación, anclaje, viento"},
    ],
    "Obra Civil": [
        {"familia": "Maquinaria", "subfamilias": ["Excavadora", "Retroexcavadora", "Compactador", "Andamio", "Plataforma"], "caracteristicas": "Capacidad, alcance, horas/días de renta"},
        {"familia": "Equipo de bombeo", "subfamilias": ["Achique", "Hidráulico", "Presurización"], "caracteristicas": "Caudal, presión, potencia, alimentación"},
        {"familia": "Equipo de medición", "subfamilias": ["Nivel láser", "Estación total", "Detector"], "caracteristicas": "Precisión, alcance, accesorios"},
    ],
}


def obtener_familias_por_especialidad(especialidad):
    return CATALOGO_EQUIPOS.get(especialidad, [])


def obtener_nombres_familias(especialidad):
    return [item["familia"] for item in obtener_familias_por_especialidad(especialidad)] or ["Otro"]


def obtener_subfamilias(especialidad, familia):
    for item in obtener_familias_por_especialidad(especialidad):
        if item["familia"] == familia:
            return item.get("subfamilias", []) or ["Otro"]
    return ["Otro"]


def obtener_sugerencia_caracteristicas(especialidad, familia):
    for item in obtener_familias_por_especialidad(especialidad):
        if item["familia"] == familia:
            return item.get("caracteristicas", "Características técnicas")
    return "Características técnicas"
