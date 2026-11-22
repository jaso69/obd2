"""
Comunicacion OBD2 generica mediante ELM327 (USB, o Bluetooth SPP como puerto COM).

Se trabaja con cabeceras activadas (ATH1) para separar respuestas de varias
centralitas y reconstruir los mensajes multi-trama de CAN (ISO-TP).
"""
import re
import time

from obd_datos import PIDS, decode_dtc, decode_pid, monitores, pid_len

HEX_LINE = re.compile(r"^[0-9A-F ]+$")
ERRORES = ("UNABLE TO CONNECT", "BUS INIT", "BUS ERROR", "CAN ERROR", "ERROR",
           "STOPPED", "FB ERROR", "DATA ERROR", "LV RESET", "BUFFER FULL")


class ELM327Error(Exception):
    pass


class ELM327:
    def __init__(self, ser, bauds=(38400, 9600, 115200, 57600), debug=False, logger=None):
        self.ser = ser
        self.bauds = bauds
        self.debug = debug
        self.logger = logger or print
        self.version = ""
        self.proto_num = ""
        self.proto_name = ""
        self.is_can = False
        self.supported = set()
        self.multi = True          # peticiones de varios PIDs a la vez (solo CAN)
        self.connected = False

    def _dbg(self, msg):
        if self.debug:
            self.logger(f"[elm327] {msg}")

    # ------------------------------------------------------------------
    def _cmd(self, cmd, timeout=3.0):
        s = self.ser
        s.reset_input_buffer()
        s.write((cmd + "\r").encode("ascii"))
        buf = b""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            chunk = s.read(s.in_waiting or 1)
            if chunk:
                buf += chunk
                if b">" in buf:
                    break
        else:
            self._dbg(f"> {cmd}  [timeout] {buf!r}")
            raise ELM327Error(f"El ELM327 no responde al comando {cmd}")
        text = buf.decode("ascii", errors="ignore").replace(">", "").replace("\x00", "")
        lines = [l.strip() for l in re.split(r"[\r\n]+", text) if l.strip()]
        if lines and lines[0].replace(" ", "").upper() == cmd.replace(" ", "").upper():
            lines = lines[1:]                     # eco
        self._dbg(f"> {cmd:<10} {' | '.join(lines)}")
        return lines

    def connect(self):
        for baud in self.bauds:
            try:
                self.ser.baudrate = baud
            except Exception:
                pass
            try:
                self.ser.write(b"\r")
                time.sleep(0.1)
                lines = self._cmd("ATZ", timeout=3)
            except ELM327Error:
                continue
            ver = next((l for l in lines if "ELM" in l.upper()), None)
            if ver:
                self.version = ver
                break
        else:
            raise ELM327Error("No se detecta ningún ELM327 en el puerto. Comprueba el puerto COM "
                              "y que el adaptador esté conectado al coche (se alimenta del OBD).")
        for c in ("ATE0", "ATL0", "ATS1", "ATH1"):
            self._cmd(c)
        try:
            self._cmd("ATAT1")                    # tiempos adaptativos (algún clon no lo tiene)
        except ELM327Error:
            pass
        self._cmd("ATSP0")
        r = self._cmd("0100", timeout=25)          # la búsqueda de protocolo puede tardar
        if not any(HEX_LINE.match(l) for l in r):
            r = self._probar_linea_k(r)
        self.proto_num = self._cmd("ATDPN")[0].lstrip("A").upper()
        self.proto_name = self._cmd("ATDP")[0]
        self.is_can = self.proto_num in ("6", "7", "8", "9", "A", "B", "C")
        self.multi = self.is_can
        self.supported = self._read_supported(self._parse(r))
        self.connected = True

    # Protocolos de línea K que se fuerzan uno a uno si falla la búsqueda automática
    # (coches anteriores a CAN, p. ej. Mercedes de antes de ~2005, con clones que no
    # inicializan bien la línea K en modo automático).
    PROTOCOLOS_K = (("5", "ISO 14230-4 KWP2000 (inicio rápido)"),
                    ("4", "ISO 14230-4 KWP2000 (inicio lento)"),
                    ("3", "ISO 9141-2"))

    def _probar_linea_k(self, r_auto):
        self.logger(f"La búsqueda automática no encontró protocolo ({' '.join(r_auto) or 'sin respuesta'}). "
                    "Probando los protocolos de línea K uno a uno...")
        for num, nombre in self.PROTOCOLOS_K:
            self.logger(f"Probando {nombre}...")
            try:
                self._cmd("ATPC", timeout=2)       # cierra el intento anterior
                self._cmd(f"ATSP{num}")
                r = self._cmd("0100", timeout=12)  # el inicio lento tarda unos 3 s
                if not any(HEX_LINE.match(l) for l in r):
                    r = self._cmd("0100", timeout=12)   # segundo intento: a veces el 1.º solo despierta la ECU
            except ELM327Error:
                continue
            if any(HEX_LINE.match(l) for l in r):
                self.logger(f"El coche responde por {nombre}.")
                return r
        try:
            self._cmd("ATSP0")                     # deja el adaptador en automático
        except ELM327Error:
            pass
        raise ELM327Error(
            f"El vehículo no responde a OBD2 ({' '.join(r_auto) or 'sin respuesta'}); probados también "
            "KWP2000 e ISO 9141 a mano.\n"
            "Pon el contacto. Si es un VAG anterior a 2004 (p. ej. el Toledo TDI del 2000) "
            "usa el modo KKL · VAG KW1281. Algunos coches con conector OBD2 (p. ej. Mercedes "
            "anteriores a 2001 en gasolina o 2004 en diésel) no cumplen OBD2 y solo responden "
            "a herramientas de la marca. Con línea K, muchos clones baratos de ELM327 tampoco funcionan.")

    # ------------------------------------------------------------------
    def _parse(self, lines):
        """Convierte las lineas en {ecu: [mensaje(bytes), ...]}."""
        frames = {}
        for line in lines:
            line = line.upper()
            if not HEX_LINE.match(line):
                continue
            tok = line.split()
            try:
                if self.is_can:
                    if len(tok[0]) == 3:            # CAN 11 bits: "7E8 06 41 ..."
                        ecu, data = tok[0], tok[1:]
                    else:                           # CAN 29 bits: "18 DA F1 10 06 41 ..."
                        ecu, data = tok[3], tok[4:]
                else:                               # Linea K: "48 6B 10 41 0C 1A F8 xx"
                    if len(tok) < 5:
                        continue
                    fmt = int(tok[0], 16)
                    if self.proto_num in ("4", "5") and fmt & 0x80 and not fmt & 0x3F and len(tok) >= 6:
                        ecu, data = tok[2], tok[4:-1]   # KWP2000 con byte de longitud aparte
                    else:
                        ecu, data = tok[2], tok[3:-1]   # se quita el checksum
                frames.setdefault(ecu, []).append(bytes(int(x, 16) for x in data))
            except ValueError:
                continue
        if not self.is_can:
            return frames
        return {ecu: self._isotp(fl) for ecu, fl in frames.items()}

    @staticmethod
    def _isotp(frames):
        msgs, cur, length = [], None, 0
        for f in frames:
            if not f:
                continue
            kind = f[0] >> 4
            if kind == 0:
                msgs.append(f[1:1 + (f[0] & 0x0F)])
            elif kind == 1 and len(f) > 1:
                length = ((f[0] & 0x0F) << 8) | f[1]
                cur = bytearray(f[2:])
            elif kind == 2 and cur is not None:
                cur += f[1:]
                if len(cur) >= length:
                    msgs.append(bytes(cur[:length]))
                    cur = None
        if cur is not None:
            msgs.append(bytes(cur))
        return msgs

    @staticmethod
    def _engine(resp):
        """Mensajes de la centralita de motor (7E8 / 10) o, si no, de la primera."""
        for ecu in ("7E8", "10", "11"):
            if ecu in resp:
                return resp[ecu]
        return resp[sorted(resp)[0]] if resp else []

    def query(self, cmd, timeout=3.0):
        lines = self._cmd(cmd, timeout)
        errs = [l for l in lines if any(e in l.upper() for e in ERRORES)]
        if errs and not any(HEX_LINE.match(l.upper()) for l in lines):
            raise ELM327Error(f"Error de comunicación: {' '.join(errs)}")
        return self._parse(lines)

    # ------------------------------------------------------------------
    def _read_supported(self, first):
        sup = set()
        base, resp = 0x00, first
        while True:
            msg = next((m for m in self._engine(resp) if len(m) >= 6 and m[0] == 0x41 and m[1] == base), None)
            if not msg:
                break
            bits = int.from_bytes(msg[2:6], "big")
            for i in range(32):
                if bits & (1 << (31 - i)):
                    sup.add(base + i + 1)
            if base + 0x20 not in sup or base >= 0xC0:
                break
            base += 0x20
            resp = self.query(f"01{base:02X}")
        return sup

    def read_pids(self, pids):
        """Devuelve {pid: bytes_de_datos} de los PIDs que respondan."""
        out = {}
        pending = [p for p in pids if pid_len(p)]
        if self.multi:
            for i in range(0, len(pending), 6):
                chunk = pending[i:i + 6]
                try:
                    got = self._read_multi(chunk)
                except ELM327Error:
                    got = None
                if got is None or len(got) < len(chunk):
                    self.multi = False             # el adaptador/ECU no lo soporta bien
                    self._dbg("Desactivadas peticiones multi-PID")
                    break
                out.update(got)
        for p in pending:
            if p in out:
                continue
            msgs = self._engine(self.query(f"01{p:02X}"))
            msg = next((m for m in msgs if len(m) >= 2 and m[0] == 0x41 and m[1] == p), None)
            if msg:
                out[p] = msg[2:]
        return out

    def _read_multi(self, pids):
        msgs = self._engine(self.query("01" + "".join(f"{p:02X}" for p in pids)))
        out = {}
        for m in msgs:
            if not m or m[0] != 0x41:
                continue
            i = 1
            while i < len(m):
                p = m[i]
                n = pid_len(p)
                if n is None or i + 1 + n > len(m):
                    return None
                out[p] = m[i + 1:i + 1 + n]
                i += 1 + n
        return out

    def _dtcs(self, mode, resp_id):
        resp = self.query(mode, timeout=5)
        codes = []
        for ecu, msgs in resp.items():
            data = bytearray()
            for m in msgs:
                if not m or m[0] != resp_id:
                    continue
                data += m[2:] if self.is_can else m[1:]   # en CAN el 2.o byte es el n.o de códigos
            for i in range(0, len(data) - 1, 2):
                if data[i] == 0 and data[i + 1] == 0:
                    continue
                c = decode_dtc(data[i], data[i + 1])
                if c not in codes:
                    codes.append(c)
        return codes

    def read_dtcs(self):
        try:
            permanentes = self._dtcs("0A", 0x4A)   # modo 0A: solo coches de ~2010 en adelante
        except ELM327Error:
            permanentes = []
        return {"stored": self._dtcs("03", 0x43), "pending": self._dtcs("07", 0x47),
                "permanent": permanentes, "mil": self.mil()[0]}

    def clear_dtcs(self):
        resp = self.query("04", timeout=5)
        if not any(m and m[0] == 0x44 for msgs in resp.values() for m in msgs):
            raise ELM327Error("La centralita no confirmó el borrado (pon el contacto con el motor parado).")

    def mil(self):
        msg = next((m for m in self._engine(self.query("0101")) if len(m) >= 3 and m[0] == 0x41), None)
        if not msg:
            return None, None
        return bool(msg[2] & 0x80), msg[2] & 0x7F

    def readiness(self):
        """Monitores de preparación: (diesel, [(nombre, completo)]) o None."""
        msg = next((m for m in self._engine(self.query("0101")) if len(m) >= 6 and m[0] == 0x41), None)
        if not msg:
            return None
        return monitores(msg[3], msg[4], msg[5])

    def _soportados_ff(self):
        """PIDs disponibles en los datos congelados (modo 02, trama 0)."""
        sup, base = set(), 0x00
        while base <= 0xC0:
            msg = next((m for m in self._engine(self.query(f"02{base:02X}00"))
                        if len(m) >= 7 and m[0] == 0x42 and m[1] == base), None)
            if not msg:
                break
            bits = int.from_bytes(msg[3:7], "big")
            for i in range(32):
                if bits & (1 << (31 - i)):
                    sup.add(base + i + 1)
            if base + 0x20 not in sup:
                break
            base += 0x20
        return sup

    def freeze_frame(self):
        """Datos congelados de la avería que encendió el testigo.

        Devuelve {"dtc": "P0171", "values": [(pid, nombre, valor, unidad)]} o None
        si no hay datos congelados guardados."""
        try:
            msg = next((m for m in self._engine(self.query("020200"))
                        if len(m) >= 5 and m[0] == 0x42 and m[1] == 0x02), None)
        except ELM327Error:
            return None
        if not msg or (msg[3] == 0 and msg[4] == 0):
            return None
        sup = self._soportados_ff() or (self.supported & set(PIDS))
        valores = []
        for p in sorted(sup):
            if p not in PIDS:
                continue
            try:
                r = next((m for m in self._engine(self.query(f"02{p:02X}00"))
                          if len(m) >= 3 and m[0] == 0x42 and m[1] == p), None)
            except ELM327Error:
                continue
            if r:
                nombre, valor, unidad, _ = decode_pid(p, r[3:])
                valores.append((p, nombre, valor, unidad))
        return {"dtc": decode_dtc(msg[3], msg[4]), "values": valores}

    def _info(self, tipo):
        """Datos del modo 09 (infotipo «tipo») unidos en bytes, o b""."""
        try:
            msgs = self._engine(self.query(f"09{tipo:02X}", timeout=5))
        except ELM327Error:
            return b""
        raw = bytearray()
        for m in msgs:
            if len(m) > 3 and m[0] == 0x49 and m[1] == tipo:
                raw += m[3:]
        return bytes(raw)

    def identificacion(self):
        """Calibración (CALID), CVN y nombre de la centralita (modo 09)."""
        def texto(b):
            return "".join(chr(c) for c in b if 32 <= c < 127).strip()
        cal = self._info(0x04)
        calids = [t for t in (texto(cal[i:i + 16]) for i in range(0, len(cal), 16)) if t]
        cvn = self._info(0x06)
        cvns = [cvn[i:i + 4].hex().upper() for i in range(0, len(cvn) - 3, 4)]
        nombre = texto(self._info(0x0A).replace(b"\x00", b" "))
        return {"calid": calids, "cvn": cvns, "nombre": nombre}

    def vin(self):
        try:
            msgs = self._engine(self.query("0902", timeout=5))
        except ELM327Error:
            return None
        raw = bytearray()
        for m in msgs:
            if len(m) > 3 and m[0] == 0x49 and m[1] == 0x02:
                raw += m[3:]
        txt = "".join(chr(c) for c in raw if 32 < c < 127)
        return txt[-17:] if txt else None

    def voltage(self):
        try:
            return self._cmd("ATRV")[0]
        except (ELM327Error, IndexError):
            return None

    def obd_standard(self):
        if 0x1C not in self.supported:
            return None
        msg = next((m for m in self._engine(self.query("011C")) if len(m) >= 3 and m[0] == 0x41), None)
        return msg[2] if msg else None

    def close(self):
        self.connected = False
        try:
            self._cmd("ATPC", timeout=1)          # cierra el protocolo
        except ELM327Error:
            pass
