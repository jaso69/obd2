"""
Prueba de la interfaz con los dos simuladores (sin coche, sin pytest).

    python tests/prueba_gui.py
    xvfb-run -a python3 tests/prueba_gui.py     (Linux sin abrir ventanas en el escritorio)

Abre la ventana real y, en modo KKL y ELM327: conecta, lee y borra averías,
lectura en vivo del panel, valores con grabación CSV y desconecta. Comprueba
también la configuración de la IA (en una carpeta temporal, no toca la tuya)
y que no salten diálogos de error ni excepciones. Tarda unos 40 segundos.
"""
import os
import sys
import tempfile
import time
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["XDG_CONFIG_HOME"] = os.environ["APPDATA"] = tempfile.mkdtemp()

import tkinter as tk                # noqa: E402
from tkinter import messagebox      # noqa: E402

import gui                          # noqa: E402
import ia                           # noqa: E402

fallos = []
dialogos = []
messagebox.showerror = lambda *a, **k: dialogos.append(("error", a))
messagebox.showinfo = lambda *a, **k: dialogos.append(("info", a))
messagebox.askyesno = lambda *a, **k: True


def ok(cond, txt):
    print(("  OK   " if cond else "  FALLO ") + txt)
    if not cond:
        fallos.append(txt)


def esperar(cond, seg):
    t = time.monotonic() + seg
    while time.monotonic() < t:
        root.update()
        if cond():
            return True
        time.sleep(0.02)
    return False


root = tk.Tk(className="ToledoDiagnosis")
errores_tk = []
root.report_callback_exception = lambda *e: errores_tk.append("".join(traceback.format_exception(*e)))
gui._elegir_fuentes(root)
app = gui.App(root)
root.update()
print(f"Fuentes: {gui.FONT} / {gui.MONO}; tamaño ventana {root.winfo_width()}x{root.winfo_height()}")
ok(gui.SIM in app.port_cb["values"], "el simulador aparece en la lista de puertos")

for modo in (gui.KKL, gui.ELM):
    print(gui.MODOS[modo])
    app.mode_var.set(gui.MODOS[modo])
    app._apply_mode()
    app.port_var.set(gui.SIM)
    app.toggle_connect()
    ok(esperar(lambda: app.connected, 40), "conecta")
    if not app.connected:
        continue
    ok(bool(app.vehicle_fields), f"datos de la centralita ({len(app.vehicle_fields)} campos)")

    app.read_dtcs()
    ok(esperar(lambda: app.dtc_tree.get_children(), 15),
       f"averías en la tabla ({len(app.dtc_tree.get_children())})")
    app.clear_dtcs()
    esperar(lambda: "Borrando" not in str(app.dtc_lbl.cget("text")), 15)
    ok(not dialogos, "borrado sin errores")

    app.toggle_live("panel")
    ch = app.ch_boost if modo == gui.KKL else app.ch_rpm
    n = lambda: sum(len(d) for d in ch.data.values())
    ok(esperar(lambda: n() >= 3, 20), f"lectura en vivo del panel ({n()} puntos en la gráfica)")
    app._stop_live()

    if modo == gui.ELM:
        app.pid_list.selection_set(0, 3)
    app.toggle_rec()
    ok(esperar(lambda: app.csv_n >= 3, 20), f"lectura de valores y grabación CSV ({app.csv_n} muestras)")
    nombre = app.csv_file.name if app.csv_file else None
    app._stop_rec()
    app._stop_live()
    if nombre:
        with open(nombre, encoding="utf-8-sig") as f:
            lineas = f.read().splitlines()
        ok(len(lineas) >= 4, f"CSV con cabecera y datos: {lineas[0][:70]}")
        os.remove(nombre)

    app.toggle_connect()
    ok(esperar(lambda: not app.connected, 10), "desconecta")

print("Errores y carpetas")
carpeta = gui.CARPETA
gui.CARPETA = os.path.join(tempfile.mkstemp()[1], "sub")   # cuelga de un archivo: no se puede crear
app.live_source = "vals"
app.toggle_rec()
app.live_source = None
ok(app.csv_file is None and dialogos and dialogos[-1][0] == "error",
   "si no se puede crear el CSV avisa en vez de fallar")
dialogos.clear()
gui.CARPETA = carpeta
if not gui.WINDOWS:
    ok(os.path.isdir(gui._carpeta_documentos()), f"carpeta de documentos: {gui._carpeta_documentos()}")
    ok(gui._grupo_puerto("/no/existe") in ("dialout", "uucp", "tty"),
       f"grupo del puerto serie: {gui._grupo_puerto('/no/existe')}")

print("Configuración IA")
cfg = ia.cargar_config()
ia.poner_clave(cfg, "anthropic", "sk-prueba-123")
ia.guardar_config(cfg)
ruta = ia._ruta_config()
if not gui.WINDOWS:
    ok(oct(os.stat(ruta).st_mode & 0o777) == "0o600", "config con permisos 600")
ok(ia.leer_clave(ia.cargar_config(), "anthropic") == "sk-prueba-123", "la API key se guarda y se recupera")

ok(not dialogos, f"sin diálogos de error {dialogos}")
ok(not errores_tk, "sin excepciones en la interfaz")
for e in errores_tk:
    print(e)
app.on_close()
esperar(lambda: False, 1)
print("\nTODO CORRECTO" if not fallos else f"\n{len(fallos)} FALLOS")
sys.exit(1 if fallos else 0)
