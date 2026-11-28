"""
Datos OBD2/EOBD estandar (SAE J1979): PIDs del modo 01 y codigos de averia genericos.
"""
import idioma
from idioma import tr


def _u16(d):
    return (d[0] << 8) | d[1]


def _pct(d):
    return d[0] * 100 / 255


def _temp(d):
    return d[0] - 40


def _trim(d):
    return (d[0] - 128) * 100 / 128


# pid: (nombre, unidad, n.o bytes, decodificador, decimales)
PIDS = {
    0x04: ("Carga del motor", "%", 1, _pct, 0),
    0x05: ("Temp. refrigerante", "°C", 1, _temp, 0),
    0x06: ("Corrección corto plazo B1", "%", 1, _trim, 1),
    0x07: ("Corrección largo plazo B1", "%", 1, _trim, 1),
    0x08: ("Corrección corto plazo B2", "%", 1, _trim, 1),
    0x09: ("Corrección largo plazo B2", "%", 1, _trim, 1),
    0x0A: ("Presión combustible", "kPa", 1, lambda d: d[0] * 3, 0),
    0x0B: ("Presión colector (MAP)", "kPa", 1, lambda d: d[0], 0),
    0x0C: ("Régimen motor", "rpm", 2, lambda d: _u16(d) / 4, 0),
    0x0D: ("Velocidad", "km/h", 1, lambda d: d[0], 0),
    0x0E: ("Avance encendido", "°", 1, lambda d: d[0] / 2 - 64, 1),
    0x0F: ("Temp. aire admisión", "°C", 1, _temp, 0),
    0x10: ("Caudal de aire (MAF)", "g/s", 2, lambda d: _u16(d) / 100, 2),
    0x11: ("Posición mariposa", "%", 1, _pct, 0),
    0x14: ("Sonda O2 B1S1", "V", 2, lambda d: d[0] / 200, 3),
    0x15: ("Sonda O2 B1S2", "V", 2, lambda d: d[0] / 200, 3),
    0x16: ("Sonda O2 B1S3", "V", 2, lambda d: d[0] / 200, 3),
    0x17: ("Sonda O2 B1S4", "V", 2, lambda d: d[0] / 200, 3),
    0x18: ("Sonda O2 B2S1", "V", 2, lambda d: d[0] / 200, 3),
    0x19: ("Sonda O2 B2S2", "V", 2, lambda d: d[0] / 200, 3),
    0x1F: ("Tiempo desde arranque", "s", 2, _u16, 0),
    0x21: ("Distancia con testigo MIL", "km", 2, _u16, 0),
    0x22: ("Presión rail (rel. vacío)", "kPa", 2, lambda d: _u16(d) * 0.079, 1),
    0x23: ("Presión rail combustible", "kPa", 2, lambda d: _u16(d) * 10, 0),
    0x24: ("Lambda sonda B1S1 (banda ancha)", "λ", 4, lambda d: _u16(d) * 2 / 65536, 3),
    0x2C: ("EGR comandada", "%", 1, _pct, 0),
    0x2D: ("Error EGR", "%", 1, _trim, 1),
    0x2E: ("Purga EVAP comandada", "%", 1, _pct, 0),
    0x2F: ("Nivel de combustible", "%", 1, _pct, 0),
    0x30: ("Calentamientos desde borrado", "", 1, lambda d: d[0], 0),
    0x31: ("Distancia desde borrado", "km", 2, _u16, 0),
    0x33: ("Presión barométrica", "kPa", 1, lambda d: d[0], 0),
    0x34: ("Lambda sonda B1S1 (corriente)", "λ", 4, lambda d: _u16(d) * 2 / 65536, 3),
    0x3C: ("Temp. catalizador B1S1", "°C", 2, lambda d: _u16(d) / 10 - 40, 0),
    0x3D: ("Temp. catalizador B2S1", "°C", 2, lambda d: _u16(d) / 10 - 40, 0),
    0x42: ("Tensión módulo de control", "V", 2, lambda d: _u16(d) / 1000, 2),
    0x43: ("Carga absoluta", "%", 2, lambda d: _u16(d) * 100 / 255, 0),
    0x44: ("Lambda comandada", "λ", 2, lambda d: _u16(d) * 2 / 65536, 3),
    0x45: ("Mariposa relativa", "%", 1, _pct, 0),
    0x46: ("Temp. ambiente", "°C", 1, _temp, 0),
    0x47: ("Mariposa absoluta B", "%", 1, _pct, 0),
    0x49: ("Pedal acelerador D", "%", 1, _pct, 0),
    0x4A: ("Pedal acelerador E", "%", 1, _pct, 0),
    0x4C: ("Actuador mariposa comandado", "%", 1, _pct, 0),
    0x4D: ("Tiempo con testigo MIL", "min", 2, _u16, 0),
    0x4E: ("Tiempo desde borrado", "min", 2, _u16, 0),
    0x52: ("Etanol en combustible", "%", 1, _pct, 0),
    0x5A: ("Pedal acelerador relativo", "%", 1, _pct, 0),
    0x5C: ("Temp. aceite", "°C", 1, _temp, 0),
    0x5E: ("Consumo de combustible", "L/h", 2, lambda d: _u16(d) / 20, 1),
}

# Longitud de los PIDs no "medibles" (necesaria para respuestas multi-PID)
PID_LEN_EXTRA = {0x00: 4, 0x01: 4, 0x03: 2, 0x13: 1, 0x1C: 1, 0x20: 4, 0x40: 4, 0x51: 1,
                 0x60: 4, 0x80: 4, 0xA0: 4, 0xC0: 4}


def pid_len(pid):
    if pid in PIDS:
        return PIDS[pid][2]
    return PID_LEN_EXTRA.get(pid)


def decode_pid(pid, data):
    """Devuelve (nombre, texto_valor, unidad, ok)."""
    if pid not in PIDS:
        return f"PID {pid:02X}h", data.hex(" "), "", False
    nombre, unidad, n, fn, dec = PIDS[pid]
    if len(data) < n:
        return nombre, "?", unidad, False
    try:
        v = fn(data[:n])
    except Exception:
        return nombre, data.hex(" "), unidad, False
    return nombre, f"{v:.{dec}f}", unidad, True


OBD_STANDARDS = {
    1: "OBD-II (CARB)", 2: "OBD (EPA)", 3: "OBD y OBD-II", 4: "OBD-I", 5: "No OBD",
    6: "EOBD (Europa)", 7: "EOBD y OBD-II", 8: "EOBD y OBD", 9: "EOBD, OBD y OBD-II",
    10: "JOBD (Japón)", 11: "JOBD y OBD-II", 12: "JOBD y EOBD", 13: "JOBD, EOBD y OBD-II",
}


def decode_dtc(a, b):
    letra = "PCBU"[a >> 6]
    return f"{letra}{(a >> 4) & 3}{a & 0xF:X}{b >> 4:X}{b & 0xF:X}"


DTCS = {
    "P0010": "Actuador posición árbol de levas A (B1): circuito",
    "P0011": "Árbol de levas A (B1): avance excesivo o rendimiento",
    "P0012": "Árbol de levas A (B1): retraso excesivo",
    "P0016": "Correlación cigüeñal / árbol de levas (B1 sensor A)",
    "P0030": "Calefactor sonda O2 B1S1: circuito",
    "P0036": "Calefactor sonda O2 B1S2: circuito",
    "P0045": "Válvula de control del turbo: circuito abierto",
    "P0069": "Correlación presión colector / barométrica",
    "P0087": "Presión de rail/sistema de combustible demasiado baja",
    "P0088": "Presión de rail/sistema de combustible demasiado alta",
    "P0100": "Caudalímetro (MAF): circuito",
    "P0101": "Caudalímetro (MAF): rango / rendimiento",
    "P0102": "Caudalímetro (MAF): señal baja",
    "P0103": "Caudalímetro (MAF): señal alta",
    "P0105": "Sensor presión colector (MAP): circuito",
    "P0106": "Sensor MAP: rango / rendimiento",
    "P0107": "Sensor MAP: señal baja",
    "P0108": "Sensor MAP: señal alta",
    "P0110": "Sensor temp. aire admisión: circuito",
    "P0112": "Sensor temp. aire admisión: señal baja",
    "P0113": "Sensor temp. aire admisión: señal alta",
    "P0115": "Sensor temp. refrigerante: circuito",
    "P0116": "Sensor temp. refrigerante: rango / rendimiento",
    "P0117": "Sensor temp. refrigerante: señal baja",
    "P0118": "Sensor temp. refrigerante: señal alta",
    "P0120": "Sensor posición mariposa/pedal A: circuito",
    "P0121": "Sensor posición mariposa A: rango / rendimiento",
    "P0122": "Sensor posición mariposa A: señal baja",
    "P0123": "Sensor posición mariposa A: señal alta",
    "P0125": "Temp. refrigerante insuficiente para control en lazo cerrado",
    "P0128": "Termostato: temp. refrigerante por debajo de la de regulación",
    "P0130": "Sonda O2 B1S1: circuito",
    "P0131": "Sonda O2 B1S1: tensión baja",
    "P0132": "Sonda O2 B1S1: tensión alta",
    "P0133": "Sonda O2 B1S1: respuesta lenta",
    "P0134": "Sonda O2 B1S1: sin actividad",
    "P0135": "Calefactor sonda O2 B1S1: circuito",
    "P0136": "Sonda O2 B1S2: circuito",
    "P0137": "Sonda O2 B1S2: tensión baja",
    "P0138": "Sonda O2 B1S2: tensión alta",
    "P0140": "Sonda O2 B1S2: sin actividad",
    "P0141": "Calefactor sonda O2 B1S2: circuito",
    "P0171": "Mezcla demasiado pobre (banco 1)",
    "P0172": "Mezcla demasiado rica (banco 1)",
    "P0174": "Mezcla demasiado pobre (banco 2)",
    "P0175": "Mezcla demasiado rica (banco 2)",
    "P0201": "Inyector cilindro 1: circuito",
    "P0202": "Inyector cilindro 2: circuito",
    "P0203": "Inyector cilindro 3: circuito",
    "P0204": "Inyector cilindro 4: circuito",
    "P0217": "Sobretemperatura del motor",
    "P0234": "Sobrepresión del turbo",
    "P0299": "Presión del turbo insuficiente",
    "P0300": "Fallos de encendido aleatorios / múltiples cilindros",
    "P0301": "Fallo de encendido cilindro 1",
    "P0302": "Fallo de encendido cilindro 2",
    "P0303": "Fallo de encendido cilindro 3",
    "P0304": "Fallo de encendido cilindro 4",
    "P0305": "Fallo de encendido cilindro 5",
    "P0306": "Fallo de encendido cilindro 6",
    "P0325": "Sensor de picado 1: circuito",
    "P0335": "Sensor posición cigüeñal A: circuito",
    "P0336": "Sensor posición cigüeñal A: rango / rendimiento",
    "P0340": "Sensor posición árbol de levas A: circuito",
    "P0341": "Sensor posición árbol de levas A: rango / rendimiento",
    "P0351": "Bobina de encendido A: circuito",
    "P0352": "Bobina de encendido B: circuito",
    "P0353": "Bobina de encendido C: circuito",
    "P0354": "Bobina de encendido D: circuito",
    "P0380": "Bujías de precalentamiento: circuito A",
    "P0400": "Recirculación de gases (EGR): caudal",
    "P0401": "EGR: caudal insuficiente",
    "P0402": "EGR: caudal excesivo",
    "P0403": "EGR: circuito de control",
    "P0404": "EGR: rango / rendimiento",
    "P0405": "Sensor EGR A: señal baja",
    "P0406": "Sensor EGR A: señal alta",
    "P0420": "Eficiencia del catalizador por debajo del umbral (B1)",
    "P0430": "Eficiencia del catalizador por debajo del umbral (B2)",
    "P0440": "Sistema EVAP: avería",
    "P0441": "Sistema EVAP: caudal de purga incorrecto",
    "P0442": "Sistema EVAP: fuga pequeña",
    "P0443": "Válvula de purga EVAP: circuito",
    "P0455": "Sistema EVAP: fuga grande",
    "P0456": "Sistema EVAP: fuga muy pequeña",
    "P0500": "Sensor de velocidad del vehículo",
    "P0501": "Sensor de velocidad: rango / rendimiento",
    "P0505": "Control de ralentí: sistema",
    "P0506": "Ralentí más bajo de lo esperado",
    "P0507": "Ralentí más alto de lo esperado",
    "P0560": "Tensión del sistema",
    "P0562": "Tensión del sistema baja",
    "P0563": "Tensión del sistema alta",
    "P0571": "Interruptor de freno A: circuito",
    "P0480": "Control del ventilador de refrigeración 1: circuito",
    "P0600": "Enlace de comunicación serie",
    "P0601": "Módulo de control: error de suma de memoria",
    "P0603": "Módulo de control: error de memoria KAM",
    "P0604": "Módulo de control: error de memoria RAM",
    "P0605": "Módulo de control: error de memoria ROM",
    "P0606": "Módulo de control: procesador",
    "P0627": "Control de la bomba de combustible: circuito abierto",
    "P0641": "Tensión de referencia de sensores A: circuito abierto",
    "P0650": "Control del testigo de averías (MIL): circuito",
    "P0670": "Módulo de precalentamiento: circuito",
    "P0685": "Control del relé principal del módulo de control: circuito abierto",
    "P0700": "Sistema de control de la transmisión (ver TCM)",
}


# True si el coche conectado por OBD2 es del grupo VAG (por el VIN): entonces los
# códigos P1xxx se describen con la tabla de VAG (vag_p1.py). Lo pone la interfaz al conectar.
marca_vag = False


def describe_dtc(code):
    if code in DTCS:
        return DTCS[code]
    if marca_vag and len(code) == 5 and code.startswith("P1") and code[1:].isdigit():
        from vag_datos import DTCS_P1
        if int(code[1:]) in DTCS_P1:
            return DTCS_P1[int(code[1:])] + " (VAG)"
    if len(code) == 5 and code[1] in "13":
        return tr("Código específico del fabricante")
    return tr("Código no incluido en la tabla")


# ---------------------------------------------------------------------------
# Monitores de preparación (readiness): PID 01 01, bytes B, C y D (SAE J1979)
# ---------------------------------------------------------------------------
MONITORES_COMUNES = ("Fallos de encendido", "Sistema de combustible", "Componentes")
MONITORES_GASOLINA = ("Catalizador", "Catalizador calefactado", "Sistema de evaporación (EVAP)",
                      "Aire secundario", "Aire acondicionado", "Sondas lambda",
                      "Calefacción de las sondas lambda", "Recirculación de gases (EGR) / VVT")
MONITORES_DIESEL = ("Catalizador NMHC", "Reducción de NOx (SCR / catalizador NOx)", None,
                    "Presión de sobrealimentación", None, "Sensores de gases de escape",
                    "Filtro de partículas (DPF)", "Recirculación de gases (EGR) / VVT")


def monitores(b, c, d):
    """Estado de los monitores a partir de los bytes B, C y D del PID 01.

    Devuelve (diesel, [(nombre, completo), ...]) solo con los monitores que el
    coche soporta."""
    diesel = bool(b & 0x08)
    out = []
    for i, nombre in enumerate(MONITORES_COMUNES):
        if b & (1 << i):
            out.append((tr(nombre), not b & (1 << (i + 4))))
    for i, nombre in enumerate(MONITORES_DIESEL if diesel else MONITORES_GASOLINA):
        if nombre and c & (1 << i):
            out.append((tr(nombre), not d & (1 << i)))
    return diesel, out


# Traducción de las tablas al idioma de la interfaz (ver idioma.py)
idioma.tabla(PIDS, lambda v: (tr(v[0]),) + v[1:])
idioma.tabla(OBD_STANDARDS)
idioma.tabla(DTCS)
