"""
Pruebas de los protocolos contra los simuladores (sin coche, sin pytest).

    python tests/prueba_simuladores.py

Comprueba KW1281 (init 5 baudios, velocidad automática, identificación,
averías, borrado, grupos, keep-alive) y ELM327 (protocolo, PIDs soportados,
VIN, MIL, averías, multi-PID, borrado) y el parseo de respuestas de línea K y
CAN 29 bits, datos congelados, monitores, averías permanentes, identificación
(modo 09), VIN, varias centralitas KW1281, test de actuadores, informe HTML y códigos de avería VAG. Tarda unos 20 segundos (el init de 5 baudios es lento por diseño).
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["OBD2DESK_IDIOMA"] = "es"     # compara textos en español (el inglés: tests/prueba_idioma.py)

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

print("ELM327: datos congelados, preparación, permanentes e identificación")
for proto, nombre in (("6", "CAN"), ("3", "ISO 9141"), ("5", "KWP2000")):
    e = ELM327(FakeELMSerial(proto), logger=lambda m: None)
    e.connect()
    d = e.read_dtcs()
    ff = e.freeze_frame()
    r = e.readiness()
    ident = e.identificacion()
    comprobar(d["permanent"] == ["P0420"] and ff and ff["dtc"] == "P0171" and len(ff["values"]) == 10
              and ("Temp. refrigerante", "83") in [(n, v) for _, n, v, _ in ff["values"]],
              f"{nombre}: permanentes y datos congelados (P0171, 10 valores)")
    comprobar(r and not r[0] and ("Sistema de evaporación (EVAP)", False) in r[1] and len(r[1]) == 8,
              f"{nombre}: monitores (8, EVAP sin completar)")
    comprobar(ident == {"calid": ["SIM-CAL-0471"], "cvn": ["1A2B3C4D"], "nombre": "ECM -EngineControl"},
              f"{nombre}: calibración, CVN y nombre de la centralita")
    e.clear_dtcs()
    comprobar(e.freeze_frame() is None and e.read_dtcs()["permanent"] == ["P0420"],
              f"{nombre}: tras borrar no hay datos congelados y la permanente sigue")

print("Monitores y VIN")
import obd_datos  # noqa: E402
import vin_datos  # noqa: E402
diesel, mons = obd_datos.monitores(0x0F, 0xE9, 0x40)
comprobar(diesel and ("Filtro de partículas (DPF)", False) in mons and ("Catalizador NMHC", True) in mons,
          "monitores de un diésel (DPF sin completar)")
v = dict(vin_datos.decodificar_vin("VSSZZZ6KZYR000001"))
comprobar(v["Fabricante"] == "SEAT" and v["País de fabricación"] == "España" and v["Año modelo"].startswith("2000")
          and "Ibiza" in v["Modelo (código VAG)"], "VIN de SEAT: fabricante, país, año 2000, modelo 6K")
comprobar(dict(vin_datos.decodificar_vin("WAUZZZ8P7AA000001"))["Año modelo"].startswith("2010")
          and "no válido" in vin_datos.decodificar_vin("123")[0][1], "VIN: año 2010 y VIN no válido")

print("KW1281 con varias centralitas en la línea K")
s = FakeSerial()
idents = {}
t = time.time()
for a in (0x17, 0x08):
    m = KW1281(s, address=a, retry_wait=0.5)
    try:
        m.connect(rapido=True)
        idents[a] = (m.ident[0], m.read_dtcs())
        m.disconnect()
    except KW1281Error as err:
        idents[a] = str(err)
comprobar(idents[0x17] == (b"1M0920821C  ", [(779, 5, False)]), "cuadro (17): identificación y avería 00779")
comprobar("no responde" in idents[0x08] and time.time() - t < 12, f"módulo ausente (08) descartado rápido ({time.time() - t:.1f} s en total)")

print("Test de actuadores KW1281")
s = FakeSerial()
m = KW1281(s, retry_wait=0.5)
m.connect()
seq = [m.actuator_test(inicio=True)]
time.sleep(0.5)                                  # el componente sigue activo con el keep-alive
comprobar(m.connected, "la sesión sigue viva mientras se activa un componente")
while seq[-1] is not None and len(seq) < 20:
    seq.append(m.actuator_test())
import simulador  # noqa: E402
comprobar(seq == simulador.ACTUADORES_TDI + [None], f"secuencia del TDI y fin ({seq})")
comprobar(m.actuator_test(inicio=True) == simulador.ACTUADORES_TDI[0], "se puede repetir el test")
m.disconnect()
m.connect()
comprobar(s.ecu.actuador == -1 and m.actuator_test(inicio=True) == simulador.ACTUADORES_TDI[0],
          "al reconectar la secuencia empieza de nuevo")
m.disconnect()
m = KW1281(s, address=0x15, retry_wait=0.5)
m.connect()
try:
    m.actuator_test(inicio=True)
    comprobar(False, "el airbag (15) rechaza el test")
except KW1281Error as err:
    comprobar("no acepta" in str(err) and m.connected, "el airbag (15) rechaza el test y la sesión sigue")
m.disconnect()

print("Informe HTML")
import informe  # noqa: E402
e = ELM327(FakeELMSerial("6"), logger=lambda m: None)
e.connect()
d = e.read_dtcs()
d["ff"], d["readiness"] = e.freeze_frame(), e.readiness()
h = informe.generar({"modo": "elm", "version": "x", "vehiculo": [("VIN", "VSSZZZ6KZYR000001")], "dtcs": d})
comprobar(all(x in h for x in ("P0171", "P0420", "Permanente", "Datos congelados", "Sin completar", "VSSZZZ6KZYR000001")),
          "informe OBD2 con averías, datos congelados y monitores")
h = informe.generar({"modo": "kkl", "vehiculo": [], "dtcs": [(553, 27, False)], "modulo": 1,
                     "escaneo": [{"addr": 3, "ok": True, "ident": ["1J0907379G", "ABS"], "dtcs": [(287, 3, True)],
                                  "error": None}, {"addr": 8, "ok": False, "error": "no responde"}]})
comprobar(all(x in h for x in ("00553", "00287", "Intermitente", "Responden 1 de 2", "Sin respuesta")),
          "informe VAG con escaneo de módulos")
comprobar("&lt;b&gt;" in informe.generar({"modo": "kkl", "vehiculo": [("x", "<b>")], "dtcs": []}), "el informe escapa el HTML")

print("Tablas de averías VAG")
import vag_datos  # noqa: E402
comprobar(vag_datos.codigo_obd(16684) == "P0300" and vag_datos.codigo_obd(17965) == "P1557"
          and vag_datos.codigo_obd(18010) == "P1602" and vag_datos.codigo_obd(1262) is None,
          "códigos 16xxx-18xxx a P0/P1 (16684=P0300, 17965=P1557)")
comprobar("P0300" in vag_datos.componente(16684) and "inmovilizador" in vag_datos.componente(17978)
          and "G70" in vag_datos.componente(553), "descripciones clásicas, P0 y P1")
comprobar("no incluido" in vag_datos.componente(18500), "código desconocido")

print()
print("TODO CORRECTO" if not fallos else f"{fallos} FALLO(S)")
sys.exit(1 if fallos else 0)
