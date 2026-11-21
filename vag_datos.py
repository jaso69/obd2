"""
Datos especificos VAG para KW1281: formulas de bloques de valores medidos,
codigos de averia (5 cifras) y grupos tipicos de la Bosch EDC15 (1.9 TDI).

Las formulas proceden de la documentacion publica del protocolo KW1281; si
algun valor sale raro, el programa muestra tambien el numero de formula y los
bytes a/b en bruto para poder revisarlo.
"""

# ---------------------------------------------------------------------------
# Formulas de los bloques de valores medidos: id -> (funcion(a, b), unidad)
# ---------------------------------------------------------------------------
def _div(x, y):
    return x / y if y else float("nan")


FORMULAS = {
    0x01: (lambda a, b: a * b / 5, "rpm"),
    0x02: (lambda a, b: a * 0.002 * b, "%"),
    0x03: (lambda a, b: a * 0.002 * b, "°"),
    0x04: (lambda a, b: abs(b - 127) * 0.01 * a, "°"),
    0x05: (lambda a, b: a * (b - 100) * 0.1, "°C"),
    0x06: (lambda a, b: 0.001 * a * b, "V"),
    0x07: (lambda a, b: 0.01 * a * b, "km/h"),
    0x08: (lambda a, b: 0.1 * a * b, ""),
    0x09: (lambda a, b: (b - 127) * 0.02 * a, "°"),
    0x0A: (lambda a, b: "FRIO" if b == 0 else "CALIENTE", ""),
    0x0B: (lambda a, b: 0.0001 * a * (b - 128) + 1, ""),
    0x0C: (lambda a, b: 0.001 * a * b, "Ω"),
    0x0D: (lambda a, b: (b - 127) * 0.001 * a, "mm"),
    0x0E: (lambda a, b: 0.005 * a * b, "bar"),
    0x0F: (lambda a, b: 0.01 * a * b, "ms"),
    0x10: (lambda a, b: format(a & b, "08b"), "bin"),
    0x11: (lambda a, b: chr(a) + chr(b), ""),
    0x12: (lambda a, b: 0.04 * a * b, "mbar"),
    0x13: (lambda a, b: a * b * 0.01, "l"),
    0x14: (lambda a, b: a * (b - 128) / 128, "%"),
    0x15: (lambda a, b: 0.001 * a * b, "V"),
    0x16: (lambda a, b: 0.001 * a * b, "ms"),
    0x17: (lambda a, b: b / 256 * a, "%"),
    0x18: (lambda a, b: 0.001 * a * b, "A"),
    0x19: (lambda a, b: b * 1.421 + a / 182, "g/s"),
    0x1A: (lambda a, b: b - a, "°C"),
    0x1B: (lambda a, b: abs(b - 128) * 0.01 * a, "°"),
    0x1C: (lambda a, b: b - a, ""),
    0x1E: (lambda a, b: b / 12 * a, "° KW"),
    0x1F: (lambda a, b: b / 2560 * a, "°C"),
    0x21: (lambda a, b: _div(100 * b, a), "%"),
    0x22: (lambda a, b: (b - 128) * 0.01 * a, "kW"),
    0x23: (lambda a, b: 0.01 * a * b, "l/h"),
    0x24: (lambda a, b: a * 2560 + b * 10, "km"),
    0x25: (lambda a, b: b, ""),
    0x26: (lambda a, b: (b - 128) * 0.001 * a, "° KW"),
    0x27: (lambda a, b: b / 256 * a, "mg/H"),
    0x28: (lambda a, b: b * 0.1 + 25.5 * a - 400, "A"),
    0x29: (lambda a, b: b + a * 255, "Ah"),
    0x2A: (lambda a, b: b * 0.1 + 25.5 * a - 400, "kW"),
    0x2B: (lambda a, b: b * 0.1 + 25.5 * a, "V"),
    0x2C: (lambda a, b: f"{a:02d}:{b:02d}", "h:m"),
    0x2D: (lambda a, b: 0.1 * a * b / 100, ""),
    0x2E: (lambda a, b: (a * b - 3200) * 0.0027, "° KW"),
    0x2F: (lambda a, b: (b - 128) * a, "ms"),
    0x30: (lambda a, b: b + a * 255, ""),
    0x31: (lambda a, b: (b / 4) * a * 0.1, "mg/H"),
    0x32: (lambda a, b: _div(b - 128, 0.01 * a), "mbar"),
    0x33: (lambda a, b: (b - 128) / 255 * a, "mg/H"),
    0x34: (lambda a, b: b * 0.02 * a - a, "Nm"),
    0x35: (lambda a, b: (b - 128) * 1.4222 + 0.006 * a, "g/s"),
    0x36: (lambda a, b: a * 256 + b, ""),
    0x37: (lambda a, b: a * b / 200, "s"),
    0x38: (lambda a, b: a * 256 + b, "WSC"),
    0x39: (lambda a, b: a * 256 + b + 65536, "WSC"),
    0x3B: (lambda a, b: (a * 256 + b) / 32768, "g/s"),
    0x3C: (lambda a, b: (a * 256 + b) * 0.01, "s"),
    0x3E: (lambda a, b: 0.256 * a * b, "S"),
    0x40: (lambda a, b: a + b, "Ω"),
    0x41: (lambda a, b: 0.01 * a * (b - 127), "mm"),
    0x42: (lambda a, b: a * b / 511.12, "V"),
    0x43: (lambda a, b: 640 * a + b * 2.5, "°"),
    0x44: (lambda a, b: (256 * a + b) / 7.365, "°/s"),
    0x45: (lambda a, b: (256 * a + b) * 0.3254, "bar"),
    0x46: (lambda a, b: (256 * a + b) * 0.192, "m/s²"),
}


def decode_value(formula, a, b):
    """Devuelve (texto_valor, unidad, conocida)."""
    f = FORMULAS.get(formula)
    if not f:
        return f"a={a} b={b}", f"(formula {formula:02X}h)", False
    fn, unit = f
    try:
        v = fn(a, b)
    except Exception:
        return f"a={a} b={b}", f"(formula {formula:02X}h)", False
    if isinstance(v, float):
        txt = f"{v:.0f}" if abs(v) >= 100 else f"{v:.2f}".rstrip("0").rstrip(".")
    else:
        txt = str(v)
    return txt, unit, True


# ---------------------------------------------------------------------------
# Tipo de fallo (byte de estado & 0x7F). El bit 0x80 indica "intermitente".
# ---------------------------------------------------------------------------
FAULT_TYPES = {
    0: "",
    1: "Cortocircuito a positivo",
    2: "Cortocircuito a masa",
    3: "Sin señal",
    4: "Fallo mecánico",
    5: "Circuito abierto",
    6: "Señal demasiado alta",
    7: "Señal demasiado baja",
    8: "Límite de regulación sobrepasado",
    9: "Límite de adaptación sobrepasado",
    10: "Límite de adaptación no alcanzado",
    11: "Límite de regulación no alcanzado",
    12: "Límite de adaptación (mult.) sobrepasado",
    13: "Límite de adaptación (mult.) no alcanzado",
    14: "Límite de adaptación (adit.) sobrepasado",
    15: "Límite de adaptación (adit.) no alcanzado",
    16: "Señal fuera de tolerancia",
    17: "Desviación de regulación",
    18: "Límite superior",
    19: "Límite inferior",
    27: "Señal no plausible",
}


# ---------------------------------------------------------------------------
# Codigos de averia VAG (5 cifras) habituales en 1.9 TDI EDC15
# ---------------------------------------------------------------------------
DTCS = {
    513: "Transmisor de régimen del motor (G28)",
    522: "Transmisor de temperatura del líquido refrigerante (G62)",
    523: "Transmisor de temperatura del aire de admisión (G42)",
    532: "Tensión de alimentación (B+)",
    550: "Regulación del comienzo de inyección",
    553: "Medidor de masa de aire (G70)",
    575: "Presión en el colector de admisión (sobrepresión/turbo)",
    625: "Señal de velocidad del vehículo",
    626: "Testigo de tiempo de precalentamiento (K29)",
    668: "Tensión de alimentación borne 30",
    1044: "Unidad de control mal codificada",
    1262: "Válvula de limitación de presión de sobrealimentación (N75)",
    1268: "Dosificador de caudal de combustible (N146)",
    65535: "Unidad de control averiada",
}


def describe_dtc(code, ftype, intermittent):
    desc = DTCS.get(code, "Código no incluido en la tabla (consultar documentación VAG)")
    t = FAULT_TYPES.get(ftype, f"Tipo de fallo {ftype}")
    extra = f" - {t}" if t else ""
    inter = " - INTERMITENTE" if intermittent else ""
    return f"{code:05d} {desc}  [{ftype:02d}{extra}{inter}]"


# ---------------------------------------------------------------------------
# Grupos de valores medidos habituales en EDC15 (1.9 TDI). Orientativo: la
# unidad real la da la formula que envia la ECU.
# ---------------------------------------------------------------------------
GRUPOS_EDC15 = {
    1: ("Inyección", ["Régimen", "Caudal inyectado", "Tensión dosificador/émbolo", "Temp. refrigerante"]),
    2: ("Acelerador", ["Régimen", "Pedal acelerador", "Estado de funcionamiento", "Temp. refrigerante"]),
    3: ("EGR / caudalímetro", ["Régimen", "Masa aire teórica", "Masa aire real", "Ciclo válvula EGR"]),
    4: ("Comienzo de inyección", ["Régimen", "Comienzo inyección teórico", "Comienzo inyección real", "Ciclo válvula"]),
    7: ("Temperaturas", ["Temp. combustible", "Valor 2", "Valor 3", "Temp. refrigerante"]),
    8: ("Limitación de caudal", ["Régimen", "Caudal solicitado", "Limitación por régimen", "Limitación por masa aire"]),
    10: ("Aire / presiones", ["Masa de aire", "Presión atmosférica", "Presión colector", "Pedal acelerador"]),
    11: ("Turbo", ["Régimen", "Presión sobrealim. teórica", "Presión sobrealim. real", "Ciclo N75"]),
    13: ("Marcha suave (cilindros)", ["Cilindro 1", "Cilindro 2", "Cilindro 3", "Cilindro 4"]),
}


MODULOS = {
    0x01: "Electrónica del motor",
    0x02: "Cambio automático",
    0x03: "ABS",
    0x08: "Climatronic",
    0x15: "Airbag",
    0x17: "Cuadro de instrumentos",
    0x35: "Cierre centralizado",
    0x56: "Radio",
}
