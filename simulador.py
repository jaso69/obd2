"""
Simulador de cable KKL + ECU EDC15 (KW1281) para probar sin coche.

Imita un objeto serial.Serial: eco de la linea K, init de 5 baudios decodificado
por tiempos reales del 'break', complementos byte a byte, contador de bloques,
identificacion, averias, borrado y grupos de valores medidos.
"""
import math
import random
import time
from collections import deque

ECU_BAUD = 9600


class FakeECU:
    def __init__(self, address=0x01, ident=None, dtcs=None):
        self.address = address
        self.dtcs = [(553, 0x1B), (1262, 0x08 | 0x80)] if dtcs is None else dtcs   # G70 no plausible, N75 intermitente
        self.ident = ident or [b"038906018FQ ", b"1,9l R4 EDC  ", b"   SG  1234",
                               bytes([0x00, 0x00, 0x04, 0x22, 0x00, 0x00])]
        self.t0 = time.monotonic()
        self.reset()

    def reset(self):
        self.state = "idle"
        self.counter = 0
        self.out = []          # bytes del bloque que se esta enviando
        self.out_idx = 0
        self.inbuf = []
        self.queue = deque()

    # --- valores simulados -------------------------------------------------
    def _rpm(self):
        t = time.monotonic() - self.t0
        return 880 + 600 * max(0.0, math.sin(t / 3)) + random.uniform(-20, 20)

    def _group(self, g):
        if self.address != 0x01:
            return None
        rpm = self._rpm()
        coolant = min(90.0, 20 + (time.monotonic() - self.t0) * 2)
        load = (rpm - 880) / 600
        if g == 1:
            return [(0x01, 200, int(rpm / 40)),          # rpm = a*b/5
                    (0x27, 100, int((4 + 20 * load) * 2.56)),  # mg/H
                    (0x06, 250, int(1500 / 250)),         # V
                    (0x05, 10, int(coolant + 100))]       # °C
        if g == 3:
            spec = 250 + 400 * load
            return [(0x01, 200, int(rpm / 40)),
                    (0x31, 100, int(spec / 2.5)),          # mg/H = b/4*a*0.1
                    (0x31, 100, int((spec + random.uniform(-15, 15)) / 2.5)),
                    (0x17, 100, int(255 * (0.6 - 0.5 * load)))]
        if g == 10:
            return [(0x31, 100, int((300 + 400 * load) / 2.5)),
                    (0x12, 250, 101),
                    (0x12, 250, int(101 + 80 * load)),
                    (0x17, 100, int(255 * load))]
        if g == 11:
            spec = 1000 + 1000 * load
            return [(0x01, 200, int(rpm / 40)),
                    (0x12, 250, int(spec / 10)),
                    (0x12, 250, int((spec + random.uniform(-40, 40)) / 10)),
                    (0x17, 100, int(255 * (0.4 + 0.4 * load)))]
        return None

    # --- bloques -------------------------------------------------------------
    def _start_block(self, title, data=b""):
        self.counter = (self.counter + 1) & 0xFF
        self.out = [len(data) + 3, self.counter, title, *data, 0x03]
        self.out_idx = 0
        self.state = "send"
        return [self.out[0]]

    def _process(self, blk):
        cnt, title, data = blk[1], blk[2], bytes(blk[3:-1])
        self.counter = cnt
        if title == 0x09 and self.queue:
            t, d = self.queue.popleft()
            return self._start_block(t, d)
        if title == 0x09:
            return self._start_block(0x09)
        if title == 0x06:
            self.reset()
            return []
        if title == 0x07:
            for i in range(0, max(len(self.dtcs), 1), 4):
                chunk = self.dtcs[i:i + 4]
                d = b"".join(bytes([c >> 8, c & 0xFF, s]) for c, s in chunk) or bytes([0xFF, 0xFF, 0x88])
                self.queue.append((0xFC, d))
            t, d = self.queue.popleft()
            return self._start_block(t, d)
        if title == 0x05:
            self.dtcs = []
            return self._start_block(0xFC, bytes([0xFF, 0xFF, 0x88]))
        if title == 0x29:
            vals = self._group(data[0])
            if vals is None:
                return self._start_block(0x0A, bytes([cnt]))
            return self._start_block(0xE7, bytes(max(0, min(255, x)) for v in vals for x in v))
        return self._start_block(0x0A, bytes([cnt]))

    def start_session(self):
        for blk in self.ident[1:]:
            self.queue.append((0xF6, blk))
        self.counter = 0
        first = self._start_block(0xF6, self.ident[0])
        return first

    def on_host_byte(self, b):
        """Byte recibido del tester. Devuelve bytes que la ECU envia como respuesta."""
        if self.state == "wait_kw":
            if b == 0x75:
                return self.start_session()
            self.reset()
            return []
        if self.state == "send":
            expected = 0xFF ^ self.out[self.out_idx]
            if b != expected:
                self.reset()
                return []
            self.out_idx += 1
            nxt = self.out[self.out_idx]
            if self.out_idx == len(self.out) - 1:
                self.state = "recv"
                self.inbuf = []
            return [nxt]
        if self.state == "recv":
            self.inbuf.append(b)
            n = self.inbuf[0]
            if len(self.inbuf) == n + 1:          # recibido el 0x03 final
                if b != 0x03:
                    self.reset()
                    return []
                return self._process(self.inbuf)
            return [0xFF ^ b]
        return []


def coche_simulado():
    """Centralitas del coche simulado en la línea K: motor, ABS, airbag y cuadro."""
    return [FakeECU(),
            FakeECU(0x03, [b"1J0907379G  ", b"ABS ITT AE 20 GI", b"   0001"], [(287, 0x03 | 0x80)]),
            FakeECU(0x15, [b"1C0909601   ", b"AIRBAG VW61 ", b"   0003"], []),
            FakeECU(0x17, [b"1M0920821C  ", b"KOMBI+WEGFAHRSP", b"   0002"], [(779, 0x05)])]


class FakeSerial:
    """Sustituto de serial.Serial con cable KKL y las centralitas simuladas."""

    def __init__(self, ecu=None, ecus=None):
        self.ecus = {e.address: e for e in (ecus or ([ecu] if ecu else coche_simulado()))}
        self.ecu = self.ecus.get(0x01) or next(iter(self.ecus.values()))
        self.baudrate = 9600
        self.timeout = 0.05
        self.dtr = True
        self.rts = False
        self.rx = deque()
        self._brk = False
        self._edges = []           # (tiempo, nivel_bajo)
        self.is_open = True

    @property
    def in_waiting(self):
        return len(self.rx)

    @property
    def break_condition(self):
        return self._brk

    @break_condition.setter
    def break_condition(self, value):
        if value != self._brk:
            self._edges.append((time.perf_counter(), value))
            if value and self.ecu.state != "idle":
                self.ecu.reset()
        self._brk = value

    def _check_init(self):
        if self._brk or not self._edges:
            return
        t_start = next((t for t, low in self._edges if low), None)
        if t_start is None or time.perf_counter() - t_start < 1.8 + 0.015:
            return

        def level_low(t):
            low = False
            for te, l in self._edges:
                if te <= t:
                    low = l
            return low

        bits = [0 if level_low(t_start + 0.1 + 0.2 * i) else 1 for i in range(1, 9)]
        self._edges = []
        addr = sum(bit << i for i, bit in enumerate(bits)) & 0x7F
        if addr not in self.ecus:
            return
        if self.ecu is not self.ecus[addr]:
            self.ecu.reset()
            self.ecu = self.ecus[addr]
        if self.baudrate != ECU_BAUD:
            self.rx.extend([0xF8, 0x00])          # basura: velocidad incorrecta
            return
        self.ecu.reset()
        self.ecu.state = "wait_kw"
        self.rx.extend([0x55, 0x01, 0x8A])

    def write(self, data):
        for b in data:
            self.rx.append(b)                      # eco de la linea K
            if self.baudrate == ECU_BAUD:
                self.rx.extend(self.ecu.on_host_byte(b))
        return len(data)

    def read(self, n=1):
        self._check_init()
        if not self.rx:
            time.sleep(self.timeout)
            self._check_init()
            if not self.rx:
                return b""
        out = bytearray()
        while self.rx and len(out) < n:
            out.append(self.rx.popleft())
        return bytes(out)

    def reset_input_buffer(self):
        self.rx.clear()

    def close(self):
        self.is_open = False


# ===========================================================================
# ELM327 simulado (coche de gasolina generico, CAN 11 bits 500 kbps)
# ===========================================================================
class FakeELMSerial:
    """Sustituto de serial.Serial que se comporta como un ELM327 conectado a un coche."""

    SUPPORTED = {0x01, 0x03, 0x04, 0x05, 0x06, 0x07, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10,
                 0x11, 0x13, 0x14, 0x15, 0x1C, 0x1F, 0x20, 0x21, 0x2F, 0x30, 0x31, 0x33,
                 0x40, 0x42, 0x44, 0x45, 0x46, 0x49, 0x4A, 0x4C, 0x51}
    VIN = "VSSZZZ6KZYR000001"

    NOMBRES = {"3": "ISO 9141-2", "4": "ISO 14230-4 (KWP 5BAUD)", "5": "ISO 14230-4 (KWP FAST)",
               "6": "ISO 15765-4 (CAN 11/500)"}

    def __init__(self, protocolo="6", auto_falla=False, cabecera_larga=False):
        """protocolo: el del coche simulado ("6" CAN; "3", "4", "5" línea K).
        auto_falla: la búsqueda automática (ATSP0) no lo encuentra, como pasa con
        algunos coches de línea K y clones. cabecera_larga: KWP2000 con el byte de
        longitud aparte (cabecera de 4 bytes)."""
        self.protocolo = protocolo
        self.auto_falla = auto_falla
        self.cabecera_larga = cabecera_larga
        self.actual = "0"                     # protocolo elegido con ATSP
        self.baudrate = 38400
        self.timeout = 0.05
        self.rx = deque()
        self.buf = ""
        self.echo = True
        self.t0 = time.monotonic()
        self.stored = ["P0171", "P0420"]
        self.pending = ["P0301"]
        self.permanent = ["P0420"]            # el borrado no las quita (hasta que el monitor pase)
        # Datos congelados de la P0171: {pid: bytes}
        self.ff = {0x04: [0x5C], 0x05: [0x7B], 0x06: [0x9E], 0x07: [0x96], 0x0B: [0x40],
                   0x0C: [0x0F, 0xA0], 0x0D: [0x46], 0x0F: [0x3E], 0x10: [0x05, 0xDC], 0x11: [0x30]}
        self.is_open = True

    @property
    def in_waiting(self):
        return len(self.rx)

    def read(self, n=1):
        if not self.rx:
            time.sleep(self.timeout)
            return b""
        out = bytearray()
        while self.rx and len(out) < n:
            out.append(self.rx.popleft())
        return bytes(out)

    def write(self, data):
        self.buf += data.decode("ascii", errors="ignore")
        while "\r" in self.buf:
            cmd, self.buf = self.buf.split("\r", 1)
            self.rx.extend(self._respond(cmd).encode("ascii"))
        return len(data)

    def reset_input_buffer(self):
        self.rx.clear()

    def close(self):
        self.is_open = False

    # ------------------------------------------------------------------
    def _respond(self, cmd):
        c = cmd.strip().upper().replace(" ", "")
        if not c:
            return "\r>"
        if c.startswith("AT"):
            if c == "ATZ":
                self.echo = True
                out = ["", "ELM327 v1.5"]
            elif c == "ATE0":
                out = ["OK"]
                text = (cmd + "\r" if self.echo else "") + "OK\r\r>"
                self.echo = False
                return text
            elif c.startswith("ATSP"):
                self.actual = c[4:] or "0"
                out = ["OK"]
            elif c == "ATDPN":
                out = [("A" if self.actual == "0" else "") + self.protocolo]
            elif c == "ATDP":
                out = [("AUTO, " if self.actual == "0" else "") + self.NOMBRES[self.protocolo]]
            elif c == "ATRV":
                out = ["14.2V"]
            elif c == "ATI":
                out = ["ELM327 v1.5"]
            else:
                out = ["OK"]
        elif self.actual == "0" and self.auto_falla:
            out = ["SEARCHING...", "UNABLE TO CONNECT"]
        elif self.actual not in ("0", self.protocolo):
            out = ["BUS INIT: ...ERROR"] if self.actual in "345" else ["NO DATA"]
        else:
            out = self._obd(c)
        return (cmd + "\r" if self.echo else "") + "\r".join(out) + "\r\r>"

    def _frames(self, payload):
        if self.protocolo in "345":
            return self._frames_k(payload)
        if len(payload) <= 7:
            return ["7E8 " + " ".join(f"{b:02X}" for b in [len(payload)] + payload)]
        lines = ["7E8 10 " + " ".join(f"{b:02X}" for b in [len(payload)] + payload[:6])]
        rest, seq = payload[6:], 1
        while rest:
            chunk = (rest[:7] + [0] * 7)[:7]
            lines.append("7E8 " + " ".join(f"{b:02X}" for b in [0x20 | (seq & 0xF)] + chunk))
            rest, seq = rest[7:], seq + 1
        return lines

    def _frames_k(self, payload):
        """Línea K: sin ISO-TP; las respuestas largas van en varios mensajes."""
        modo = payload[0]
        if modo in (0x43, 0x47, 0x4A):                       # 3 códigos por mensaje, sin contador
            codes = payload[2:] or [0, 0]
            msgs = [[modo] + (codes[i:i + 6] + [0] * 6)[:6] for i in range(0, len(codes), 6)]
        elif modo == 0x49 and payload[1] == 0x02:      # VIN: 5 mensajes de 4 bytes
            vin = [0, 0, 0] + payload[3:]
            msgs = [[0x49, 0x02, n + 1] + vin[n * 4:n * 4 + 4] for n in range(5)]
        elif modo == 0x49:                             # CALID, CVN, nombre: mensajes de 4 bytes
            d = payload[3:]
            msgs = [[0x49, payload[1], n // 4 + 1] + d[n:n + 4] for n in range(0, len(d), 4)]
        else:
            msgs = [payload]
        out = []
        for m in msgs:
            if self.protocolo == "3":
                head = [0x48, 0x6B, 0x10]
            elif self.cabecera_larga:
                head = [0x80, 0xF1, 0x10, len(m)]
            else:
                head = [0x80 | len(m), 0xF1, 0x10]
            trama = head + m
            out.append(" ".join(f"{b:02X}" for b in trama + [sum(trama) & 0xFF]))
        return out

    @staticmethod
    def _enc(code):
        letra = "PCBU".index(code[0])
        a = (letra << 6) | (int(code[1]) << 4) | int(code[2], 16)
        return [a, int(code[3:5], 16)]

    def _obd(self, c):
        try:
            mode = c[:2]
            if mode == "01":
                payload = [0x41]
                for i in range(2, len(c), 2):
                    p = int(c[i:i + 2], 16)
                    d = self._pid(p)
                    if d is not None:
                        payload += [p] + d
                return self._frames(payload) if len(payload) > 1 else ["NO DATA"]
            if mode in ("03", "07", "0A"):
                codes = {"03": self.stored, "07": self.pending, "0A": self.permanent}[mode]
                payload = [0x40 + int(mode, 16), len(codes)]
                for code in codes:
                    payload += self._enc(code)
                return self._frames(payload)
            if mode == "04":
                self.stored, self.pending, self.ff = [], [], {}
                return self._frames([0x44])
            if mode == "02" and len(c) == 6:
                p = int(c[2:4], 16)
                if p == 0x02:
                    return self._frames([0x42, 0x02, 0x00] + (self._enc("P0171") if self.ff else [0, 0]))
                if p == 0x00:
                    bits = sum(1 << (31 - (q - 1)) for q in list(self.ff) + [0x02] if q <= 0x20)
                    return self._frames([0x42, 0x00, 0x00] + list(bits.to_bytes(4, "big")))
                if p in self.ff:
                    return self._frames([0x42, p, 0x00] + self.ff[p])
                return ["NO DATA"]
            if c == "0902":
                return self._frames([0x49, 0x02, 0x01] + [ord(x) for x in self.VIN])
            if c == "0904":
                return self._frames([0x49, 0x04, 0x01] + [ord(x) for x in "SIM-CAL-0471".ljust(16, "\0")])
            if c == "0906":
                return self._frames([0x49, 0x06, 0x01, 0x1A, 0x2B, 0x3C, 0x4D])
            if c == "090A":
                return self._frames([0x49, 0x0A, 0x01] + [ord(x) for x in "ECM\0-EngineControl".ljust(20, "\0")])
        except ValueError:
            return ["?"]
        return ["NO DATA"]

    def _pid(self, p):
        if p in (0x00, 0x20, 0x40, 0x60):
            bits = 0
            for i in range(32):
                if p + i + 1 in self.SUPPORTED:
                    bits |= 1 << (31 - i)
            return list(bits.to_bytes(4, "big")) if bits or p == 0 else None
        if p not in self.SUPPORTED:
            return None
        t = time.monotonic() - self.t0
        f = max(0.0, math.sin(t / 4))                   # 0 = ralentí, 1 = acelerando
        rpm = 800 + 2200 * f + random.uniform(-15, 15)
        clamp = lambda v: max(0, min(255, int(v)))
        u16 = lambda v: [(int(v) >> 8) & 0xFF, int(v) & 0xFF]
        valores = {
            0x01: [0x80 | len(self.stored) if self.stored else 0, 0x07, 0xE5, 0x04],   # EVAP sin completar
            0x03: [0x02, 0x00],
            0x04: [clamp(255 * (0.18 + 0.6 * f))],
            0x05: [clamp(min(90, 20 + t * 2) + 40)],
            0x06: [clamp(128 + random.uniform(-6, 6))],
            0x07: [clamp(128 + 9)],
            0x0B: [clamp(32 + 60 * f)],
            0x0C: u16(rpm * 4),
            0x0D: [clamp(130 * f if f > 0.05 else 0)],     # para 0 s, pasa de 100 (cronómetro 0-100)
            0x0E: [clamp((8 + 18 * f + 64) * 2)],
            0x0F: [clamp(24 + 40)],
            0x10: u16((3 + 38 * f) * 100),
            0x11: [clamp(255 * (0.13 + 0.55 * f))],
            0x13: [0x03],
            0x14: [clamp(200 * (0.45 + 0.4 * math.sin(t * 5))), 0xFF],
            0x15: [clamp(200 * 0.68), 0xFF],
            0x1C: [6],
            0x1F: u16(t),
            0x21: u16(42),
            0x2F: [clamp(255 * 0.62)],
            0x30: [12],
            0x31: u16(300),
            0x33: [101],
            0x42: u16(14200 + random.uniform(-80, 80)),
            0x44: u16(32768),
            0x45: [clamp(255 * 0.5 * f)],
            0x46: [18 + 40],
            0x49: [clamp(255 * (0.15 + 0.6 * f))],
            0x4A: [clamp(255 * (0.08 + 0.3 * f))],
            0x4C: [clamp(255 * 0.55 * f)],
            0x51: [1],                                      # gasolina
        }
        return valores.get(p, [0])
