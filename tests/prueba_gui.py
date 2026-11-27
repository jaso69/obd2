"""
Prueba de la interfaz con los dos simuladores (sin coche, sin pytest).

    python tests/prueba_gui.py
    xvfb-run -a python3 tests/prueba_gui.py     (Linux sin abrir ventanas en el escritorio)

Abre la ventana real y, en modo KKL y ELM327: conecta, lee y borra averías,
lectura en vivo del panel, valores con grabación CSV y desconecta. Comprueba
también la configuración de la IA (en una carpeta temporal, no toca la tuya)
y que no salten diálogos de error ni excepciones. Incluye el escaneo de módulos
VAG, los datos congelados y monitores OBD2, el informe HTML (sin abrir el
navegador) y la conexión WiFi con un ELM327 simulado en 127.0.0.1. Tarda
unos 90 segundos.

Idioma: español por defecto; con OBD2DESK_IDIOMA=en se prueba en inglés y además
se buscan restos de español en todos los textos de la ventana. Al final cambia
de idioma con el selector y comprueba que la ventana se reconstruye.
"""
import os
import sys
import tempfile
import time
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["XDG_CONFIG_HOME"] = os.environ["APPDATA"] = tempfile.mkdtemp()
os.environ["OBD2DESK_SIN_COMPROBAR_VERSION"] = "1"   # sin consultar GitHub durante la prueba
os.environ.setdefault("OBD2DESK_IDIOMA", "es")
IDIOMA = os.environ["OBD2DESK_IDIOMA"]

import socket                       # noqa: E402
import threading                    # noqa: E402
import tkinter as tk                # noqa: E402
import webbrowser                   # noqa: E402
from tkinter import messagebox, ttk # noqa: E402

import re                           # noqa: E402

import gui                          # noqa: E402
import ia                           # noqa: E402
import idioma                       # noqa: E402
from idioma import tr               # noqa: E402

fallos = []
dialogos = []
messagebox.showerror = lambda *a, **k: dialogos.append(("error", a))
messagebox.showinfo = lambda *a, **k: dialogos.append(("info", a))
messagebox.askyesno = lambda *a, **k: True
abiertos = []
webbrowser.open = lambda url, *a, **k: abiertos.append(url)


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


ESPANOL = re.compile(r"[áéíóúñ¿¡]|\b(de|del|la|el|los|las|para|con|sin|una?|averías?|módulos?|"
                     r"puerto|conectar|leer|borrar|grupos?|motor|datos)\b", re.I)


NOMBRES_PROPIOS = re.compile(r"Córdoba|Škoda|Citroën")      # modelos y marcas: no se traducen


def descripciones_puertos():
    """Descripciones de los puertos serie reales del PC: las da el sistema operativo en su
    idioma (p. ej. «Puerto de comunicaciones (COM1)» en un Windows en español)."""
    try:
        from serial.tools import list_ports
        return {p.description for p in list_ports.comports() if p.description}
    except Exception:
        return set()


PUERTOS_SISTEMA = descripciones_puertos()


def textos_ventana(w):
    """Todos los textos visibles de la ventana (etiquetas, botones, pestañas, tablas, cuadros de texto)."""
    out = []
    try:
        out.append(str(w.cget("text")))
    except tk.TclError:
        pass
    if isinstance(w, ttk.Notebook):
        out += [w.tab(t, "text") for t in w.tabs()]
    elif isinstance(w, ttk.Treeview):
        out += [w.heading(c, "text") for c in w["columns"]]
        out += [str(v) for i in w.get_children() for v in w.item(i, "values")]
    elif isinstance(w, tk.Text):
        out.append(w.get("1.0", "end"))
    elif isinstance(w, ttk.Combobox):
        out += list(w["values"])
    elif isinstance(w, tk.Listbox):
        out += list(w.get(0, "end"))
    for h in w.winfo_children():
        out += textos_ventana(h)
    return out


def revisar_idioma(donde):
    """En inglés: que no quede texto en español en la ventana."""
    if IDIOMA != "en":
        return
    restos = set()
    for t in textos_ventana(root):
        for linea in t.splitlines():
            linea = re.sub(r"\d\d:\d\d:\d\d  \[.*", "", linea)        # depuración del registro
            for desc in PUERTOS_SISTEMA:                                # no son textos del programa
                linea = linea.replace(desc, "")
            if ESPANOL.search(NOMBRES_PROPIOS.sub("", linea)) and "Español" not in linea:
                restos.add(linea.strip())
    ok(not restos, f"sin textos en español ({donde})")
    for r in sorted(restos)[:15]:
        print("       ", r[:110])


root = tk.Tk(className=gui.NOMBRE)
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
    if modo == gui.ELM:
        estados = [app.dtc_tree.item(i, "values")[3] for i in app.dtc_tree.get_children()]
        ok(estados.count(tr("Permanente")) == 1, f"averías memorizadas, pendientes y permanentes {estados}")
        ok(len(app.ff_tree.get_children()) == 10 and "P0171" in str(app.ff_lbl.cget("text")),
           "datos congelados de la P0171 (10 valores)")
        textos = [str(w.cget("text")) for w in app.ready_card.winfo_children()]
        ok(any(tr("{n} de {total} sin completar", n=1, total=8) in t for t in textos),
           "monitores de preparación en Vehículo (1 de 8 sin completar)")
        campos = dict(app.vehicle_fields)
        ok(campos.get("  " + tr("Fabricante")) == "SEAT" and campos.get(tr("Calibración (CALID)")) == "SIM-CAL-0471",
           "VIN decodificado y calibración en Vehículo")
    else:
        app.scan_modules([0x01, 0x03, 0x08, 0x17], confirmar=False)
        ok(esperar(lambda: app.scan_result is not None and app.connected and app.worker.online
                   and not app.scanning, 90), "escaneo de módulos y vuelta al módulo 01")
        filas = [app.dtc_tree.item(i, "values") for i in app.dtc_tree.get_children()]
        ok(len(filas) == 7 and tr("Responden {n} de {total} módulos · {averias} avería(s)", n=3, total=4, averias=4)
           == str(app.dtc_lbl.cget("text")), f"escaneo: 3 módulos de 4, 4 averías ({len(filas)} filas)")
    revisar_idioma(f"averías {modo}")
    app.nb.select(app.tab_ecu)
    revisar_idioma(f"vehículo {modo}")
    app.make_report()
    ok(esperar(lambda: getattr(app, "last_report", None) and abiertos, 20), "informe generado y abierto")
    if getattr(app, "last_report", None):
        with open(app.last_report, encoding="utf-8") as f:
            h = f.read()
        claves = (("P0171", tr("Datos congelados"), tr("Monitores de preparación (readiness)"), "SEAT")
                  if modo == gui.ELM else ("00553", tr("Escaneo de módulos"), "00779"))
        ok(all(c in h for c in claves), f"contenido del informe ({', '.join(claves)})")
        if IDIOMA == "en":
            cuerpo = re.sub(r"<[^>]+>|<style>.*?</style>", " ", h, flags=re.S)
            ok(not re.search(r"[áéíóúñ]", NOMBRES_PROPIOS.sub("", cuerpo)), "informe en inglés")
        os.remove(app.last_report)
        app.last_report = None
        abiertos.clear()
    app.clear_dtcs()
    esperar(lambda: tr("Borrando...") != str(app.dtc_lbl.cget("text")), 15)
    ok(not dialogos, "borrado sin errores")

    app.toggle_live("panel")
    ch = app.ch_boost if modo == gui.KKL else app.ch_rpm
    n = lambda: sum(len(d) for d in ch.data.values())
    ok(esperar(lambda: n() >= 3, 20), f"lectura en vivo del panel ({n()} puntos en la gráfica)")
    app.nb.select(app.tab_panel)
    revisar_idioma(f"panel {modo}")
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
    revisar_idioma(f"valores medidos {modo}")

    app.toggle_connect()
    ok(esperar(lambda: not app.connected, 10), "desconecta")

print("ELM327 WiFi (adaptador simulado en 127.0.0.1)")
from simulador import FakeELMSerial  # noqa: E402
srv = socket.socket()
srv.bind(("127.0.0.1", 0))
srv.listen(1)


def servir():
    c, _ = srv.accept()
    elm = FakeELMSerial()
    while True:
        d = c.recv(256)
        if not d:
            break
        elm.write(d)
        if elm.rx:
            c.sendall(bytes(elm.rx))
            elm.rx.clear()


threading.Thread(target=servir, daemon=True).start()
app.mode_var.set(gui.MODOS[gui.ELM])
app._apply_mode()
ok(gui.WIFI in app.port_cb["values"] and str(app.port_cb.cget("state")) == "normal",
   "opción WiFi en la lista y puerto editable en OBD2")
app.port_var.set(f"127.0.0.1:{srv.getsockname()[1]}")
app.toggle_connect()
ok(esperar(lambda: app.connected, 40), "conecta por WiFi")
if app.connected:
    app.read_dtcs()
    ok(esperar(lambda: app.dtc_tree.get_children(), 15), "lee averías por WiFi")
    app.toggle_connect()
    ok(esperar(lambda: not app.connected, 10), "desconecta")
ok(gui.wifi_destino(gui.WIFI) == ("192.168.0.10", 35000) and gui.wifi_destino("COM3") is None
   and gui.wifi_destino("/dev/ttyUSB0") is None, "reconoce direcciones WiFi y puertos serie")
ok(gui.version_mayor("v0.3.1", "0.3.0") and not gui.version_mayor("v0.3.0", "0.3.0")
   and not gui.version_mayor("v0.2.9", "0.3.0") and gui.version_mayor("v1.0.0", "0.10.0"), "comparación de versiones")

ok(not dialogos, f"sin diálogos de error hasta aquí {dialogos}")

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

print("Cambio de idioma con el selector")
app.nb.select(app.tab_ia)
revisar_idioma("asistente IA y registro")
otro = "es" if IDIOMA == "en" else "en"
app.lang_var.set(idioma.IDIOMAS[otro])
app._cambiar_idioma()
ok(esperar(lambda: getattr(root, "app", None) is not None and root.app is not app, 10), "la ventana se reconstruye")
nueva = getattr(root, "app", app)
ok(idioma.actual() == otro and ia.cargar_config().get("idioma") == otro, f"idioma {otro} aplicado y guardado")
ok(str(nueva.conn_btn.cget("text")) == ("Connect" if otro == "en" else "Conectar")
   and gui.SIM in nueva.port_cb["values"], "textos de la ventana en el idioma nuevo")
ok(ia.leer_clave(ia.cargar_config(), "anthropic") == "sk-prueba-123", "se conserva la configuración de la IA")
nueva.port_var.set(gui.SIM)
nueva.toggle_connect()
ok(esperar(lambda: nueva.connected, 40), "conecta después de cambiar de idioma")
nueva.toggle_connect()
esperar(lambda: not nueva.connected, 10)
app = nueva

if IDIOMA == "en" or otro == "en":
    ok(not idioma.faltan, "sin textos sin traducir al inglés durante la prueba")
    for t in sorted(idioma.faltan):
        print("       falta:", repr(t))

ok(not dialogos, f"sin diálogos de error {dialogos}")
ok(not errores_tk, "sin excepciones en la interfaz")
for e in errores_tk:
    print(e)
app.on_close()
esperar(lambda: False, 1)
print("\nTODO CORRECTO" if not fallos else f"\n{len(fallos)} FALLOS")
sys.exit(1 if fallos else 0)
