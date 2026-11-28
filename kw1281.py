"""
Implementacion del protocolo VAG KW1281 (KWP1281) sobre cable KKL (FTDI).

Resumen del protocolo
---------------------
* Linea K (pin 7 del OBD), half-duplex: todo lo que enviamos vuelve como eco.
* Inicio: direccion del modulo (0x01 = motor) enviada a 5 baudios, 7 bits +
  paridad impar, generada con "break" en el puerto serie (linea K a masa).
* La ECU responde a su velocidad (9600 o 10400 baudios normalmente):
      0x55 (sync)  KW1  KW2      -> para KW1281: 0x01 0x8A
  y el tester contesta con el complemento de KW2 (0xFF ^ 0x8A = 0x75).
* Despues se intercambian bloques por turnos:
      [longitud] [contador] [titulo] [datos...] [0x03]
  longitud = n.o de bytes tras ella (incluido el 0x03).
  Cada byte, salvo el 0x03 final, lo confirma el receptor enviando su
  complemento (0xFF ^ byte). El contador sube 1 en cada bloque (de ambos lados).
* Si nadie tiene nada que decir, se intercambian bloques ACK (0x09) para
  mantener viva la sesion; si se deja de hacer ~1 s, la ECU corta.
"""
import threading
import time

from idioma import tr

# Titulos de bloque
ACK = 0x09
ACTUATOR_TEST = 0x04
NAK = 0x0A
END_COMM = 0x06
CLEAR_DTC = 0x05
GET_DTC = 0x07
GROUP_READ = 0x29
R_ACTUATOR = 0xF5
R_ASCII = 0xF6
R_DTC = 0xFC
R_GROUP = 0xE7

BLOCK_END = 0x03


class KW1281Error(Exception):
    def __init__(self, msg, sin_respuesta=False, kwp2000=False):
        super().__init__(msg)
        self.sin_respuesta = sin_respuesta      # la centralita no contestó nada al init
        self.kwp2000 = kwp2000                  # habla KWP2000 en vez de KW1281


class Block:
    __slots__ = ("counter", "title", "data")

    def __init__(self, counter, title, data):
        self.counter = counter
        self.title = title
        self.data = bytes(data)

    def __repr__(self):
        return f"Block(cnt={self.counter:02X}, title={self.title:02X}, data={self.data.hex(' ')})"


class KW1281:
    def __init__(self, ser, address=0x01, bauds=(10400, 9600), byte_delay=0.001,
                 retry_wait=2.5, keepalive_gap=0.1, debug=False, logger=None):
        """
        ser:        objeto tipo pyserial (serial.Serial) ya abierto.
        address:    direccion del modulo (0x01 motor, 0x17 cuadro, 0x03 ABS...).
        bauds:      velocidades a probar tras el init de 5 baudios.
        byte_delay: pausa antes de enviar cada byte/complemento (s).
        """
        self.ser = ser
        self.address = address
        self.bauds = bauds
        self.byte_delay = byte_delay
        self.retry_wait = retry_wait
        self.keepalive_gap = keepalive_gap
        self.debug = debug
        self.logger = logger or print

        self.baud = None
        self.keywords = None
        self.echo = True
        self.ident = []          # bloques de identificacion (bytes)
        self.connected = False
        self.error = None

        self._counter = None
        self._pending = None
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread = None
        self._last = 0.0

    # ------------------------------------------------------------------
    # Nivel fisico
    # ------------------------------------------------------------------
    def _dbg(self, msg):
        if self.debug:
            self.logger(f"[kw1281] {msg}")

    def _five_baud(self, addr):
        """Envia 'addr' a 5 baudios (7 bits + paridad impar) mediante break."""
        b = addr & 0x7F
        if bin(b).count("1") % 2 == 0:
            b |= 0x80                       # paridad impar
        bits = [0] + [(b >> i) & 1 for i in range(8)] + [1]   # start, LSB..MSB, stop
        s = self.ser
        s.break_condition = False
        time.sleep(0.3)                     # linea en reposo antes del init
        t0 = time.perf_counter()
        for i, bit in enumerate(bits[:-1]):
            s.break_condition = (bit == 0)  # break = linea K a nivel bajo
            target = t0 + (i + 1) * 0.2
            while True:
                rest = target - time.perf_counter()
                if rest <= 0:
                    break
                if rest > 0.003:
                    time.sleep(0.001)
        s.break_condition = False           # bit de stop (nivel alto)

    def _read_raw(self, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            d = self.ser.read(1)
            if d:
                return d[0]
        raise KW1281Error(tr("Timeout esperando byte de la ECU"))

    def _write_raw(self, b):
        self.ser.write(bytes([b]))
        if self.echo:
            e = self._read_raw(0.3)
            if e != b:
                raise KW1281Error(tr("Eco incorrecto: enviado {tx}, leído {rx}", tx=f"{b:02X}", rx=f"{e:02X}"))

    def _send_byte(self, b, expect_ack=True):
        if self.byte_delay:
            time.sleep(self.byte_delay)
        self._write_raw(b)
        if expect_ack:
            c = self._read_raw(0.5)
            if c != (0xFF ^ b):
                raise KW1281Error(tr("Complemento incorrecto: enviado {tx}, ECU {rx}", tx=f"{b:02X}", rx=f"{c:02X}"))

    def _recv_byte(self, ack=True):
        if self._pending is not None:
            b, self._pending = self._pending, None
        else:
            b = self._read_raw(1.0)
        if ack:
            if self.byte_delay:
                time.sleep(self.byte_delay)
            self._write_raw(0xFF ^ b)
        return b

    # ------------------------------------------------------------------
    # Bloques
    # ------------------------------------------------------------------
    def _send_block(self, title, data=b""):
        self._counter = (self._counter + 1) & 0xFF
        raw = [len(data) + 3, self._counter, title, *data]
        self._dbg(f"TX {Block(self._counter, title, data)}")
        for b in raw:
            self._send_byte(b)
        self._send_byte(BLOCK_END, expect_ack=False)

    def _recv_block(self):
        n = self._recv_byte()
        if n < 3:
            raise KW1281Error(tr("Longitud de bloque no válida: {n}", n=n))
        cnt = self._recv_byte()
        if self._counter is not None and cnt != (self._counter + 1) & 0xFF:
            self._dbg(f"Aviso: contador {cnt:02X}, esperado {(self._counter + 1) & 0xFF:02X}")
        self._counter = cnt
        title = self._recv_byte()
        data = [self._recv_byte() for _ in range(n - 3)]
        end = self._recv_byte(ack=False)
        if end != BLOCK_END:
            raise KW1281Error(tr("Fin de bloque incorrecto: {b}", b=f"{end:02X}"))
        self._last = time.monotonic()
        blk = Block(cnt, title, data)
        self._dbg(f"RX {blk}")
        return blk

    def _receive_until_ack(self, blk):
        """Recibe bloques (ya recibido 'blk'), confirmando con ACK hasta que la ECU envie ACK."""
        result = []
        while blk.title != ACK:
            result.append(blk)
            if blk.title in (NAK, R_GROUP, R_ACTUATOR):
                break
            self._send_block(ACK)
            blk = self._recv_block()
        return result

    def _transact(self, title, data=b""):
        self._send_block(title, data)
        return self._receive_until_ack(self._recv_block())

    # ------------------------------------------------------------------
    # Conexion
    # ------------------------------------------------------------------
    def _init(self, baud):
        s = self.ser
        s.baudrate = baud
        self._counter = None
        self._pending = None
        self.echo = True
        self._dbg(f"Init 5 baudios a {self.address:02X}, escuchando a {baud}")
        self._five_baud(self.address)
        time.sleep(0.01)
        s.reset_input_buffer()              # descarta basura producida por el break
        deadline = time.monotonic() + 1.5
        sync = None
        while time.monotonic() < deadline:
            try:
                sync = self._read_raw(deadline - time.monotonic())
            except KW1281Error:
                break
            if sync == 0x55:
                break
        if sync != 0x55:
            raise KW1281Error(tr("Sin byte de sincronismo 0x55 a {baud} baudios (leído {rx})", baud=baud,
                                 rx=tr("nada") if sync is None else f"{sync:02X}"), sin_respuesta=sync is None)
        kw1 = self._read_raw(0.5)
        kw2 = self._read_raw(0.5)
        self.keywords = (kw1, kw2)
        self._dbg(f"Keywords {kw1:02X} {kw2:02X}")
        if (kw1, kw2) != (0x01, 0x8A):
            if kw2 == 0x8F or kw1 & 0x80:
                raise KW1281Error(tr("La ECU responde con keywords {kw}: habla KWP2000, no KW1281.",
                                     kw=f"{kw1:02X} {kw2:02X}"), kwp2000=True)
            self._dbg("Keywords no tipicas de KW1281, se intenta igualmente")
        time.sleep(0.03)                    # W4: 25-50 ms
        self.ser.write(bytes([0xFF ^ kw2]))
        first = self._read_raw(1.0)
        if first == 0xFF ^ kw2:
            self.echo = True
        else:                                # cable sin eco: ya es el 1er byte del bloque
            self.echo = False
            self._pending = first
        self.baud = baud

    def connect(self, rapido=False):
        """rapido: si el módulo no contesta nada a la primera velocidad, se da por
        ausente sin probar las demás (para escanear todos los módulos)."""
        with self._lock:
            last = None
            for i, baud in enumerate(self.bauds):
                if i:
                    time.sleep(self.retry_wait)   # la ECU debe olvidar el intento anterior
                try:
                    self._init(baud)
                    break
                except KW1281Error as e:
                    last = e
                    if e.kwp2000:
                        raise
                    if rapido and e.sin_respuesta:
                        raise KW1281Error(tr("El módulo {dir} no responde", dir=f"{self.address:02X}"), sin_respuesta=True)
                    self._dbg(str(e))
            else:
                raise KW1281Error(tr("No se pudo iniciar la comunicación: {e}", e=last))

            self.ident = [b.data for b in self._receive_until_ack(self._recv_block())
                          if b.title == R_ASCII]
            self.connected = True
            self.error = None
        self._stop.clear()
        self._thread = threading.Thread(target=self._keepalive, daemon=True)
        self._thread.start()
        return self.ident

    def disconnect(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        with self._lock:
            if self.connected:
                try:
                    self._send_block(END_COMM)
                except KW1281Error:
                    pass
            self.connected = False

    def _keepalive(self):
        while not self._stop.is_set():
            time.sleep(0.02)
            if time.monotonic() - self._last < self.keepalive_gap:
                continue
            if not self._lock.acquire(blocking=False):
                continue
            try:
                if self.connected:
                    self._transact(ACK)
            except KW1281Error as e:
                self.connected = False
                self.error = e
            finally:
                self._lock.release()

    def _call(self, title, data=b""):
        with self._lock:
            if not self.connected:
                raise KW1281Error(tr("Sin conexión con la ECU ({e})", e=self.error or tr("no conectado")))
            try:
                return self._transact(title, data)
            except KW1281Error as e:
                self.connected = False
                self.error = e
                raise

    # ------------------------------------------------------------------
    # Servicios
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_dtcs(blocks):
        dtcs = []
        for blk in blocks:
            if blk.title != R_DTC:
                continue
            d = blk.data
            for i in range(0, len(d) - 2, 3):
                code = (d[i] << 8) | d[i + 1]
                status = d[i + 2]
                if code == 0xFFFF and status == 0x88:
                    continue                 # "sin averias"
                dtcs.append((code, status & 0x7F, bool(status & 0x80)))
        return dtcs

    def read_dtcs(self):
        """Lista de (codigo, tipo_fallo, intermitente)."""
        return self._parse_dtcs(self._call(GET_DTC))

    def clear_dtcs(self):
        """Borra averias. Devuelve las que siguen presentes."""
        return self._parse_dtcs(self._call(CLEAR_DTC))

    def read_group(self, group):
        """Lee un bloque de valores medidos. Devuelve lista de (formula, a, b)
        o, para el grupo 0, la lista de bytes en bruto."""
        blocks = self._call(GROUP_READ, bytes([group & 0xFF]))
        if not blocks or blocks[0].title != R_GROUP:
            raise KW1281Error(tr("Grupo {g} no soportado por la ECU", g=f"{group:03d}"))
        d = blocks[0].data
        if group == 0:
            return list(d)
        return [(d[i], d[i + 1], d[i + 2]) for i in range(0, len(d) - 2, 3)]

    def actuator_test(self, inicio=False):
        """Test de actuadores (diagnóstico de elementos finales, servicio 0x04): cada llamada
        pasa al siguiente componente, que la centralita activa hasta la llamada siguiente.

        Devuelve el código del componente (en la numeración de averías VAG: 01265 = EGR N18)
        o None cuando la secuencia ha terminado. Con el motor en marcha o en una centralita
        que no tiene el test, la centralita contesta NAK y se lanza KW1281Error.
        inicio: primera llamada; si da NAK se reintenta sin el byte de datos, que algunas
        centralitas no esperan.
        """
        blocks = self._call(ACTUATOR_TEST, b"\x00")
        if inicio and blocks and blocks[0].title == NAK:
            blocks = self._call(ACTUATOR_TEST)
        if not blocks:
            return None                      # ACK: no quedan componentes
        b = blocks[0]
        if b.title == R_ACTUATOR and len(b.data) >= 2:
            code = (b.data[0] << 8) | b.data[1]
            return None if code in (0x0000, 0xFFFF) else code
        if b.title == NAK:
            raise KW1281Error(tr("La centralita no acepta el test de actuadores: no lo tiene o no se cumplen "
                                 "las condiciones (motor parado y contacto puesto)."))
        raise KW1281Error(tr("Respuesta inesperada al test de actuadores: {blk}", blk=b))
