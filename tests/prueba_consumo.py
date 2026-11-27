"""
Prueba del cálculo de consumo y del cronómetro 0-100 (sin coche ni ventanas, <1 s):

    python tests/prueba_consumo.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import consumo as c  # noqa: E402

fallos = []


def ok(cond, txt):
    print(("  OK   " if cond else "  FALLO ") + txt)
    if not cond:
        fallos.append(txt)


def cerca(a, b, tol):
    return a is not None and abs(a - b) <= tol


print("Consumo en L/h")
# PID 5E manda sobre todo lo demás
ok(c.litros_hora_obd({0x5E: 6.5, 0x10: 30}, c.GASOLINA, 1.6) == 6.5, "PID 5E directo")
# 14,7 g/s de aire en gasolina = 1 g/s de gasolina = 3600/745 = 4,83 L/h
ok(cerca(c.litros_hora_obd({0x10: 14.7}, c.GASOLINA, None), 4.832, 0.01), "caudalímetro, gasolina, lambda 1")
ok(cerca(c.litros_hora_obd({0x10: 14.7, 0x44: 0.8}, c.GASOLINA, None), 6.040, 0.01), "lambda comandada 0,8 (mezcla rica)")
# diésel: sin sonda de banda ancha no se calcula; con lambda 2,5 sí
ok(c.litros_hora_obd({0x10: 14.5}, c.DIESEL, None) is None, "diésel sin lambda: no se inventa el consumo")
ok(cerca(c.litros_hora_obd({0x10: 36.25, 0x24: 2.5}, c.DIESEL, None), 3600 / 832, 0.01), "diésel con lambda 2,5")
# sin caudalímetro: 35 kPa, 800 rpm, 25 °C, 1,6 L → unos 3,6 g/s de aire (ralentí) → ~1,2 L/h
lh = c.litros_hora_obd({0x0B: 35, 0x0C: 800, 0x0F: 25}, c.GASOLINA, 1.6)
ok(cerca(lh, 1.19, 0.05), f"presión de colector y cilindrada ({lh:.2f} L/h al ralentí)")
ok(c.litros_hora_obd({0x0B: 35, 0x0C: 800}, c.GASOLINA, None) is None, "sin cilindrada no hay estimación por presión")
# VAG EDC15: 5 mg/carrera a 900 rpm, 4 cilindros = 150 mg/s = 0,65 L/h
ok(cerca(c.litros_hora_vag(5, 900, 4), 0.649, 0.005), "EDC15: caudal inyectado × régimen")
ok(c.litros_hora_vag(-1, 900, 4) == 0, "EDC15: caudal negativo (retención) = 0")

print("Método y PIDs a leer")
ok(c.metodo([0x0C, 0x0D, 0x5E], c.DIESEL) == "5E", "con PID 5E")
ok(c.metodo([0x0C, 0x0D, 0x10], c.GASOLINA) == "MAF", "gasolina con caudalímetro")
ok(c.metodo([0x0C, 0x0D, 0x0B], c.GASOLINA) == "MAP", "gasolina sin caudalímetro")
ok(c.metodo([0x0C, 0x0D, 0x10], c.DIESEL) is None, "diésel sin sonda de banda ancha")
ok(c.metodo([0x0C, 0x0D, 0x10, 0x34], c.DIESEL) == "MAF", "diésel con sonda de banda ancha")
ok(c.pids_necesarios([0x04, 0x0C, 0x0D, 0x10, 0x11, 0x44], c.GASOLINA) == [0x0D, 0x0C, 0x10, 0x44],
   "solo los PIDs necesarios (más muestras por segundo)")

print("Trayecto")
tr_ = c.Trayecto()
# 1 hora simulada a 100 km/h y 6 L/h, en muestras cada 0,2 s
t = 0.0
while t <= 3600 + 1e-6:
    tr_.muestra(t, 6.0, 100)
    t += 0.2
ok(cerca(tr_.litros, 6.0, 0.01) and cerca(tr_.km, 100, 0.1), f"1 h a 100 km/h y 6 L/h: {tr_.litros:.2f} L, {tr_.km:.1f} km")
ok(cerca(tr_.l100_medio(), 6.0, 0.01) and cerca(tr_.l100_instantaneo(), 6.0, 0.01), "6,0 L/100 km medio e instantáneo")
tr_.muestra(t + 60, 6.0, 100)                       # hueco de un minuto: no se integra
ok(cerca(tr_.km, 100, 0.1), "un hueco en las lecturas no suma distancia")
tr_.reiniciar()
tr_.muestra(0, 1.0, 0)
tr_.muestra(1, 1.0, 0)
ok(tr_.l100_instantaneo() is None and tr_.instantaneo()[0] == 1.0, "parado: L/h, sin L/100 km")
ok(tr_.l100_medio() is None, "sin distancia no hay consumo medio")

print("Cronómetro 0-100")


def acelerar(cr, t0, aceleracion, dt, hasta=110, ruido=None):
    """Muestras de velocidad (km/h enteros, como el PID 0D) con aceleración constante en km/h/s."""
    t, res = t0, None
    while True:
        v = int(aceleracion * (t - t0))
        r = cr.muestra(t, v)
        if r is not None:
            res = r
        if v >= hasta:
            return res, t
        t += dt


cr = c.Cronometro()
ok(cr.muestra(0, 30) is None and cr.estado == cr.PARADO, "en marcha no arranca: hay que parar antes")
cr.muestra(0.5, 0)
ok(cr.estado == cr.LISTO, "parado: listo")
# 12,5 km/h por segundo → 0-100 en 8,0 s; 0-50 en 4,0 s
res, t = acelerar(cr, 1.0, 12.5, 0.15)
ok(cerca(res, 8.0, 0.2), f"0-100 con muestras cada 0,15 s: {res:.2f} s (real 8,00)")
ok(cerca(cr.tiempos[0][1], 4.0, 0.2), f"paso por 50: {cr.tiempos[0][1]:.2f} s (real 4,00)")
ok(cr.estado == cr.PARADO, "tras medir espera a que el coche pare")
cr.muestra(t + 5, 0)
res2, t = acelerar(cr, t + 5.2, 10, 0.1)
ok(cerca(res2, 10.0, 0.2) and cr.mejor == res, f"segunda medida {res2:.2f} s; el mejor sigue siendo {cr.mejor:.2f} s")
ok(len(cr.tiempos) == 2, "guarda las medidas")

cr = c.Cronometro()
cr.muestra(0, 0)
for i, v in enumerate((5, 20, 40, 60, 52)):              # soltó el pedal a 60
    cr.muestra(0.5 + i * 0.5, v)
ok(cr.estado == cr.PARADO and cr.aviso == "frenada" and not cr.tiempos, "frenar a mitad anula la medida")
cr.muestra(10, 0)
cr.muestra(10.2, 10)
cr.muestra(14, 40)
ok(cr.estado == cr.PARADO and cr.aviso == "hueco", "un hueco en las lecturas anula la medida")

print()
if fallos:
    print(f"HAY {len(fallos)} FALLOS")
    sys.exit(1)
print("TODO CORRECTO")
