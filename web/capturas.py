"""
Genera las capturas de la web con los simuladores, en una pantalla virtual.

    xvfb-run -a -s "-screen 0 2400x1500x24 -dpi 144" python3 web/capturas.py        (español)
    xvfb-run -a -s "-screen 0 2400x1500x24 -dpi 144" python3 web/capturas.py en     (inglés)

Necesita ImageMagick (import, magick). Deja las imágenes en web/img/ (*.webp y og.jpg)
o, en inglés, en web/img/en/.
La conversación del asistente IA es un guion de ejemplo (no gasta saldo): solo
se sustituye la llamada al modelo; las herramientas se ejecutan de verdad
contra el simulador, así que las lecturas y el diálogo son los reales.
"""
import os
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, RAIZ)
os.environ["XDG_CONFIG_HOME"] = os.environ["APPDATA"] = tempfile.mkdtemp()
os.environ["OBD2DESK_SIN_COMPROBAR_VERSION"] = "1"
IDIOMA = sys.argv[1] if len(sys.argv) > 1 else "es"
os.environ["OBD2DESK_IDIOMA"] = IDIOMA
EN = IDIOMA == "en"

import tkinter as tk                # noqa: E402
from tkinter import messagebox      # noqa: E402

import gui                          # noqa: E402
import ia                           # noqa: E402

SALIDA = os.path.join(RAIZ, "web", "img", "en") if EN else os.path.join(RAIZ, "web", "img")
os.makedirs(SALIDA, exist_ok=True)
messagebox.askyesno = lambda *a, **k: True

TEXTO_IA = """## Conclusión
Ahora mismo el aire y el turbo responden bien: en el acelerón la masa de aire real (grupo 003) y la presión de turbo real (grupo 011) siguen a las teóricas. Las dos averías memorizadas apuntan a un fallo **que va y viene**.

## Causas más probables
- **Caudalímetro (G70) o su conector**: avería 00553, señal no plausible. Si falla a ratos, la centralita entra en emergencia y recorta potencia.
- **Regulación del turbo (N75 y tubos de vacío)**: avería 01262 intermitente, límite de regulación sobrepasado.

## Qué hacer
- Limpia el conector del caudalímetro y mueve el cableado al ralentí mirando el grupo 003.
- Revisa los tubos de vacío de la N75 y del actuador del turbo.
- Borra las averías y vuelve a leerlas tras una prueba: si reaparece la 00553, cambia el caudalímetro.

Puedes circular mientras tanto, sin forzar el motor.
"""

TEXTO_IA_EN = """## Conclusion
Right now the air and the turbo respond well: during the rev the actual air mass (block 003) and the actual boost pressure (block 011) follow the specified values. The two stored faults point to a problem **that comes and goes**.

## Most likely causes
- **Air mass meter (G70) or its connector**: fault 00553, implausible signal. If it drops out intermittently, the ECU goes into limp mode and cuts power.
- **Boost control (N75 and vacuum hoses)**: intermittent fault 01262, control limit exceeded.

## What to do
- Clean the air mass meter connector and wiggle the wiring at idle while watching block 003.
- Check the vacuum hoses of the N75 and the turbo actuator.
- Clear the faults and read them again after a test drive: if 00553 comes back, replace the air mass meter.

You can keep driving in the meantime, without pushing the engine.
"""


def esperar(cond, seg):
    t = time.monotonic() + seg
    while time.monotonic() < t:
        root.update()
        if cond():
            return True
        time.sleep(0.02)
    return False


def pausa(seg):
    esperar(lambda: False, seg)


def capturar(nombre, ventana=None):
    """Captura la pantalla virtual recortada a la ventana principal (incluye diálogos encima) o a otra ventana."""
    ventana = ventana or root
    root.update()
    pausa(0.5)
    x, y, w, h = ventana.winfo_rootx(), ventana.winfo_rooty(), ventana.winfo_width(), ventana.winfo_height()
    png = os.path.join(tempfile.gettempdir(), "captura.png")
    subprocess.run(["import", "-window", "root", "-crop", f"{w}x{h}+{x}+{y}", "+repage", png], check=True)
    destino = os.path.join(SALIDA, nombre + ".webp")
    subprocess.run(["magick", png, "-quality", "88", destino], check=True)
    # versión de 1000 px para pantallas pequeñas (srcset de la web)
    subprocess.run(["magick", png, "-resize", "1000x", "-quality", "85",
                    os.path.join(SALIDA, nombre + "-1000.webp")], check=True)
    print(f"  {destino} ({os.path.getsize(destino) // 1024} KB)")


def como_principal(win):
    """Pone una ventana secundaria encima y del mismo tamaño que la principal (capturas iguales)."""
    win.geometry(f"{root.winfo_width()}x{root.winfo_height()}+{root.winfo_rootx()}+{root.winfo_rooty()}")
    win.lift()
    root.update()
    pausa(1)


def conectar(modo):
    if app.connected:
        app.toggle_connect()
        esperar(lambda: not app.connected, 10)
    app.mode_var.set(gui.MODOS[modo])
    app._apply_mode()
    app.port_var.set(gui.SIM)
    app.toggle_connect()
    if not esperar(lambda: app.connected, 40):
        sys.exit("No conecta con el simulador")


def guion_ia(self, peticion, on_text, on_tool, cancelado):
    """Sustituye a Conversacion.enviar: herramientas reales, texto de ejemplo."""
    on_tool("estado_conexion", {})
    on_tool("leer_averias", {})
    on_tool("consultar_historial", {})
    on_text("There are two stored faults. I'll check the air and the turbo with the engine running.\n" if EN else
            "Hay dos averías memorizadas. Voy a comprobar el aire y el turbo con el motor en marcha.\n")
    on_tool("pedir_accion_usuario", {"instruccion": (
        "Start the engine and let it idle. When you press Done, floor the throttle in neutral and release it. "
        "Mind the belt and the fan." if EN else
        "Arranca el motor y déjalo al ralentí. Al pulsar Hecho, da un acelerón a fondo en vacío y suelta. "
        "Cuidado con la correa y el ventilador.")})
    on_tool("leer_valores", {"elementos": ["3", "11"], "muestras": 10, "intervalo_s": 0})
    for parte in (TEXTO_IA_EN if EN else TEXTO_IA).split(" "):
        on_text(parte + " ")
        time.sleep(0.005)
    return True


root = tk.Tk(className=gui.NOMBRE)
gui._elegir_fuentes(root)
app = gui.App(root)


root.geometry("+0+0")
pausa(1)

print("KKL")
conectar(gui.KKL)
app.toggle_live("panel")
pausa(25)                                   # llena las gráficas
app.nb.select(app.tab_panel)
capturar("panel-kkl")
# imagen para redes sociales (1200x630, JPG porque no todas admiten WebP)
subprocess.run(["magick", os.path.join(SALIDA, "panel-kkl.webp"), "-resize", "1200x", "-gravity", "north",
                "-crop", "1200x630+0+0", "+repage", "-quality", "85", os.path.join(SALIDA, "og.jpg")], check=True)
app._stop_live()

app.nb.select(app.tab_vals)
for g, v in app.group_vars.items():
    v.set(g in (1, 3, 11))
app.toggle_rec()
pausa(4)
app.tree.selection_set([app.tree_items[(11, 1)], app.tree_items[(11, 2)]])   # gráfica: turbo teórico y real
pausa(20)
capturar("valores-kkl")
nombre = app.csv_file.name if app.csv_file else None
app._stop_rec()
app._stop_live()
if nombre:
    os.remove(nombre)

app.nb.select(app.tab_dtc)
print("Escaneo de módulos (unos 2 minutos)")
app.scan_modules(confirmar=False)
esperar(lambda: app.scan_result is not None and not app.scanning, 240)
esperar(lambda: str(app.dtc_read_btn.cget("state")) == "normal", 30)   # ya ha vuelto al módulo 01
pausa(1)
capturar("averias-kkl")

print("Test de actuadores")
app.test_actuadores()
va = app.ventana_act
como_principal(va.win)
va.ok_var.set(True)
va._botones()
for _ in range(2):
    va.siguiente()
    esperar(lambda: va.estado != "esperando", 10)
pausa(3.5)
capturar("actuadores", va.win)
va.terminar()
esperar(lambda: va.estado == "fin", 20)
va.cerrar()

print("Adaptación y codificación")
app.adaptacion()
vd = app.ventana_adapt
como_principal(vd.win)
vd.ok_var.set(True)
vd.canal_var.set("1")
vd.leer()
esperar(lambda: vd.ocupado is None, 10)
vd.valor_var.set("130")
vd.probar()
esperar(lambda: vd.ocupado is None, 10)
vd.guardar()                                # queda apuntado en el registro de cambios
esperar(lambda: vd.ocupado is None, 10)
vd.valor_var.set("132")
vd.probar()
esperar(lambda: vd.ocupado is None, 10)
capturar("adaptacion", vd.win)
vd.cerrar()
esperar(lambda: not vd.win.winfo_exists(), 10)

app.nb.select(app.tab_ecu)
capturar("vehiculo-kkl")

print("Asistente IA")
ia.Conversacion.enviar = guion_ia
app.nb.select(app.tab_ia)
app.ai_key.insert(0, "clave-de-ejemplo")
app._ai_save()                              # en la config temporal
app.ai_entry.insert(0, "It lacks power when accelerating and blows some black smoke" if EN else
                    "Le falta potencia al acelerar y echa algo de humo negro")
app._ai_ask()
if not esperar(lambda: app.ai_dialog is not None, 30):
    sys.exit("No aparece el diálogo de la IA")
pausa(1)
capturar("ia-accion")
w, reply = app.ai_dialog
app.ai_dialog = None
reply.put((gui.tr("Hecho"), False))
w.destroy()
esperar(lambda: not app.ai_busy, 60)
pausa(1)
app.ai_txt.see("1.0")
capturar("ia-diagnostico")

print("ELM327")
conectar(gui.ELM)
app.toggle_live("panel")
pausa(25)
app.nb.select(app.tab_panel)
capturar("panel-obd")
app._stop_live()

print("Consumo y 0-100")
app.nb.select(app.tab_cons)
app.worker.ser.t0 = time.monotonic() - (8 * 3.14159265 - 1.5)   # el simulador sale de parado en 1,5 s
app.toggle_live("cons")
esperar(lambda: app.crono.tiempos, 30)
pausa(9)
capturar("consumo-obd")
app._stop_live()

print("Visor de CSV (30 s de grabación)")
app.nb.select(app.tab_vals)
app.pid_list.selection_clear(0, "end")
for pid in (0x0C, 0x0D, 0x04, 0x05, 0x10, 0x11):
    if pid in app.pid_order:
        app.pid_list.selection_set(app.pid_order.index(pid))
app.toggle_rec()
pausa(30)
nombre = app.csv_file.name if app.csv_file else None
app._stop_rec()
app._stop_live()
if nombre:
    v = app.abrir_csv(nombre)
    como_principal(v.win)
    v.lista.selection_clear(0, "end")
    for i in range(v.lista.size()):
        if v.lista.get(i).strip().split(" (")[0] in (gui.tr("Velocidad"), gui.tr("Carga del motor"), gui.tr("Temp. refrigerante")):
            v.lista.selection_set(i)
    v._elegir()
    root.update()
    v.grafica._mover(type("E", (), {"x": int(v.grafica.winfo_width() * 0.42)})())
    capturar("visor-csv", v.win)
    v.win.destroy()
    os.remove(nombre)

app.nb.select(app.tab_dtc)
app.read_dtcs()
esperar(lambda: app.ff_tree.get_children(), 15)
capturar("averias-obd")

print("Historial")
app.clear_dtcs()
esperar(lambda: gui.tr("Comparado con el diagnóstico del {fecha} ({tipo}):", fecha="", tipo="")[:12]
        in str(app.hist_lbl.cget("text")), 20)
vh = app.ver_historial()
for w in vh.win.winfo_children():                 # la carpeta temporal de la captura, como la de verdad
    if isinstance(w, gui.ttk.Label) and app.historial.carpeta in str(w.cget("text")):
        w.configure(text=str(w.cget("text")).replace(app.historial.carpeta, "~/.config/OBD2Desk/historial"))
como_principal(vh.win)
capturar("historial", vh.win)
vh.win.destroy()
app.nb.select(app.tab_ecu)
capturar("vehiculo-obd")

print("Ayuda")
app.nb.select(app.tab_ayuda)
app.ayuda_lista.selection_set(0)
capturar("ayuda")

print("KKL con un motor de gasolina")
import simulador                    # noqa: E402
simulador.GASOLINA = True
conectar(gui.KKL)
app.toggle_live("panel")
pausa(25)
app.nb.select(app.tab_panel)
capturar("panel-gasolina")
app._stop_live()
app.nb.select(app.tab_vals)
for g, v in app.group_vars.items():
    v.set(g in (2, 3, 5))
app.rec_lbl.configure(text="")
app.toggle_live("vals")
pausa(3)
app.tree.selection_set([app.tree_items[(2, 1)], app.tree_items[(3, 2)]])   # gráfica: carga y mariposa
pausa(30)
capturar("valores-gasolina")
app._stop_live()

print("Ajustes básicos (adaptación de la mariposa)")
app.nb.select(app.tab_dtc)
app.ajustes_basicos()
vb = app.ventana_ajustes
como_principal(vb.win)
vb.ok_var.set(True)
vb._botones()
vb.activar()
pausa(5)
capturar("ajustes", vb.win)
vb.cerrar()
esperar(lambda: not vb.win.winfo_exists(), 10)
simulador.GASOLINA = False

app.toggle_connect()
esperar(lambda: not app.connected, 10)
app.on_close()
pausa(1)
