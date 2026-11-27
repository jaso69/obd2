"""
Prueba del lector de CSV del visor (sin ventanas, <1 s):

    python tests/prueba_csv.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("OBD2DESK_IDIOMA", "es")

import csv_datos as c  # noqa: E402

fallos = []


def ok(cond, txt):
    print(("  OK   " if cond else "  FALLO ") + txt)
    if not cond:
        fallos.append(txt)


def archivo(texto):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8-sig", newline="")
    f.write(texto)
    f.close()
    return f.name


print("CSV del programa (;  coma decimal  t (s))")
r = c.leer(archivo("t (s);G001 Régimen (rpm);G001 Caudal inyectado (mg/H);G001 Temp. refrigerante (°C)\r\n"
                   "0,00;880;4,7;20\r\n0,35;1200;9,1;21\r\n0,70;2400;18,4;21\r\n"))
ok(r["eje"] == "s" and r["n"] == 3 and len(r["columnas"]) == 3, "3 columnas, 3 filas, eje en segundos")
nombre, unidad, puntos = r["columnas"][1]
ok((nombre, unidad) == ("G001 Caudal inyectado", "mg/H"), f"nombre y unidad separados: {nombre!r} {unidad!r}")
ok(puntos == [(0.0, 4.7), (0.35, 9.1), (0.7, 18.4)], "valores con coma decimal")
mn, md, mx = c.resumen(puntos)
ok(mn == 4.7 and abs(md - 32.2 / 3) < 1e-9 and mx == 18.4, "mínimo, media y máximo")
mn, md, mx = c.resumen(puntos, 0.3, 1)
ok(mn == 9.1 and abs(md - 13.75) < 1e-9 and mx == 18.4, "resumen de un tramo (zoom)")
ok(c.resumen(puntos, 5, 6) is None, "tramo sin datos")

print("CSV de otros programas")
r = c.leer(archivo("Time,RPM,Speed (km/h),Note\n0.0,800,0,ok\n0.5,1500,12,\n1.0,,25,x\n"))
ok(r["eje"] == "s" and [x[0] for x in r["columnas"]] == ["RPM", "Speed"], "separador «,», punto decimal; ignora texto")
ok(r["columnas"][0][2] == [(0.0, 800.0), (0.5, 1500.0)], "celdas vacías se saltan")
r = c.leer(archivo("a;b\n1;1.234,5\n2;-3\n"))
ok(r["eje"] == "muestra" and r["columnas"][1][2] == [(1, 1234.5), (2, -3.0)], "sin columna de tiempo: nº de muestra; miles con punto")
r = c.leer(archivo("t\tv\n0\t1\n1\t2\n"))
ok(r["columnas"][0][2] == [(0.0, 1.0), (1.0, 2.0)], "separador tabulador")
for texto, que in (("", "vacío"), ("t (s);a\n", "solo cabecera"), ("x;y\nhola;adiós\n", "sin números")):
    try:
        c.leer(archivo(texto))
        ok(False, f"archivo {que}: debería avisar")
    except ValueError as e:
        ok(bool(str(e)), f"archivo {que}: «{e}»")

print("Reducir puntos para dibujar")
muchos = [(i * 0.1, (i % 100) * 1.0) for i in range(36000)]
muchos[12345] = (1234.5, 999.0)                       # un pico aislado
red = c.reducir(muchos, 2000)
ok(len(red) <= 2100 and max(v for _, v in red) == 999.0, f"36000 → {len(red)} puntos sin perder el pico")
ok(all(red[i][0] <= red[i + 1][0] for i in range(len(red) - 1)), "siguen en orden")
ok(c.reducir(muchos[:50], 2000) == muchos[:50], "pocos puntos: sin cambios")

print()
if fallos:
    print(f"HAY {len(fallos)} FALLOS")
    sys.exit(1)
print("TODO CORRECTO")
