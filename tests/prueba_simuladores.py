"""
Pruebas de los protocolos contra los simuladores (sin coche, sin pytest).

    python tests/prueba_simuladores.py

Comprueba KW1281 (init 5 baudios, velocidad automática, identificación,
averías, borrado, grupos, keep-alive) y ELM327 (protocolo, PIDs soportados,
VIN, MIL, averías, multi-PID, borrado) y el parseo de respuestas de línea K y
CAN 29 bits. Tarda unos 10 segundos (el init de 5 baudios es lento por diseño).
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from elm327 import ELM327, ELM327Error         # noqa: E402
from kw1281 import KW1281, KW1281Error          # noqa: E402
from simulador import FakeELMSerial, FakeSerial  # noqa: E402
from toledo import leer_grupo_formateado        # noqa: E402

fallos = 0


def comprobar(cond, texto):
    global fallos
    print(("  OK   " if cond else "  FALLO ") + texto)
    if not cond:
        fallos += 1


print("KW1281 (cable KKL + EDC15 simulada)")
ecu = KW1281(FakeSerial(), retry_wait=0.5)
t = time.time()
ecu.connect()
comprobar(ecu.baud == 9600 and ecu.keywords == (0x01, 0x8A), f"conexión a {ecu.baud} bd en {time.time() - t:.1f} s, keywords 01 8A")
comprobar(ecu.ident[0].startswith(b"0389"), "identificación de la centralita")
dtcs = ecu.read_dtcs()
comprobar([d[0] for d in dtcs] == [553, 1262] and dtcs[1][2], "averías 00553 y 01262 (intermitente)")
time.sleep(1.5)
comprobar(ecu.connected, "keep-alive mantiene la sesión 1,5 s sin actividad")
g11 = leer_grupo_formateado(ecu, 11)
comprobar(len(g11) == 4 and g11[2][2] == "mbar", "grupo 011 con 4 campos y presión en mbar")
try:
    ecu.read_group(99)
    comprobar(False, "grupo inexistente da error")
except KW1281Error:
    comprobar(True, "grupo inexistente da error")
comprobar(ecu.clear_dtcs() == [] and ecu.read_dtcs() == [], "borrado de averías")
ecu.disconnect()

print("ELM327 (coche OBD2 simulado)")
e = ELM327(FakeELMSerial())
e.connect()
comprobar(e.is_can and "15765" in e.proto_name, f"protocolo {e.proto_name}")
comprobar({0x0C, 0x0D, 0x05}.issubset(e.supported), "PIDs soportados incluyen rpm, velocidad y refrigerante")
comprobar(e.vin() == FakeELMSerial.VIN, "VIN multi-trama")
comprobar(e.mil() == (True, 2), "testigo MIL encendido con 2 averías")
d = e.read_dtcs()
comprobar(d["stored"] == ["P0171", "P0420"] and d["pending"] == ["P0301"], "averías memorizadas y pendientes")
r = e.read_pids([0x0C, 0x0D, 0x05, 0x04, 0x0F, 0x10, 0x11, 0x42])
comprobar(len(r) == 8 and e.multi, "lectura multi-PID de 8 PIDs")
e.clear_dtcs()
comprobar(e.read_dtcs()["stored"] == [], "borrado de averías")

for proto, larga, nombre in (("5", False, "KWP2000 rápido"), ("4", True, "KWP2000 lento, cabecera de 4 bytes"),
                             ("3", False, "ISO 9141-2")):
    print(f"ELM327 (línea K {nombre}, falla la búsqueda automática)")
    e = ELM327(FakeELMSerial(proto, auto_falla=True, cabecera_larga=larga), logger=lambda m: None)
    e.connect()
    comprobar(e.proto_num == proto and not e.is_can and not e.multi, f"protocolo forzado {e.proto_name}")
    comprobar({0x0C, 0x0D, 0x05}.issubset(e.supported), "PIDs soportados")
    comprobar(e.vin() == FakeELMSerial.VIN, "VIN en 5 mensajes")
    comprobar(e.mil() == (True, 2), "testigo MIL")
    d = e.read_dtcs()
    comprobar(d["stored"] == ["P0171", "P0420"] and d["pending"] == ["P0301"], "averías")
    comprobar(len(e.read_pids([0x0C, 0x0D, 0x05, 0x42])) == 4, "lectura de 4 PIDs uno a uno")
    e.clear_dtcs()
    comprobar(e.read_dtcs()["stored"] == [], "borrado de averías")

print("ELM327 (coche que no responde a nada)")
s = FakeELMSerial("5", auto_falla=True)
s.protocolo = "X"                                 # ningún protocolo forzado encaja
e = ELM327(s, logger=lambda m: None)
try:
    e.connect()
    comprobar(False, "da error claro")
except ELM327Error as err:
    comprobar("KWP2000" in str(err) and s.actual == "0", "da error claro y deja el adaptador en automático")

print("Parseo de respuestas")
k = ELM327(None)
k.proto_num, k.is_can = "3", False
comprobar(k._parse(["48 6B 10 41 0C 1A F8 E3"]) == {"10": [bytes([0x41, 0x0C, 0x1A, 0xF8])]}, "línea K (ISO 9141)")
k.proto_num, k.is_can = "7", True
vin = k._parse(["18 DA F1 10 10 14 49 02 01 56 53 53", "18 DA F1 10 21 5A 5A 5A 36 4B 5A 59",
                "18 DA F1 10 22 52 30 30 30 30 30 31"])
comprobar(vin["10"][0][3:] == b"VSSZZZ6KZYR000001", "CAN 29 bits multi-trama")

print()
print("TODO CORRECTO" if not fallos else f"{fallos} FALLO(S)")
sys.exit(1 if fallos else 0)
