"""
Datos especificos VAG para KW1281: formulas de bloques de valores medidos,
codigos de averia (5 cifras) y grupos tipicos de la Bosch EDC15 (1.9 TDI).

Las formulas proceden de la documentacion publica del protocolo KW1281; si
algun valor sale raro, el programa muestra tambien el numero de formula y los
bytes a/b en bruto para poder revisarlo.
"""

import re

import idioma
import vag_p1
from idioma import tr

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
    0x0A: (lambda a, b: tr("FRÍO") if b == 0 else tr("CALIENTE"), ""),
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
        return f"a={a} b={b}", tr("(fórmula {f})", f=f"{formula:02X}h"), False
    fn, unit = f
    try:
        v = fn(a, b)
    except Exception:
        return f"a={a} b={b}", tr("(fórmula {f})", f=f"{formula:02X}h"), False
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
    20: "Fallo en el ajuste básico",
    21: "Tiempo de aumento de presión delantero demasiado largo",
    22: "Tiempo de reducción de presión delantero demasiado largo",
    23: "Tiempo de aumento de presión trasero demasiado largo",
    24: "Tiempo de reducción de presión trasero demasiado largo",
    27: "Señal no plausible",
}


# ---------------------------------------------------------------------------
# Codigos de averia VAG de 5 cifras (formato clasico 00xxx-01xxx).
# Los mismos numeros se usan en todas las centralitas VAG; aqui estan los mas
# habituales de motor (gasolina y TDI), cambio, ABS, airbag, cuadro e
# inmovilizador, confort y radio. Fuente: documentacion publica de VAG/KW1281.
# ---------------------------------------------------------------------------
DTCS = {
    # Cambio automático
    258: "Válvula magnética 1 del cambio (N88)",
    260: "Válvula magnética 2 del cambio (N89)",
    262: "Válvula magnética 3 del cambio (N90)",
    264: "Válvula magnética 4 del cambio (N91)",
    266: "Válvula magnética 5 del cambio (N92)",
    268: "Válvula magnética 6 del cambio (N93)",
    293: "Conmutador multifunción del cambio (F125)",
    300: "Transmisor de temperatura del ATF (G93)",
    652: "Supervisión de marchas",
    # Motor y comunes
    281: "Transmisor de velocidad del vehículo (G22)",
    282: "Posicionador de la mariposa (V60)",
    513: "Transmisor de régimen del motor (G28)",
    515: "Transmisor Hall / posición del árbol de levas (G40)",
    516: "Interruptor de ralentí (F60)",
    518: "Potenciómetro de la mariposa (G69)",
    519: "Transmisor de presión del colector de admisión (G71)",
    522: "Transmisor de temperatura del líquido refrigerante (G62)",
    523: "Transmisor de temperatura del aire de admisión (G42)",
    524: "Sensor de picado 1 (G61)",
    525: "Sonda lambda (G39)",
    532: "Tensión de alimentación (B+)",
    533: "Regulación del ralentí",
    537: "Regulación lambda",
    540: "Sensor de picado 2 (G66)",
    543: "Régimen máximo del motor sobrepasado",
    545: "Conexión eléctrica motor-cambio",
    550: "Regulación del comienzo de inyección",
    553: "Medidor de masa de aire (G70)",
    561: "Adaptación de la mezcla",
    575: "Presión en el colector de admisión (sobrepresión/turbo)",
    577: "Regulación de picado, cilindro 1",
    578: "Regulación de picado, cilindro 2",
    579: "Regulación de picado, cilindro 3",
    580: "Regulación de picado, cilindro 4",
    625: "Señal de velocidad del vehículo",
    626: "Testigo de tiempo de precalentamiento (K29)",
    638: "Conexión eléctrica motor-cambio 2",
    668: "Tensión de alimentación borne 30",
    1025: "Testigo de averías del motor (K83, MIL)",
    1044: "Unidad de control mal codificada",
    1087: "Ajuste básico no realizado",
    1119: "Señal de reconocimiento de marcha",
    1165: "Unidad de mando de la mariposa (J338)",
    1235: "Válvula de aire secundario (N112)",
    1237: "Válvula de corte de combustible (N109)",
    1242: "Etapas finales en la unidad de control",
    1247: "Válvula del depósito de carbón activo (N80)",
    1249: "Inyector del cilindro 1 (N30)",
    1250: "Inyector del cilindro 2 (N31)",
    1251: "Inyector del cilindro 3 (N32)",
    1252: "Inyector del cilindro 4 (N33)",
    1259: "Relé de la bomba de combustible (J17)",
    1262: "Válvula de limitación de presión de sobrealimentación (N75)",
    1264: "Bomba de aire secundario (V101)",
    1265: "Válvula de recirculación de gases de escape (EGR, N18)",
    1268: "Dosificador de caudal de combustible (N146)",
    # Bus de datos (CAN de tracción)
    1312: "Bus de datos de tracción",
    1314: "Unidad de control del motor (sin comunicación)",
    1316: "Unidad de control del ABS (sin comunicación)",
    1317: "Unidad de control en el cuadro de instrumentos (J285)",
    1321: "Unidad de control de los airbags (J234)",
    # ABS
    283: "Sensor de velocidad delantero izquierdo (G47)",
    285: "Sensor de velocidad delantero derecho (G45)",
    287: "Sensor de velocidad trasero derecho (G44)",
    290: "Sensor de velocidad trasero izquierdo (G46)",
    526: "Interruptor de la luz de freno (F)",
    1130: "Funcionamiento del ABS",
    1276: "Bomba hidráulica del ABS (V64)",
    # Airbag
    588: "Detonador del airbag del conductor (N95)",
    589: "Detonador del airbag del acompañante (N131)",
    595: "Datos de colisión memorizados",
    1217: "Detonador del airbag lateral del conductor (N199)",
    1218: "Detonador del airbag lateral del acompañante (N200)",
    1280: "Airbag del acompañante desactivado",
    # Cuadro de instrumentos e inmovilizador
    562: "Transmisor de nivel/temperatura del aceite (G266)",
    771: "Transmisor de nivel de combustible (G)",
    779: "Transmisor de temperatura exterior (G17)",
    1039: "Transmisor de temperatura del refrigerante del cuadro (G2)",
    1176: "Llave: señal demasiado baja (inmovilizador)",
    1177: "Unidad de control del motor (inmovilizador)",
    1179: "Programación de llave incorrecta (inmovilizador)",
    # Confort / cierre centralizado
    849: "Contacto S en el conmutador de encendido (D)",
    955: "Llave 1 (mando a distancia)",
    956: "Llave 2 (mando a distancia)",
    1330: "Unidad central del sistema de confort (J393)",
    1331: "Unidad de control de la puerta del conductor (J386)",
    1332: "Unidad de control de la puerta del acompañante (J387)",
    1333: "Unidad de control de la puerta trasera izquierda (J388)",
    1334: "Unidad de control de la puerta trasera derecha (J389)",
    # Radio
    852: "Altavoces delanteros",
    853: "Altavoces traseros",
    856: "Antena de radio",
    65535: "Unidad de control averiada",
}

# Codigos OBD especificos de VAG (P1xxx) en formato de 5 cifras (17xxx-18xxx):
# vag_p1.py, con la descripcion en espanol e ingles (no pasan por textos_en.py).
DTCS_P1 = dict(vag_p1.P1)


def codigo_obd(code):
    """Codigo OBD (p. ej. «P0300») equivalente a un codigo VAG 16xxx-18xxx, o None.

    VAG escribe los codigos OBD con 5 cifras: P0xxx = 16384 + xxx y
    P1xxx = 16408 + 1xxx (16684 = P0300, 17965 = P1557).
    """
    if 16384 <= code <= 17383:
        return f"P{code - 16384:04d}"
    if 17408 <= code <= 18407:
        return f"P{code - 16408:04d}"
    return None


def componente(code):
    """Descripcion del codigo de averia VAG (clasico o en formato OBD)."""
    if code in DTCS:
        return DTCS[code]
    p = codigo_obd(code)
    if p:
        if p.startswith("P1"):
            desc = DTCS_P1.get(int(p[1:]), tr("código específico de VAG no incluido en la tabla"))
        else:
            from obd_datos import describe_dtc as obd_desc
            desc = obd_desc(p)
        return f"{p} · {desc}"
    return tr("Código no incluido en la tabla (consultar documentación VAG)")


def describe_dtc(code, ftype, intermittent):
    desc = componente(code)
    t = FAULT_TYPES.get(ftype, tr("Tipo de fallo {n}", n=ftype))
    extra = f" - {t}" if t else ""
    inter = " - " + tr("INTERMITENTE") if intermittent else ""
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

# TDI inyector-bomba (PD, Bosch EDC15P/EDC16). Fuente: manual de taller VAG, «Display group
# overview» del TDI de inyector-bomba (Audi A3 8L).
GRUPOS_PD = {
    1: ("Inyección", ["Régimen", "Caudal inyectado", "Tiempo de inyección teórico", "Temp. refrigerante"]),
    2: ("Acelerador", ["Régimen", "Pedal acelerador", "Estado de funcionamiento", "Temp. refrigerante"]),
    3: ("EGR / caudalímetro", ["Régimen", "Masa aire teórica", "Masa aire real", "Ciclo válvula EGR"]),
    4: ("Inyectores-bomba", ["Régimen", "Comienzo inyección teórico", "Tiempo de inyección real",
                             "Ángulo de sincronización"]),
    6: ("Pedales y regulador de velocidad", ["Velocidad", "Interruptores de freno y embrague",
                                             "Pedal acelerador", "Regulador de velocidad"]),
    7: ("Temperaturas", ["Temp. combustible", "Valor 2", "Temp. colector de admisión", "Temp. refrigerante"]),
    8: ("Limitación de caudal", ["Régimen", "Caudal solicitado", "Limitación al cambiar de marcha",
                                 "Limitación por humos"]),
    10: ("Aire / presiones", ["Masa de aire", "Presión atmosférica", "Presión colector", "Pedal acelerador"]),
    11: ("Turbo", ["Régimen", "Presión sobrealim. teórica", "Presión sobrealim. real", "Ciclo N75"]),
    13: ("Marcha suave (cilindros)", ["Cilindro 1", "Cilindro 2", "Cilindro 3", "Cilindro 4"]),
    18: ("Estado de los inyectores-bomba", ["Inyector 1", "Inyector 2", "Inyector 3", "Inyector 4"]),
    23: ("Conmutación de los inyectores-bomba", ["Cilindro 1", "Cilindro 2", "Cilindro 3", "Cilindro 4"]),
}

# Gasolina: grupos estándar de VAG (Ross-Tech, «Standardized Measuring Blocks»), orientativos
# para motores de 1999-2000 en adelante. Algunos cambian según el motor (caudalímetro o
# sensor de presión, uno o dos bancos): el nombre lo indica entre paréntesis.
GRUPOS_GASOLINA = {
    1: ("Datos generales", ["Régimen", "Temp. refrigerante", "Regulación lambda",
                            "Condiciones del ajuste básico (o lambda banco 2)"]),
    2: ("Carga e inyección", ["Régimen", "Carga", "Tiempo de inyección medio", "Masa de aire (o presión colector)"]),
    3: ("Aire y encendido", ["Régimen", "Masa de aire (o presión colector)", "Ángulo de la mariposa",
                             "Avance de encendido"]),
    4: ("Tensión y temperaturas", ["Régimen", "Tensión", "Temp. refrigerante", "Temp. aire de admisión"]),
    5: ("Estado de funcionamiento", ["Régimen", "Carga", "Velocidad", "Estado de funcionamiento"]),
    10: ("Encendido", ["Régimen", "Carga", "Ángulo de la mariposa", "Avance de encendido"]),
    11: ("Encendido y temperaturas", ["Régimen", "Temp. refrigerante", "Temp. aire de admisión",
                                      "Avance de encendido"]),
    20: ("Picado: retraso del encendido", ["Cilindro 1", "Cilindro 2", "Cilindro 3", "Cilindro 4"]),
    22: ("Picado: cilindros 1 y 2", ["Régimen", "Carga", "Retraso cilindro 1", "Retraso cilindro 2"]),
    23: ("Picado: cilindros 3 y 4", ["Régimen", "Carga", "Retraso cilindro 3", "Retraso cilindro 4"]),
    31: ("Sondas lambda", ["Banco 1, sonda 1", "Banco 1, sonda 2", "Banco 2, sonda 1", "Banco 2, sonda 2"]),
    32: ("Adaptación de la mezcla", ["Banco 1, ralentí", "Banco 1, carga parcial", "Banco 2, ralentí",
                                    "Banco 2, carga parcial"]),
    33: ("Regulación lambda", ["Regulación lambda banco 1", "Tensión sonda banco 1", "Regulación lambda banco 2",
                              "Tensión sonda banco 2"]),
    115: ("Turbo", ["Régimen", "Carga", "Presión turbo teórica", "Presión turbo real"]),
    118: ("Turbo: válvula y temperatura", ["Régimen", "Temp. aire de admisión", "Ciclo válvula del turbo",
                                          "Presión antes de la mariposa"]),
}

# Tipo de motor -> (nombre, grupos, grupos marcados por defecto)
MOTORES = {
    "edc15": ("TDI bomba rotativa (EDC15V)", GRUPOS_EDC15, (1, 11)),
    "pd": ("TDI inyector-bomba (PD)", GRUPOS_PD, (1, 11)),
    "gasolina": ("Gasolina (grupos estándar)", GRUPOS_GASOLINA, (2, 3)),
}


def ajustes_basicos(motor):
    """Ajustes básicos habituales de la centralita del motor: {grupo: (título, condiciones,
    nombres de los campos o None para los del grupo de valores medidos)}."""
    egr = (tr("EGR desactivada (comprobar el caudalímetro)"),
           tr("Motor en marcha. La válvula EGR se cierra mientras dura, para comparar la masa de aire real con la "
              "esperada sin recirculación de gases."), None)
    if motor == "edc15":
        return {
            4: (tr("Comienzo de inyección (calado de la bomba)"),
                tr("Motor caliente (más de 80 °C) al ralentí. La centralita deja de regular el comienzo de inyección: "
                   "compara el real con el teórico para comprobar el calado de la bomba."), None),
            3: egr,
        }
    if motor == "pd":
        return {3: egr}
    if motor == "gasolina":
        cond = tr("Contacto puesto, motor parado y sin pisar el acelerador. Espera a que termine (unos 10 s, el "
                  "último campo cambia) y sal del ajuste básico. Se hace tras limpiar o cambiar la mariposa o tras "
                  "desconectar la batería.")
        return {
            98: (tr("Adaptación de la mariposa (acelerador por cable)"), cond,
                 [tr("Potenciómetro de la mariposa"), tr("Posicionador de la mariposa"),
                  tr("Estado de funcionamiento"), tr("Estado de la adaptación")]),
            60: (tr("Adaptación de la mariposa (acelerador electrónico)"), cond,
                 [tr("Potenciómetro 1 de la mariposa"), tr("Potenciómetro 2 de la mariposa"),
                  tr("Paso de la adaptación"), tr("Estado de la adaptación")]),
            1: (tr("Ajuste básico del motor (ralentí y avance)"),
                tr("Motor caliente al ralentí y sin consumidores (luces, aire acondicionado). La centralita fija el "
                   "ralentí y el avance para comprobarlos o ajustarlos."), None),
        }
    return {}


def detectar_motor(ident):
    """Tipo de motor (clave de MOTORES) según la identificación de la centralita de motor, o None.

    Diésel si pone EDC (Bosch EDC15/16); inyector-bomba si la referencia es 038906019, 038906012 o
    03G906 (las 038906018 son de bomba rotativa). Gasolina si describe el motor (p. ej.
    «1.8L R4/5VT», «2,0l R4/2V MOTR») sin EDC. Es una estimación: el usuario puede cambiarlo.
    """
    textos = [t.strip().upper() for t in ident if t and t.strip()]
    if not textos:
        return None
    todo = " ".join(textos)
    if "EDC" in todo:
        ref = textos[0].replace(" ", "")
        return "pd" if ref.startswith(("038906019", "038906012", "03G906")) else "edc15"
    if re.search(r"\d[.,]\d\s*L\s*[RV]\d", todo):
        return "gasolina"
    return None


MODULOS = {
    0x01: "Electrónica del motor",
    0x02: "Cambio automático",
    0x03: "ABS",
    0x08: "Climatronic",
    0x09: "Electrónica central",
    0x15: "Airbag",
    0x16: "Columna de dirección",
    0x17: "Cuadro de instrumentos",
    0x19: "Gateway (bus de datos)",
    0x22: "Tracción total (Haldex)",
    0x25: "Inmovilizador",
    0x35: "Cierre centralizado",
    0x36: "Memoria asiento conductor",
    0x37: "Navegación",
    0x45: "Alarma / habitáculo",
    0x46: "Módulo central de confort",
    0x55: "Faros (alcance / xenón)",
    0x56: "Radio",
    0x65: "Presión de neumáticos",
    0x76: "Ayuda al aparcamiento",
    0x77: "Teléfono",
}

# Traducción de las tablas al idioma de la interfaz (ver idioma.py)
for _t in (FAULT_TYPES, DTCS, MODULOS):
    idioma.tabla(_t)
idioma.tabla(DTCS_P1, lambda v: v[1] if idioma.actual() == "en" else v[0])
for _t in (GRUPOS_EDC15, GRUPOS_PD, GRUPOS_GASOLINA):
    idioma.tabla(_t, lambda v: (tr(v[0]), [tr(x) for x in v[1]]))
