"""
Comprueba las traducciones al inglés (sin abrir ventanas, ~1 s):

    python tests/prueba_idioma.py

- todos los textos con tr("...") del código tienen traducción en textos_en.py,
- también los de las tablas de datos (averías, PIDs, módulos, VIN...),
- los huecos {nombre} coinciden entre el español y el inglés,
- no hay claves repetidas en textos_en.py.
"""
import ast
import glob
import os
import re
import string
import sys

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, RAIZ)
os.environ["OBD2DESK_IDIOMA"] = "es"

import elm327      # noqa: E402,F401
import gui         # noqa: E402,F401
import ia          # noqa: E402
import idioma      # noqa: E402
import informe     # noqa: E402,F401
import obd_datos   # noqa: E402
import vin_datos   # noqa: E402
from textos_en import EN  # noqa: E402

fallos = []


def ok(cond, txt):
    print(("  OK   " if cond else "  FALLO ") + txt)
    if not cond:
        fallos.append(txt)


def huecos(t):
    return {c[1] for c in string.Formatter().parse(t) if c[1] is not None}


# textos con tr("...") en el código
literales = set()
for f in glob.glob(os.path.join(RAIZ, "*.py")):
    if f.endswith("textos_en.py"):
        continue
    for n in ast.walk(ast.parse(open(f, encoding="utf-8").read())):
        if (isinstance(n, ast.Call) and getattr(n.func, "id", None) == "tr" and n.args
                and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)):
            literales.add(n.args[0].value)
faltan = sorted(t for t in literales if t not in EN)
ok(not faltan, f"{len(literales)} textos tr() del código traducidos")
for t in faltan:
    print("       falta:", repr(t))

# tablas y textos que se traducen al usarse
idioma.faltan.clear()
idioma.poner("en")
for h in ia.herramientas():
    pass
for t in obd_datos.MONITORES_COMUNES + obd_datos.MONITORES_GASOLINA + obd_datos.MONITORES_DIESEL:
    if t:
        idioma.tr(t)
for _, _, p in vin_datos.PAISES:
    idioma.tr(p)
for v in list(vin_datos.FABRICANTES.values()) + list(vin_datos.MODELOS_VAG.values()):
    vin_datos._parentesis(v)
for _, nombre in elm327.ELM327.PROTOCOLOS_K:
    idioma.tr(nombre)
ok(not idioma.faltan, "tablas de datos, herramientas de la IA y VIN traducidos")
for t in sorted(idioma.faltan):
    print("       falta:", repr(t))
ok(obd_datos.PIDS[0x0C][0] == "Engine speed" and vin_datos.decodificar_vin("VSSZZZ1MZYR000001")[0][1] == "SEAT",
   "las tablas cambian de idioma")
idioma.poner("es")
ok(obd_datos.PIDS[0x0C][0] == "Régimen motor", "y vuelven al español")

# huecos {nombre}
mal = [k for k, v in EN.items() if huecos(k) != huecos(v)]
ok(not mal, "los huecos {nombre} coinciden en las traducciones")
for k in mal:
    print("       huecos distintos:", repr(k))

# claves repetidas (en un dict literal la última pisa a las anteriores sin avisar)
arbol = ast.parse(open(os.path.join(RAIZ, "textos_en.py"), encoding="utf-8").read())
claves = [k.value for n in ast.walk(arbol) if isinstance(n, ast.Dict) for k in n.keys]
rep = sorted({k for k in claves if claves.count(k) > 1})
ok(not rep, f"sin claves repetidas en textos_en.py ({len(claves)} textos)")
for k in rep:
    print("       repetida:", repr(k))

# restos de español en las traducciones
sospechosos = [v for v in EN.values() if re.search(r"[áéíóúñ¿¡]| de la | del ", v)]
ok(not sospechosos, "las traducciones no contienen español")
for v in sospechosos:
    print("       ¿español?:", repr(v))

print("\nTODO CORRECTO" if not fallos else f"\n{len(fallos)} FALLOS")
sys.exit(1 if fallos else 0)
