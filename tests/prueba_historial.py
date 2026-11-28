"""
Prueba del historial de diagnósticos por coche (sin ventanas, <1 s):

    python tests/prueba_historial.py
"""
import datetime
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import historial as h  # noqa: E402

fallos = []


def ok(cond, txt):
    print(("  OK   " if cond else "  FALLO ") + txt)
    if not cond:
        fallos.append(txt)


def av(codigo, estado="presente", modulo=1):
    return {"modulo": modulo, "codigo": codigo, "texto": f"texto {codigo}", "estado": estado}


def reg(tipo, modulos, averias):
    return {"tipo": tipo, "modulos": modulos, "averias": averias, "mil": None}


t0 = datetime.datetime(2026, 11, 20, 10, 0)
hi = h.Historial(os.path.join(tempfile.mkdtemp(), "historial"))

print("Guardar y comparar")
r, ant = hi.guardar("VSSZZZ1MZYR000001", "SEAT · 2000", reg("lectura", [1], [av("00553"), av("01262", "intermitente")]), t0)
ok(ant is None and r["fecha"] == "2026-11-20T10:00:00", "primer registro, sin anterior")
r, ant = hi.guardar("VSSZZZ1MZYR000001", "SEAT · 2000", reg("lectura", [1], [av("00553"), av("01262", "intermitente")]),
                    t0 + datetime.timedelta(minutes=10))
ok(len(hi.cargar("VSSZZZ1MZYR000001")["registros"]) == 1, "la misma lectura 10 min después no se duplica")
r2, ant = hi.guardar("VSSZZZ1MZYR000001", "SEAT · 2000", reg("lectura", [1], [av("00553"), av("00522")]),
                     t0 + datetime.timedelta(days=3))
c = h.comparar(ant, r2)
ok([a["codigo"] for a in c["nuevas"]] == ["00522"] and [a["codigo"] for a in c["resueltas"]] == ["01262"]
   and [a["codigo"] for a in c["repetidas"]] == ["00553"], "nuevas, ya no aparecen y se repiten")
r3, ant = hi.guardar("VSSZZZ1MZYR000001", "", reg("borrado", [1], []), t0 + datetime.timedelta(days=3, minutes=1))
ok(ant is r2 or ant == r2, "un borrado se compara con la lectura de antes")
ok([a["codigo"] for a in h.comparar(ant, r3)["resueltas"]] == ["00522", "00553"], "tras borrar: ninguna sigue")
ok(hi.cargar("VSSZZZ1MZYR000001")["nombre"] == "SEAT · 2000", "el nombre se conserva si llega vacío")

print("Escaneo de módulos (solo cuentan los módulos comunes)")
esc, ant = hi.guardar("VSSZZZ1MZYR000001", "SEAT · 2000",
                      reg("escaneo", [1, 3, 17], [av("00553"), av("00283", modulo=3), av("01176", modulo=17)]),
                      t0 + datetime.timedelta(days=5))
c = h.comparar(ant, esc)
ok([a["codigo"] for a in c["nuevas"]] == ["00553"] and not c["resueltas"],
   "escaneo frente al borrado del motor: solo compara el módulo 01")
lec, ant = hi.guardar("VSSZZZ1MZYR000001", "SEAT · 2000", reg("lectura", [3], []), t0 + datetime.timedelta(days=6))
ok(ant is esc or ant == esc, "una lectura del ABS busca el último registro que leyó el ABS")
ok([a["codigo"] for a in h.comparar(ant, lec)["resueltas"]] == ["00283"], "y la avería del ABS ya no aparece")

print("Varios coches, archivos y VIN")
hi.guardar("CALID-SIM/CAL 0471", "Coche sin VIN", reg("lectura", [0], [av("P0171", "memorizada", 0)]),
           t0 + datetime.timedelta(days=7))
coches = hi.coches()
ok([c[0] for c in coches] == ["CALID-SIM/CAL 0471", "VSSZZZ1MZYR000001"] and coches[1][2] == 5,
   f"lista de coches, el más reciente primero ({[(c[0], c[2]) for c in coches]})")
ok(all("/" not in n for n in os.listdir(hi.carpeta)), "nombres de archivo seguros")
hi.borrar_registro("CALID-SIM/CAL 0471", 0)
ok([c[0] for c in hi.coches()] == ["VSSZZZ1MZYR000001"], "borrar el único registro quita el coche")
with open(os.path.join(hi.carpeta, "roto.json"), "w") as f:
    f.write("{no es json")
ok(len(hi.coches()) == 1 and hi.cargar("roto")["registros"] == [], "un archivo dañado no rompe nada")
ok(h.buscar_vin(["038906018FQ", "  VSSZZZ1MZYR123456 IMMO-1234"]) == "VSSZZZ1MZYR123456", "VIN dentro de la identificación VAG")
ok(h.buscar_vin(["038906018FQ 1,9l R4 EDC", "SG 1234", "AAAAAAAAAAAAAAAAA", "12345678901234567"]) is None,
   "sin falsos VIN (todo letras o todo números)")

print("Registro de cambios en las centralitas")
import cambios  # noqa: E402
cb = cambios.Cambios(os.path.join(tempfile.mkdtemp(), "sub"))
ok(cb.todos() == [] and cb.de(1, "038906018FQ") == [], "sin archivo: lista vacía")
cb.registrar(1, "038906018FQ ", "adaptacion", 1, 128, 131, 8704, fecha=datetime.datetime(2026, 11, 28, 18, 0))
cb.registrar(1, "038906018FQ", "codificacion", None, 2, 4, 8704, fecha=datetime.datetime(2026, 11, 28, 18, 5))
cb.registrar(0x17, "1M0920821C", "adaptacion", 2, 0, 10)
with open(cb.ruta, "a", encoding="utf-8") as f:
    f.write('{"fecha": "2026-11-28T18:10:00", "modulo": 1, "refer')          # línea cortada a medias
d = cb.de(1, "038906018FQ")
ok([r["tipo"] for r in d] == ["codificacion", "adaptacion"] and d[1]["antes"] == 128 and d[1]["canal"] == 1,
   "cambios de una centralita, el más reciente primero")
ok(len(cb.todos()) == 3 and cb.de(0x17, "1M0920821C")[0]["despues"] == 10, "una línea cortada no rompe el registro")
cb.registrar(1, "038906018FQ", "adaptacion", 1, 131, 128)
ok(len(cb.de(1, "038906018FQ")) == 3, "se añade sin reescribir lo anterior")
try:
    cb.registrar(1, "x", "otra", 1, 0, 0)
    ok(False, "tipo no válido rechazado")
except ValueError:
    ok(True, "tipo no válido rechazado")

print()
if fallos:
    print(f"HAY {len(fallos)} FALLOS")
    sys.exit(1)
print("TODO CORRECTO")
