"""Catálogo maestro escalable de equipos para levantamientos AXIA.

La clasificación estable (familia/subfamilia/características) vive en código.
La marca y el modelo se capturan de forma dinámica para evitar que AXIA dependa
cada vez que los fabricantes renuevan sus líneas de producto.
"""

# Catálogo visible homologado. Las marcas reales se presentan en orden alfabético;
# las opciones de control permanecen en los extremos para facilitar la captura.
_MARCAS_BASE = [
    "Hikvision", "Dahua", "Axis", "Hanwha", "Bosch", "ZKTeco",
    "Ubiquiti", "MikroTik", "Cisco", "Aruba", "TP-Link", "Panduit", "Tripp Lite",
    "APC", "Schneider Electric", "Siemens", "ABB", "Eaton", "Generac", "Cummins",
    "Carrier", "York", "Daikin", "Midea", "LG", "Samsung", "Sungrow", "Huawei",
    "Canadian Solar", "Jinko Solar", "HP", "Dell", "Lenovo", "Acer", "Asus", "Epson",
    "Brother", "Canon", "Logitech", "Kingston", "Western Digital", "Seagate",
    "Synology", "QNAP"
]
MARCAS_COMUNES = ["Por definir", *sorted(_MARCAS_BASE, key=str.casefold), "Otra"]

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
    "Tecnología, Equipos y Periféricos": [
        {"familia": "Accesorios", "subfamilias": ["Base para laptop", "Base para monitor", "Docking station", "Hub USB", "Lector de tarjetas", "Soporte de pared", "Soporte VESA"], "caracteristicas": "Compatibilidad, conexiones, material, capacidad y montaje"},
        {"familia": "Almacenamiento", "subfamilias": ["Disco duro externo", "HDD", "Memoria USB", "NAS", "SSD NVMe", "SSD SATA", "Tarjeta microSD", "Tarjeta SD"], "caracteristicas": "Capacidad, interfaz, velocidad, formato, uso y garantía"},
        {"familia": "Audio", "subfamilias": ["Audífonos", "Barra de sonido", "Bocinas", "Diadema", "Interfaz de audio", "Micrófono"], "caracteristicas": "Conectividad, potencia, patrón, canales, alimentación y compatibilidad"},
        {"familia": "Componentes", "subfamilias": ["Fuente de poder", "Gabinete", "Memoria RAM", "Procesador", "Tarjeta de red", "Tarjeta de video", "Tarjeta madre"], "caracteristicas": "Formato, capacidad, interfaz, potencia y compatibilidad"},
        {"familia": "Computadora", "subfamilias": ["All-in-One", "Escritorio", "Mini PC", "Thin client", "Workstation"], "caracteristicas": "Procesador, RAM, almacenamiento, gráficos, sistema operativo, garantía"},
        {"familia": "Energía", "subfamilias": ["Cargador", "Fuente de poder", "Multicontacto", "No-break", "PDU", "Regulador", "UPS"], "caracteristicas": "VA/W, voltaje, autonomía, conectores y protecciones"},
        {"familia": "Gaming", "subfamilias": ["Consola", "Control", "Monitor gaming", "Silla gaming", "Teclado/Mouse gaming"], "caracteristicas": "Plataforma, conectividad, resolución, frecuencia y compatibilidad"},
        {"familia": "Impresión y digitalización", "subfamilias": ["Escáner", "Impresora de etiquetas", "Impresora gran formato", "Impresora inyección de tinta", "Impresora láser", "Impresora térmica", "Multifuncional", "Plotter"], "caracteristicas": "Color/mono, ppm, dúplex, red, consumible, tamaño y volumen mensual"},
        {"familia": "Laptop", "subfamilias": ["Ejecutiva", "Gaming", "Oficina", "Rugged", "Workstation móvil"], "caracteristicas": "Procesador, RAM, SSD, pantalla, batería, puertos y garantía"},
        {"familia": "Monitores y Pantallas", "subfamilias": ["Digital Signage", "Monitor curvo", "Monitor de escritorio", "Monitor portátil", "Monitor profesional", "Pantalla / TV", "Pantalla comercial", "Pantalla interactiva", "Smart TV", "Videowall"], "caracteristicas": "Pulgadas, resolución, panel, frecuencia, HDR, entradas, VESA y operación"},
        {"familia": "Periféricos", "subfamilias": ["Cámara web", "Escáner", "Lector biométrico", "Lector de código de barras", "Mouse", "Tableta digitalizadora", "Teclado"], "caracteristicas": "Conectividad, compatibilidad, alimentación, resolución y funciones"},
        {"familia": "Punto de Venta", "subfamilias": ["Cajón de dinero", "Impresora de tickets", "Lector de código de barras", "Monitor touch", "Terminal POS"], "caracteristicas": "Interfaces, tamaño, compatibilidad, alimentación y montaje"},
        {"familia": "Proyección", "subfamilias": ["Pantalla de proyección", "Proyector", "Proyector láser", "Soporte para proyector"], "caracteristicas": "Lúmenes, resolución, tiro, entradas, tamaño y montaje"},
        {"familia": "Redes y conectividad", "subfamilias": ["Access Point", "Adaptador de red", "Firewall", "Módem", "Router", "Switch"], "caracteristicas": "Puertos, velocidad, Wi-Fi, PoE, administración, VPN y throughput"},
        {"familia": "Servidor", "subfamilias": ["Blade", "NAS", "Rack", "Torre"], "caracteristicas": "CPU, RAM ECC, almacenamiento, RAID, fuentes, red y licenciamiento"},
        {"familia": "Software y Licencias", "subfamilias": ["Antivirus", "Diseño", "Licencia CAL", "Ofimática", "Respaldo", "Sistema operativo"], "caracteristicas": "Edición, vigencia, usuarios/dispositivos, modalidad y compatibilidad"},
        {"familia": "Tablets y Movilidad", "subfamilias": ["E-reader", "Smartphone", "Tablet", "Tablet industrial"], "caracteristicas": "Pantalla, almacenamiento, conectividad, batería, protección y sistema operativo"},
        {"familia": "Videoconferencia", "subfamilias": ["Barra de videoconferencia", "Cámara PTZ", "Controlador táctil", "Kit de sala", "Speakerphone"], "caracteristicas": "Resolución, encuadre, micrófonos, conexiones, plataforma y tamaño de sala"},
        {"familia": "Otro", "subfamilias": ["Otro / especificar"], "caracteristicas": "Descripción, compatibilidad y características técnicas requeridas"},
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
    return sorted([item["familia"] for item in obtener_familias_por_especialidad(especialidad)], key=str.casefold) or ["Otro"]


def obtener_subfamilias(especialidad, familia):
    for item in obtener_familias_por_especialidad(especialidad):
        if item["familia"] == familia:
            return sorted(item.get("subfamilias", []) or ["Otro"], key=str.casefold)
    return ["Otro"]


def obtener_sugerencia_caracteristicas(especialidad, familia):
    for item in obtener_familias_por_especialidad(especialidad):
        if item["familia"] == familia:
            return item.get("caracteristicas", "Características técnicas")
    return "Características técnicas"
