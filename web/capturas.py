"""
Genera las capturas de la web con los simuladores, en una pantalla virtual.

    xvfb-run -a -s "-screen 0 2400x1500x24 -dpi 144" python3 web/capturas.py

Necesita ImageMagick (import, magick). Deja las imágenes en web/img/ (*.webp y og.jpg).
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
os.environ["TOLEDO_SIN_COMPROBAR_VERSION"] = "1"

import tkinter as tk                # noqa: E402
from tkinter import messagebox      # noqa: E402

import gui                          # noqa: E402
import ia                           # noqa: E402

SALIDA = os.path.join(RAIZ, "web", "img")
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


def capturar(nombre):
    """Captura la pantalla virtual recortada a la ventana principal (incluye diálogos encima)."""
    root.update()
    pausa(0.5)
    x, y, w, h = root.winfo_rootx(), root.winfo_rooty(), root.winfo_width(), root.winfo_height()
    png = os.path.join(tempfile.gettempdir(), "captura.png")
    subprocess.run(["import", "-window", "root", "-crop", f"{w}x{h}+{x}+{y}", "+repage", png], check=True)
    destino = os.path.join(SALIDA, nombre + ".webp")
    subprocess.run(["magick", png, "-quality", "88", destino], check=True)
    print(f"  {destino} ({os.path.getsize(destino) // 1024} KB)")


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
    on_text("Hay dos averías memorizadas. Voy a comprobar el aire y el turbo con el motor en marcha.\n")
    on_tool("pedir_accion_usuario", {"instruccion": "Arranca el motor y déjalo al ralentí. Al pulsar "
                                     "Hecho, da un acelerón a fondo en vacío y suelta. Cuidado con la "
                                     "correa y el ventilador."})
    on_tool("leer_valores", {"elementos": ["3", "11"], "muestras": 10, "intervalo_s": 0})
    for parte in TEXTO_IA.split(" "):
        on_text(parte + " ")
        time.sleep(0.005)
    return True


root = tk.Tk(className="ToledoDiagnosis")
gui._elegir_fuentes(root)
app = gui.App(root)


def renombrar(w):
    """La web ya usa el nombre OBD2Desk; el programa aún no (pendiente de renombrar)."""
    try:
        if w.cget("text") == "Toledo Diagnosis":
            w.configure(text="OBD2Desk")
    except tk.TclError:
        pass
    for h in w.winfo_children():
        renombrar(h)


renombrar(root)
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
pausa(6)
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

app.nb.select(app.tab_ecu)
capturar("vehiculo-kkl")

print("Asistente IA")
ia.Conversacion.enviar = guion_ia
app.nb.select(app.tab_ia)
app.ai_key.insert(0, "clave-de-ejemplo")
app._ai_save()                              # en la config temporal
app.ai_entry.insert(0, "Le falta potencia al acelerar y echa algo de humo negro")
app._ai_ask()
if not esperar(lambda: app.ai_dialog is not None, 30):
    sys.exit("No aparece el diálogo de la IA")
pausa(1)
capturar("ia-accion")
w, reply = app.ai_dialog
app.ai_dialog = None
reply.put(("Hecho", False))
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
app.nb.select(app.tab_dtc)
app.read_dtcs()
esperar(lambda: app.ff_tree.get_children(), 15)
capturar("averias-obd")
app.nb.select(app.tab_ecu)
capturar("vehiculo-obd")

app.toggle_connect()
esperar(lambda: not app.connected, 10)
app.on_close()
pausa(1)
