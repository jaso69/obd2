"""
Consumo de combustible y cronómetro 0-100 km/h a partir de los valores en vivo.

Sin interfaz: la ventana le pasa cada muestra ({clave: número}) con su instante
(time.monotonic()) y lee los resultados. Así se puede probar sin coche
(tests/prueba_consumo.py).

Cómo se calcula el consumo (L/h), por orden de preferencia:
  ELM327 · OBD2
    1. PID 5E (consumo que da la propia centralita).
    2. Aire aspirado / (relación estequiométrica × lambda) → gramos de combustible.
       El aire sale del caudalímetro (PID 10) o, si no hay, se estima con la presión
       del colector (PID 0B), el régimen (0C), la temperatura del aire (0F) y la
       cilindrada («speed density», rendimiento volumétrico 85 %).
       Lambda: en gasolina la comandada (PID 44) o 1; en diésel hace falta la sonda
       lambda de banda ancha (PID 24 o 34), porque un diésel trabaja con mucho aire
       de sobra y suponer lambda 1 daría consumos varias veces mayores.
  KKL · VAG (EDC15)
    Caudal inyectado (grupo 001, mg por carrera) × régimen × cilindros / 2.
    La EDC15 no da la velocidad: solo L/h y litros gastados.

Lo mismo que cualquier programa OBD: es una estimación (±10 % con caudalímetro).
"""
import time

GASOLINA, DIESEL = "gasolina", "diesel"

# relación aire/combustible estequiométrica y densidad (g/L)
AFR = {GASOLINA: 14.7, DIESEL: 14.5}
DENSIDAD = {GASOLINA: 745.0, DIESEL: 832.0}
R_AIRE = 287.05          # J/(kg·K)
RENDIMIENTO_VOL = 0.85

# PID 51 (tipo de combustible, SAE J1979): códigos que tratamos como gasolina o diésel
TIPO_PID51 = {1: GASOLINA, 4: DIESEL, 9: GASOLINA, 12: GASOLINA, 16: GASOLINA,
              17: GASOLINA, 19: DIESEL, 20: GASOLINA, 22: DIESEL}

P_VELOCIDAD, P_RPM, P_MAP, P_IAT, P_MAF, P_LAMBDA_CMD, P_CONSUMO = 0x0D, 0x0C, 0x0B, 0x0F, 0x10, 0x44, 0x5E
P_LAMBDA_ANCHA = (0x24, 0x34)

HUECO_MAX = 3.0          # s: si entre dos muestras pasa más, no se integra ese tramo
VENTANA = 2.0            # s: el consumo instantáneo se promedia en esta ventana


def pids_necesarios(soportados, combustible):
    """PIDs que hay que leer para el consumo y el 0-100 (lo menos posible: más muestras por segundo)."""
    s = set(soportados)
    out = [p for p in (P_VELOCIDAD, P_RPM) if p in s]
    if P_CONSUMO in s:
        return out + [P_CONSUMO]
    if P_MAF in s:
        out.append(P_MAF)
    elif P_MAP in s:
        out += [p for p in (P_MAP, P_IAT) if p in s]
    if combustible == GASOLINA and P_LAMBDA_CMD in s:
        out.append(P_LAMBDA_CMD)
    if combustible == DIESEL:
        out += [p for p in P_LAMBDA_ANCHA if p in s][:1]
    return out


def metodo(soportados, combustible):
    """Cómo se calculará el consumo: '5E', 'MAF', 'MAP' o None si no se puede."""
    s = set(soportados)
    if P_CONSUMO in s:
        return "5E"
    if combustible == DIESEL and not s.intersection(P_LAMBDA_ANCHA):
        return None
    if P_MAF in s:
        return "MAF"
    if {P_MAP, P_RPM}.issubset(s):
        return "MAP"
    return None


def litros_hora_obd(v, combustible, cilindrada):
    """Consumo en L/h con los PIDs leídos (v: {pid: número}); None si faltan datos."""
    if v.get(P_CONSUMO) is not None:
        return v[P_CONSUMO]
    aire = v.get(P_MAF)                                       # g/s
    if aire is None:
        mapa, rpm = v.get(P_MAP), v.get(P_RPM)
        if mapa is None or rpm is None or not cilindrada:
            return None
        t = (v.get(P_IAT) if v.get(P_IAT) is not None else 25) + 273.15
        aire = mapa * 1000 * cilindrada / 1000 * RENDIMIENTO_VOL * rpm / 120 / (R_AIRE * t) * 1000
    if combustible == DIESEL:
        lam = next((v[p] for p in P_LAMBDA_ANCHA if v.get(p) is not None), None)
        if lam is None:
            return None
    else:
        lam = v.get(P_LAMBDA_CMD) or 1.0
    if lam <= 0:
        return None
    gramos_s = aire / (AFR[combustible] * lam)
    return gramos_s * 3600 / DENSIDAD[combustible]


def litros_hora_vag(caudal_mg, rpm, cilindros):
    """EDC15: caudal inyectado (mg/carrera) → L/h de gasóleo (motor de 4 tiempos)."""
    if caudal_mg is None or rpm is None:
        return None
    mg_s = max(0.0, caudal_mg) * rpm / 60 * cilindros / 2
    return mg_s * 3600 / (DENSIDAD[DIESEL] * 1000)


class Trayecto:
    """Acumula consumo, distancia y tiempo de un trayecto."""

    def __init__(self):
        self.reiniciar()

    def reiniciar(self):
        self.litros = 0.0
        self.km = 0.0
        self.segundos = 0.0
        self.ultimo = None                  # (t, L/h, km/h)
        self.recientes = []                 # [(t, L/h, km/h)] de la ventana
        self.max_lh = 0.0

    def muestra(self, t, lh, kmh=None):
        """Una muestra: lh en L/h (o None), kmh en km/h (o None si no se conoce)."""
        if lh is None:
            return
        if self.ultimo:
            t0, lh0, v0 = self.ultimo
            dt = t - t0
            if 0 < dt <= HUECO_MAX:
                self.segundos += dt
                self.litros += (lh0 + lh) / 2 * dt / 3600
                if kmh is not None and v0 is not None:
                    self.km += (v0 + kmh) / 2 * dt / 3600
        self.ultimo = (t, lh, kmh)
        self.recientes.append((t, lh, kmh))
        self.recientes = [m for m in self.recientes if t - m[0] <= VENTANA]
        self.max_lh = max(self.max_lh, lh)

    def instantaneo(self):
        """(L/h, km/h) promediados en la ventana reciente; (None, None) sin datos."""
        if not self.recientes:
            return None, None
        lh = sum(m[1] for m in self.recientes) / len(self.recientes)
        vs = [m[2] for m in self.recientes if m[2] is not None]
        return lh, (sum(vs) / len(vs) if vs else None)

    def l100_instantaneo(self, vmin=5):
        lh, kmh = self.instantaneo()
        if lh is None or kmh is None or kmh < vmin:
            return None
        return lh / kmh * 100

    def l100_medio(self, km_min=0.1):
        return self.litros / self.km * 100 if self.km >= km_min else None


class Cronometro:
    """0-100 km/h (con el paso por 50). Se arma con el coche parado y mide al arrancar.

    Los instantes de salida y de paso por 50 y 100 se interpolan entre muestras:
    con un ELM327 (5-10 muestras/s) el error queda en una o dos décimas."""

    PARADO, LISTO, MIDIENDO = "parado", "listo", "midiendo"

    def __init__(self, objetivo=100, parcial=50):
        self.objetivo = objetivo
        self.parcial = parcial
        self.tiempos = []                   # [(0-100 s, 0-50 s o None)]
        self.mejor = None
        self.aviso = None                   # por qué se anuló la última medida
        self._a_cero()

    def _a_cero(self):
        self.estado = self.PARADO
        self.t_salida = None
        self.t_parcial = None
        self.v_max = 0
        self.anterior = None                # (t, km/h)

    def muestra(self, t, kmh):
        """Devuelve el tiempo 0-100 cuando se completa una medida; si no, None."""
        if kmh is None:
            return None
        ant = self.anterior
        self.anterior = (t, kmh)
        if ant and t - ant[0] > HUECO_MAX:              # hueco en las lecturas: no fiable
            if self.estado == self.MIDIENDO:
                self.aviso = "hueco"
            self._a_cero()
            self.anterior = (t, kmh)
            ant = None
        if kmh <= 0:
            if self.estado == self.MIDIENDO:
                self.aviso = "parada"
            self._a_cero()
            self.estado = self.LISTO
            self.anterior = (t, kmh)
            return None
        if self.estado == self.LISTO and ant:
            # salida: entre la última muestra a 0 y esta, extrapolando hacia atrás
            t0, v0 = ant
            self.t_salida = t0 + (t - t0) * 0.5 if v0 <= 0 else t0
            self.estado = self.MIDIENDO
            self.aviso = None
        if self.estado != self.MIDIENDO:
            return None
        self.v_max = max(self.v_max, kmh)
        if kmh < self.v_max - 5:                         # ha frenado o soltado: se anula
            self.aviso = "frenada"
            self._a_cero()
            return None
        cruce = lambda v: ant[0] + (v - ant[1]) / (kmh - ant[1]) * (t - ant[0]) if ant and kmh > ant[1] else t
        if self.t_parcial is None and kmh >= self.parcial:
            self.t_parcial = cruce(self.parcial)
        if kmh >= self.objetivo:
            total = cruce(self.objetivo) - self.t_salida
            parcial = self.t_parcial - self.t_salida if self.t_parcial else None
            self.tiempos.insert(0, (total, parcial))
            del self.tiempos[5:]
            self.mejor = total if self.mejor is None else min(self.mejor, total)
            self._a_cero()                               # hasta volver a parar
            return total
        return None

    def transcurrido(self, ahora=None):
        if self.estado != self.MIDIENDO:
            return None
        return (ahora if ahora is not None else time.monotonic()) - self.t_salida
