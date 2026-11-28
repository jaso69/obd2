"""
Prueba de la tabla de códigos genéricos OBD2 (obd_codigos.py, generada por
herramientas/codigos_genericos.py) y de cómo los describe obd_datos.describe_dtc.
Uso: python tests/prueba_codigos.py   (< 1 s; debe decir «TODO CORRECTO»)
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import idioma  # noqa: E402
import obd_datos  # noqa: E402
from obd_codigos import CODIGOS  # noqa: E402

fallos = []


def comprobar(cond, texto):
    print(("  ok    " if cond else "  FALLO ") + texto)
    if not cond:
        fallos.append(texto)


print("Tabla obd_codigos.py")
comprobar(len(CODIGOS) == 9533, f"9533 códigos ({len(CODIGOS)})")
formato = re.compile(r"^[PBCU][0-3][0-9A-F]{3}$")
comprobar(all(formato.match(c) for c in CODIGOS), "todos los códigos tienen formato SAE (P0420, U0100…)")
comprobar(all(en and isinstance(en, str) for en, _ in CODIGOS.values()), "todos tienen título en inglés")
traducidos = sum(1 for _, es in CODIGOS.values() if es)
comprobar(traducidos / len(CODIGOS) > 0.93, f"más del 93 % traducido al español ({traducidos / len(CODIGOS) * 100:.1f} %)")
comprobar(not any(c.startswith(("P1", "B1", "B2", "B3", "C1", "C2", "C3", "U1", "U2")) for c in CODIGOS),
          "no incluye rangos del fabricante (P1, B1-B3, C1-C3, U1-U2)")
comprobar(all(es is None or (es[0].isupper() or es[0].isdigit() or es[0] in "¿(«") for _, es in CODIGOS.values()),
          "las traducciones empiezan en mayúscula")
comprobar(not any(es and ("  " in es or es.endswith((" de", " del", ":"))) for _, es in CODIGOS.values()),
          "sin dobles espacios ni frases cortadas")

ejemplos = {
    "P2463": "Restricción del filtro de partículas diésel - acumulación de hollín (banco 1)",
    "U0140": "Sin comunicación con el módulo de control de la carrocería",
    "P0118": "Sensor de temperatura del refrigerante del motor 1: circuito, valor alto",
    "C0040": "Interruptor del pedal del freno A",
}
for c, esperado in ejemplos.items():
    comprobar(CODIGOS[c][1] == esperado, f"{c} = «{CODIGOS[c][1]}»")

print("describe_dtc")
idioma.poner("es")
comprobar(obd_datos.describe_dtc("P0420") == obd_datos.DTCS["P0420"], "P0420: manda la descripción revisada a mano")
comprobar(obd_datos.describe_dtc("P2463") == ejemplos["P2463"], "P2463 en español: de la tabla genérica")
comprobar(obd_datos.describe_dtc("P1570") == "Código específico del fabricante", "P1570 sin VIN VAG: específico del fabricante")
obd_datos.marca_vag = True
comprobar("(VAG)" in obd_datos.describe_dtc("P1570"), "P1570 con VIN VAG: tabla de VAG")
obd_datos.marca_vag = False
comprobar(obd_datos.describe_dtc("B1234") == "Código específico del fabricante", "B1234: específico del fabricante")
sin = next(c for c, (en, es) in CODIGOS.items() if es is None)
comprobar(obd_datos.describe_dtc(sin) == CODIGOS[sin][0], f"{sin} sin traducir: se muestra el inglés")
idioma.poner("en")
comprobar(obd_datos.describe_dtc("P2463") == CODIGOS["P2463"][0], "P2463 en inglés: título de OBDex")
comprobar(obd_datos.describe_dtc("U0100") == "Lost Communication With ECM/PCM A", "U0100 en inglés")
idioma.poner("es")

print()
if fallos:
    print(f"FALLAN {len(fallos)} COMPROBACIONES")
    sys.exit(1)
print("TODO CORRECTO")
