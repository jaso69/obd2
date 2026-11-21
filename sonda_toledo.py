"""
Sonda de protocolos para SEAT Toledo II 1.9 TDI (2000) con ELM327.

Centralita esperada: Bosch EDC15V (motores AHF/ASV/ALH/AGR) o EDC15P (ARL).
Estos diesel NO estan obligados a EOBD (obligatorio en diesel desde 2003/04),
asi que lo importante es averiguar que protocolo VAG habla la centralita de
motor (direccion 0x01) por la linea K (pin 7 del conector):

  - Keywords 01 8A  -> KW1281 (protocolo propietario VAG). El ELM327 NO puede
                       mantener esta comunicacion -> hace falta cable KKL.
  - Keywords EF 8F  -> KWP2000 (ISO 14230). Se puede trabajar con el ELM327.
                       (u otros con bit 0x80 en KB2)

Uso:
  python sonda_toledo.py COM5            (ELM327 USB o Bluetooth)
  python sonda_toledo.py 192.168.0.10:35000   (ELM327 WiFi)
  python sonda_toledo.py COM5 --baud 9600

Contacto puesto (motor parado vale). Todo se guarda en sonda_log.txt.
"""
import argparse
import datetime
import re
import socket
import sys
import time

LOG_FILE = "sonda_log.txt"
_log = None


def log(msg=""):
    print(msg)
    _log.write(msg + "\n")
    _log.flush()


# --------------------------------------------------------------------------
# Transporte (serie / Bluetooth SPP / WiFi TCP)
# --------------------------------------------------------------------------
class SerialTransport:
    def __init__(self, port, baud):
        import serial  # pyserial
        self.ser = serial.Serial(port, baud, timeout=0.1)

    def write(self, data):
        self.ser.write(data)

    def read(self):
        return self.ser.read(self.ser.in_waiting or 1)

    def flush_input(self):
        self.ser.reset_input_buffer()

    def close(self):
        self.ser.close()


class TCPTransport:
    def __init__(self, host, port):
        self.sock = socket.create_connection((host, port), timeout=5)
        self.sock.settimeout(0.1)

    def write(self, data):
        self.sock.sendall(data)

    def read(self):
        try:
            return self.sock.recv(1024)
        except socket.timeout:
            return b""

    def flush_input(self):
        while self.read():
            pass

    def close(self):
        self.sock.close()


class ELM:
    def __init__(self, transport):
        self.t = transport

    def cmd(self, command, timeout=5.0):
        """Envia un comando y devuelve las lineas de respuesta (sin eco ni '>')."""
        self.t.flush_input()
        self.t.write((command + "\r").encode("ascii"))
        buf = b""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            chunk = self.t.read()
            if chunk:
                buf += chunk
                if b">" in buf:
                    break
        else:
            lines = self._lines(buf, command)
            log(f"  > {command:<16} [TIMEOUT] {' | '.join(lines)}")
            return lines + ["TIMEOUT"]
        lines = self._lines(buf, command)
        log(f"  > {command:<16} {' | '.join(lines) if lines else '(vacio)'}")
        return lines

    @staticmethod
    def _lines(buf, command):
        text = buf.decode("ascii", errors="ignore").replace(">", "")
        lines = [l.strip() for l in re.split(r"[\r\n]+", text) if l.strip()]
        if lines and lines[0].replace(" ", "").upper() == command.replace(" ", "").upper():
            lines = lines[1:]
        return lines


def is_hex_line(line):
    return bool(re.fullmatch(r"[0-9A-Fa-f ]+", line)) and len(line.replace(" ", "")) >= 2


def ok_data(lines):
    return any(is_hex_line(l) for l in lines)


def reset(elm):
    elm.cmd("ATZ", timeout=4)
    time.sleep(0.3)
    for c in ("ATE0", "ATL0", "ATS1", "ATH1"):
        elm.cmd(c)


# --------------------------------------------------------------------------
# Pruebas
# --------------------------------------------------------------------------
def prueba_adaptador(elm):
    log("\n=== 1. Adaptador ===")
    reset(elm)
    ver = elm.cmd("ATI")
    elm.cmd("AT@1")
    volt = elm.cmd("ATRV")
    log(f"  Version: {ver}  Tension en pin 16: {volt}")
    return ver


def prueba_obd_generico(elm):
    log("\n=== 2. OBD2/EOBD generico (probablemente NO responda en un TDI del 2000) ===")
    resultados = {}
    for proto, nombre in (("0", "auto"), ("3", "ISO 9141-2"),
                          ("4", "ISO 14230 5-baud"), ("5", "ISO 14230 fast")):
        reset(elm)
        elm.cmd(f"ATSP{proto}")
        r = elm.cmd("0100", timeout=15)
        ok = ok_data(r)
        resultados[nombre] = ok
        if ok:
            elm.cmd("ATDP")
        log(f"  -> {nombre}: {'RESPONDE' if ok else 'no responde'}")
    return resultados


def prueba_keywords(elm, baud_kb):
    """Init 5 baudios a la direccion 0x01 (motor) y lectura de keywords."""
    log(f"\n=== 3. Init 5 baudios a direccion 0x01 (motor), ISO baud {baud_kb} ===")
    reset(elm)
    elm.cmd("ATSP3")          # ISO 9141: init 5 baudios clasico
    elm.cmd("ATIIA01")        # direccion de init = 01 (centralita motor VAG)
    elm.cmd(f"ATIB{baud_kb}") # 10 = 10400 baud, 96 = 9600 baud
    elm.cmd("ATKW0")          # no rechazar keywords no estandar (KW1281)
    elm.cmd("ATSH8101F1")
    elm.cmd("ATST FF")        # timeout largo
    r = elm.cmd("0100", timeout=15)   # fuerza el init; da igual la respuesta
    kw = elm.cmd("ATKW")
    log(f"  Respuesta al init: {r}")
    log(f"  Keywords: {kw}")
    return parse_keywords(kw)


def parse_keywords(lines):
    txt = " ".join(lines)
    m = re.search(r"1:([0-9A-F]{2})\s*2:([0-9A-F]{2})", txt, re.I)
    if not m:
        return None
    return int(m.group(1), 16), int(m.group(2), 16)


def prueba_kwp2000(elm):
    """Intenta KWP2000 propio de VAG hacia la direccion 0x01."""
    log("\n=== 4. KWP2000 (ISO 14230) a direccion 0x01 ===")
    exitos = []
    for proto, nombre in (("5", "fast init"), ("4", "5-baud init")):
        reset(elm)
        elm.cmd(f"ATSP{proto}")
        elm.cmd("ATIIA01")
        elm.cmd("ATSH8101F1")       # formato 0x80+long, destino 01, origen F1
        elm.cmd("ATWM8101F13E")     # tester present para mantener la sesion
        elm.cmd("ATST FF")
        for req, desc in (("1089", "startDiagnosticSession 0x89 (VAG)"),
                          ("1A9B", "readEcuIdentification 0x9B (VAG)"),
                          ("2101", "readDataByLocalId 0x01")):
            r = elm.cmd(req, timeout=10)
            ok = ok_data(r)
            log(f"  -> {nombre} / {desc}: {'RESPONDE' if ok else 'no'}")
            if ok:
                exitos.append((nombre, req, r))
    return exitos


# --------------------------------------------------------------------------
def abrir(destino, baud):
    if re.fullmatch(r"[\w.\-]+:\d+", destino) and not destino.upper().startswith("COM"):
        host, port = destino.rsplit(":", 1)
        return TCPTransport(host, int(port))
    return SerialTransport(destino, baud)


def main():
    global _log
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("destino", help="Puerto COM (COM5) o host:puerto WiFi (192.168.0.10:35000)")
    ap.add_argument("--baud", type=int, default=38400, help="Baudios PC<->ELM (38400 por defecto)")
    args = ap.parse_args()

    _log = open(LOG_FILE, "a", encoding="utf-8")
    log("=" * 70)
    log(f"Sonda Toledo 1.9 TDI - {datetime.datetime.now():%Y-%m-%d %H:%M:%S}  ({args.destino})")

    try:
        t = abrir(args.destino, args.baud)
    except Exception as e:
        log(f"No se pudo abrir {args.destino}: {e}")
        sys.exit(1)
    elm = ELM(t)

    try:
        prueba_adaptador(elm)
        generico = prueba_obd_generico(elm)
        kw = prueba_keywords(elm, "10")
        if kw is None:
            kw = prueba_keywords(elm, "96")
        kwp = prueba_kwp2000(elm)
    finally:
        t.close()

    log("\n" + "=" * 70)
    log("RESUMEN")
    log("=" * 70)
    if any(generico.values()):
        log("* La centralita responde a OBD2 generico: " +
            ", ".join(k for k, v in generico.items() if v))
    else:
        log("* Sin OBD2 generico (lo esperado en un TDI del 2000).")

    if kw is None:
        log("* No se obtuvieron keywords: revisa contacto, conector o que el ELM")
        log("  soporte ATIIA (v1.4+). Muchos clones 'v2.1' son en realidad v1.0.")
    else:
        kb1, kb2 = kw
        log(f"* Keywords ECU motor: {kb1:02X} {kb2:02X}")
        if (kb1, kb2) == (0x01, 0x8A):
            log("  => KW1281 (protocolo VAG antiguo). El ELM327 NO sirve para esto.")
            log("     Necesitas un cable KKL / VAG-COM (FTDI) y lo implementamos en Python.")
        elif kb2 == 0x8F or kb1 & 0x80:
            log("  => KWP2000. Se puede seguir con el ELM327.")
        else:
            log("  => Keywords no habituales: pasa el log para analizarlo.")

    if kwp:
        log("* KWP2000 hacia 0x01 RESPONDE con:")
        for nombre, req, r in kwp:
            log(f"    {nombre} {req}: {r}")
    else:
        log("* KWP2000 hacia 0x01 no respondio.")
    log(f"\nLog completo en {LOG_FILE}")
    _log.close()


if __name__ == "__main__":
    main()
