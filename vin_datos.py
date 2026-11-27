"""
Decodificación del número de bastidor (VIN, ISO 3779): fabricante, país, año
modelo y, en los VAG, el código de modelo (posiciones 7-8).

Las tablas cubren los fabricantes más habituales en Europa; lo que no está en
ellas se muestra sin descifrar.
"""
import datetime
import re

from idioma import tr

FABRICANTES = {
    "WVW": "Volkswagen", "WV1": "Volkswagen (vehículos comerciales)", "WV2": "Volkswagen (vehículos comerciales)",
    "WVG": "Volkswagen (SUV)", "WAU": "Audi", "WUA": "Audi Sport", "TRU": "Audi (Hungría)",
    "VSS": "SEAT", "TMB": "Škoda", "WBA": "BMW", "WBS": "BMW M", "WBY": "BMW i", "WMW": "MINI",
    "WDB": "Mercedes-Benz", "WDD": "Mercedes-Benz", "WDC": "Mercedes-Benz (SUV)",
    "WDF": "Mercedes-Benz (furgonetas)", "W1K": "Mercedes-Benz", "WP0": "Porsche", "WP1": "Porsche (SUV)",
    "W0L": "Opel", "W0V": "Opel", "WF0": "Ford (Alemania)", "VS6": "Ford (España)", "VSX": "Opel (España)",
    "VF1": "Renault", "VF3": "Peugeot", "VF7": "Citroën", "VR3": "Peugeot", "VR7": "Citroën",
    "VS7": "Citroën (España)", "VSK": "Nissan (España)", "UU1": "Dacia",
    "ZFA": "Fiat", "ZAR": "Alfa Romeo", "ZLA": "Lancia", "ZFF": "Ferrari",
    "SAJ": "Jaguar", "SAL": "Land Rover", "SJN": "Nissan (Reino Unido)", "SB1": "Toyota (Reino Unido)",
    "YV1": "Volvo", "YS3": "Saab", "NMT": "Toyota (Turquía)", "VNK": "Toyota (Francia)",
    "JTD": "Toyota", "JTE": "Toyota", "JT1": "Toyota", "JHM": "Honda", "JN1": "Nissan", "JMZ": "Mazda",
    "JM1": "Mazda", "JS2": "Suzuki", "TSM": "Suzuki (Hungría)", "KMH": "Hyundai", "TMA": "Hyundai (Chequia)",
    "KNA": "Kia", "U5Y": "Kia (Eslovaquia)", "5YJ": "Tesla", "1HG": "Honda (EE. UU.)", "1FA": "Ford (EE. UU.)", "1G1": "Chevrolet", "LRW": "Tesla (China)", "XTA": "Lada",
}

# Prefijos de dos letras (o una) -> país, de lo más concreto a lo más general.
PAISES = (
    ("VS", "VW", "España"), ("VF", "VR", "Francia"), ("W", "W", "Alemania"), ("ZA", "Z0", "Italia"),
    ("SA", "SM", "Reino Unido"), ("TM", "TV", "República Checa"), ("TR", "TR", "Hungría"),
    ("YS", "YW", "Suecia"), ("YA", "YE", "Bélgica"), ("XL", "XM", "Países Bajos"), ("UU", "U7", "Rumanía"),
    ("U5", "U7", "Eslovaquia"), ("NM", "NM", "Turquía"), ("J", "J", "Japón"), ("KL", "KR", "Corea del Sur"),
    ("L", "L", "China"), ("1", "1", "Estados Unidos"), ("4", "5", "Estados Unidos"), ("2", "2", "Canadá"),
    ("3", "3", "México"), ("9A", "9E", "Brasil"), ("X3", "X0", "Rusia"),
)

# Código de modelo VAG (posiciones 7 y 8 del VIN europeo)
MODELOS_VAG = {
    "1H": "Golf III / Vento", "1J": "Volkswagen Golf IV / Bora",
    "1M": "SEAT Toledo II / León I", "1K": "Volkswagen Golf V-VI / Jetta",
    "1P": "SEAT León II", "5P": "SEAT Altea / Toledo III", "6K": "SEAT Ibiza II / Córdoba",
    "6L": "SEAT Ibiza III / Córdoba", "9N": "Volkswagen Polo IV", "3B": "Volkswagen Passat B5",
    "3C": "Volkswagen Passat B6-B7", "1T": "Volkswagen Touran", "5N": "Volkswagen Tiguan",
    "7L": "Volkswagen Touareg", "7M": "Sharan / Alhambra / Galaxy (1.ª generación)",
    "8L": "Audi A3 (8L)", "8P": "Audi A3 (8P)", "8D": "Audi A4 (B5)", "8E": "Audi A4 (B6-B7)",
    "1U": "Škoda Octavia I", "1Z": "Škoda Octavia II", "6Y": "Škoda Fabia I",
}
VAG = ("WVW", "WV1", "WV2", "WVG", "WAU", "WUA", "TRU", "VSS", "TMB")

LETRAS_ANIO = "ABCDEFGHJKLMNPRSTVWXY123456789"     # ciclo de 30 años (sin I, O, Q, U, Z ni 0)


def _parentesis(texto):
    """Traduce lo que va entre paréntesis («Ford (Alemania)»): el resto son nombres propios."""
    return re.sub(r"\(([^)]*)\)", lambda m: "(" + tr(m.group(1)) + ")", texto)


def anio_modelo(c, hoy=None):
    """Año modelo de la posición 10. Se elige el más reciente que no sea futuro."""
    if c not in LETRAS_ANIO:
        return None
    limite = (hoy or datetime.date.today()).year + 1
    anio = 1980 + LETRAS_ANIO.index(c)
    while anio + 30 <= limite:
        anio += 30
    return anio


def pais(vin):
    for desde, hasta, nombre in PAISES:
        n = len(desde)
        if desde <= vin[:n] <= hasta:
            return tr(nombre)
    return None


def decodificar_vin(vin, hoy=None):
    """Lista de (campo, valor) con lo que se puede deducir del VIN."""
    vin = (vin or "").strip().upper()
    if len(vin) != 17 or any(c in "IOQ" for c in vin):
        return [("VIN", tr("no válido (deben ser 17 caracteres, sin I, O ni Q)"))]
    wmi = vin[:3]
    fab = FABRICANTES.get(wmi)
    out = [(tr("Fabricante"), _parentesis(fab) if fab else tr("desconocido (código {wmi})", wmi=wmi))]
    p = pais(vin)
    if p:
        out.append((tr("País de fabricación"), p))
    anio = anio_modelo(vin[9], hoy)
    if anio:
        out.append((tr("Año modelo"), tr("{anio} (posición 10 del VIN)", anio=anio)))
    if wmi in VAG:
        modelo = MODELOS_VAG.get(vin[6:8])
        out.append((tr("Modelo (código VAG)"), f"{vin[6:8]} · {_parentesis(modelo)}" if modelo else vin[6:8]))
    out.append((tr("Planta y n.º de serie"), f"{vin[10]} · {vin[11:]}"))
    return out
