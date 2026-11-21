"""
Interfaz grafica de diagnostico: VAG KW1281 (cable KKL) y OBD2 generico (ELM327).

    python gui.py

Elige el tipo de conexion, el puerto COM (o "Simulador") y pulsa Conectar.
"""
import csv
import datetime
import math
import os
import queue
import sys
import threading
import time
import tkinter as tk
import webbrowser
from collections import deque
from tkinter import messagebox, ttk

import ia
from elm327 import ELM327, ELM327Error
from kw1281 import KW1281, KW1281Error
from obd_datos import OBD_STANDARDS, PIDS, decode_pid
from obd_datos import describe_dtc as describe_obd_dtc
from toledo import leer_grupo_formateado, texto_id
from vag_datos import DTCS, FAULT_TYPES, GRUPOS_EDC15, MODULOS
from vag_datos import describe_dtc as vag_describe_dtc

# ---------------------------------------------------------------------------
# Estilo
# ---------------------------------------------------------------------------
BG = "#111418"
PANEL = "#181c22"
CARD = "#1f242c"
CARD2 = "#262c36"
TRACK = "#2f3642"
FG = "#e8ebf0"
MUTED = "#8a93a2"
ACCENT = "#ff7a29"      # naranja
BLUE = "#4aa8ff"
OK = "#3ccf7a"
WARN = "#f5b83d"
ERR = "#ef5350"

WINDOWS = sys.platform == "win32"
# Fuentes: en Linux se eligen al arrancar entre las instaladas (ver _elegir_fuentes)
FONT = "Segoe UI" if WINDOWS else "DejaVu Sans"
MONO = "Consolas" if WINDOWS else "DejaVu Sans Mono"
SIM = "Simulador (sin coche)"

KKL, ELM = "kkl", "elm"
MODOS = {KKL: "KKL · VAG KW1281 (hasta 2004)", ELM: "ELM327 · OBD2 genérico"}

PANEL_GROUPS = [1, 3, 11]
PANEL_PIDS = [0x0C, 0x0D, 0x05, 0x04, 0x0F, 0x10, 0x11, 0x42]

# Carpeta donde se guardan los CSV: junto al .exe si esta empaquetado
if getattr(sys, "frozen", False):
    CARPETA = os.path.dirname(sys.executable)
else:
    CARPETA = os.path.dirname(os.path.abspath(__file__))


def recurso(nombre):
    """Ruta a un archivo incluido (funciona tambien dentro del .exe de PyInstaller)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, nombre)


def _dpi_aware():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            # icono propio en la barra de tareas (en vez del de Python)
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("toledo.kw1281.diagnosis")
        except Exception:
            pass


def _elegir_fuentes(root):
    """En Linux usa la primera fuente disponible de cada lista (Fedora: Noto/Cantarell...)."""
    global FONT, MONO
    if WINDOWS:
        return
    from tkinter import font as tkfont
    disponibles = set(tkfont.families(root))
    for f in ("Noto Sans", "Cantarell", "Ubuntu", "DejaVu Sans", "Liberation Sans"):
        if f in disponibles:
            FONT = f
            break
    for f in ("Noto Sans Mono", "DejaVu Sans Mono", "Liberation Mono", "Ubuntu Mono"):
        if f in disponibles:
            MONO = f
            break


def _poner_icono(win, defecto=False):
    try:
        if WINDOWS:
            if defecto:
                win.iconbitmap(default=recurso("icono.ico"))
            else:
                win.iconbitmap(recurso("icono.ico"))
        else:
            img = tk.PhotoImage(file=recurso("icono.png"))
            win.iconphoto(defecto, img)
            win._icono = img                   # evita que el recolector borre la imagen
    except tk.TclError:
        pass


def _barra_oscura(root):
    if sys.platform == "win32":
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
            val = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
        except Exception:
            pass


def num(rows, i=0):
    try:
        return float(rows[i][1])
    except (IndexError, ValueError, TypeError):
        return None


def rows_of(data, key):
    v = data.get(key)
    return v if isinstance(v, list) else []


def nice_step(x):
    if x <= 0:
        return 1
    e = 10 ** math.floor(math.log10(x))
    for m in (1, 2, 2.5, 5, 10):
        if m * e >= x:
            return m * e
    return 10 * e


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------
class Gauge(tk.Canvas):
    def __init__(self, parent, title, unit, vmin, vmax, major, warn=None, s=1.0, decimals=0):
        self.s = s
        self.r = 78 * s
        w = int(2 * self.r + 60 * s)
        h = int(2 * self.r + 30 * s)
        super().__init__(parent, width=w, height=h, bg=CARD, highlightthickness=0)
        self.cx, self.cy = w / 2, self.r + 18 * s
        self.vmin, self.vmax, self.warn, self.decimals = vmin, vmax, warn, decimals
        self.unit = unit
        r, cx, cy = self.r, self.cx, self.cy
        bbox = (cx - r, cy - r, cx + r, cy + r)
        self.bbox = bbox
        self.create_arc(bbox, start=210, extent=-240, style="arc", width=12 * s, outline=TRACK)
        if warn is not None:
            a = self._ang(warn)
            self.create_arc(bbox, start=a, extent=-(a + 30), style="arc", width=3 * s, outline=ERR)
        v = vmin
        while v <= vmax + 1e-9:
            a = math.radians(self._ang(v))
            x1, y1 = cx + (r - 13 * s) * math.cos(a), cy - (r - 13 * s) * math.sin(a)
            x2, y2 = cx + (r - 19 * s) * math.cos(a), cy - (r - 19 * s) * math.sin(a)
            self.create_line(x1, y1, x2, y2, fill=MUTED, width=max(1, int(1.5 * s)))
            xl, yl = cx + (r - 32 * s) * math.cos(a), cy - (r - 32 * s) * math.sin(a)
            lbl = f"{v / 1000:g}k" if vmax >= 2000 and v else f"{v:g}"
            self.create_text(xl, yl, text=lbl, fill=MUTED, font=(FONT, 8))
            v += major
        self.create_text(cx, cy + r * 0.78, text=title, fill=FG, font=(FONT, 10, "bold"))
        self.set(None)

    def _ang(self, v):
        f = (v - self.vmin) / (self.vmax - self.vmin)
        return 210 - 240 * max(0.0, min(1.0, f))

    def set(self, v, spec=None):
        self.delete("val")
        cx, cy, s = self.cx, self.cy, self.s
        if v is None:
            txt = "--"
        else:
            color = ERR if self.warn is not None and v >= self.warn else ACCENT
            ext = self._ang(v) - 210
            if abs(ext) > 0.5:
                self.create_arc(self.bbox, start=210, extent=ext, style="arc",
                                width=12 * s, outline=color, tags="val")
            txt = f"{v:.{self.decimals}f}"
        if spec is not None:
            a = math.radians(self._ang(spec))
            r = self.r
            self.create_line(cx + (r - 9 * s) * math.cos(a), cy - (r - 9 * s) * math.sin(a),
                             cx + (r + 9 * s) * math.cos(a), cy - (r + 9 * s) * math.sin(a),
                             fill=BLUE, width=3 * s, tags="val")
        self.create_text(cx, cy - 4 * s, text=txt, fill=FG if v is not None else MUTED,
                         font=(FONT, 22, "bold"), tags="val")
        self.create_text(cx, cy + 20 * s, text=self.unit, fill=MUTED, font=(FONT, 9), tags="val")


class Chart(tk.Canvas):
    def __init__(self, parent, title, unit, series, window=60, ymin_top=10, s=1.0):
        super().__init__(parent, bg=CARD, highlightthickness=0, height=int(210 * s))
        self.title, self.unit, self.series = title, unit, series
        self.window, self.ymin_top, self.s = window, ymin_top, s
        self.data = {name: deque() for name, _ in series}
        self.bind("<Configure>", lambda e: self.redraw())

    def clear(self):
        for d in self.data.values():
            d.clear()
        self.redraw()

    def add(self, t, values):
        for name, v in values.items():
            if v is None or name not in self.data:
                continue
            d = self.data[name]
            d.append((t, v))
            while d and d[0][0] < t - self.window:
                d.popleft()

    def redraw(self):
        self.delete("all")
        s = self.s
        w, h = self.winfo_width(), self.winfo_height()
        if w < 50:
            return
        L, R, T, B = 52 * s, 14 * s, 34 * s, 24 * s
        tid = self.create_text(14 * s, 16 * s, text=self.title, anchor="w", fill=FG, font=(FONT, 10, "bold"))
        self.create_text(self.bbox(tid)[2] + 8 * s, 16 * s, text=self.unit, anchor="w",
                         fill=MUTED, font=(FONT, 9))
        x = w - R
        for name, color in reversed(self.series):
            tid = self.create_text(x, 16 * s, text=name, anchor="e", fill=MUTED, font=(FONT, 9))
            x = self.bbox(tid)[0] - 6 * s
            self.create_rectangle(x - 10 * s, 13 * s, x, 19 * s, fill=color, outline="")
            x -= 18 * s

        vals = [v for d in self.data.values() for _, v in d]
        top = max(max(vals) * 1.1 if vals else 0, self.ymin_top)
        step = nice_step(top / 4)
        top = step * math.ceil(top / step)
        pw, ph = w - L - R, h - T - B
        v = 0
        while v <= top + 1e-9:
            y = T + ph - v / top * ph
            self.create_line(L, y, w - R, y, fill=TRACK)
            self.create_text(L - 6 * s, y, text=f"{v:g}", anchor="e", fill=MUTED, font=(FONT, 8))
            v += step
        for i, lbl in ((0, f"-{self.window}s"), (0.5, f"-{self.window // 2}s"), (1, "ahora")):
            self.create_text(L + pw * i, h - B + 12 * s, text=lbl, fill=MUTED, font=(FONT, 8))

        now = time.monotonic()
        for name, color in self.series:
            pts = []
            for t, v in self.data[name]:
                pts += [L + pw * (1 - (now - t) / self.window), T + ph - max(0, min(v, top)) / top * ph]
            if len(pts) >= 4:
                self.create_line(*pts, fill=color, width=2 * s)


# ---------------------------------------------------------------------------
# Hilo de comunicacion
# ---------------------------------------------------------------------------
class Worker(threading.Thread):
    def __init__(self, out_q):
        super().__init__(daemon=True)
        self.tasks = queue.Queue()
        self.out = out_q
        self.mode = None
        self.ecu = None          # KW1281
        self.elm = None          # ELM327
        self.ser = None
        self.live_items = None
        self.live_gen = 0
        self.debug = False
        self.online = False
        self.elm_errors = 0

    def post(self, kind, payload=None):
        self.out.put((kind, payload))

    def log(self, msg):
        self.post("log", msg)

    def submit(self, *task):
        self.tasks.put(task)

    def run(self):
        while True:
            try:
                task = self.tasks.get(timeout=0.01 if self.live_items else 0.1)
            except queue.Empty:
                task = None
            if task:
                if task[0] == "quit":
                    self._disconnect()
                    self.post("quit")
                    return
                try:
                    self.handle(*task)
                except Exception as e:
                    self.log(f"Error: {e}")
                    self.post("error", str(e))
                    if self.mode == ELM and self.online and self._is_port_error(e):
                        self._lost(str(e))
                self._check_lost()
                continue
            if self.live_items and self.online:
                self._read_live()
            self._check_lost()

    @staticmethod
    def _is_port_error(e):
        return isinstance(e, OSError) or type(e).__name__ == "SerialException"

    def _lost(self, msg):
        self.online = False
        self.live_items = None
        self.post("lost", msg)

    def _check_lost(self):
        if self.online and self.mode == KKL and self.ecu and not self.ecu.connected:
            self._lost(str(self.ecu.error))

    def _disconnect(self):
        self.live_items = None
        if self.ecu:
            try:
                self.ecu.disconnect()
            except Exception:
                pass
        if self.elm:
            try:
                self.elm.close()
            except Exception:
                pass
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ecu = self.elm = self.ser = None
        self.online = False

    def _open(self, mode, port):
        if port == SIM:
            import simulador
            return simulador.FakeSerial() if mode == KKL else simulador.FakeELMSerial()
        import serial
        if mode == KKL:
            ser = serial.Serial(port, 9600, timeout=0.05)
            ser.dtr, ser.rts = True, False
            if not WINDOWS:
                try:
                    ser.set_low_latency_mode(True)   # FTDI: latencia de 16 ms a 1 ms
                except Exception as e:
                    self.log(f"Aviso: no se pudo activar baja latencia en {port} ({e})")
        else:
            ser = serial.Serial(port, 38400, timeout=0.05)
        return ser

    def handle(self, kind, *args):
        if kind == "connect":
            mode, port, addr = args
            self._disconnect()
            self.mode = mode
            self.log(f"Abriendo {port}...")
            self.ser = self._open(mode, port)
            try:
                info = self._connect_kkl(addr) if mode == KKL else self._connect_elm()
            except Exception:
                self._disconnect()
                raise
            self.online = True
            self.elm_errors = 0
            self.post("connected", info)
        elif kind == "disconnect":
            self._disconnect()
            self.log("Desconectado.")
            self.post("disconnected")
        elif kind == "dtcs":
            self.post("dtcs", self.ecu.read_dtcs() if self.mode == KKL else self.elm.read_dtcs())
        elif kind == "clear":
            if self.mode == KKL:
                self.post("cleared", self.ecu.clear_dtcs())
            else:
                self.elm.clear_dtcs()
                self.post("cleared", self.elm.read_dtcs())
        elif kind == "live":
            self.live_items = args[0] or None
            self.live_gen = args[1]
        elif kind == "debug":
            self.debug = args[0]
            for b in (self.ecu, self.elm):
                if b:
                    b.debug = args[0]
        elif kind == "tool":
            nombre, entrada, reply = args
            try:
                reply.put(self._tool(nombre, entrada))
            except Exception as e:
                reply.put((f"Error de comunicación: {e}", True))
                if self.mode == ELM and self.online and self._is_port_error(e):
                    self._lost(str(e))

    # ---------------- herramientas del asistente IA ----------------
    @staticmethod
    def _fmt_obd_dtcs(d):
        def lista(codes):
            return "\n".join(f"- {c}: {describe_obd_dtc(c)}" for c in codes) or "- ninguna"
        return (f"Memorizadas:\n{lista(d['stored'])}\nPendientes:\n{lista(d['pending'])}\n"
                f"Testigo MIL: {'encendido' if d['mil'] else 'apagado'}")

    def _tool(self, nombre, e):
        if not self.online:
            return ("No hay conexión con el vehículo. Pide al usuario que conecte "
                    "(selector Conexión, Puerto y botón Conectar).", True)
        if nombre == "leer_averias":
            if self.mode == KKL:
                d = self.ecu.read_dtcs()
                self.post("dtcs", d)
                return ("\n".join("- " + vag_describe_dtc(*x) for x in d) or "Sin averías memorizadas.", False)
            d = self.elm.read_dtcs()
            self.post("dtcs", d)
            return self._fmt_obd_dtcs(d), False
        if nombre == "borrar_averias":
            if self.mode == KKL:
                rest = self.ecu.clear_dtcs()
                self.post("cleared", rest)
                return ("Averías borradas. " + ("Siguen presentes (avería activa):\n" +
                        "\n".join("- " + vag_describe_dtc(*x) for x in rest) if rest else "No queda ninguna."), False)
            self.elm.clear_dtcs()
            d = self.elm.read_dtcs()
            self.post("cleared", d)
            return "Averías borradas. Estado después de borrar:\n" + self._fmt_obd_dtcs(d), False
        if nombre == "leer_valores":
            return self._tool_valores(e)
        return f"Herramienta desconocida: {nombre}", True

    def _tool_valores(self, e):
        els = e.get("elementos")
        if isinstance(els, (str, int)):
            els = [els]
        if not isinstance(els, list) or not els:
            return "Indica al menos un grupo o PID en 'elementos'.", True
        try:
            muestras = max(1, min(40, int(e.get("muestras") or 1)))
        except (TypeError, ValueError):
            muestras = 1
        try:
            intervalo = max(0.0, min(5.0, float(e.get("intervalo_s") or 0)))
        except (TypeError, ValueError):
            intervalo = 0.0
        if muestras * intervalo > 120:
            intervalo = 120 / muestras
        items, notas = [], []
        for x in els:
            s = str(x).strip().upper()
            try:
                if self.mode == KKL:
                    v = int(s, 10)
                    ok = 0 <= v <= 255
                else:
                    v = int(s[2:] if s.startswith("0X") else s.rstrip("H"), 16)
                    ok = v in PIDS and v in self.elm.supported
            except ValueError:
                ok = False
            if ok and v not in items:
                items.append(v)
            elif not ok:
                notas.append(f"'{x}' no es válido o no está soportado por el vehículo; se ignora.")
        limite = 4 if self.mode == KKL else 10
        if len(items) > limite:
            notas.append(f"Solo se leen los {limite} primeros.")
            items = items[:limite]
        if not items:
            return "Ningún grupo o PID válido.\n" + "\n".join(notas), True

        serie = []
        t0 = time.monotonic()
        for i in range(muestras):
            espera = t0 + i * intervalo - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            data = self._muestra(items)
            serie.append((time.monotonic() - t0, data))
            if self.mode == KKL and not self.ecu.connected:
                notas.append("Se perdió la conexión durante la lectura.")
                break
        self.post("tool_live", serie[-1][1])
        return self._fmt_serie(serie, notas), False

    def _muestra(self, items):
        """Una lectura de los grupos/PIDs indicados: {clave: filas o texto de error}."""
        data = {}
        if self.mode == KKL:
            for g in items:
                try:
                    data[g] = leer_grupo_formateado(self.ecu, g)
                except KW1281Error as e:
                    data[g] = str(e)
                    if not self.ecu.connected:
                        break
        else:
            raw = self.elm.read_pids(items)
            for p in items:
                if p in raw:
                    data[p] = [decode_pid(p, raw[p])]
                else:
                    data[p] = "Sin respuesta"
        return data

    def _etiqueta(self, k):
        if self.mode == KKL:
            return f"G{k:03d}"
        return f"PID {k:02X}"

    def _fmt_serie(self, serie, notas):
        cols, errores = [], {}
        for _, data in serie:
            for k, rows in data.items():
                if isinstance(rows, str):
                    errores[k] = rows
                    continue
                for i, (nombre, _, unidad, ok) in enumerate(rows):
                    c = (k, i)
                    if c not in [x[0] for x in cols]:
                        cols.append((c, f"{self._etiqueta(k)} {nombre}" + (f" ({unidad})" if unidad else "")
                                     + ("" if ok else " [fórmula desconocida]")))
        out = []
        if len(serie) == 1:
            data = serie[0][1]
            for (k, i), titulo in cols:
                rows = data.get(k)
                if isinstance(rows, list) and i < len(rows):
                    out.append(f"- {titulo}: {rows[i][1]}")
        elif cols:
            out.append("t(s) | " + " | ".join(t for _, t in cols))
            for t, data in serie:
                vals = []
                for (k, i), _ in cols:
                    rows = data.get(k)
                    vals.append(rows[i][1] if isinstance(rows, list) and i < len(rows) else "-")
                out.append(f"{t:.2f} | " + " | ".join(vals))
        for k, err in errores.items():
            out.append(f"{self._etiqueta(k)}: {err}")
        if self.mode == KKL and cols:
            notas.append("Los nombres de los campos VAG son orientativos; la unidad la da la propia centralita.")
        return "\n".join(out + notas)

    def _connect_kkl(self, addr):
        self.ecu = KW1281(self.ser, address=addr, debug=self.debug, logger=self.log)
        self.log(f"Init a 5 baudios al módulo {addr:02X}...")
        self.ecu.connect()
        e = self.ecu
        ident = [texto_id(d) for d in e.ident] + ["", "", ""]
        self.log(f"Conectado a {e.baud} baudios, keywords {e.keywords[0]:02X} {e.keywords[1]:02X}")
        kw = f"{e.keywords[0]:02X} {e.keywords[1]:02X}" + ("  (KW1281)" if e.keywords == (0x01, 0x8A) else "")
        return {
            "mode": KKL,
            "status": f"Conectado · {MODULOS.get(addr, f'Módulo {addr:02X}')} · {e.baud} bd",
            "title": ident[0].strip(),
            "fields": [("Módulo", f"{addr:02X} · {MODULOS.get(addr, '?')}"),
                       ("Referencia", ident[0].strip() or "—"),
                       ("Componente", ident[1].strip() or "—"),
                       ("Software / taller", ident[2].strip() or "—"),
                       ("Datos adicionales", "  ".join(x for x in ident[3:] if x) or "—"),
                       ("Velocidad", f"{e.baud} baudios"),
                       ("Keywords", kw),
                       ("Eco del cable", "Sí" if e.echo else "No")],
        }

    def _connect_elm(self):
        self.elm = ELM327(self.ser, debug=self.debug, logger=self.log)
        self.log("Buscando ELM327 y protocolo OBD2 (puede tardar hasta 25 s)...")
        self.elm.connect()
        e = self.elm
        vin, volt = e.vin(), e.voltage()
        mil, ndtc = e.mil()
        std = e.obd_standard()
        self.log(f"Conectado: {e.version} · {e.proto_name}")
        medibles = sorted(p for p in e.supported if p in PIDS)
        return {
            "mode": ELM,
            "status": f"Conectado · OBD2 · {e.proto_name.replace('AUTO, ', '')}",
            "title": vin or e.proto_name,
            "supported": medibles,
            "fields": [("Adaptador", e.version),
                       ("Protocolo", e.proto_name),
                       ("Bastidor (VIN)", vin or "No disponible"),
                       ("Tensión batería", volt or "—"),
                       ("Estándar OBD", OBD_STANDARDS.get(std, "—") if std else "—"),
                       ("Testigo de avería (MIL)", "—" if mil is None else
                        (f"ENCENDIDO · {ndtc} avería(s)" if mil else f"Apagado · {ndtc} avería(s)")),
                       ("PIDs soportados", f"{len(e.supported)} ({len(medibles)} con valor legible)")],
        }

    def _read_live(self):
        items = list(self.live_items or [])
        if self.mode == KKL:
            data = self._muestra(items)
        else:
            try:
                data = self._muestra(items)
                self.elm_errors = 0
            except ELM327Error as e:
                self.elm_errors += 1
                data = {"Error": str(e)}
                if self.elm_errors >= 5:
                    self._lost(str(e))
                    return
            except Exception as e:
                if self._is_port_error(e):
                    self._lost(str(e))
                    return
                raise
        self.post("live", (self.live_gen, time.monotonic(), data))


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------
class App:
    def __init__(self, root):
        self.root = root
        self.s = root.winfo_fpixels("1i") / 96
        self.q = queue.Queue()
        self.worker = Worker(self.q)
        self.worker.start()
        self.mode = KKL
        self.connected = False
        self.supported = []
        self.live_source = None
        self.live_gen = 0
        self.csv_file = self.csv_writer = None
        self.csv_header = None
        self.csv_t0 = 0
        self.csv_n = 0
        self.tree_items = {}
        # Asistente IA
        self.cfg = ia.cargar_config()
        self.ai_chat = None          # ia.Conversacion
        self.ai_dialog = None        # (ventana, reply) de pedir_accion_usuario
        self.ai_busy = False
        self.ai_cancel = False
        self.ai_line = ""
        self.ai_conv = 0
        self.ai_first_chunk = True
        self.vehicle_fields = []
        self.last_dtc_text = None
        self.last_live_text = None

        root.title("Toledo Diagnosis · VAG KW1281 / OBD2")
        root.configure(bg=BG)
        _poner_icono(root, defecto=True)
        root.geometry(f"{int(1240 * self.s)}x{int(800 * self.s)}")
        root.minsize(int(1080 * self.s), int(680 * self.s))
        self._style()
        self._build()
        self._apply_mode()
        self._set_connected(False)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(50, self.poll)
        root.after(100, lambda: _barra_oscura(root))

    # ---------------- estilo ----------------
    def _style(self):
        st = ttk.Style(self.root)
        st.theme_use("clam")
        self.root.option_add("*TCombobox*Listbox.background", CARD2)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.font", (FONT, 10))
        st.configure(".", background=BG, foreground=FG, font=(FONT, 10), borderwidth=0)
        st.configure("TFrame", background=BG)
        st.configure("Panel.TFrame", background=PANEL)
        st.configure("Card.TFrame", background=CARD)
        st.configure("TLabel", background=BG, foreground=FG)
        st.configure("Panel.TLabel", background=PANEL)
        st.configure("Card.TLabel", background=CARD)
        st.configure("Muted.TLabel", background=CARD, foreground=MUTED)
        st.configure("PanelMuted.TLabel", background=PANEL, foreground=MUTED)
        st.configure("Title.TLabel", background=PANEL, font=(FONT, 15, "bold"))
        st.configure("Big.TLabel", background=CARD, font=(FONT, 18, "bold"))
        st.configure("TButton", background=CARD2, foreground=FG, padding=(14, 7),
                     bordercolor=TRACK, focusthickness=0, focuscolor=CARD2)
        st.map("TButton", background=[("disabled", CARD), ("active", TRACK)],
               foreground=[("disabled", "#555c68")])
        st.configure("Accent.TButton", background=ACCENT, foreground="#111", font=(FONT, 10, "bold"))
        st.map("Accent.TButton", background=[("disabled", CARD), ("active", "#ff9550")])
        st.configure("Danger.TButton", background="#5a2326", foreground="#ffd5d5")
        st.map("Danger.TButton", background=[("disabled", CARD), ("active", "#7a2b30")])
        st.configure("TCombobox", fieldbackground=CARD2, background=CARD2, foreground=FG,
                     arrowcolor=FG, bordercolor=TRACK, lightcolor=CARD2, darkcolor=CARD2,
                     padding=5, selectbackground=CARD2, selectforeground=FG)
        st.map("TCombobox", fieldbackground=[("readonly", CARD2), ("disabled", CARD)],
               foreground=[("readonly", FG), ("disabled", MUTED)])
        st.configure("TEntry", fieldbackground=CARD2, foreground=FG, insertcolor=FG,
                     bordercolor=TRACK, lightcolor=CARD2, darkcolor=CARD2, padding=5)
        st.configure("TCheckbutton", background=CARD, foreground=FG, indicatorbackground=CARD2,
                     indicatorforeground=ACCENT, focuscolor=CARD)
        st.map("TCheckbutton", background=[("active", CARD)],
               indicatorbackground=[("selected", CARD2)])
        st.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(12, 8, 12, 0),
                     bordercolor=PANEL, lightcolor=PANEL, darkcolor=PANEL)
        st.configure("TNotebook.Tab", background=BG, foreground=MUTED, padding=(18, 9),
                     font=(FONT, 10, "bold"), borderwidth=0, bordercolor=BG,
                     lightcolor=BG, darkcolor=BG, focuscolor=BG)
        st.map("TNotebook.Tab", background=[("selected", PANEL)], foreground=[("selected", FG)],
               bordercolor=[("selected", PANEL)], lightcolor=[("selected", ACCENT)],
               focuscolor=[("selected", PANEL)])
        st.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=FG,
                     rowheight=int(28 * self.s), bordercolor=CARD, lightcolor=CARD,
                     darkcolor=CARD, borderwidth=0, font=(FONT, 10))
        st.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        st.map("Treeview", background=[("selected", "#3a3226")], foreground=[("selected", FG)])
        st.configure("Treeview.Heading", background=CARD2, foreground=MUTED,
                     font=(FONT, 9, "bold"), padding=6, relief="flat")
        st.map("Treeview.Heading", background=[("active", TRACK)])
        st.configure("Vertical.TScrollbar", background=CARD2, troughcolor=CARD, arrowcolor=MUTED,
                     bordercolor=CARD, lightcolor=CARD2, darkcolor=CARD2, gripcount=0, arrowsize=12)
        st.map("Vertical.TScrollbar", background=[("active", TRACK)])

    # ---------------- construccion ----------------
    def _build(self):
        s = self.s
        head = ttk.Frame(self.root, style="Panel.TFrame", padding=(18, 12))
        head.pack(fill="x")
        left = ttk.Frame(head, style="Panel.TFrame")
        left.pack(side="left")
        ttk.Label(left, text="Toledo Diagnosis", style="Title.TLabel").pack(anchor="w")
        st_row = ttk.Frame(left, style="Panel.TFrame")
        st_row.pack(anchor="w")
        self.status_dot = tk.Canvas(st_row, width=int(12 * s), height=int(12 * s), bg=PANEL, highlightthickness=0)
        self.status_dot.pack(side="left", padx=(0, 6))
        self.status_lbl = ttk.Label(st_row, text="Desconectado", style="PanelMuted.TLabel")
        self.status_lbl.pack(side="left")

        right = ttk.Frame(head, style="Panel.TFrame")
        right.pack(side="right")
        ttk.Label(right, text="Conexión", style="PanelMuted.TLabel").grid(row=0, column=0, padx=(0, 6))
        self.mode_var = tk.StringVar(value=MODOS[KKL])
        self.mode_cb = ttk.Combobox(right, textvariable=self.mode_var, values=list(MODOS.values()),
                                    state="readonly", width=27)
        self.mode_cb.grid(row=0, column=1, padx=(0, 14))
        self.mode_cb.bind("<<ComboboxSelected>>", lambda e: self._apply_mode())

        ttk.Label(right, text="Puerto", style="PanelMuted.TLabel").grid(row=0, column=2, padx=(0, 6))
        self.port_var = tk.StringVar()
        self.port_cb = ttk.Combobox(right, textvariable=self.port_var, state="readonly", width=26)
        self.port_cb.grid(row=0, column=3)
        self.refresh_btn = ttk.Button(right, text="↻", width=3, command=self.refresh_ports)
        self.refresh_btn.grid(row=0, column=4, padx=(4, 14))

        self.mod_lbl = ttk.Label(right, text="Módulo", style="PanelMuted.TLabel")
        self.mod_lbl.grid(row=0, column=5, padx=(0, 6))
        self.mod_var = tk.StringVar()
        mods = [f"{a:02X} · {n}" for a, n in MODULOS.items()]
        self.mod_cb = ttk.Combobox(right, textvariable=self.mod_var, values=mods, state="readonly", width=22)
        self.mod_cb.current(0)
        self.mod_cb.grid(row=0, column=6, padx=(0, 14))
        self.conn_btn = ttk.Button(right, text="Conectar", style="Accent.TButton", width=12,
                                   command=self.toggle_connect)
        self.conn_btn.grid(row=0, column=7)

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True)
        self.tab_panel = ttk.Frame(self.nb, style="Panel.TFrame", padding=16)
        self.tab_vals = ttk.Frame(self.nb, style="Panel.TFrame", padding=16)
        self.tab_dtc = ttk.Frame(self.nb, style="Panel.TFrame", padding=16)
        self.tab_ecu = ttk.Frame(self.nb, style="Panel.TFrame", padding=16)
        self.tab_log = ttk.Frame(self.nb, style="Panel.TFrame", padding=16)
        self.tab_ia = ttk.Frame(self.nb, style="Panel.TFrame", padding=16)
        for t, n in ((self.tab_panel, "  Panel  "), (self.tab_vals, "  Valores medidos  "),
                     (self.tab_dtc, "  Averías  "), (self.tab_ecu, "  Vehículo  "),
                     (self.tab_ia, "  ✦ Asistente IA  "), (self.tab_log, "  Registro  ")):
            self.nb.add(t, text=n)
        self._build_panel()
        self._build_vals()
        self._build_dtc()
        self._build_ecu()
        self._build_ia()
        self._build_log()

        self.bar = ttk.Label(self.root, text="Listo. Elige conexión y puerto, y pulsa Conectar.",
                             style="PanelMuted.TLabel", padding=(18, 6))
        self.bar.pack(fill="x", side="bottom")

    def _card(self, parent, **kw):
        return ttk.Frame(parent, style="Card.TFrame", padding=kw.pop("padding", 12), **kw)

    def _stats_row(self, parent, items):
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.pack(fill="x", pady=12)
        out = {}
        for i, (key, title) in enumerate(items):
            frame.columnconfigure(i, weight=1)
            c = self._card(frame)
            c.grid(row=0, column=i, padx=6, sticky="ew")
            ttk.Label(c, text=title, style="Muted.TLabel").pack(anchor="w")
            v = tk.StringVar(value="--")
            ttk.Label(c, textvariable=v, style="Big.TLabel").pack(anchor="w")
            out[key] = v
        return out

    def _gauges_row(self, parent, gauges):
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.pack(fill="x")
        out = []
        for i, args in enumerate(gauges):
            frame.columnconfigure(i, weight=1)
            g = Gauge(frame, *args[:6], s=self.s, decimals=args[6] if len(args) > 6 else 0)
            g.grid(row=0, column=i, padx=6, sticky="ew")
            out.append(g)
        return out

    def _charts_row(self, parent, charts):
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.pack(fill="both", expand=True)
        frame.rowconfigure(0, weight=1)
        out = []
        for i, args in enumerate(charts):
            frame.columnconfigure(i, weight=1)
            c = Chart(frame, *args[:3], ymin_top=args[3], s=self.s)
            c.grid(row=0, column=i, padx=6, sticky="nsew")
            out.append(c)
        return out

    def _build_panel(self):
        p = self.tab_panel
        top = ttk.Frame(p, style="Panel.TFrame")
        top.pack(fill="x", pady=(0, 12))
        self.panel_lbl = ttk.Label(top, text="", style="PanelMuted.TLabel")
        self.panel_lbl.pack(side="left")
        self.panel_btn = ttk.Button(top, text="▶  Iniciar lectura", style="Accent.TButton",
                                    command=lambda: self.toggle_live("panel"))
        self.panel_btn.pack(side="right")

        # Panel VAG (KW1281)
        self.panel_vag = ttk.Frame(p, style="Panel.TFrame")
        self.g_rpm, self.g_iq, self.g_boost, self.g_temp = self._gauges_row(self.panel_vag, [
            ("Régimen", "rpm", 0, 5000, 1000, 4500),
            ("Caudal inyectado", "mg/H", 0, 60, 10, None, 1),
            ("Presión turbo", "mbar", 0, 2500, 500, 2300),
            ("Refrigerante", "°C", 0, 120, 20, 105)])
        self.vag_stats = self._stats_row(self.panel_vag, [
            ("n75", "Ciclo N75 (turbo)"), ("egr", "Ciclo válvula EGR"),
            ("volt", "Tensión dosificador"), ("maf", "Masa de aire real")])
        self.ch_boost, self.ch_maf = self._charts_row(self.panel_vag, [
            ("Presión de turbo · G011", "mbar", [("Teórica", BLUE), ("Real", ACCENT)], 2000),
            ("Masa de aire · G003", "mg/H", [("Teórica", BLUE), ("Real", ACCENT)], 500)])

        # Panel OBD2 (ELM327)
        self.panel_obd = ttk.Frame(p, style="Panel.TFrame")
        self.o_rpm, self.o_speed, self.o_temp, self.o_load = self._gauges_row(self.panel_obd, [
            ("Régimen", "rpm", 0, 8000, 1000, 6500),
            ("Velocidad", "km/h", 0, 240, 40, None),
            ("Refrigerante", "°C", 0, 120, 20, 105),
            ("Carga del motor", "%", 0, 100, 20, None)])
        self.obd_stats = self._stats_row(self.panel_obd, [
            ("iat", "Temp. aire admisión"), ("maf", "Caudal de aire (MAF)"),
            ("tps", "Posición mariposa"), ("volt", "Tensión centralita")])
        self.ch_rpm, self.ch_load = self._charts_row(self.panel_obd, [
            ("Régimen motor", "rpm", [("RPM", ACCENT)], 3000),
            ("Carga y mariposa", "%", [("Carga", ACCENT), ("Mariposa", BLUE)], 100)])

    def _build_vals(self):
        p = self.tab_vals
        side = self._card(p, padding=14)
        side.pack(side="left", fill="y", padx=(0, 14))
        self.side_title = ttk.Label(side, text="", style="Card.TLabel", font=(FONT, 11, "bold"))
        self.side_title.pack(anchor="w", pady=(0, 8))

        # Selección VAG
        self.side_vag = ttk.Frame(side, style="Card.TFrame")
        self.group_vars = {}
        for g, (t, _) in GRUPOS_EDC15.items():
            v = tk.BooleanVar(value=g in (1, 11))
            ttk.Checkbutton(self.side_vag, text=f"{g:03d}  {t}", variable=v).pack(anchor="w", pady=2)
            self.group_vars[g] = v
        ttk.Label(self.side_vag, text="Otros grupos (ej. 5, 20)", style="Muted.TLabel").pack(anchor="w", pady=(12, 4))
        self.extra_groups = ttk.Entry(self.side_vag, width=22)
        self.extra_groups.pack(anchor="w", fill="x")

        # Selección OBD2
        self.side_obd = ttk.Frame(side, style="Card.TFrame")
        ttk.Label(self.side_obd, text="Ctrl+clic para elegir varios", style="Muted.TLabel").pack(anchor="w", pady=(0, 4))
        lb_frame = ttk.Frame(self.side_obd, style="Card.TFrame")
        lb_frame.pack(fill="both", expand=True)
        self.pid_list = tk.Listbox(lb_frame, selectmode="extended", bg=CARD2, fg=FG, bd=0,
                                   highlightthickness=0, selectbackground=ACCENT, selectforeground="#111",
                                   activestyle="none", font=(FONT, 10), width=30, height=14,
                                   exportselection=False)
        sb = ttk.Scrollbar(lb_frame, orient="vertical", command=self.pid_list.yview)
        self.pid_list.configure(yscrollcommand=sb.set)
        self.pid_list.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.pid_list.insert("end", "  (conecta para ver los PIDs)")
        self.pid_order = []

        self.side_btns = ttk.Frame(side, style="Card.TFrame")
        self.side_btns.pack(side="bottom", fill="x")
        self.vals_btn = ttk.Button(self.side_btns, text="▶  Iniciar lectura", style="Accent.TButton",
                                   command=lambda: self.toggle_live("vals"))
        self.vals_btn.pack(fill="x", pady=(18, 6))
        self.rec_btn = ttk.Button(self.side_btns, text="●  Grabar CSV", command=self.toggle_rec)
        self.rec_btn.pack(fill="x")
        self.rec_lbl = ttk.Label(self.side_btns, text="", style="Muted.TLabel", wraplength=int(220 * self.s))
        self.rec_lbl.pack(anchor="w", pady=(8, 0))

        main = self._card(p, padding=0)
        main.pack(side="left", fill="both", expand=True)
        cols = ("grupo", "campo", "valor", "unidad")
        self.tree = ttk.Treeview(main, columns=cols, show="headings")
        for c, t, w, a in (("grupo", "GRUPO", 90, "center"), ("campo", "CAMPO", 320, "w"),
                           ("valor", "VALOR", 140, "e"), ("unidad", "UNIDAD", 110, "w")):
            self.tree.heading(c, text=t, anchor=a)
            self.tree.column(c, width=int(w * self.s), anchor=a, stretch=(c == "campo"))
        self.tree.tag_configure("err", foreground=ERR)
        self.tree.tag_configure("unk", foreground=WARN)
        self.tree.tag_configure("first", background=CARD2)
        sb = ttk.Scrollbar(main, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _build_dtc(self):
        p = self.tab_dtc
        top = ttk.Frame(p, style="Panel.TFrame")
        top.pack(fill="x", pady=(0, 12))
        self.dtc_read_btn = ttk.Button(top, text="Leer averías", style="Accent.TButton", command=self.read_dtcs)
        self.dtc_read_btn.pack(side="left")
        self.dtc_clear_btn = ttk.Button(top, text="Borrar averías", style="Danger.TButton", command=self.clear_dtcs)
        self.dtc_clear_btn.pack(side="left", padx=10)
        self.dtc_lbl = ttk.Label(top, text="", style="Panel.TLabel", font=(FONT, 11, "bold"))
        self.dtc_lbl.pack(side="left", padx=10)

        card = self._card(p, padding=0)
        card.pack(fill="both", expand=True)
        cols = ("codigo", "comp", "tipo", "estado")
        self.dtc_tree = ttk.Treeview(card, columns=cols, show="headings")
        for c, t, w, st in (("codigo", "CÓDIGO", 100, False), ("comp", "COMPONENTE", 430, True),
                            ("tipo", "TIPO DE FALLO", 300, True), ("estado", "ESTADO", 130, False)):
            self.dtc_tree.heading(c, text=t, anchor="w")
            self.dtc_tree.column(c, width=int(w * self.s), stretch=st)
        self.dtc_tree.tag_configure("inter", foreground=WARN)
        self.dtc_tree.tag_configure("fixed", foreground=ERR)
        self.dtc_tree.pack(fill="both", expand=True)
        self.dtc_help = ttk.Label(p, text="", style="PanelMuted.TLabel")
        self.dtc_help.pack(anchor="w", pady=(10, 0))

    def _build_ecu(self):
        self.ecu_card = self._card(self.tab_ecu, padding=22)
        self.ecu_card.pack(fill="x", anchor="n")
        self._fill_ecu([])

    def _fill_ecu(self, fields):
        for w in self.ecu_card.winfo_children():
            w.destroy()
        title = "Identificación de la centralita" if self.mode == KKL else "Datos del vehículo (OBD2)"
        ttk.Label(self.ecu_card, text=title, style="Card.TLabel",
                  font=(FONT, 13, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))
        if not fields:
            ttk.Label(self.ecu_card, text="Conecta para ver los datos.", style="Muted.TLabel").grid(row=1, column=0, sticky="w")
            return
        for i, (k, v) in enumerate(fields, 1):
            ttk.Label(self.ecu_card, text=k, style="Muted.TLabel", width=24).grid(row=i, column=0, sticky="w", pady=5)
            ttk.Label(self.ecu_card, text=v, style="Card.TLabel", font=(MONO, 11)).grid(row=i, column=1, sticky="w")

    def _build_log(self):
        p = self.tab_log
        top = ttk.Frame(p, style="Panel.TFrame")
        top.pack(fill="x", pady=(0, 10))
        self.debug_var = tk.BooleanVar(value=False)
        cb = tk.Checkbutton(top, text="Mostrar comunicación detallada (depuración)", variable=self.debug_var,
                            command=lambda: self.worker.submit("debug", self.debug_var.get()),
                            bg=PANEL, fg=FG, selectcolor=CARD2, activebackground=PANEL,
                            activeforeground=FG, font=(FONT, 10), bd=0, highlightthickness=0)
        cb.pack(side="left")
        ttk.Button(top, text="Limpiar", command=lambda: self.log_txt.delete("1.0", "end")).pack(side="right")
        card = self._card(p, padding=0)
        card.pack(fill="both", expand=True)
        self.log_txt = tk.Text(card, bg=CARD, fg=FG, insertbackground=FG, font=(MONO, 10),
                               bd=0, highlightthickness=0, padx=12, pady=10, wrap="none")
        sb = ttk.Scrollbar(card, orient="vertical", command=self.log_txt.yview)
        self.log_txt.configure(yscrollcommand=sb.set)
        self.log_txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.log_txt.tag_configure("err", foreground=ERR)
        self.log_txt.tag_configure("dbg", foreground=MUTED)

    # ---------------- asistente IA ----------------
    def _build_ia(self):
        p, s = self.tab_ia, self.s
        side = self._card(p, padding=16)
        side.pack(side="left", fill="y", padx=(0, 14))
        ttk.Label(side, text="Configuración de la IA", style="Card.TLabel",
                  font=(FONT, 11, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(side, text="Proveedor", style="Muted.TLabel").pack(anchor="w")
        self.ai_prov_var = tk.StringVar()
        self.ai_prov_cb = ttk.Combobox(side, textvariable=self.ai_prov_var, state="readonly", width=26,
                                       values=[v["nombre"] for v in ia.PROVEEDORES.values()])
        self.ai_prov_cb.pack(anchor="w", fill="x", pady=(2, 10))
        self.ai_prov_cb.bind("<<ComboboxSelected>>", lambda e: self._ai_load_provider())
        ttk.Label(side, text="Modelo", style="Muted.TLabel").pack(anchor="w")
        self.ai_model = ttk.Entry(side, width=28)
        self.ai_model.pack(anchor="w", fill="x", pady=(2, 10))
        ttk.Label(side, text="API key", style="Muted.TLabel").pack(anchor="w")
        self.ai_key = ttk.Entry(side, width=28, show="•")
        self.ai_key.pack(anchor="w", fill="x", pady=(2, 4))
        self.ai_show = tk.BooleanVar(value=False)
        tk.Checkbutton(side, text="Mostrar", variable=self.ai_show,
                       command=lambda: self.ai_key.configure(show="" if self.ai_show.get() else "•"),
                       bg=CARD, fg=MUTED, selectcolor=CARD2, activebackground=CARD, activeforeground=FG,
                       font=(FONT, 9), bd=0, highlightthickness=0).pack(anchor="w")
        link = tk.Label(side, text="Conseguir una API key ↗", bg=CARD, fg=BLUE, cursor="hand2", font=(FONT, 9, "underline"))
        link.pack(anchor="w", pady=(4, 12))
        link.bind("<Button-1>", lambda e: webbrowser.open(ia.PROVEEDORES[self._ai_prov()]["url_clave"]))
        ttk.Button(side, text="Guardar", style="Accent.TButton", command=self._ai_save).pack(fill="x")
        self.ai_cfg_lbl = ttk.Label(side, text="", style="Muted.TLabel", wraplength=int(230 * s))
        self.ai_cfg_lbl.pack(anchor="w", pady=(8, 0))
        ttk.Label(side, text=("La clave se guarda cifrada y solo funciona con tu usuario de Windows "
                              "en este equipo." if WINDOWS else
                              "La clave se guarda en ~/.config/ToledoDiagnosis, legible solo por tu usuario.")
                             + "\n\nAl analizar se envían al proveedor elegido los datos "
                             "del vehículo (incluido el VIN), las averías, los valores medidos y, si lo "
                             "pides, el registro del programa.",
                  style="Muted.TLabel", wraplength=int(230 * s), font=(FONT, 8)).pack(side="bottom", anchor="w")

        main = ttk.Frame(p, style="Panel.TFrame")
        main.pack(side="left", fill="both", expand=True)
        top = ttk.Frame(main, style="Panel.TFrame")
        top.pack(fill="x", pady=(0, 10))
        self.ai_btn_dtc = ttk.Button(top, text="Analizar averías del vehículo", style="Accent.TButton",
                                     command=lambda: self._ai_analyze("vehiculo"))
        self.ai_btn_dtc.pack(side="left")
        self.ai_btn_log = ttk.Button(top, text="Analizar errores del programa",
                                     command=lambda: self._ai_analyze("programa"))
        self.ai_btn_log.pack(side="left", padx=8)
        self.ai_btn_stop = ttk.Button(top, text="■ Detener", command=self._ai_stop, state="disabled")
        self.ai_btn_stop.pack(side="right")
        ttk.Button(top, text="Nueva conversación", command=self._ai_new).pack(side="right", padx=8)

        card = self._card(main, padding=0)
        card.pack(fill="both", expand=True)
        self.ai_txt = tk.Text(card, bg=CARD, fg=FG, insertbackground=FG, font=(FONT, 10), bd=0,
                              highlightthickness=0, padx=16, pady=12, wrap="word", spacing1=2, spacing3=2)
        sb = ttk.Scrollbar(card, orient="vertical", command=self.ai_txt.yview)
        self.ai_txt.configure(yscrollcommand=sb.set)
        self.ai_txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        t = self.ai_txt
        t.tag_configure("user", foreground=ACCENT, font=(FONT, 10, "bold"), spacing1=12)
        t.tag_configure("who", foreground=MUTED, font=(FONT, 9, "bold"), spacing1=12)
        t.tag_configure("h", font=(FONT, 12, "bold"), spacing1=10, spacing3=4)
        t.tag_configure("b", font=(FONT, 10, "bold"))
        t.tag_configure("i", foreground=MUTED, font=(FONT, 10, "italic"))
        t.tag_configure("li", lmargin1=12, lmargin2=28)
        t.tag_configure("err", foreground=ERR)
        t.tag_configure("muted", foreground=MUTED)
        t.tag_configure("tool", foreground=BLUE, font=(FONT, 9, "bold"), spacing1=4)
        t.tag_configure("tool_res", foreground=MUTED, font=(FONT, 9))
        t.bind("<Key>", lambda e: None if (e.state & 4 and e.keysym.lower() in ("c", "a")) else "break")

        ask = ttk.Frame(main, style="Panel.TFrame")
        ask.pack(fill="x", pady=(10, 0))
        self.ai_entry = ttk.Entry(ask, font=(FONT, 10))
        self.ai_entry.pack(side="left", fill="x", expand=True)
        self.ai_entry.bind("<Return>", lambda e: self._ai_ask())
        self.ai_btn_send = ttk.Button(ask, text="Enviar", style="Accent.TButton", command=self._ai_ask)
        self.ai_btn_send.pack(side="left", padx=(8, 0))

        prov = self.cfg.get("proveedor", "anthropic")
        self.ai_prov_var.set(ia.PROVEEDORES.get(prov, ia.PROVEEDORES["anthropic"])["nombre"])
        self._ai_load_provider()
        self._ai_new()

    def _ai_prov(self):
        return next(k for k, v in ia.PROVEEDORES.items() if v["nombre"] == self.ai_prov_var.get())

    def _ai_load_provider(self):
        prov = self._ai_prov()
        self.ai_model.delete(0, "end")
        self.ai_model.insert(0, ia.modelo_de(self.cfg, prov))
        self.ai_key.delete(0, "end")
        clave = ia.leer_clave(self.cfg, prov)
        self.ai_key.insert(0, clave)
        self.ai_cfg_lbl.configure(text="Clave guardada." if clave else "Sin API key para este proveedor.",
                                  foreground=OK if clave else WARN)

    def _ai_save(self):
        prov = self._ai_prov()
        modelo = self.ai_model.get().strip() or ia.PROVEEDORES[prov]["modelo"]
        try:
            ia.poner_clave(self.cfg, prov, self.ai_key.get().strip())
        except ia.IAError as e:
            messagebox.showerror("Asistente IA", str(e))
            return
        self.cfg["proveedor"] = prov
        self.cfg["modelos"][prov] = modelo
        ia.guardar_config(self.cfg)
        self.ai_cfg_lbl.configure(text=f"Guardado · {ia.PROVEEDORES[prov]['nombre']} · {modelo}", foreground=OK)

    def _ai_context(self, incluir_log):
        partes = [f"Fecha: {datetime.datetime.now():%Y-%m-%d %H:%M}",
                  f"Modo de conexión: {MODOS[self.mode]}",
                  f"Estado: {'conectado' if self.connected else 'no conectado'}"]
        if self.vehicle_fields:
            partes.append("\n## Datos del vehículo / centralita")
            partes += [f"- {k}: {v}" for k, v in self.vehicle_fields]
        partes.append("\n## Averías")
        partes.append(self.last_dtc_text or "No se han leído averías en esta sesión.")
        partes.append("\n## Últimos valores medidos")
        partes.append(self.last_live_text or "No se han leído valores medidos en esta sesión.")
        if incluir_log:
            lineas = self.log_txt.get("1.0", "end").strip().splitlines()[-150:]
            partes.append("\n## Registro del programa (últimas líneas)")
            partes.append("\n".join(lineas) if lineas else "(vacío)")
        return "\n".join(partes)

    def _ai_analyze(self, tipo):
        if tipo == "vehiculo":
            visible = "Analiza las averías y los datos del vehículo."
            peticion = ("Analiza mi vehículo: lee las averías (si no están leídas o son antiguas), haz las "
                        "comprobaciones de valores medidos que consideres necesarias y dime qué pasa, causas "
                        "probables y qué hacer.\n\nContexto actual de la aplicación:\n"
                        + self._ai_context(incluir_log=False))
        else:
            visible = "Analiza los errores del programa y de la comunicación."
            peticion = ("Analiza el registro de la aplicación: ¿hay errores de comunicación con el coche o el "
                        "adaptador? ¿Qué significan y cómo los soluciono?\n\n" + self._ai_context(incluir_log=True))
        self._ai_send(peticion, visible + "  (datos adjuntos)")

    def _ai_ask(self):
        texto = self.ai_entry.get().strip()
        if not texto or self.ai_busy:
            return
        self.ai_entry.delete(0, "end")
        if self.ai_chat is None or self.ai_chat.vacia():   # primer mensaje: adjunta el contexto actual
            peticion = texto + "\n\n---\nContexto actual de la aplicación:\n" + self._ai_context(incluir_log=False)
        else:
            peticion = texto
        self._ai_send(peticion, texto)

    def _ai_send(self, peticion, visible):
        if self.ai_busy:
            return
        prov = self._ai_prov()
        clave = self.ai_key.get().strip() or ia.leer_clave(self.cfg, prov)
        if not clave:
            messagebox.showinfo("Asistente IA", "Introduce y guarda una API key para "
                                f"{ia.PROVEEDORES[prov]['nombre']}.")
            return
        modelo = self.ai_model.get().strip() or ia.PROVEEDORES[prov]["modelo"]
        c = self.ai_chat
        if c is None or (c.proveedor, c.modelo, c.api_key) != (prov, modelo, clave):
            if c is not None and not c.vacia():
                self._ai_new()                     # otro proveedor/modelo: conversación nueva
            self.ai_chat = ia.Conversacion(prov, clave, modelo)
        if self.ai_chat.vacia():
            self.ai_txt.delete("1.0", "end")
        t = self.ai_txt
        t.insert("end", ("\n" if t.index("end-1c") != "1.0" else "") + "TÚ\n", "who")
        t.insert("end", visible + "\n", "user")
        t.insert("end", f"\n{ia.PROVEEDORES[prov]['nombre'].upper()} · {modelo}\n", "who")
        self._ai_placeholder()
        self._ai_set_busy(True)
        conv, chat = self.ai_conv, self.ai_chat

        def run():
            try:
                ok = chat.enviar(peticion,
                                 on_text=lambda x: self.q.put(("ai_chunk", (conv, x))),
                                 on_tool=lambda n, i: self._ai_tool(conv, n, i),
                                 cancelado=lambda: self.ai_cancel or conv != self.ai_conv)
                self.q.put(("ai_done", (conv, ok)))
            except ia.IAError as e:
                self.q.put(("ai_error", (conv, str(e))))
            except Exception as e:
                self.q.put(("ai_error", (conv, f"{type(e).__name__}: {e}")))
        threading.Thread(target=run, daemon=True).start()

    # --- herramientas (se ejecutan en el hilo de la IA) ---
    def _ai_wait(self, reply, conv):
        while True:
            try:
                return reply.get(timeout=0.3)
            except queue.Empty:
                if self.ai_cancel or conv != self.ai_conv:
                    return ("Cancelado por el usuario.", True)

    def _ai_main(self, fn, conv, asincrono=False):
        """Ejecuta fn en el hilo de la interfaz y espera su resultado (res, es_error)."""
        reply = queue.Queue()
        self.q.put(("ai_main", (fn, reply, asincrono)))
        return self._ai_wait(reply, conv)

    def _ai_tool(self, conv, nombre, entrada):
        self.q.put(("ai_tool", (conv, self._ai_tool_desc(nombre, entrada))))
        if nombre == "pedir_accion_usuario":
            res = self._ai_main(lambda reply: self._ai_dialog(str(entrada.get("instruccion", "")), reply),
                                conv, asincrono=True)
        elif nombre == "estado_conexion":
            res = self._ai_main(self._ai_estado, conv)
        elif nombre == "leer_registro":
            try:
                n = max(10, min(300, int(entrada.get("lineas", 80))))
            except (TypeError, ValueError):
                n = 80
            res = self._ai_main(lambda: ("\n".join(self.log_txt.get("1.0", "end").strip().splitlines()[-n:])
                                         or "(registro vacío)", False), conv)
        elif nombre in ("leer_averias", "leer_valores", "borrar_averias"):
            if nombre == "borrar_averias":
                ok = self._ai_main(lambda: (messagebox.askyesno(
                    "Asistente IA", "La IA quiere borrar las averías de la centralita para ver si reaparecen.\n\n"
                    "¿Lo permites? (motor parado, contacto puesto)"), False), conv)
                if ok[0] is not True:
                    res = ("El usuario no ha permitido borrar las averías.", False)
                    self.q.put(("ai_tool_res", (conv, res[0])))
                    return res
            reply = queue.Queue()
            self.worker.submit("tool", nombre, entrada, reply)
            res = self._ai_wait(reply, conv)
        else:
            res = (f"Herramienta desconocida: {nombre}", True)
        resumen = res[0].strip().splitlines()[0] if res[0].strip() else ""
        if nombre == "pedir_accion_usuario" or res[1]:
            self.q.put(("ai_tool_res", (conv, resumen)))
        return res

    def _ai_tool_desc(self, nombre, e):
        if nombre == "leer_valores":
            els = e.get("elementos") or []
            if not isinstance(els, list):
                els = [els]
            tipo = "grupos" if self.mode == KKL else "PIDs"
            n = e.get("muestras", 1)
            extra = f" · {n} muestras" if isinstance(n, int) and n > 1 else ""
            return f"Leyendo {tipo} {', '.join(str(x) for x in els)}{extra}"
        return {"estado_conexion": "Consultando el estado de la conexión",
                "leer_averias": "Leyendo averías",
                "borrar_averias": "Solicitando borrar averías",
                "leer_registro": "Leyendo el registro del programa",
                "pedir_accion_usuario": "Esperando al usuario: " + str(e.get("instruccion", ""))}.get(nombre, nombre)

    def _ai_estado(self):
        lineas = [f"Modo de conexión: {MODOS[self.mode]}",
                  f"Conectado: {'sí' if self.connected else 'no'}"]
        if self.connected:
            lineas += [f"{k}: {v}" for k, v in self.vehicle_fields]
            if self.mode == KKL:
                lineas.append("Grupos habituales EDC15: " + ", ".join(
                    f"{g:03d} {t}" for g, (t, _) in GRUPOS_EDC15.items())
                    + ". Se pueden pedir otros números de grupo (1-255); si no existen, la centralita lo indica.")
            else:
                lineas.append("PIDs soportados: " + ", ".join(f"{p:02X} {PIDS[p][0]}" for p in self.supported))
        else:
            lineas.append("Para conectar, el usuario debe elegir Conexión y Puerto arriba y pulsar Conectar.")
        return "\n".join(lineas), False

    def _ai_dialog(self, instruccion, reply):
        """Ventana no modal con la instrucción de la IA; responde a reply cuando el usuario decide."""
        if self.ai_dialog is not None:
            self.ai_dialog[0].destroy()
        w = tk.Toplevel(self.root, bg=CARD)
        w.title("El asistente necesita tu ayuda")
        w.attributes("-topmost", True)
        w.resizable(False, False)
        _poner_icono(w)
        f = ttk.Frame(w, style="Card.TFrame", padding=20)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text="✦ Acción solicitada por la IA", style="Card.TLabel",
                  font=(FONT, 11, "bold"), foreground=ACCENT).pack(anchor="w")
        ttk.Label(f, text=instruccion, style="Card.TLabel", font=(FONT, 11),
                  wraplength=int(420 * self.s)).pack(anchor="w", pady=(10, 14))
        ttk.Label(f, text="Comentario opcional (qué has visto, por qué no puedes…)",
                  style="Muted.TLabel").pack(anchor="w")
        com = ttk.Entry(f, width=50)
        com.pack(fill="x", pady=(2, 14))
        btns = ttk.Frame(f, style="Card.TFrame")
        btns.pack(fill="x")

        def responder(texto):
            if self.ai_dialog is None or self.ai_dialog[0] is not w:
                return
            self.ai_dialog = None
            c = com.get().strip()
            reply.put((texto + (f". Comentario del usuario: {c}" if c else ""), False))
            w.destroy()
        ttk.Button(btns, text="Hecho", style="Accent.TButton",
                   command=lambda: responder("Hecho")).pack(side="right")
        ttk.Button(btns, text="No puedo",
                   command=lambda: responder("El usuario no puede hacerlo")).pack(side="right", padx=8)
        w.protocol("WM_DELETE_WINDOW", lambda: responder("El usuario cerró la ventana sin hacerlo"))
        self.ai_dialog = (w, reply)
        w.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - w.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - w.winfo_height()) // 3
        w.geometry(f"+{max(0, x)}+{max(0, y)}")
        w.lift()
        com.focus_set()

    def _ai_close_dialog(self):
        if self.ai_dialog is not None:
            w, reply = self.ai_dialog
            self.ai_dialog = None
            reply.put(("Cancelado por el usuario.", True))
            w.destroy()

    def _ai_set_busy(self, busy):
        self.ai_busy = busy
        self.ai_cancel = False
        st = "disabled" if busy else "normal"
        for b in (self.ai_btn_dtc, self.ai_btn_log, self.ai_btn_send):
            b.configure(state=st)
        self.ai_btn_stop.configure(state="normal" if busy else "disabled")

    def _ai_stop(self):
        self.ai_cancel = True
        self._ai_close_dialog()

    def _ai_new(self):
        self.ai_conv += 1                 # descarta respuestas en curso de la conversación anterior
        self._ai_close_dialog()
        if self.ai_busy:
            self._ai_set_busy(False)
        self.ai_chat = None
        t = self.ai_txt
        t.delete("1.0", "end")
        t.insert("end", "Asistente de diagnóstico\n", "h")
        t.insert("end", "Describe abajo lo que le pasa al coche (p. ej. «le falta potencia por encima de 3000 rpm "
                        "y echa humo negro») y la IA hará las comprobaciones que necesite: leer averías, valores "
                        "medidos y pedirte que arranques, aceleres, etc.\n\nTambién puedes pulsar «Analizar averías "
                        "del vehículo», o «Analizar errores del programa» si algo falla al conectar.\n", "muted")

    # --- render Markdown sencillo, linea a linea ---
    def _ai_insert_inline(self, text, base=()):
        partes = text.split("**")
        for i, parte in enumerate(partes):
            if parte:
                self.ai_txt.insert("end", parte, base + (("b",) if i % 2 else ()))

    def _ai_render_line(self, line):
        t = self.ai_txt
        s = line.rstrip()
        if s.startswith("#"):
            t.insert("end", s.lstrip("#").strip().replace("**", "") + "\n", "h")
        elif s.lstrip().startswith(("- ", "* ", "• ")):
            ind = len(s) - len(s.lstrip())
            t.insert("end", "    " * (ind // 2) + "•  ", ("li",))
            self._ai_insert_inline(s.lstrip()[2:], ("li",))
            t.insert("end", "\n")
        elif s.startswith("*(") and s.endswith(")*"):
            t.insert("end", s[1:-1] + "\n", "i")
        else:
            self._ai_insert_inline(s)
            t.insert("end", "\n")

    def _ai_placeholder(self):
        t = self.ai_txt
        t.mark_set("ai_start", "end-1c")
        t.mark_gravity("ai_start", "left")
        t.insert("end", "Pensando…", "muted")
        t.see("end")
        self.ai_line = ""
        self.ai_first_chunk = True

    def _ai_flush(self):
        """Quita el 'Pensando…' o vuelca la línea parcial pendiente."""
        t = self.ai_txt
        if self.ai_first_chunk:
            t.delete("ai_start", "end-1c")
        else:
            t.delete("ai_pending", "end-1c")
            if self.ai_line:
                self._ai_render_line(self.ai_line)
        self.ai_line = ""
        self.ai_first_chunk = False

    def _ai_chunk(self, text):
        t = self.ai_txt
        if self.ai_first_chunk:
            t.delete("ai_start", "end-1c")
            self.ai_first_chunk = False
        else:
            t.delete("ai_pending", "end-1c")          # quita la línea parcial mostrada
        self.ai_line += text
        *completas, self.ai_line = self.ai_line.split("\n")
        for line in completas:
            self._ai_render_line(line)
        t.mark_set("ai_pending", "end-1c")
        t.mark_gravity("ai_pending", "left")
        t.insert("end", self.ai_line)
        t.see("end")

    def _ai_tool_line(self, texto, resultado=False):
        self._ai_flush()
        t = self.ai_txt
        if t.get("end-2c") != "\n":
            t.insert("end", "\n")
        t.insert("end", ("      → " if resultado else "⚙  ") + texto + "\n", "tool_res" if resultado else "tool")
        self._ai_placeholder()

    def _ai_finish(self, ok=True, error=None):
        self._ai_flush()
        t = self.ai_txt
        if error:
            t.insert("end", f"\nError: {error}\n", "err")
        elif not ok:
            t.insert("end", "\n(detenido: esta respuesta no se recordará en la conversación)\n", "muted")
        t.see("end")
        self._ai_close_dialog()
        self._ai_set_busy(False)

    # ---------------- modo ----------------
    def _apply_mode(self):
        self.mode = next(k for k, v in MODOS.items() if v == self.mode_var.get())
        kkl = self.mode == KKL
        self.mod_cb.configure(state="readonly" if kkl else "disabled")
        self.panel_vag.pack_forget()
        self.panel_obd.pack_forget()
        (self.panel_vag if kkl else self.panel_obd).pack(fill="both", expand=True)
        self.panel_lbl.configure(text="Lectura en vivo de los grupos 001 · 003 · 011" if kkl
                                 else "Lectura en vivo de PIDs OBD2 estándar")
        self.side_vag.pack_forget()
        self.side_obd.pack_forget()
        (self.side_vag if kkl else self.side_obd).pack(fill="both", expand=True, before=self.side_btns)
        self.side_title.configure(text="Grupos a leer" if kkl else "PIDs a leer")
        self.tree.heading("grupo", text="GRUPO" if kkl else "PID")
        self.dtc_tree.heading("tipo", text="TIPO DE FALLO" if kkl else "TIPO")
        self.dtc_help.configure(
            text="Intermitente = el fallo apareció pero no está presente ahora. "
                 "Si tras borrar vuelve a aparecer, la avería sigue activa." if kkl else
                 "Pendiente = detectado una vez, aún sin confirmar. Al borrar se apaga el testigo MIL "
                 "y se reinician los monitores de emisiones (la ITV puede rechazarlo hasta completar ciclos).")
        self.dtc_tree.delete(*self.dtc_tree.get_children())
        self.dtc_lbl.configure(text="")
        self._fill_ecu([])
        self.vehicle_fields, self.last_dtc_text, self.last_live_text = [], None, None
        self.refresh_ports()

    # ---------------- utilidades ----------------
    def refresh_ports(self):
        items, ftdi, bt = [], None, None
        try:
            from serial.tools import list_ports
            for p in sorted(list_ports.comports(), key=lambda p: p.device):
                label = f"{p.device} · {p.description}"
                items.append(label)
                if ftdi is None and p.vid == 0x0403:
                    ftdi = label
                if bt is None and ("bluetooth" in (p.description or "").lower()
                                   or p.device.startswith("/dev/rfcomm")):
                    bt = label
        except Exception:
            pass
        items.append(SIM)
        self.port_cb["values"] = items
        cur = self.port_var.get()
        prefer = ftdi if self.mode == KKL else (bt or ftdi)
        self.port_var.set(cur if cur in items and cur != SIM else (prefer or items[0]))

    def log(self, msg):
        tag = "err" if msg.startswith("Error") else ("dbg" if msg.startswith("[") else None)
        self.log_txt.insert("end", f"{datetime.datetime.now():%H:%M:%S}  {msg}\n", tag)
        if int(self.log_txt.index("end-1c").split(".")[0]) > 3000:
            self.log_txt.delete("1.0", "500.0")
        self.log_txt.see("end")

    def status(self, text, color):
        self.status_dot.delete("all")
        d = int(12 * self.s)
        self.status_dot.create_oval(2, 2, d - 2, d - 2, fill=color, outline="")
        self.status_lbl.configure(text=text)

    def _set_connected(self, on, info=None):
        self.connected = on
        state = "normal" if on else "disabled"
        for b in (self.panel_btn, self.vals_btn, self.rec_btn, self.dtc_read_btn, self.dtc_clear_btn):
            b.configure(state=state)
        self.port_cb.configure(state="disabled" if on else "readonly")
        self.mode_cb.configure(state="disabled" if on else "readonly")
        self.mod_cb.configure(state="disabled" if on or self.mode != KKL else "readonly")
        self.refresh_btn.configure(state="disabled" if on else "normal")
        self.conn_btn.configure(text="Desconectar" if on else "Conectar",
                                style="TButton" if on else "Accent.TButton", state="normal")
        if on:
            self.status(info["status"], OK)
        else:
            self.status("Desconectado", MUTED)
            self._stop_live()
            self._stop_rec()

    def _key_label(self, k):
        if isinstance(k, str):
            return k
        return f"{k:03d}" if self.mode == KKL else f"{k:02X}h"

    # ---------------- acciones ----------------
    def toggle_connect(self):
        if self.connected:
            self.worker.submit("disconnect")
            return
        port = self.port_var.get()
        if port != SIM:
            port = port.split(" · ")[0]
        addr = int(self.mod_var.get().split(" · ")[0], 16)
        self.conn_btn.configure(state="disabled")
        self.mode_cb.configure(state="disabled")
        if self.mode == KKL:
            self.status("Conectando... (init 5 baudios)", WARN)
            self.bar.configure(text="Conectando: puede tardar hasta 6 s mientras prueba las velocidades.")
        else:
            self.status("Conectando con el ELM327...", WARN)
            self.bar.configure(text="Conectando: la búsqueda del protocolo OBD2 puede tardar hasta 25 s.")
        self.worker.submit("connect", self.mode, port, addr)

    def _selected_items(self):
        if self.mode == ELM:
            return [self.pid_order[i] for i in self.pid_list.curselection() if i < len(self.pid_order)]
        gs = [g for g, v in self.group_vars.items() if v.get()]
        for x in self.extra_groups.get().replace(";", ",").split(","):
            x = x.strip()
            if x.isdigit() and 0 <= int(x) <= 255 and int(x) not in gs:
                gs.append(int(x))
        return gs

    def toggle_live(self, source):
        if self.live_source == source:
            self._stop_live()
            return
        if source == "panel":
            items = PANEL_GROUPS if self.mode == KKL else [p for p in PANEL_PIDS if p in self.supported]
        else:
            items = self._selected_items()
        if not items:
            messagebox.showinfo("Valores medidos", "Selecciona al menos un grupo o PID.")
            return
        self._stop_rec()
        self.live_source = source
        self.live_gen += 1
        self.worker.submit("live", items, self.live_gen)
        self.panel_btn.configure(text="■  Detener" if source == "panel" else "▶  Iniciar lectura")
        self.vals_btn.configure(text="■  Detener" if source == "vals" else "▶  Iniciar lectura")
        if source == "panel":
            for c in (self.ch_boost, self.ch_maf, self.ch_rpm, self.ch_load):
                c.clear()
        else:
            self.tree.delete(*self.tree.get_children())
            self.tree_items = {}
        self.bar.configure(text=f"Leyendo {', '.join(self._key_label(k) for k in items)}")

    def _stop_live(self):
        self.live_gen += 1
        if self.live_source:
            self.worker.submit("live", None, self.live_gen)
        self.live_source = None
        self.panel_btn.configure(text="▶  Iniciar lectura")
        self.vals_btn.configure(text="▶  Iniciar lectura")
        self._stop_rec()

    def toggle_rec(self):
        if self.csv_file:
            self._stop_rec()
            return
        if self.live_source != "vals":
            self.toggle_live("vals")
            if self.live_source != "vals":
                return
        name = os.path.join(CARPETA, f"log_{datetime.datetime.now():%Y%m%d_%H%M%S}.csv")
        self.csv_file = open(name, "w", newline="", encoding="utf-8-sig")
        self.csv_writer = csv.writer(self.csv_file, delimiter=";")
        self.csv_header = None
        self.csv_n = 0
        self.csv_t0 = time.monotonic()
        self.rec_btn.configure(text="■  Parar grabación", style="Danger.TButton")
        self.rec_lbl.configure(text=f"Grabando en {os.path.basename(name)}")
        self.log(f"Grabando CSV: {name}")

    def _stop_rec(self):
        if not self.csv_file:
            return
        name = self.csv_file.name
        self.csv_file.close()
        self.csv_file = self.csv_writer = None
        self.rec_btn.configure(text="●  Grabar CSV", style="TButton")
        self.rec_lbl.configure(text=f"Guardadas {self.csv_n} muestras en {os.path.basename(name)}")
        self.log(f"CSV guardado ({self.csv_n} muestras): {name}")

    def read_dtcs(self):
        self.dtc_lbl.configure(text="Leyendo...", foreground=FG)
        self.worker.submit("dtcs")

    def clear_dtcs(self):
        if messagebox.askyesno("Borrar averías",
                               "¿Borrar las averías memorizadas en la centralita?\n\n"
                               "Hazlo con el motor parado y el contacto puesto."):
            self.dtc_lbl.configure(text="Borrando...", foreground=FG)
            self.worker.submit("clear")

    def _show_dtcs(self, payload, after_clear=False):
        t = self.dtc_tree
        t.delete(*t.get_children())
        if self.mode == KKL:
            for code, ftype, inter in payload:
                comp = DTCS.get(code, "Código no incluido en la tabla")
                tipo = f"{ftype:02d} · {FAULT_TYPES.get(ftype, 'Desconocido') or '—'}"
                tag = "inter" if inter else ("fixed" if after_clear else "")
                t.insert("", "end", values=(f"{code:05d}", comp, tipo,
                                            "Intermitente" if inter else "Presente"), tags=(tag,))
            n = len(payload)
            if not n:
                txt, color = ("Averías borradas · no queda ninguna" if after_clear else "Sin averías memorizadas"), OK
            elif after_clear:
                txt, color = f"{n} avería(s) siguen presentes tras borrar", ERR
            else:
                txt, color = f"{n} avería(s) memorizada(s)", WARN
        else:
            for estado, codes in (("Memorizada", payload["stored"]), ("Pendiente", payload["pending"])):
                for code in codes:
                    tipo = "Genérico (SAE)" if code[1] in "02" else "Específico del fabricante"
                    tag = "inter" if estado == "Pendiente" else ("fixed" if after_clear else "")
                    t.insert("", "end", values=(code, describe_obd_dtc(code), tipo, estado), tags=(tag,))
            ns, npend, mil = len(payload["stored"]), len(payload["pending"]), payload["mil"]
            mil_txt = "testigo MIL ENCENDIDO" if mil else "testigo MIL apagado"
            if not ns and not npend:
                txt = ("Averías borradas · " if after_clear else "Sin averías · ") + mil_txt
                color = OK
            else:
                txt = f"{ns} memorizada(s) · {npend} pendiente(s) · {mil_txt}"
                color = ERR if after_clear or mil else WARN
        self.dtc_lbl.configure(text=txt, foreground=color)
        # Contexto para el asistente IA
        filas = [" — ".join(str(v) for v in t.item(i, "values")) for i in t.get_children()]
        cab = f"Leídas a las {datetime.datetime.now():%H:%M:%S}" + (" (justo después de borrar)" if after_clear else "")
        self.last_dtc_text = cab + ". " + txt + "\n" + "\n".join(f"- {f}" for f in filas)

    def _live_to_text(self, data):
        lineas = []
        for k, rows in data.items():
            etiqueta = (f"G{k:03d}" if self.mode == KKL else f"PID {k:02X}h") if isinstance(k, int) else k
            if isinstance(rows, str):
                lineas.append(f"- {etiqueta}: {rows}")
                continue
            for nombre, valor, unidad, ok in rows:
                lineas.append(f"- {etiqueta} {nombre}: {valor} {unidad}".rstrip() + ("" if ok else " (fórmula desconocida)"))
        return f"Leídos a las {datetime.datetime.now():%H:%M:%S}\n" + "\n".join(lineas)

    # ---------------- datos en vivo ----------------
    def _chart_add(self, t, data):
        if self.mode == KKL:
            g3, g11 = rows_of(data, 3), rows_of(data, 11)
            if g11:
                self.ch_boost.add(t, {"Teórica": num(g11, 1), "Real": num(g11, 2)})
            if g3:
                self.ch_maf.add(t, {"Teórica": num(g3, 1), "Real": num(g3, 2)})
        else:
            self.ch_rpm.add(t, {"RPM": num(rows_of(data, 0x0C))})
            self.ch_load.add(t, {"Carga": num(rows_of(data, 0x04)), "Mariposa": num(rows_of(data, 0x11))})

    def _update_panel(self, data):
        def fmt(rows, i=0):
            try:
                return f"{rows[i][1]} {rows[i][2]}"
            except IndexError:
                return "--"
        if self.mode == KKL:
            g1, g3, g11 = rows_of(data, 1), rows_of(data, 3), rows_of(data, 11)
            self.g_rpm.set(num(g1, 0) if g1 else num(g11, 0))
            self.g_iq.set(num(g1, 1))
            self.g_temp.set(num(g1, 3))
            self.g_boost.set(num(g11, 2), spec=num(g11, 1))
            self.vag_stats["n75"].set(fmt(g11, 3))
            self.vag_stats["egr"].set(fmt(g3, 3))
            self.vag_stats["volt"].set(fmt(g1, 2))
            self.vag_stats["maf"].set(fmt(g3, 2))
            self.ch_boost.redraw()
            self.ch_maf.redraw()
        else:
            r = lambda p: rows_of(data, p)
            self.o_rpm.set(num(r(0x0C)))
            self.o_speed.set(num(r(0x0D)))
            self.o_temp.set(num(r(0x05)))
            self.o_load.set(num(r(0x04)))
            self.obd_stats["iat"].set(fmt(r(0x0F)))
            self.obd_stats["maf"].set(fmt(r(0x10)))
            self.obd_stats["tps"].set(fmt(r(0x11)))
            self.obd_stats["volt"].set(fmt(r(0x42)))
            self.ch_rpm.redraw()
            self.ch_load.redraw()
        errs = [f"{self._key_label(k)}: {v}" for k, v in data.items() if isinstance(v, str)]
        if errs:
            self.bar.configure(text=" · ".join(errs))

    def _update_tree(self, data):
        for k, rows in data.items():
            if isinstance(rows, str):
                key = (k, "err")
                vals = (self._key_label(k), rows, "", "")
                if key in self.tree_items:
                    self.tree.item(self.tree_items[key], values=vals)
                else:
                    self.tree_items[key] = self.tree.insert("", "end", values=vals, tags=("err",))
                continue
            for i, (nombre, valor, unidad, ok) in enumerate(rows):
                key = (k, i)
                vals = (self._key_label(k) if i == 0 else "", nombre, valor, unidad)
                first = i == 0 and self.mode == KKL
                tags = tuple(x for x in ("first" if first else "", "" if ok else "unk") if x)
                if key in self.tree_items:
                    self.tree.item(self.tree_items[key], values=vals)
                else:
                    self.tree_items[key] = self.tree.insert("", "end", values=vals, tags=tags)

    def _write_csv(self, data):
        if any(isinstance(v, str) for v in data.values()):
            return
        if self.csv_header is None:
            pref = (lambda k: f"G{k:03d} ") if self.mode == KKL else (lambda k: "")
            self.csv_header = ["t (s)"] + [f"{pref(k)}{n} ({u})" for k, rows in data.items()
                                           for n, _, u, _ in rows]
            self.csv_writer.writerow(self.csv_header)
        fila = [f"{time.monotonic() - self.csv_t0:.2f}".replace(".", ",")]
        fila += [v.replace(".", ",") for rows in data.values() for _, v, _, _ in rows]
        self.csv_writer.writerow(fila)
        self.csv_n += 1
        if self.csv_n % 10 == 0:
            self.csv_file.flush()
            self.rec_lbl.configure(text=f"Grabando · {self.csv_n} muestras")

    # ---------------- bucle de eventos ----------------
    def poll(self):
        last = None
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "live":
                    gen, t, data = payload
                    if gen != self.live_gen:
                        continue                  # lectura de una sesion anterior
                    last = data
                    if self.live_source == "vals" and self.csv_writer:
                        self._write_csv(data)
                    elif self.live_source == "panel":
                        self._chart_add(t, data)
                    continue
                self._handle(kind, payload)
                if kind == "quit":
                    return
        except queue.Empty:
            pass
        if last is not None:
            self.last_live_text = self._live_to_text(last)
            if self.live_source == "panel":
                self._update_panel(last)
            elif self.live_source == "vals":
                self._update_tree(last)
        self.root.after(50, self.poll)

    def _fill_pid_list(self, pids):
        self.pid_list.delete(0, "end")
        self.pid_order = list(pids)
        for i, p in enumerate(pids):
            self.pid_list.insert("end", f"  {p:02X}h   {PIDS[p][0]}")
            if p in PANEL_PIDS:
                self.pid_list.selection_set(i)
        if not pids:
            self.pid_list.insert("end", "  (el vehículo no ofrece PIDs legibles)")

    def _handle(self, kind, payload):
        if kind == "log":
            self.log(payload)
        elif kind == "connected":
            self.supported = payload.get("supported", [])
            if payload["mode"] == ELM:
                self._fill_pid_list(self.supported)
            self._set_connected(True, payload)
            self._fill_ecu(payload["fields"])
            self.vehicle_fields = payload["fields"]
            self.bar.configure(text=f"Conectado: {payload.get('title', '')}")
        elif kind == "disconnected":
            self._set_connected(False)
            self.bar.configure(text="Desconectado.")
        elif kind == "lost":
            self._set_connected(False)
            self.status("Conexión perdida", ERR)
            self.bar.configure(text=f"Conexión perdida: {payload}. Pulsa Conectar para reintentar.")
            self.log(f"Error: conexión perdida ({payload})")
        elif kind == "error":
            if not self.connected:
                self._set_connected(False)
                self.status("Error de conexión", ERR)
                if self.mode == KKL:
                    ayuda = ("Revisa: contacto puesto, puerto " + ("COM" if WINDOWS else "(/dev/ttyUSB0)")
                             + ", cable FTDI y que la radio no bloquee la línea K.")
                elif WINDOWS:
                    ayuda = ("Revisa: contacto puesto y puerto COM. Si el ELM327 es Bluetooth, "
                             "Windows crea dos puertos COM: prueba el otro.")
                else:
                    ayuda = ("Revisa: contacto puesto y puerto. Un ELM327 Bluetooth debe estar enlazado "
                             "como /dev/rfcomm0 (sudo rfcomm bind 0 <MAC>).")
                if not WINDOWS and "ermission" in str(payload):
                    ayuda += ("\n\nSin permiso para el puerto: añade tu usuario al grupo dialout "
                              "(sudo usermod -aG dialout $USER) y vuelve a iniciar sesión.")
                messagebox.showerror("No se pudo conectar", f"{payload}\n\n{ayuda}")
            else:
                self.dtc_lbl.configure(text="", foreground=FG)
                messagebox.showerror("Error", payload)
            self.bar.configure(text=f"Error: {payload}")
        elif kind == "dtcs":
            self._show_dtcs(payload)
        elif kind == "cleared":
            self._show_dtcs(payload, after_clear=True)
        elif kind == "tool_live":
            self.last_live_text = self._live_to_text(payload)
        elif kind == "ai_main":
            fn, reply, asincrono = payload
            try:
                if asincrono:
                    fn(reply)                           # responderá más tarde (diálogo)
                else:
                    reply.put(fn())
            except Exception as e:
                reply.put((f"Error: {e}", True))
        elif kind in ("ai_chunk", "ai_done", "ai_error", "ai_tool", "ai_tool_res"):
            conv, data = payload
            if conv != self.ai_conv:
                return                                  # conversación ya descartada
            if kind == "ai_chunk":
                self._ai_chunk(data)
            elif kind == "ai_tool":
                self._ai_tool_line(data)
            elif kind == "ai_tool_res":
                self._ai_tool_line(data, resultado=True)
            elif kind == "ai_done":
                self._ai_finish(ok=data)
            else:
                self._ai_finish(error=data)
        elif kind == "quit":
            self.root.destroy()

    def on_close(self):
        self._stop_rec()
        self.worker.submit("quit")
        self.root.after(3000, self.root.destroy)   # por si el hilo no responde


def _autotest_ia(salida):
    """Comprueba (sin gastar saldo) que los SDKs de IA y HTTPS funcionan en el .exe."""
    lineas = []
    for prov in ia.PROVEEDORES:
        try:
            ia.Conversacion(prov, "clave-de-prueba", ia.PROVEEDORES[prov]["modelo"]).enviar(
                "hola", lambda t: None, lambda n, i: ("", False))
            lineas.append(f"{prov}: respuesta inesperada")
        except ia.IAError as e:
            lineas.append(f"{prov}: {e}")
        except Exception as e:
            lineas.append(f"{prov}: FALLO {type(e).__name__}: {e}")
    with open(salida, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--autotest-ia":
        _autotest_ia(sys.argv[2])
        return
    _dpi_aware()
    root = tk.Tk(className="ToledoDiagnosis")   # en Linux: WM_CLASS para el lanzador .desktop
    _elegir_fuentes(root)
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
