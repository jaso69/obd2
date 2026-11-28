"""
Interfaz grafica de diagnostico: VAG KW1281 (cable KKL) y OBD2 generico (ELM327).

    python gui.py

Elige el tipo de conexion, el puerto COM (o "Simulador") y pulsa Conectar.
"""
import bisect
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
from tkinter import filedialog, messagebox, ttk

import ayuda
import cambios
import consumo
import csv_datos
import historial
import ia
import idioma
import obd_datos
import informe
from elm327 import ELM327, ELM327Error
from idioma import tr
from kw1281 import KW1281, KW1281Error
from obd_datos import OBD_STANDARDS, PIDS, decode_pid
from obd_datos import describe_dtc as describe_obd_dtc
from toledo import formatear_grupo, leer_grupo_formateado, texto_id
from vag_datos import FAULT_TYPES, MODULOS, MOTORES, ajustes_basicos, componente as vag_componente, detectar_motor
from vag_datos import describe_dtc as vag_describe_dtc
from vin_datos import VAG as VIN_VAG, decodificar_vin

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
NOMBRE = "OBD2Desk"
WIFI = "WiFi · 192.168.0.10:35000"      # dirección habitual de los ELM327 WiFi
VERSION = "0.7.0"
URL_RELEASES = "https://github.com/jaso69/obd2/releases"

KKL, ELM = "kkl", "elm"


def _textos_fijos():
    """Textos que se usan como valores (puerto simulado, modos): dependen del idioma."""
    global SIM, MODOS
    SIM = tr("Simulador (sin coche)")
    MODOS = {KKL: tr("KKL · VAG KW1281 (hasta 2004)"), ELM: tr("ELM327 · OBD2 genérico")}


_textos_fijos()

PANEL_GROUPS = [1, 3, 11]               # TDI (EDC15 e inyector-bomba)
PANEL_GROUPS_GASOLINA = [2, 3, 4]       # gasolina (grupos estándar de VAG)
PANEL_PIDS = [0x0C, 0x0D, 0x05, 0x04, 0x0F, 0x10, 0x11, 0x42]


def _carpeta_documentos():
    """Carpeta de documentos del usuario en Linux (~/Documentos, ~/Documents...)."""
    try:
        import subprocess
        d = subprocess.run(["xdg-user-dir", "DOCUMENTS"], capture_output=True, text=True,
                           timeout=2).stdout.strip()
        if d and os.path.isdir(d) and d != os.path.expanduser("~"):
            return d
    except Exception:
        pass
    for d in ("Documentos", "Documents"):
        if os.path.isdir(os.path.expanduser(f"~/{d}")):
            return os.path.expanduser(f"~/{d}")
    return os.path.expanduser("~")


# Carpeta donde se guardan los CSV: junto al .exe si esta empaquetado en Windows;
# en Linux el binario suele estar en ~/.local/bin, asi que van a Documentos/OBD2Desk
if getattr(sys, "frozen", False):
    CARPETA = (os.path.dirname(sys.executable) if WINDOWS
               else os.path.join(_carpeta_documentos(), NOMBRE))
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
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("jasodev.obd2desk")
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


def _grupo_puerto(puerto):
    """Grupo con acceso al puerto serie en Linux (dialout; uucp en Arch)."""
    import grp
    for ruta in (puerto, "/dev/ttyUSB0", "/dev/ttyS0"):
        try:
            nombre = grp.getgrgid(os.stat(ruta).st_gid).gr_name
            if nombre != "root":
                return nombre
        except (OSError, KeyError):
            pass
    return "dialout"


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
        self.mensaje = ""                    # se muestra si no hay series
        self.bind("<Configure>", lambda e: self.redraw())

    def configurar(self, title, unit, series, datos=None):
        """Cambia las series (y opcionalmente sus datos previos: {nombre: [(t, v)]})."""
        self.title, self.unit, self.series = title, unit, series
        self.data = {name: deque((datos or {}).get(name, ())) for name, _ in series}
        self.redraw()

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

        if not self.series:
            self.create_text(w / 2, h / 2, text=self.mensaje, fill=MUTED, font=(FONT, 10),
                             width=max(100, w - 60 * s), justify="center")
            return
        vals = [v for d in self.data.values() for _, v in d]
        lo, top = escala_y(vals, self.ymin_top)
        pw, ph = w - L - R, h - T - B
        dibujar_eje_y(self, lo, top, L, T, w - R, ph, s)
        for i, lbl in ((0, f"-{self.window}s"), (0.5, f"-{self.window // 2}s"), (1, tr("ahora"))):
            self.create_text(L + pw * i, h - B + 12 * s, text=lbl, fill=MUTED, font=(FONT, 8))

        now = time.monotonic()
        for name, color in self.series:
            pts = []
            for t, v in self.data[name]:
                pts += [L + pw * (1 - (now - t) / self.window), T + ph - (max(lo, min(v, top)) - lo) / (top - lo) * ph]
            if len(pts) >= 4:
                self.create_line(*pts, fill=color, width=2 * s)


def escala_y(vals, ymin_top=1):
    """(abajo, arriba) del eje Y con números redondos; incluye el 0 y los negativos."""
    lo = min(0.0, min(vals) * 1.1) if vals else 0.0
    top = max(max(vals) * 1.1 if vals else 0, ymin_top if lo == 0 else 0, lo + 1e-6)
    if top <= 0:
        top = 0.0
    step = nice_step((top - lo) / 4)
    top = step * math.ceil(top / step - 1e-9)
    lo = step * math.floor(lo / step + 1e-9)
    if top - lo < step:
        top = lo + step
    return lo, top


def dibujar_eje_y(cv, lo, top, x0, y0, x1, ph, s):
    step = nice_step((top - lo) / 4)
    v = lo
    while v <= top + step * 1e-6:
        y = y0 + ph - (v - lo) / (top - lo) * ph
        cv.create_line(x0, y, x1, y, fill=TRACK)
        cv.create_text(x0 - 6 * s, y, text=f"{round(v, 6):g}", anchor="e", fill=MUTED, font=(FONT, 8))
        v += step


def recortar(pts, a, b):
    """Puntos entre a y b; si la línea entra o sale del tramo, se corta justo en el borde."""
    out = [p for p in pts if a <= p[0] <= b]
    dentro = lambda p, q, x: (x, p[1] + (q[1] - p[1]) * (x - p[0]) / (q[0] - p[0]))
    if pts and pts[0][0] < a:
        q = next((p for p in pts if p[0] >= a), None)
        if q and q[0] > pts[0][0]:
            out.insert(0, dentro(pts[0], q, a))
    if pts and pts[-1][0] > b:
        p = next((p for p in reversed(pts) if p[0] <= b), None)
        if p and pts[-1][0] > p[0]:
            out.append(dentro(p, pts[-1], b))
    return out


COLORES_SERIE = [ACCENT, BLUE, OK, WARN]


class GraficaFija(tk.Canvas):
    """Gráfica de una grabación completa: eje X fijo, valores bajo el ratón y zoom arrastrando."""

    def __init__(self, parent, s=1.0, al_cambiar=None):
        super().__init__(parent, bg=CARD, highlightthickness=0)
        self.s = s
        self.series = []                 # [(nombre, unidad, color, puntos)]
        self.eje = "s"
        self.rango = None                # (x0, x1) visible; None = todo
        self.total = (0, 1)
        self.raton = None                # x en píxeles bajo el ratón
        self.arrastre = None             # x en píxeles donde empezó el arrastre
        self.al_cambiar = al_cambiar     # se llama al cambiar el zoom
        self.mensaje = ""
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Motion>", self._mover)
        self.bind("<Leave>", lambda e: self._mover(None))
        self.bind("<ButtonPress-1>", self._pulsar)
        self.bind("<ButtonRelease-1>", self._soltar)
        self.bind("<Double-Button-1>", lambda e: self.ver_todo())
        self.bind("<Button-3>", lambda e: self.ver_todo())

    def poner(self, series, eje):
        self.series, self.eje = series, eje
        xs = [p[0] for *_, pts in series for p in (pts[0], pts[-1]) if pts]
        self.total = (min(xs), max(xs)) if xs else (0, 1)
        if self.total[1] <= self.total[0]:
            self.total = (self.total[0], self.total[0] + 1)
        if self.rango and not (self.total[0] <= self.rango[0] < self.rango[1] <= self.total[1]):
            self.rango = None
        self.redraw()

    def visible(self):
        return self.rango or self.total

    def ver_todo(self):
        self.rango = None
        self.redraw()
        if self.al_cambiar:
            self.al_cambiar()

    def ampliar(self, x0, x1):
        if x1 - x0 > (self.total[1] - self.total[0]) * 1e-4:
            self.rango = (max(x0, self.total[0]), min(x1, self.total[1]))
            self.redraw()
            if self.al_cambiar:
                self.al_cambiar()

    def _marco(self):
        s = self.s
        w, h = self.winfo_width(), self.winfo_height()
        return 58 * s, 14 * s, 34 * s, 26 * s, w, h

    def _x_a_valor(self, px):
        L, R, _, _, w, _ = self._marco()
        a, b = self.visible()
        return a + (px - L) / max(1, w - L - R) * (b - a)

    def _mover(self, e):
        self.raton = e.x if e else None
        self.redraw()

    def _pulsar(self, e):
        self.arrastre = e.x

    def _soltar(self, e):
        if self.arrastre is not None and abs(e.x - self.arrastre) > 8 * self.s:
            a, b = sorted((self._x_a_valor(self.arrastre), self._x_a_valor(e.x)))
            self.arrastre = None
            self.ampliar(a, b)
            return
        self.arrastre = None
        self.redraw()

    def redraw(self):
        self.delete("all")
        s = self.s
        L, R, T, B, w, h = self._marco()
        if w < 80 or h < 60:
            return
        if not self.series:
            self.create_text(w / 2, h / 2, text=self.mensaje, fill=MUTED, font=(FONT, 10),
                             width=max(100, w - 60 * s), justify="center")
            return
        a, b = self.visible()
        pw, ph = w - L - R, h - T - B
        unidades = list(dict.fromkeys(u for _, u, _, _ in self.series if u))
        self.create_text(L, 16 * s, text=" · ".join(unidades), anchor="w", fill=MUTED, font=(FONT, 9))
        x = w - R
        for nombre, _, color, _ in reversed(self.series):
            tid = self.create_text(x, 16 * s, text=nombre, anchor="e", fill=MUTED, font=(FONT, 9))
            x = self.bbox(tid)[0] - 6 * s
            self.create_rectangle(x - 10 * s, 13 * s, x, 19 * s, fill=color, outline="")
            x -= 18 * s
        vistos, trazos = [], []
        for *_, pts in self.series:
            i = max(0, bisect.bisect_left(pts, (a, -math.inf)) - 1)
            j = bisect.bisect_right(pts, (b, math.inf)) + 1
            trazos.append(pts[i:j])                    # con el punto anterior y el siguiente: la línea sigue
            vistos.append([p for p in pts[i:j] if a <= p[0] <= b])
        lo, top = escala_y([v for pts in (vistos if any(vistos) else trazos) for _, v in pts])
        dibujar_eje_y(self, lo, top, L, T, w - R, ph, s)
        X = lambda v: L + (v - a) / (b - a) * pw
        Y = lambda v: T + ph - (v - lo) / (top - lo) * ph
        for i in range(5):
            v = a + (b - a) * i / 4
            etiqueta = (f"{v:.1f} s" if b - a < 60 else f"{int(v // 60)}:{int(v % 60):02d}") if self.eje == "s" else f"{v:.0f}"
            self.create_text(X(v), h - B + 13 * s, text=etiqueta, fill=MUTED, font=(FONT, 8),
                             anchor="w" if i == 0 else "e" if i == 4 else "center")
        for (_, _, color, _), pts in zip(self.series, trazos):
            pts = csv_datos.reducir(recortar(pts, a, b), int(pw * 2))
            coords = [c for x_, v in pts for c in (X(x_), Y(v))]
            if len(coords) >= 4:
                self.create_line(*coords, fill=color, width=max(1, 1.6 * s))

            elif len(coords) == 2:
                self.create_oval(coords[0] - 2, coords[1] - 2, coords[0] + 2, coords[1] + 2, fill=color, outline="")
        if self.arrastre is not None and self.raton is not None:
            x0, x1 = sorted((self.arrastre, self.raton))
            self.create_rectangle(max(L, x0), T, min(w - R, x1), T + ph, outline=ACCENT, stipple="gray25", fill=ACCENT)
        elif self.raton is not None and L <= self.raton <= w - R:
            xv = self._x_a_valor(self.raton)
            self.create_line(self.raton, T, self.raton, T + ph, fill=MUTED, dash=(3, 3))
            lineas = [(f"t = {xv:.2f} s" if self.eje == "s" else tr("muestra {n}", n=f"{xv:.0f}"), FG)]
            for (nombre, unidad, color, _), pts in zip(self.series, vistos):
                if not pts:
                    continue
                cerca = min(pts, key=lambda p: abs(p[0] - xv))
                self.create_oval(X(cerca[0]) - 3 * s, Y(cerca[1]) - 3 * s, X(cerca[0]) + 3 * s, Y(cerca[1]) + 3 * s,
                                 fill=color, outline="")
                lineas.append((f"{nombre}: {round(cerca[1], 3):g} {unidad}".rstrip(), color))
            izq = self.raton > L + pw * 0.6
            y = T + 8 * s
            for texto, color in lineas:
                self.create_text(self.raton + (-10 if izq else 10) * s, y, text=texto, anchor="ne" if izq else "nw",
                                 fill=color, font=(FONT, 9, "bold"))
                y += 17 * s


def texto_ff(ff):
    """Datos congelados en texto (para el asistente IA)."""
    if not ff:
        return tr("Datos congelados: no hay ninguno guardado.")
    vals = "\n".join(f"- {n}: {v} {u}".rstrip() for _, n, v, u in ff["values"]) or tr("- (sin valores)")
    return tr("Datos congelados (avería {dtc}: {desc}):", dtc=ff["dtc"], desc=describe_obd_dtc(ff["dtc"])) + f"\n{vals}"


def texto_readiness(r):
    if not r:
        return tr("Monitores de preparación: no disponibles.")
    diesel, mons = r
    sin = [n for n, ok in mons if not ok]
    return (tr("Monitores de preparación (motor {tipo}): {ok} de {total} completos",
               tipo=tr("diésel") if diesel else tr("gasolina"), ok=len(mons) - len(sin), total=len(mons))
            + (tr("; sin completar: {lista}.", lista=", ".join(sin)) if sin else "."))


def wifi_destino(puerto):
    """(host, puerto) si el texto es una dirección WiFi («WiFi · 192.168.0.10:35000» o «ip:puerto»)."""
    txt = puerto.split(" · ")[-1].strip()
    host, _, num = txt.rpartition(":")
    if host and num.isdigit() and " " not in host and not host.startswith("/"):
        return host, int(num)
    return None


def version_mayor(a, b):
    """True si la versión a («v0.3.1») es mayor que b («0.3.0»)."""
    def t(v):
        try:
            return tuple(int(x) for x in v.strip().lstrip("vV").split("-")[0].split("."))
        except ValueError:
            return ()
    return t(a) > t(b)


def comprobar_version(avisar):
    """Consulta la última versión publicada en GitHub (en segundo plano, 5 s como mucho)."""
    def run():
        try:
            import json
            import urllib.request
            req = urllib.request.Request("https://api.github.com/repos/jaso69/obd2/releases/latest",
                                         headers={"Accept": "application/vnd.github+json",
                                                  "User-Agent": NOMBRE})
            with urllib.request.urlopen(req, timeout=5) as r:
                datos = json.load(r)
            tag = datos.get("tag_name", "")
            if version_mayor(tag, VERSION):
                avisar(tag, datos.get("html_url") or URL_RELEASES)
        except Exception:
            pass                                # sin conexión o API caída: no se avisa
    threading.Thread(target=run, daemon=True).start()


def cabecera_csv(modo, data):
    pref = (lambda k: f"G{k:03d} ") if modo == KKL else (lambda k: "")
    return ["t (s)"] + [f"{pref(k)}{n} ({u})" for k, rows in data.items() for n, _, u, _ in rows]


def fila_csv(t, data):
    return [f"{t:.2f}".replace(".", ",")] + [v.replace(".", ",") for rows in data.values() for _, v, _, _ in rows]


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
        self.scan_stop = threading.Event()
        self.grupos = MOTORES["edc15"][1]    # nombres de los campos de los grupos VAG (según el motor)
        self.basico = None                   # (grupo, nombres) en ajuste básico
        self.basico_t = 0.0

    def post(self, kind, payload=None):
        self.out.put((kind, payload))

    def log(self, msg):
        self.post("log", msg)

    def submit(self, *task):
        self.tasks.put(task)

    def run(self):
        while True:
            try:
                task = self.tasks.get(timeout=0.01 if self.live_items or self.basico else 0.1)
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
                    self.log(tr("Error: {e}", e=e))
                    self.post("error", str(e))
                    if self.mode == ELM and self.online and self._is_port_error(e):
                        self._lost(str(e))
                self._check_lost()
                continue
            if self.live_items and self.online:
                self._read_live()
            elif self.basico and self.online:
                self._read_basico()
            self._check_lost()

    @staticmethod
    def _is_port_error(e):
        return isinstance(e, OSError) or type(e).__name__ == "SerialException"

    def _read_basico(self):
        """Repite la petición de ajuste básico (unas 4 veces por segundo) y manda sus valores."""
        if time.monotonic() - self.basico_t < 0.25:
            return
        self.basico_t = time.monotonic()
        g, nombres = self.basico
        try:
            campos = self.ecu.basic_setting(g)
        except KW1281Error as e:
            self.basico = None
            self.log(tr("Error: {e}", e=e))
            self.post("basic", {"error": str(e)})
            return
        self.post("basic", {"filas": formatear_grupo(campos, g, {g: ("", nombres)} if nombres else self.grupos)})

    def _lost(self, msg):
        self.online = False
        self.live_items = None
        self.basico = None
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
        destino = wifi_destino(port) if mode == ELM else None
        if destino:
            self.log(tr("Conectando por WiFi a {host}:{puerto}...", host=destino[0], puerto=destino[1]))
            try:
                return serial.serial_for_url(f"socket://{destino[0]}:{destino[1]}", timeout=0.05)
            except Exception as e:
                raise ELM327Error(tr("No se pudo conectar al ELM327 WiFi en {host}:{puerto} ({e}). "
                                     "Conecta el ordenador a la red WiFi del adaptador (suele llamarse "
                                     "«WiFi_OBDII» o «V-LINK») y comprueba la dirección.",
                                     host=destino[0], puerto=destino[1], e=e))
        if mode == KKL:
            ser = serial.Serial(port, 9600, timeout=0.05)
            ser.dtr, ser.rts = True, False
            if not WINDOWS:
                try:
                    ser.set_low_latency_mode(True)   # FTDI: latencia de 16 ms a 1 ms
                except Exception as e:
                    self.log(tr("Aviso: no se pudo activar baja latencia en {puerto} ({e})", puerto=port, e=e))
        else:
            ser = serial.Serial(port, 38400, timeout=0.05)
        return ser

    def handle(self, kind, *args):
        if kind == "connect":
            mode, port, addr = args
            self._disconnect()
            self.mode = mode
            self.log(tr("Abriendo {puerto}...", puerto=port))
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
            self.log(tr("Desconectado."))
            self.post("disconnected")
        elif kind == "dtcs":
            self.post("dtcs", self.ecu.read_dtcs() if self.mode == KKL else self._elm_dtcs())
        elif kind == "clear":
            if self.mode == KKL:
                self.post("cleared", self.ecu.clear_dtcs())
            else:
                self.elm.clear_dtcs()
                self.post("cleared", self._elm_dtcs())
        elif kind == "scan":
            try:
                self._scan(args[0])
            except Exception as e:              # p. ej. se desenchufa el cable a mitad
                self.log(tr("Error: {e}", e=e))
                self._lost(tr("error durante el escaneo: {e}", e=e))
        elif kind == "report":
            if self.mode == KKL:
                d = self.ecu.read_dtcs()
                self.post("dtcs", d)
                self.post("report", {"dtcs": d, "modulo": self.ecu.address})
            else:
                d = self._elm_dtcs()
                self.post("dtcs", d)
                self.post("report", {"dtcs": d})
        elif kind == "act":
            try:
                self.post("act", {"code": self.ecu.actuator_test(inicio=args[0])})
            except KW1281Error as e:
                self.log(tr("Error: {e}", e=e))
                self.post("act", {"error": str(e)})
        elif kind == "basic":
            self.basico = (args[0], args[1])
            self.basico_t = 0.0
            self.log(tr("Ajuste básico del grupo {g}.", g=f"{args[0]:03d}"))
        elif kind == "basic_stop":
            g = self.basico[0] if self.basico else args[0]
            self.basico = None
            try:
                self.ecu.read_group(g)          # una lectura normal saca a la centralita del ajuste básico
            except KW1281Error as e:
                if not self.ecu.connected:
                    raise
                self.log(tr("Aviso: {e}", e=e))
            self.log(tr("Fin del ajuste básico del grupo {g}.", g=f"{g:03d}"))
            self.post("basic", {"stopped": True})
        elif kind == "act_stop":
            # La centralita deja de activar el componente al cerrar la sesión: se vuelve a conectar.
            self.log(tr("Fin del test de actuadores: se reinicia la comunicación para apagar el componente."))
            try:
                self.ecu.disconnect()
                time.sleep(1.0)
                self.ecu.connect()
                self.post("act", {"stopped": True})
            except Exception as e:
                self.post("act", {"stopped": True, "error": str(e)})
                self._lost(tr("no se pudo reconectar tras el test de actuadores: {e}", e=e))
        elif kind == "adapt":
            self._adaptar(*args)
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
                reply.put((tr("Error de comunicación: {e}", e=e), True))
                if self.mode == ELM and self.online and self._is_port_error(e):
                    self._lost(str(e))

    def _adaptar(self, accion, *datos):
        """Canales de adaptación, código de acceso y codificación (VentanaAdaptacion)."""
        r = {"accion": accion}
        try:
            if accion == "leer":
                r.update(canal=datos[0], valor=self.ecu.adaptation_read(datos[0]))
            elif accion in ("probar", "deshacer_prueba"):
                r.update(canal=datos[0], valor=self.ecu.adaptation_test(datos[0], datos[1]))
            elif accion == "guardar":
                r.update(canal=datos[0], valor=self.ecu.adaptation_save(*datos))
                self.log(tr("Canal de adaptación {c} guardado: {v}.", c=f"{datos[0]:02d}", v=r["valor"]))
            elif accion == "login":
                self.ecu.login(*datos)
                r.update(codigo=datos[0])
                self.log(tr("Código de acceso aceptado."))
            elif accion == "codificar":
                try:
                    r.update(codificacion=self.ecu.set_coding(*datos))
                    self.log(tr("Codificación cambiada a {v}.", v=f"{datos[0]:05d}"))
                finally:
                    if self.ecu.connected:
                        r["info"] = self._info_kkl()
        except (KW1281Error, ValueError) as e:
            self.log(tr("Error: {e}", e=e))
            r["error"] = str(e)
        self.post("adapt", r)

    # ---------------- herramientas del asistente IA ----------------
    @staticmethod
    def _fmt_obd_dtcs(d):
        def lista(codes):
            return "\n".join(f"- {c}: {describe_obd_dtc(c)}" for c in codes) or tr("- ninguna")
        return (tr("Memorizadas:") + f"\n{lista(d['stored'])}\n" + tr("Pendientes:") + f"\n{lista(d['pending'])}\n"
                + tr("Permanentes (no se borran hasta que el monitor correspondiente pasa):") + "\n"
                + f"{lista(d.get('permanent') or [])}\n"
                + tr("Testigo MIL: {estado}", estado=tr("encendido") if d["mil"] else tr("apagado")) + "\n"
                + f"{texto_ff(d.get('ff'))}\n{texto_readiness(d.get('readiness'))}")

    def _elm_dtcs(self):
        """Averías OBD2 con datos congelados y monitores de preparación."""
        d = self.elm.read_dtcs()
        for clave, fn in (("ff", self.elm.freeze_frame), ("readiness", self.elm.readiness)):
            try:
                d[clave] = fn()
            except ELM327Error as e:
                self.log(tr("Aviso: no se pudieron leer los datos congelados ({e})", e=e) if clave == "ff"
                         else tr("Aviso: no se pudieron leer los monitores ({e})", e=e))
                d[clave] = None
        return d

    def _scan(self, direcciones):
        """Escanea los módulos VAG: identificación y averías de cada uno que responda."""
        orig = self.ecu.address
        self.scan_stop.clear()
        self.online = False                      # que no salte «conexión perdida» al cambiar de módulo
        self.live_items = None
        try:
            self.ecu.disconnect()
        except Exception:
            pass
        res = []
        for i, a in enumerate(direcciones):
            if self.scan_stop.is_set():
                self.log(tr("Escaneo detenido por el usuario."))
                break
            self.post("scan_progress", (i, len(direcciones), a))
            time.sleep(0.3)
            ecu = KW1281(self.ser, address=a, debug=self.debug, logger=self.log)
            try:
                ecu.connect(rapido=True)
            except KW1281Error as e:
                self.log(tr("Módulo {dir}: {e}", dir=f"{a:02X}", e=e))
                res.append({"addr": a, "ok": False, "error": str(e)})
                continue
            ident = [texto_id(d) for d in ecu.ident]
            try:
                dtcs, err = ecu.read_dtcs(), None
            except KW1281Error as e:
                dtcs, err = None, str(e)
            try:
                ecu.disconnect()
            except Exception:
                pass
            self.log(tr("Módulo {dir} ({nombre}): ", dir=f"{a:02X}", nombre=MODULOS.get(a, "?")) +
                     (tr("{n} avería(s)", n=len(dtcs)) if dtcs is not None else tr("error al leer averías: {e}", e=err)))
            res.append({"addr": a, "ok": True, "ident": ident, "dtcs": dtcs, "error": err})
        self.post("scan_done", res)
        self.log(tr("Volviendo al módulo {dir}...", dir=f"{orig:02X}"))
        try:
            info = self._connect_kkl(orig)
        except Exception as e:
            self._lost(tr("no se pudo volver al módulo {dir}: {e}", dir=f"{orig:02X}", e=e))
            return
        self.online = True
        self.post("connected", info)

    def _tool(self, nombre, e):
        if not self.online:
            return (tr("No hay conexión con el vehículo. Pide al usuario que conecte "
                       "(selector Conexión, Puerto y botón Conectar)."), True)
        if nombre == "leer_averias":
            if self.mode == KKL:
                d = self.ecu.read_dtcs()
                self.post("dtcs", d)
                return ("\n".join("- " + vag_describe_dtc(*x) for x in d) or tr("Sin averías memorizadas."), False)
            d = self._elm_dtcs()
            self.post("dtcs", d)
            return self._fmt_obd_dtcs(d), False
        if nombre == "borrar_averias":
            if self.mode == KKL:
                rest = self.ecu.clear_dtcs()
                self.post("cleared", rest)
                return (tr("Averías borradas. ") + (tr("Siguen presentes (avería activa):") + "\n" +
                        "\n".join("- " + vag_describe_dtc(*x) for x in rest) if rest else tr("No queda ninguna.")), False)
            self.elm.clear_dtcs()
            d = self._elm_dtcs()
            self.post("cleared", d)
            return tr("Averías borradas. Estado después de borrar:") + "\n" + self._fmt_obd_dtcs(d), False
        if nombre == "leer_valores":
            return self._tool_valores(e)
        if nombre == "grabar_valores":
            return self._tool_grabar(e)
        return tr("Herramienta desconocida: {nombre}", nombre=nombre), True

    def _tool_items(self, els):
        """Grupos o PIDs válidos pedidos por la IA: (lista, notas) o (None, error)."""
        if isinstance(els, (str, int)):
            els = [els]
        if not isinstance(els, list) or not els:
            return None, (tr("Indica al menos un grupo o PID en 'elementos'."), True)
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
                notas.append(tr("'{x}' no es válido o no está soportado por el vehículo; se ignora.", x=x))
        limite = 4 if self.mode == KKL else 10
        if len(items) > limite:
            notas.append(tr("Solo se leen los {n} primeros.", n=limite))
            items = items[:limite]
        if not items:
            return None, (tr("Ningún grupo o PID válido.") + "\n" + "\n".join(notas), True)
        return items, notas

    def _tool_grabar(self, e):
        items, notas = self._tool_items(e.get("elementos"))
        if items is None:
            return notas
        try:
            segundos = max(2.0, min(120.0, float(e.get("segundos") or 10)))
        except (TypeError, ValueError):
            segundos = 10.0
        ruta = os.path.join(CARPETA, f"ia_{datetime.datetime.now():%Y%m%d_%H%M%S}.csv")
        try:
            os.makedirs(CARPETA, exist_ok=True)
            f = open(ruta, "w", newline="", encoding="utf-8-sig")
        except OSError as ex:
            return tr("No se pudo crear el archivo:") + f" {ex}", True
        self.log(tr("La IA graba {s} s en {archivo}", s=f"{segundos:g}", archivo=ruta))
        serie, cabecera, errores = [], None, {}
        with f:
            w = csv.writer(f, delimiter=";")
            t0 = time.monotonic()
            siguiente = t0
            while time.monotonic() - t0 < segundos:
                espera = siguiente - time.monotonic()
                if espera > 0:
                    time.sleep(espera)            # como mucho 50 muestras/s (un ELM327 real da unas 10)
                siguiente = time.monotonic() + 0.02
                data = self._muestra(items)
                t = time.monotonic() - t0
                malos = {k: v for k, v in data.items() if isinstance(v, str)}
                errores.update(malos)
                if not malos:
                    if cabecera is None:
                        cabecera = cabecera_csv(self.mode, data)
                        w.writerow(cabecera)
                    w.writerow(fila_csv(t, data))
                    serie.append((t, data))
                if self.mode == KKL and not self.ecu.connected:
                    notas.append(tr("Se perdió la conexión durante la lectura."))
                    break
        if not serie:
            try:
                os.remove(ruta)
            except OSError:
                pass
            return (tr("No se pudo grabar ninguna muestra.") + "\n"
                    + "\n".join(f"{self._etiqueta(k)}: {v}" for k, v in errores.items())), True
        self.post("tool_live", serie[-1][1])
        dur = serie[-1][0] or 1
        lineas = [tr("Grabadas {n} muestras en {s} s ({ritmo} por segundo). Archivo: {archivo} (el usuario puede "
                     "abrirlo con «Abrir CSV...» en Valores medidos).", n=len(serie), s=f"{dur:.1f}",
                     ritmo=f"{len(serie) / dur:.1f}", archivo=ruta),
                  tr("Resumen (mínimo / media / máximo):")]
        for k, rows in serie[0][1].items():
            for i, (nombre, _, unidad, _) in enumerate(rows):
                vs = []
                for _, d in serie:
                    try:
                        vs.append(float(d[k][i][1]))
                    except (ValueError, IndexError, KeyError, TypeError):
                        pass
                if vs:
                    f3 = lambda v: f"{round(v, 3):g}"
                    lineas.append(f"- {self._etiqueta(k)} {nombre}: {f3(min(vs))} / {f3(sum(vs) / len(vs))} / "
                                  f"{f3(max(vs))} {unidad}".rstrip())
        paso = max(1, -(-len(serie) // 25))
        muestra = serie[::paso]
        if muestra[-1] is not serie[-1]:
            muestra.append(serie[-1])
        lineas.append(tr("Serie (una de cada {k} muestras):", k=paso))
        if errores:
            notas.append(tr("Algunas lecturas fallaron y no se grabaron: {lista}",
                            lista="; ".join(f"{self._etiqueta(k)}: {v}" for k, v in errores.items())))
        return "\n".join(lineas) + "\n" + self._fmt_serie(muestra, notas), False

    def _tool_valores(self, e):
        items, notas = self._tool_items(e.get("elementos"))
        if items is None:
            return notas
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

        serie = []
        t0 = time.monotonic()
        for i in range(muestras):
            espera = t0 + i * intervalo - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            data = self._muestra(items)
            serie.append((time.monotonic() - t0, data))
            if self.mode == KKL and not self.ecu.connected:
                notas.append(tr("Se perdió la conexión durante la lectura."))
                break
        self.post("tool_live", serie[-1][1])
        return self._fmt_serie(serie, notas), False

    def _muestra(self, items):
        """Una lectura de los grupos/PIDs indicados: {clave: filas o texto de error}."""
        data = {}
        if self.mode == KKL:
            for g in items:
                try:
                    data[g] = leer_grupo_formateado(self.ecu, g, self.grupos)
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
                    data[p] = tr("Sin respuesta")
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
                                     + ("" if ok else tr(" [fórmula desconocida]"))))
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
            notas.append(tr("Los nombres de los campos VAG son orientativos; la unidad la da la propia centralita."))
        return "\n".join(out + notas)

    def _connect_kkl(self, addr):
        self.ecu = KW1281(self.ser, address=addr, debug=self.debug, logger=self.log)
        self.log(tr("Init a 5 baudios al módulo {dir}...", dir=f"{addr:02X}"))
        self.ecu.connect()
        e = self.ecu
        self.log(tr("Conectado a {baud} baudios, keywords {kw}", baud=e.baud, kw=f"{e.keywords[0]:02X} {e.keywords[1]:02X}"))
        return self._info_kkl()

    def _info_kkl(self):
        """Identificación de la centralita conectada por KKL (al conectar y tras cambiar la codificación)."""
        e = self.ecu
        addr = e.address
        cod = KW1281.codificacion(e.ident)
        ident = [texto_id(d) for d in e.ident if not (cod and len(d) >= 5 and d[0] == 0)] + ["", "", ""]
        kw = f"{e.keywords[0]:02X} {e.keywords[1]:02X}" + ("  (KW1281)" if e.keywords == (0x01, 0x8A) else "")
        return {
            "mode": KKL,
            "status": tr("Conectado · {modulo} · {baud} bd",
                         modulo=MODULOS.get(addr, tr("Módulo {dir}", dir=f"{addr:02X}")), baud=e.baud),
            "title": ident[0].strip(),
            "addr": addr,
            "motor": detectar_motor(ident) if addr == 0x01 else None,
            "ident": [x.strip() for x in ident if x.strip()],
            "codificacion": cod,
            "fields": [(tr("Módulo"), f"{addr:02X} · {MODULOS.get(addr, '?')}"),
                       (tr("Referencia"), ident[0].strip() or "—"),
                       (tr("Componente"), ident[1].strip() or "—"),
                       (tr("Software / taller"), ident[2].strip() or "—"),
                       (tr("Codificación"), tr("{c} · código de taller {t}", c=f"{cod[0]:05d}", t=f"{cod[1]:05d}")
                        if cod else "—"),
                       (tr("Datos adicionales"), "  ".join(x for x in ident[3:] if x) or "—"),
                       (tr("Velocidad"), tr("{baud} baudios", baud=e.baud)),
                       ("Keywords", kw),
                       (tr("Eco del cable"), tr("Sí") if e.echo else "No")],
        }

    def _connect_elm(self):
        self.elm = ELM327(self.ser, debug=self.debug, logger=self.log)
        self.log(tr("Buscando ELM327 y protocolo OBD2 (puede tardar hasta 25 s, o más si hay que probar la línea K)..."))
        self.elm.connect()
        e = self.elm
        vin, volt = e.vin(), e.voltage()
        obd_datos.marca_vag = bool(vin) and vin[:3] in VIN_VAG
        mil, ndtc = e.mil()
        std = e.obd_standard()
        ident = e.identificacion()
        try:
            ready = e.readiness()
        except ELM327Error:
            ready = None
        self.log(tr("Conectado: {version} · {protocolo}", version=e.version, protocolo=e.proto_name))
        medibles = sorted(p for p in e.supported if p in PIDS)
        combustible = None
        if 0x51 in e.supported:                       # tipo de combustible (para el consumo)
            try:
                combustible = consumo.TIPO_PID51.get(e.read_pids([0x51]).get(0x51, b"\0")[0])
            except (ELM327Error, IndexError):
                pass
        campos = [(tr("Adaptador"), e.version),
                  (tr("Protocolo"), e.proto_name),
                  (tr("Bastidor (VIN)"), vin or tr("No disponible"))]
        if vin:
            campos += [(f"  {k}", v) for k, v in decodificar_vin(vin)]
        campos += [(tr("Tensión batería"), volt or "—"),
                   (tr("Estándar OBD"), OBD_STANDARDS.get(std, "—") if std else "—"),
                   (tr("Testigo de avería (MIL)"), "—" if mil is None else
                    (tr("ENCENDIDO · {n} avería(s)", n=ndtc) if mil else tr("Apagado · {n} avería(s)", n=ndtc)))]
        if ident["nombre"]:
            campos.append((tr("Centralita"), ident["nombre"]))
        if ident["calid"]:
            campos.append((tr("Calibración (CALID)"), "  ".join(ident["calid"])))
        if ident["cvn"]:
            campos.append((tr("Verificación (CVN)"), "  ".join(ident["cvn"])))
        campos.append((tr("PIDs soportados"), tr("{n} ({legibles} con valor legible)",
                                                n=len(e.supported), legibles=len(medibles))))
        return {
            "mode": ELM,
            "status": tr("Conectado · OBD2 · {protocolo}", protocolo=e.proto_name.replace("AUTO, ", "")),
            "title": vin or e.proto_name,
            "supported": medibles,
            "combustible": combustible,
            "vin": vin,
            "calid": ident["calid"],
            "readiness": ready,
            "fields": campos,
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


class VisorCSV:
    """Ventana para ver una grabación CSV: columnas a elegir, gráfica con zoom y resumen."""

    def __init__(self, app, ruta, datos):
        self.app, self.datos = app, datos
        s = app.s
        self.win = win = tk.Toplevel(app.root)
        win.title(tr("Visor de CSV · {archivo}", archivo=os.path.basename(ruta)))
        win.configure(bg=PANEL)
        _poner_icono(win)
        win.geometry(f"{int(1120 * s)}x{int(660 * s)}")
        win.minsize(int(760 * s), int(460 * s))
        cols = datos["columnas"]
        xs = [p[0] for *_, pts in cols for p in pts]
        duracion = (f"{max(xs) - min(xs):.1f} s" if datos["eje"] == "s" else tr("sin columna de tiempo"))
        cab = ttk.Frame(win, style="Panel.TFrame", padding=(16, 12, 16, 0))
        cab.pack(fill="x")
        ttk.Label(cab, text=os.path.basename(ruta), style="Panel.TLabel", font=(FONT, 12, "bold")).pack(side="left")
        ttk.Label(cab, text="   " + tr("{n} muestras · {columnas} columnas · {duracion}", n=datos["n"],
                                       columnas=len(cols), duracion=duracion),
                  style="PanelMuted.TLabel").pack(side="left")
        ttk.Button(cab, text=tr("Ver todo"), command=lambda: self.grafica.ver_todo()).pack(side="right")

        cuerpo = ttk.Frame(win, style="Panel.TFrame", padding=16)
        cuerpo.pack(fill="both", expand=True)
        lado = app._card(cuerpo, padding=12)
        lado.pack(side="left", fill="y", padx=(0, 14))
        ttk.Label(lado, text=tr("Columnas (Ctrl+clic: hasta 4)"), style="Muted.TLabel").pack(anchor="w", pady=(0, 6))
        marco = ttk.Frame(lado, style="Card.TFrame")
        marco.pack(fill="both", expand=True)
        self.lista = tk.Listbox(marco, selectmode="extended", bg=CARD2, fg=FG, bd=0, highlightthickness=0,
                                selectbackground=ACCENT, selectforeground="#111", activestyle="none",
                                font=(FONT, 10), width=34, exportselection=False)
        sb = ttk.Scrollbar(marco, orient="vertical", command=self.lista.yview)
        self.lista.configure(yscrollcommand=sb.set)
        self.lista.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for nombre, unidad, _ in cols:
            self.lista.insert("end", f"  {nombre}" + (f" ({unidad})" if unidad else ""))
        self.lista.bind("<<ListboxSelect>>", lambda e: self._elegir())
        self.resumen = ttk.Label(lado, text="", style="Card.TLabel", font=(MONO, 9), justify="left")
        self.resumen.pack(anchor="w", pady=(10, 0))

        der = app._card(cuerpo, padding=0)
        der.pack(side="left", fill="both", expand=True)
        self.grafica = GraficaFija(der, s=s, al_cambiar=self._resumir)
        self.grafica.mensaje = tr("Elige una o varias columnas a la izquierda.")
        self.grafica.pack(fill="both", expand=True)
        ttk.Label(win, text=tr("Pasa el ratón por la gráfica para ver los valores · arrastra para ampliar un tramo "
                               "· doble clic o «Ver todo» para volver."),
                  style="PanelMuted.TLabel", padding=(16, 0, 16, 10)).pack(fill="x")
        self.lista.selection_set(0)
        self._elegir()

    def _elegir(self):
        sel = list(self.lista.curselection())
        if len(sel) > 4:
            for i in sel[4:]:
                self.lista.selection_clear(i)
            sel = sel[:4]
        cols = self.datos["columnas"]
        self.grafica.poner([(cols[i][0], cols[i][1], color, cols[i][2]) for i, color in zip(sel, COLORES_SERIE)],
                           self.datos["eje"])
        self._resumir()

    def _resumir(self):
        a, b = self.grafica.visible()
        lineas = []
        for nombre, unidad, _, pts in self.grafica.series:
            r = csv_datos.resumen(pts, a, b)
            if r:
                f = lambda v: f"{round(v, 2):g}"
                lineas.append(f"{nombre[:30]}\n  {tr('mín')} {f(r[0])}  {tr('media')} {f(r[1])}  {tr('máx')} {f(r[2])} {unidad}")
        if self.grafica.rango:
            dec = 0 if self.datos["eje"] != "s" else 1 if b - a >= 10 else 2 if b - a >= 0.1 else 3
            lineas.insert(0, tr("Tramo: {a} - {b}", a=f"{a:.{dec}f}", b=f"{b:.{dec}f}")
                          + (" s" if self.datos["eje"] == "s" else ""))
        self.resumen.configure(text="\n".join(lineas))


class VentanaActuadores:
    """Test de actuadores KW1281: la centralita activa sus componentes uno a uno."""

    def __init__(self, app):
        self.app = app
        s = app.s
        self.estado = "listo"        # listo, esperando, activo, parando, fin
        self.cerrando = False
        self.n = 0
        self.desde = None
        self.win = win = tk.Toplevel(app.root)
        win.title(tr("Test de actuadores"))
        win.configure(bg=PANEL)
        _poner_icono(win)
        win.geometry(f"{int(820 * s)}x{int(640 * s)}")
        win.minsize(int(640 * s), int(520 * s))
        win.transient(app.root)
        win.protocol("WM_DELETE_WINDOW", self.cerrar)

        p = ttk.Frame(win, style="Panel.TFrame", padding=18)
        p.pack(fill="both", expand=True)
        ttk.Label(p, text=tr("Test de actuadores · {modulo}", modulo=app.mod_var.get()), style="Panel.TLabel",
                  font=(FONT, 12, "bold")).pack(anchor="w")
        aviso = self.app._card(p, padding=(14, 10))
        aviso.pack(fill="x", pady=(10, 10))
        for i, txt in enumerate((
                tr("La centralita activa de verdad, uno a uno, sus componentes (relés, electroválvulas, inyectores, "
                   "testigos...) para comprobar que funcionan: se oye un clic o un zumbido, o se enciende un testigo."),
                tr("• Motor parado y contacto puesto. Con el motor en marcha la centralita no lo acepta."),
                tr("• Cada componente sigue activo hasta que pulses «Siguiente componente». No lo dejes mucho rato: "
                   "en un gasolina los inyectores y la bomba pueden mandar combustible al motor."),
                tr("• Apártate del ventilador y de las piezas móviles. Con la batería baja puede fallar."),
                tr("• «Terminar» apaga el componente reiniciando la comunicación (tarda unos segundos). Quitar el "
                   "contacto también lo para."))):
            ttk.Label(aviso, text=txt, style="Card.TLabel", wraplength=int(740 * s), justify="left",
                      foreground=WARN if i == 2 else None).pack(anchor="w", pady=(0, 4))
        self.ok_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(p, text=tr("He leído los avisos: el motor está parado y el contacto puesto"),
                        variable=self.ok_var, command=self._botones).pack(anchor="w")

        self.actual = ttk.Label(p, text="—", style="Panel.TLabel", font=(FONT, 13, "bold"),
                                wraplength=int(760 * s))
        self.actual.pack(anchor="w", pady=(14, 0))
        self.info = ttk.Label(p, text=tr("Pulsa «Iniciar» para activar el primer componente."),
                              style="PanelMuted.TLabel", wraplength=int(760 * s))
        self.info.pack(anchor="w", pady=(2, 10))

        btns = ttk.Frame(p, style="Panel.TFrame")
        btns.pack(fill="x", side="bottom", pady=(12, 0))
        self.btn = ttk.Button(btns, text=tr("Iniciar"), style="Accent.TButton", width=24, command=self.siguiente)
        self.btn.pack(side="left")
        self.fin_btn = ttk.Button(btns, text=tr("Cerrar"), width=14, command=self.terminar)
        self.fin_btn.pack(side="right")

        card = self.app._card(p, padding=0)
        card.pack(fill="both", expand=True)
        self.lista = ttk.Treeview(card, columns=("n", "codigo", "comp"), show="headings", height=6)
        for c, txt, w, st in (("n", tr("Nº"), 50, False), ("codigo", tr("CÓDIGO"), 90, False),
                              ("comp", tr("COMPONENTE"), 560, True)):
            self.lista.heading(c, text=txt, anchor="w")
            self.lista.column(c, width=int(w * s), stretch=st)
        self.lista.pack(fill="both", expand=True)
        self._botones()
        self._reloj()
        app.act_en_curso = True
        win.after(150, self._modal)

    def _modal(self):
        try:
            self.win.grab_set()          # mientras tanto no se puede leer nada más de la centralita
        except tk.TclError:
            pass

    def _destruir(self):
        self.app.act_en_curso = False
        try:
            self.win.after_cancel(self.reloj_id)
        except (tk.TclError, AttributeError):
            pass
        self.win.destroy()

    def _botones(self):
        e = self.estado
        listo = self.ok_var.get() and e in ("listo", "activo", "fin")
        self.btn.configure(state="normal" if listo else "disabled",
                           text=tr("Siguiente componente") if e in ("activo", "esperando") and self.n else
                           tr("Repetir el test") if e == "fin" else tr("Iniciar"))
        activo = e == "activo" or (e == "esperando" and self.n)
        self.fin_btn.configure(state="disabled" if e in ("esperando", "parando") else "normal",
                               text=tr("Terminar") if activo else tr("Cerrar"),
                               style="Danger.TButton" if activo else "TButton")

    def _reloj(self):
        if not self.win.winfo_exists():
            return
        if self.estado == "activo" and self.desde:
            self.info.configure(text=tr("Activo desde hace {s} s. Comprueba que funciona y pulsa «Siguiente "
                                        "componente».", s=int(time.monotonic() - self.desde)), foreground=MUTED)
        self.reloj_id = self.win.after(500, self._reloj)

    def siguiente(self):
        inicio = self.estado in ("listo", "fin")
        if inicio:
            self.n = 0
            self.lista.delete(*self.lista.get_children())
        self.estado = "esperando"
        self.info.configure(text=tr("Esperando a la centralita..."), foreground=MUTED)
        self._botones()
        self.app.worker.submit("act", inicio)

    def terminar(self):
        if self.estado == "activo":
            self.estado = "parando"
            self.info.configure(text=tr("Apagando el componente (reiniciando la comunicación)..."), foreground=MUTED)
            self._botones()
            self.app.worker.submit("act_stop")
        elif self.estado not in ("esperando", "parando"):
            self._destruir()

    def cerrar(self):
        if self.estado in ("activo", "esperando", "parando"):
            self.cerrando = True
            if self.estado == "activo":
                self.terminar()
        else:
            self._destruir()

    def respuesta(self, r):
        if not self.win.winfo_exists():
            return
        if r.get("stopped"):
            self.estado = "fin"
            self.desde = None
            self.actual.configure(text="—")
            self.info.configure(text=tr("Test detenido: {e}", e=r["error"]) if r.get("error") else
                                tr("Test detenido y comunicación restablecida."),
                                foreground=ERR if r.get("error") else OK)
        elif r.get("error"):
            self.desde = None
            self.actual.configure(text="—")
            self.info.configure(text=r["error"], foreground=ERR)
            self.estado = "activo" if self.n else "fin"     # algo puede seguir activo: se reconecta
            if self.n:
                self.terminar()
        elif r["code"] is None:
            self.estado = "fin"
            self.desde = None
            self.actual.configure(text=tr("Test terminado"))
            self.info.configure(text=tr("La centralita ha probado todos sus componentes ({n}).", n=self.n), foreground=OK)
            self.app.log(tr("Test de actuadores terminado ({n} componentes).", n=self.n))
        else:
            c = r["code"]
            self.n += 1
            self.estado = "activo"
            self.desde = time.monotonic()
            self.actual.configure(text=f"{self.n}. {c:05d} · {vag_componente(c)}")
            self.lista.insert("", "end", values=(self.n, f"{c:05d}", vag_componente(c)))
            self.lista.see(self.lista.get_children()[-1])
            self.app.log(tr("Test de actuadores: {n}. {codigo} {comp}", n=self.n, codigo=f"{c:05d}",
                            comp=vag_componente(c)))
            if self.cerrando:
                self.terminar()
        if self.cerrando and self.estado == "fin":
            self._destruir()
            return
        self._reloj_info_inmediata()
        self._botones()

    def _reloj_info_inmediata(self):
        if self.estado == "activo":
            self.info.configure(text=tr("Activo desde hace {s} s. Comprueba que funciona y pulsa «Siguiente "
                                        "componente».", s=0), foreground=MUTED)

    def perdida(self):
        """Se ha perdido la conexión: la centralita ya no activa nada."""
        if self.win.winfo_exists():
            self.estado = "fin"
            self.desde = None
            self.actual.configure(text="—")
            self.info.configure(text=tr("Conexión perdida: el test se ha detenido."), foreground=ERR)
            self._botones()
            if self.cerrando:
                self._destruir()


class VentanaAjustes:
    """Ajustes básicos KW1281: la centralita entra en el modo de ajuste básico de un grupo."""

    def __init__(self, app):
        self.app = app
        s = app.s
        self.estado = "listo"        # listo, activo, saliendo
        self.cerrando = False
        self.desde = None
        self.grupo = None
        addr = int(app.mod_var.get().split(" · ")[0], 16)
        self.ajustes = ajustes_basicos(app.motor) if addr == 0x01 else {}
        self.win = win = tk.Toplevel(app.root)
        win.title(tr("Ajustes básicos"))
        win.configure(bg=PANEL)
        _poner_icono(win)
        win.geometry(f"{int(820 * s)}x{int(680 * s)}")
        win.minsize(int(640 * s), int(560 * s))
        win.transient(app.root)
        win.protocol("WM_DELETE_WINDOW", self.cerrar)

        p = ttk.Frame(win, style="Panel.TFrame", padding=18)
        p.pack(fill="both", expand=True)
        ttk.Label(p, text=tr("Ajustes básicos · {modulo}", modulo=app.mod_var.get()), style="Panel.TLabel",
                  font=(FONT, 12, "bold")).pack(anchor="w")
        aviso = app._card(p, padding=(14, 10))
        aviso.pack(fill="x", pady=(10, 10))
        for i, txt in enumerate((
                tr("La centralita entra en el modo de ajuste básico del grupo elegido: según el grupo, aprende una "
                   "posición (p. ej. la mariposa), deja de regular algo (p. ej. la EGR) o muestra valores para "
                   "ajustar a mano (p. ej. el calado de la bomba)."),
                tr("• Haz solo los ajustes que sepas para qué sirven y en las condiciones que pide el manual de "
                   "taller de tu motor. Un ajuste hecho a destiempo puede dejar un ralentí irregular hasta repetirlo bien."),
                tr("• No cambia la codificación ni los canales de adaptación; lo que aprende la centralita se puede "
                   "volver a hacer."),
                tr("• «Salir del ajuste básico» devuelve la centralita al modo normal. Quitar el contacto también."))):
            ttk.Label(aviso, text=txt, style="Card.TLabel", wraplength=int(740 * s), justify="left",
                      foreground=WARN if i == 1 else None).pack(anchor="w", pady=(0, 4))

        fila = ttk.Frame(p, style="Panel.TFrame")
        fila.pack(fill="x")
        ttk.Label(fila, text=tr("Grupo"), style="Panel.TLabel").pack(side="left", padx=(0, 8))
        opciones = [f"{g:03d} · {a[0]}" for g, a in self.ajustes.items()]
        self.grupo_var = tk.StringVar(value=opciones[0] if opciones else "")
        self.grupo_cb = ttk.Combobox(fila, textvariable=self.grupo_var, values=opciones, width=60)
        self.grupo_cb.pack(side="left", fill="x", expand=True)
        self.grupo_cb.bind("<<ComboboxSelected>>", lambda e: self._elegido())
        self.grupo_var.trace_add("write", lambda *a: self._elegido())
        self.cond = ttk.Label(p, text="", style="PanelMuted.TLabel", wraplength=int(760 * s), justify="left")
        self.cond.pack(anchor="w", pady=(6, 6))
        self.ok_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(p, text=tr("Se cumplen las condiciones de este ajuste"), variable=self.ok_var,
                        command=self._botones).pack(anchor="w")
        self.info = ttk.Label(p, text="", style="PanelMuted.TLabel", wraplength=int(760 * s))
        self.info.pack(anchor="w", pady=(10, 8))

        btns = ttk.Frame(p, style="Panel.TFrame")
        btns.pack(fill="x", side="bottom", pady=(12, 0))
        self.btn = ttk.Button(btns, text=tr("Activar ajuste básico"), style="Accent.TButton", width=26,
                              command=self.activar)
        self.btn.pack(side="left")
        self.fin_btn = ttk.Button(btns, text=tr("Cerrar"), width=14, command=self.cerrar)
        self.fin_btn.pack(side="right")

        card = app._card(p, padding=0)
        card.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(card, columns=("campo", "valor", "unidad"), show="headings", height=4)
        for c, txt, w, st in (("campo", tr("CAMPO"), 420, True), ("valor", tr("VALOR"), 160, False),
                              ("unidad", tr("UNIDAD"), 120, False)):
            self.tabla.heading(c, text=txt, anchor="w")
            self.tabla.column(c, width=int(w * s), stretch=st)
        self.tabla.pack(fill="both", expand=True)
        self._elegido()
        self._reloj()
        app.act_en_curso = True
        win.after(150, self._modal)

    def _modal(self):
        try:
            self.win.grab_set()
        except tk.TclError:
            pass

    def _destruir(self):
        self.app.act_en_curso = False
        try:
            self.win.after_cancel(self.reloj_id)
        except (tk.TclError, AttributeError):
            pass
        self.win.destroy()

    def _numero(self):
        """Número de grupo escrito o elegido (1-254), o None."""
        txt = self.grupo_var.get().strip().split(" · ")[0].strip()
        try:
            g = int(txt)
        except ValueError:
            return None
        return g if 1 <= g <= 254 else None

    def _elegido(self):
        g = self._numero()
        if g in self.ajustes:
            self.cond.configure(text=self.ajustes[g][1], foreground=MUTED)
        elif g is None:
            self.cond.configure(text=tr("Elige un ajuste o escribe el número de grupo (1-254) que indica el manual de "
                                        "taller."), foreground=MUTED)
        else:
            self.cond.configure(text=tr("Grupo {g}: haz el ajuste en las condiciones que indica el manual de taller.",
                                        g=f"{g:03d}"), foreground=WARN)
        if self.estado == "listo":
            self.ok_var.set(False)
        self._botones()

    def _botones(self):
        e = self.estado
        if e == "activo":
            self.btn.configure(state="normal", text=tr("Salir del ajuste básico"), style="Danger.TButton")
        else:
            listo = e == "listo" and self.ok_var.get() and self._numero() is not None
            self.btn.configure(state="normal" if listo else "disabled", text=tr("Activar ajuste básico"),
                               style="Accent.TButton")
        self.fin_btn.configure(state="disabled" if e == "saliendo" else "normal")
        self.grupo_cb.configure(state="normal" if e == "listo" else "disabled")

    def _reloj(self):
        if not self.win.winfo_exists():
            return
        if self.estado == "activo" and self.desde:
            self.info.configure(text=tr("En ajuste básico del grupo {g} desde hace {s} s.", g=f"{self.grupo:03d}",
                                        s=int(time.monotonic() - self.desde)), foreground=OK)
        self.reloj_id = self.win.after(500, self._reloj)

    def activar(self):
        if self.estado == "activo":
            self.salir()
            return
        g = self._numero()
        if g is None:
            return
        self.grupo = g
        nombres = self.ajustes[g][2] if g in self.ajustes else None
        self.estado = "activo"
        self.desde = time.monotonic()
        self.tabla.delete(*self.tabla.get_children())
        self.info.configure(text=tr("Esperando a la centralita..."), foreground=MUTED)
        self._botones()
        self.app.worker.submit("basic", g, nombres)

    def salir(self):
        self.estado = "saliendo"
        self.desde = None
        self.info.configure(text=tr("Saliendo del ajuste básico..."), foreground=MUTED)
        self._botones()
        self.app.worker.submit("basic_stop", self.grupo)

    def cerrar(self):
        if self.estado == "activo":
            self.cerrando = True
            self.salir()
        elif self.estado == "saliendo":
            self.cerrando = True
        else:
            self._destruir()

    def respuesta(self, r):
        if not self.win.winfo_exists():
            return
        if r.get("stopped"):
            self.estado = "listo"
            self.info.configure(text=tr("Fuera del ajuste básico: la centralita vuelve a funcionar normal."),
                                foreground=OK)
            if self.cerrando:
                self._destruir()
                return
        elif r.get("error"):
            self.estado = "listo"
            self.desde = None
            self.info.configure(text=r["error"], foreground=ERR)
        elif self.estado == "activo":
            filas = r["filas"]
            hijos = self.tabla.get_children()
            if len(hijos) != len(filas):
                self.tabla.delete(*hijos)
                hijos = [self.tabla.insert("", "end") for _ in filas]
            for i, (nombre, valor, unidad, _ok) in zip(hijos, filas):
                self.tabla.item(i, values=(nombre, valor, unidad))
        self._botones()

    def perdida(self):
        if self.win.winfo_exists():
            self.estado = "listo"
            self.desde = None
            self.info.configure(text=tr("Conexión perdida: el ajuste básico se ha detenido."), foreground=ERR)
            self._botones()
            if self.cerrando:
                self._destruir()


class VentanaAdaptacion:
    """Canales de adaptación y codificación KW1281: escriben en la centralita, con confirmación y
    un registro de cada cambio con su valor anterior (cambios.py)."""

    def __init__(self, app):
        self.app = app
        s = app.s
        self.addr = int(app.mod_var.get().split(" · ")[0], 16)
        self.referencia = (app.kkl_ident or [""])[0]
        self.cod = app.kkl_codificacion
        self.registro = cambios.Cambios(ia.carpeta_config())
        self.ocupado = None          # acción enviada a la centralita y aún sin respuesta
        self.leido = None            # (canal, valor guardado)
        self.probado = None          # (canal, valor) probado y aún sin guardar
        self.cerrando = False
        self.win = win = tk.Toplevel(app.root)
        win.title(tr("Adaptación y codificación"))
        win.configure(bg=PANEL)
        _poner_icono(win)
        win.geometry(f"{int(860 * s)}x{int(820 * s)}")
        win.minsize(int(700 * s), int(700 * s))
        win.transient(app.root)
        win.protocol("WM_DELETE_WINDOW", self.cerrar)

        p = ttk.Frame(win, style="Panel.TFrame", padding=18)
        p.pack(fill="both", expand=True)
        ttk.Label(p, text=tr("Adaptación y codificación · {modulo}", modulo=app.mod_var.get()), style="Panel.TLabel",
                  font=(FONT, 12, "bold")).pack(anchor="w")
        aviso = app._card(p, padding=(14, 10))
        aviso.pack(fill="x", pady=(10, 10))
        for i, txt in enumerate((
                tr("Esto escribe en la centralita. Un valor equivocado puede dejar el coche funcionando mal (o sin "
                   "arrancar, si es del inmovilizador) hasta volver a poner el valor de antes."),
                tr("• Cambia solo los canales y la codificación que indica el manual de taller de tu coche, con los "
                   "valores que da. Si no lo tienes claro, no lo hagas."),
                tr("• Motor parado y contacto puesto, salvo que el manual diga otra cosa, y la batería en buen estado."),
                tr("• Un valor nuevo primero se prueba (la centralita lo usa sin guardarlo) y después se guarda. "
                   "Cada cambio guardado queda apuntado abajo con el valor de antes para poder volver a él."))):
            ttk.Label(aviso, text=txt, style="Card.TLabel", wraplength=int(780 * s), justify="left",
                      foreground=WARN if i == 0 else None).pack(anchor="w", pady=(0, 4))
        self.ok_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(p, text=tr("He leído los avisos y tengo los valores del manual de taller"),
                        variable=self.ok_var, command=self._botones).pack(anchor="w")

        def numero(padre, ancho):
            v = tk.StringVar()
            e = ttk.Entry(padre, textvariable=v, width=ancho)
            v.trace_add("write", lambda *a: self._botones())
            return v, e

        # canal de adaptación
        ad = app._card(p, padding=(14, 10))
        ad.pack(fill="x", pady=(12, 0))
        ttk.Label(ad, text=tr("Canal de adaptación"), style="Card.TLabel", font=(FONT, 11, "bold")).grid(
            row=0, column=0, columnspan=5, sticky="w", pady=(0, 6))
        ttk.Label(ad, text=tr("Canal"), style="Card.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 8))
        self.canal_var, e = numero(ad, 6)
        e.grid(row=1, column=1, sticky="w")
        self.leer_btn = ttk.Button(ad, text=tr("Leer"), width=12, command=self.leer)
        self.leer_btn.grid(row=1, column=2, sticky="w", padx=(8, 0))
        self.guardado_lbl = ttk.Label(ad, text="", style="Card.TLabel", font=(FONT, 11, "bold"))
        self.guardado_lbl.grid(row=1, column=3, columnspan=2, sticky="w", padx=(14, 0))
        ttk.Label(ad, text=tr("Valor nuevo"), style="Card.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 8),
                                                                        pady=(8, 0))
        self.valor_var, e = numero(ad, 8)
        e.grid(row=2, column=1, sticky="w", pady=(8, 0))
        self.probar_btn = ttk.Button(ad, text=tr("Probar"), width=12, command=self.probar)
        self.probar_btn.grid(row=2, column=2, sticky="w", padx=(8, 0), pady=(8, 0))
        self.guardar_btn = ttk.Button(ad, text=tr("Guardar"), style="Danger.TButton", width=12, command=self.guardar)
        self.guardar_btn.grid(row=2, column=3, sticky="w", padx=(8, 0), pady=(8, 0))

        # código de acceso y codificación
        cd = app._card(p, padding=(14, 10))
        cd.pack(fill="x", pady=(10, 0))
        ttk.Label(cd, text=tr("Código de acceso (login)"), style="Card.TLabel").grid(row=0, column=0, sticky="w",
                                                                                     padx=(0, 8))
        self.login_var, e = numero(cd, 8)
        e.grid(row=0, column=1, sticky="w")
        self.login_btn = ttk.Button(cd, text=tr("Enviar código"), width=16, command=self.login)
        self.login_btn.grid(row=0, column=2, sticky="w", padx=(8, 0))
        ttk.Label(cd, text=tr("Solo si el manual lo pide para un canal o para codificar."),
                  style="Muted.TLabel").grid(row=0, column=3, sticky="w", padx=(12, 0))
        ttk.Label(cd, text=tr("Codificación"), style="Card.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 8),
                                                                         pady=(10, 0))
        self.cod_var, e = numero(cd, 8)
        e.grid(row=1, column=1, sticky="w", pady=(10, 0))
        self.cod_btn = ttk.Button(cd, text=tr("Guardar codificación"), style="Danger.TButton", width=20,
                                  command=self.codificar)
        self.cod_btn.grid(row=1, column=2, columnspan=2, sticky="w", padx=(8, 0), pady=(10, 0))
        self.cod_lbl = ttk.Label(cd, text="", style="Muted.TLabel")
        self.cod_lbl.grid(row=2, column=0, columnspan=4, sticky="w", pady=(4, 0))
        ttk.Label(cd, text=tr("Código de taller"), style="Card.TLabel").grid(row=3, column=0, sticky="w",
                                                                             padx=(0, 8), pady=(10, 0))
        self.taller_var, e = numero(cd, 8)
        e.grid(row=3, column=1, sticky="w", pady=(10, 0))
        ttk.Label(cd, text=tr("Se guarda en la centralita con cada cambio (0-99999)."),
                  style="Muted.TLabel").grid(row=3, column=2, columnspan=2, sticky="w", padx=(8, 0), pady=(10, 0))
        self.taller_var.set(f"{self.cod[1]:05d}" if self.cod else "00000")

        self.info = ttk.Label(p, text=tr("Escribe el número de canal y pulsa «Leer»."), style="PanelMuted.TLabel",
                              wraplength=int(800 * s))
        self.info.pack(anchor="w", pady=(10, 6))

        btns = ttk.Frame(p, style="Panel.TFrame")
        btns.pack(fill="x", side="bottom", pady=(12, 0))
        self.volver_btn = ttk.Button(btns, text=tr("Volver al valor anterior"), width=24, command=self.volver)
        self.volver_btn.pack(side="left")
        self.fin_btn = ttk.Button(btns, text=tr("Cerrar"), width=14, command=self.cerrar)
        self.fin_btn.pack(side="right")

        ttk.Label(p, text=tr("Cambios guardados en esta centralita"), style="Panel.TLabel").pack(anchor="w")
        card = app._card(p, padding=0)
        card.pack(fill="both", expand=True, pady=(4, 0))
        self.lista = ttk.Treeview(card, columns=("fecha", "que", "antes", "despues"), show="headings", height=4)
        for c, txt, w, st in (("fecha", tr("FECHA"), 170, False), ("que", tr("CAMBIO"), 300, True),
                              ("antes", tr("ANTES"), 110, False), ("despues", tr("DESPUÉS"), 110, False)):
            self.lista.heading(c, text=txt, anchor="w")
            self.lista.column(c, width=int(w * s), stretch=st)
        self.lista.pack(fill="both", expand=True)
        self.lista.bind("<<TreeviewSelect>>", lambda e: self._botones())
        self._pintar_cod()
        self._pintar_lista()
        self._botones()
        app.act_en_curso = True
        win.after(150, self._modal)

    def _modal(self):
        try:
            self.win.grab_set()
        except tk.TclError:
            pass

    def _destruir(self):
        self.app.act_en_curso = False
        self.win.destroy()

    @staticmethod
    def _num(var, minimo, maximo):
        try:
            v = int(var.get().strip())
        except ValueError:
            return None
        return v if minimo <= v <= maximo else None

    def _canal(self):
        return self._num(self.canal_var, 1, 255)

    def _valor(self):
        return self._num(self.valor_var, 0, 65535)

    def _taller(self):
        return self._num(self.taller_var, 0, 99999)

    def _pintar_cod(self):
        if self.cod:
            self.cod_lbl.configure(text=tr("Codificación actual: {c} · código de taller {t}", c=f"{self.cod[0]:05d}",
                                           t=f"{self.cod[1]:05d}"))
        else:
            self.cod_lbl.configure(text=tr("Esta centralita no informa de su codificación: no se puede cambiar desde aquí."))

    def _pintar_lista(self):
        self.lista.delete(*self.lista.get_children())
        self.filas = {}
        for r in self.registro.de(self.addr, self.referencia):
            que = (tr("Canal {c}", c=f"{r['canal']:02d}") if r["tipo"] == "adaptacion" else tr("Codificación"))
            fmt = (lambda v: f"{v:05d}") if r["tipo"] == "codificacion" else str
            i = self.lista.insert("", "end", values=(r["fecha"].replace("T", " "), que, fmt(r["antes"]),
                                                     fmt(r["despues"])))
            self.filas[i] = r

    def _botones(self):
        if not hasattr(self, "filas"):               # aún construyendo la ventana
            return
        libre = self.ocupado is None and not self.cerrando and self.app.connected
        ok = libre and self.ok_var.get() and self._taller() is not None
        canal, valor = self._canal(), self._valor()
        leido = self.leido is not None and self.leido[0] == canal
        self.leer_btn.configure(state="normal" if libre and canal else "disabled")
        self.probar_btn.configure(state="normal" if ok and leido and valor is not None else "disabled")
        self.guardar_btn.configure(state="normal" if ok and leido and self.probado == (canal, valor) else "disabled")
        self.login_btn.configure(state="normal" if ok and self._num(self.login_var, 0, 65535) is not None
                                 else "disabled")
        self.cod_btn.configure(state="normal" if ok and self.cod and self._num(self.cod_var, 0, 32767) is not None
                               else "disabled")
        self.volver_btn.configure(state="normal" if libre and self.lista.selection() else "disabled")
        self.fin_btn.configure(state="normal" if not self.cerrando else "disabled")

    def _enviar(self, accion, *datos, texto=None):
        self.ocupado = accion
        self.info.configure(text=texto or tr("Esperando a la centralita..."), foreground=MUTED)
        self._botones()
        self.app.worker.submit("adapt", accion, *datos)

    def leer(self):
        c = self._canal()
        if c is None:
            return
        self._deshacer_prueba()
        self.leido = self.probado = None
        self.guardado_lbl.configure(text="")
        self._enviar("leer", c)

    def probar(self):
        c, v = self._canal(), self._valor()
        if c is None or v is None:
            return
        self._enviar("probar", c, v, texto=tr("Probando el valor {v} en el canal {c}...", v=v, c=f"{c:02d}"))

    def guardar(self):
        c, v, t = self._canal(), self._valor(), self._taller()
        if self.probado != (c, v) or t is None or not self.leido:
            return
        if not messagebox.askyesno(tr("Guardar adaptación"),
                                   tr("¿Guardar en la centralita el canal {c}?", c=f"{c:02d}") + "\n\n"
                                   + tr("Antes: {a}\nAhora: {v}", a=self.leido[1], v=v) + "\n\n"
                                   + tr("El valor de antes queda apuntado para poder volver a él."), parent=self.win):
            return
        self._enviar("guardar", c, v, t, texto=tr("Guardando el canal {c}...", c=f"{c:02d}"))

    def login(self):
        v, t = self._num(self.login_var, 0, 65535), self._taller()
        if v is None or t is None:
            return
        self._enviar("login", v, t)

    def codificar(self):
        v, t = self._num(self.cod_var, 0, 32767), self._taller()
        if v is None or t is None or not self.cod:
            return
        if not messagebox.askyesno(tr("Guardar codificación"),
                                   tr("¿Cambiar la codificación de la centralita?") + "\n\n"
                                   + tr("Antes: {a}\nAhora: {v}", a=f"{self.cod[0]:05d}", v=f"{v:05d}") + "\n\n"
                                   + tr("Una codificación equivocada puede encender testigos o hacer que el coche "
                                        "funcione mal. La de antes queda apuntada para poder volver a ella."),
                                   parent=self.win):
            return
        self.cod_antes = self.cod[0]
        self._enviar("codificar", v, t, texto=tr("Guardando la codificación {v}...", v=f"{v:05d}"))

    def volver(self):
        sel = self.lista.selection()
        if not sel:
            return
        r = self.filas[sel[0]]
        if r["tipo"] == "codificacion":
            self.cod_var.set(f"{r['antes']:05d}")
            self.info.configure(text=tr("Codificación de antes puesta: {v}. Pulsa «Guardar codificación» para "
                                        "escribirla.", v=f"{r['antes']:05d}"), foreground=MUTED)
        else:
            self.canal_var.set(str(r["canal"]))
            self.valor_var.set(str(r["antes"]))
            self.leer()
            self.valor_var.set(str(r["antes"]))
            self.info.configure(text=tr("Valor de antes puesto: {v}. Pruébalo y guárdalo para volver a él.",
                                        v=r["antes"]), foreground=MUTED)

    def _deshacer_prueba(self):
        """Un valor probado y no guardado: se vuelve a probar el guardado para que la centralita lo use."""
        if self.probado and self.leido and self.probado[0] == self.leido[0] and self.probado[1] != self.leido[1]:
            self.app.worker.submit("adapt", "deshacer_prueba", self.leido[0], self.leido[1])
        self.probado = None

    def cerrar(self):
        if self.ocupado:
            self.cerrando = True
            self._botones()
            return
        self._deshacer_prueba()
        self._destruir()

    def respuesta(self, r):
        if not self.win.winfo_exists():
            return
        accion = r["accion"]
        if accion == "deshacer_prueba":
            return
        self.ocupado = None
        if r.get("info"):
            self.app._kkl_identificado(r["info"])
            self.cod = r["info"].get("codificacion")
            self._pintar_cod()
        if r.get("error"):
            self.info.configure(text=r["error"], foreground=ERR)
            if accion == "probar":
                self.probado = None
        elif accion == "leer":
            self.leido = (r["canal"], r["valor"])
            self.guardado_lbl.configure(text=tr("Valor guardado: {v}", v=r["valor"]))
            if not self.valor_var.get().strip():
                self.valor_var.set(str(r["valor"]))
            self.info.configure(text=tr("Canal {c} leído. Escribe el valor nuevo y pulsa «Probar».",
                                        c=f"{r['canal']:02d}"), foreground=OK)
        elif accion == "probar":
            self.probado = (r["canal"], r["valor"])
            if str(r["valor"]) != self.valor_var.get().strip():
                self.valor_var.set(str(r["valor"]))
            self.info.configure(text=tr("La centralita usa ahora {v} sin guardarlo. Comprueba el resultado y pulsa "
                                        "«Guardar», o cierra para dejar el valor de antes.", v=r["valor"]),
                                foreground=OK)
        elif accion == "guardar":
            antes = self.leido[1]
            self.registro.registrar(self.addr, self.referencia, "adaptacion", r["canal"], antes, r["valor"],
                                    self._taller() or 0)
            self.app.log(tr("Adaptación del módulo {m}, canal {c}: {a} → {v}.", m=f"{self.addr:02X}",
                            c=f"{r['canal']:02d}", a=antes, v=r["valor"]))
            self.leido = (r["canal"], r["valor"])
            self.probado = None
            self.guardado_lbl.configure(text=tr("Valor guardado: {v}", v=r["valor"]))
            self.info.configure(text=tr("Guardado: el canal {c} vale ahora {v} (antes {a}).", c=f"{r['canal']:02d}",
                                        v=r["valor"], a=antes), foreground=OK)
            self._pintar_lista()
        elif accion == "login":
            self.info.configure(text=tr("Código de acceso aceptado."), foreground=OK)
        elif accion == "codificar":
            nueva = r["codificacion"][0]
            self.registro.registrar(self.addr, self.referencia, "codificacion", None, self.cod_antes, nueva,
                                    r["codificacion"][1])
            self.app.log(tr("Codificación del módulo {m}: {a} → {v}.", m=f"{self.addr:02X}",
                            a=f"{self.cod_antes:05d}", v=f"{nueva:05d}"))
            self.info.configure(text=tr("Codificación guardada: {v} (antes {a}).", v=f"{nueva:05d}",
                                        a=f"{self.cod_antes:05d}"), foreground=OK)
            self._pintar_lista()
        if self.cerrando:
            self.cerrar()
            return
        self._botones()

    def perdida(self):
        if self.win.winfo_exists():
            self.ocupado = None
            self.probado = None
            self.info.configure(text=tr("Conexión perdida con la centralita."), foreground=ERR)
            self._botones()
            if self.cerrando:
                self._destruir()


class VentanaHistorial:
    """Diagnósticos guardados de cada coche y comparación de cada uno con el anterior."""

    def __init__(self, app):
        self.app = app
        s = app.s
        self.win = win = tk.Toplevel(app.root)
        win.title(tr("Historial de diagnósticos"))
        win.configure(bg=PANEL)
        _poner_icono(win)
        win.geometry(f"{int(1080 * s)}x{int(620 * s)}")
        win.minsize(int(760 * s), int(420 * s))
        self.coches = []
        self.datos = None

        cab = ttk.Frame(win, style="Panel.TFrame", padding=(16, 12, 16, 0))
        cab.pack(fill="x")
        ttk.Label(cab, text=tr("Coche"), style="PanelMuted.TLabel").pack(side="left", padx=(0, 8))
        self.coche_var = tk.StringVar()
        self.coche_cb = ttk.Combobox(cab, textvariable=self.coche_var, state="readonly", width=72)
        self.coche_cb.pack(side="left")
        self.coche_cb.bind("<<ComboboxSelected>>", lambda e: self._mostrar_coche())
        self.borrar_btn = ttk.Button(cab, text=tr("Borrar este diagnóstico"), command=self._borrar)
        self.borrar_btn.pack(side="right")

        cuerpo = ttk.Frame(win, style="Panel.TFrame", padding=16)
        cuerpo.pack(fill="both", expand=True)
        izq = app._card(cuerpo, padding=0)
        izq.pack(side="left", fill="y", padx=(0, 14))
        self.lista = ttk.Treeview(izq, columns=("fecha", "tipo", "n"), show="headings", selectmode="browse")
        for c, t, w, a in (("fecha", tr("FECHA"), 140, "w"), ("tipo", tr("TIPO"), 170, "w"), ("n", tr("AVERÍAS"), 80, "e")):
            self.lista.heading(c, text=t, anchor=a)
            self.lista.column(c, width=int(w * s), anchor=a, stretch=False)
        self.lista.pack(fill="y", expand=True)
        self.lista.bind("<<TreeviewSelect>>", lambda e: self._mostrar_registro())
        der = app._card(cuerpo, padding=0)
        der.pack(side="left", fill="both", expand=True)
        self.texto = tk.Text(der, bg=CARD, fg=FG, bd=0, highlightthickness=0, wrap="word", padx=16, pady=12,
                             font=(FONT, 10), cursor="arrow")
        sb = ttk.Scrollbar(der, orient="vertical", command=self.texto.yview)
        self.texto.configure(yscrollcommand=sb.set)
        self.texto.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for tag, kw in (("h1", {"font": (FONT, 12, "bold")}), ("h2", {"font": (FONT, 10, "bold"), "spacing1": 10}),
                        ("muted", {"foreground": MUTED}), ("nueva", {"foreground": ERR}),
                        ("resuelta", {"foreground": OK}), ("repetida", {"foreground": WARN}),
                        ("cod", {"font": (MONO, 10)})):
            self.texto.tag_configure(tag, **kw)
        ttk.Label(win, text=tr("Cada lectura, borrado y escaneo de averías se guarda automáticamente en {carpeta}",
                               carpeta=app.historial.carpeta),
                  style="PanelMuted.TLabel", padding=(16, 0, 16, 10)).pack(fill="x")
        self.recargar(app.coche[0] if app.coche else None)

    def recargar(self, preferido=None):
        self.coches = self.app.historial.coches()
        self.coche_cb.configure(values=[f"{n}  ·  {i}" + "  ·  " + tr("{n} diagnóstico(s)", n=k) if n != i else
                                        f"{n}  ·  " + tr("{n} diagnóstico(s)", n=k) for i, n, k, _ in self.coches])
        ids = [c[0] for c in self.coches]
        if not ids:
            self.coche_var.set("")
            self.datos = None
            self.lista.delete(*self.lista.get_children())
            self._escribir([(tr("Todavía no hay diagnósticos guardados. Se guardan solos al leer, borrar o "
                                "escanear averías con el coche conectado."), "muted")])
            self.borrar_btn.configure(state="disabled")
            return
        actual = ids.index(preferido) if preferido in ids else (
            ids.index(self.datos["id"]) if self.datos and self.datos["id"] in ids else 0)
        self.coche_cb.current(actual)
        self._mostrar_coche()

    def _mostrar_coche(self):
        i = self.coche_cb.current()
        if i < 0:
            return
        self.datos = self.app.historial.cargar(self.coches[i][0])
        self.lista.delete(*self.lista.get_children())
        regs = self.datos["registros"]
        for j in range(len(regs) - 1, -1, -1):
            r = regs[j]
            self.lista.insert("", "end", iid=str(j), values=(self.app._fecha_txt(r["fecha"]),
                                                             self.app._tipo_txt(r["tipo"]), len(r["averias"])))
        if regs:
            self.lista.selection_set(str(len(regs) - 1))
            self.lista.focus(str(len(regs) - 1))
        self._mostrar_registro()

    def _escribir(self, trozos):
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        for t, tag in trozos:
            self.texto.insert("end", t, tag)
        self.texto.configure(state="disabled")

    def _linea(self, a, tag=""):
        mod = f"[{a['modulo']:02X}] " if a.get("modulo") else ""
        return [(f"  {mod}{a['codigo']}  ", ("cod", tag) if tag else "cod"),
                (f"{a['texto']}", tag), (f"  · {self.app._estado_txt(a['estado'])}\n", "muted")]

    def _mostrar_registro(self):
        sel = self.lista.selection()
        if not self.datos or not sel:
            self.borrar_btn.configure(state="disabled")
            return
        self.borrar_btn.configure(state="normal")
        regs = self.datos["registros"]
        j = int(sel[0])
        r = regs[j]
        a = self.app
        mods = ", ".join(f"{m:02X} · {MODULOS.get(m, '?')}" for m in r["modulos"] if m)
        out = [(f"{a._tipo_txt(r['tipo'])} · {a._fecha_txt(r['fecha'])}\n", "h1")]
        if mods:
            out.append((tr("Módulos: {lista}", lista=mods) + "\n", "muted"))
        if r.get("mil") is not None:
            out.append(((tr("testigo MIL ENCENDIDO") if r["mil"] else tr("testigo MIL apagado")) + "\n", "muted"))
        out.append((tr("Averías ({n})", n=len(r["averias"])) + "\n", "h2"))
        for x in r["averias"]:
            out += self._linea(x)
        if not r["averias"]:
            out.append(("  " + tr("Ninguna") + "\n", "muted"))
        ant = historial.anterior(regs, j)
        if ant is None:
            out.append(("\n" + tr("No hay un diagnóstico anterior de estos módulos con el que compararlo.") + "\n", "muted"))
        else:
            c = historial.comparar(ant, r)
            out.append(("\n" + tr("Comparado con el diagnóstico del {fecha} ({tipo})", fecha=a._fecha_txt(ant["fecha"]),
                                  tipo=a._tipo_txt(ant["tipo"]).lower()) + "\n", "h2"))
            for clave, titulo, tag in (("nuevas", tr("Nuevas"), "nueva"), ("resueltas", tr("Ya no aparecen"), "resuelta"),
                                       ("repetidas", tr("Se repiten"), "repetida")):
                out.append((f"{titulo} ({len(c[clave])})\n", ("h2", tag)))
                for x in c[clave]:
                    out += self._linea(x, tag)
        self._escribir(out)

    def _borrar(self):
        sel = self.lista.selection()
        if not self.datos or not sel:
            return
        r = self.datos["registros"][int(sel[0])]
        if not messagebox.askyesno(tr("Historial de diagnósticos"),
                                   tr("¿Borrar del historial el diagnóstico del {fecha}?",
                                      fecha=self.app._fecha_txt(r["fecha"])), parent=self.win):
            return
        self.app.historial.borrar_registro(self.datos["id"], int(sel[0]))
        self.recargar(self.datos["id"])


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------
class App:
    def __init__(self, root):
        self.root = root
        self.cfg = ia.cargar_config()
        if self.cfg.get("idioma") in idioma.IDIOMAS and not os.environ.get("OBD2DESK_IDIOMA"):
            idioma.poner(self.cfg["idioma"])
        _textos_fijos()
        self.reiniciar = None        # función para reconstruir la ventana (cambio de idioma)
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
        self.vals_hist = {}                      # (clave, fila): deque[(t, valor)] del último minuto
        self.vals_nombres = {}                   # (clave, fila): (nombre, unidad)
        self.vals_serie = {}                     # (clave, fila): nombre de su serie en la gráfica
        self.visores = []                        # ventanas del visor de CSV abiertas
        self.historial = historial.Historial(os.path.join(ia.carpeta_config(), "historial"))
        self.coche = None                        # (id, nombre) del coche conectado, para el historial
        self.vag_motor = None                    # (id, nombre) por la centralita de motor VAG (sin VIN)
        self.ventana_historial = None
        self.ventana_act = None                  # VentanaActuadores abierta
        self.ventana_ajustes = None              # VentanaAjustes abierta
        self.ventana_adapt = None                # VentanaAdaptacion abierta
        self.kkl_ident = []                      # identificación y codificación de la centralita KKL conectada
        self.kkl_codificacion = None
        self.act_en_curso = False                # la IA no lee nada durante un test de actuadores o ajuste básico
        self.informe_ia = None                   # informe pedido por la IA: {"texto", "reply"}
        # Consumo y 0-100
        self.trayecto = consumo.Trayecto()
        self.crono = consumo.Cronometro()
        self.combustible_coche = None            # el que dice el PID 51 al conectar
        self.cons_muestras = deque()             # instantes de las últimas muestras (muestras/s)
        # Asistente IA
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
        self.last_dtcs = None        # última lectura de averías (para el informe)
        self.scan_result = None      # último escaneo de módulos VAG
        self.scanning = False

        root.title(f"{NOMBRE} {VERSION} · VAG KW1281 / OBD2")
        root.configure(bg=BG)
        _poner_icono(root, defecto=True)
        self._style()
        self._build()
        self._apply_mode()
        # la cabecera manda en el ancho: con fuentes anchas (Noto Sans en Linux) no cabe en 1240;
        # se mide con los textos de estado más largos que pueden salir al conectar
        ancho = 0
        largo = max(MODULOS.values(), key=len)
        for texto in (tr("Conectado · {modulo} · {baud} bd", modulo=largo, baud=10400),
                      tr("Conectado · OBD2 · {protocolo}", protocolo="ISO 15765-4 (CAN 29/500)")):
            self.status_lbl.configure(text=texto)
            root.update_idletasks()
            ancho = max(ancho, root.winfo_reqwidth())
        # y la barra de Averías con los botones de KKL y el resultado más largo de un escaneo
        ocultos = [b for b in (self.scan_btn, self.act_btn, self.ajustes_btn, self.adapt_btn) if not b.winfo_manager()]
        for b in ocultos:
            b.pack(side="left", padx=(10, 0), before=self.dtc_lbl)
        self.dtc_lbl.configure(text=tr("Responden {n} de {total} módulos · {averias} avería(s)", n=len(MODULOS),
                                       total=len(MODULOS), averias=99))
        root.update_idletasks()
        ancho = max(ancho, root.winfo_reqwidth())
        for b in ocultos:
            b.pack_forget()
        self.dtc_lbl.configure(text="")
        self._set_connected(False)
        root.geometry(f"{max(int(1240 * self.s), ancho)}x{int(800 * self.s)}")
        root.minsize(max(int(1080 * self.s), ancho), int(680 * self.s))
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(50, self.poll)
        root.after(100, lambda: _barra_oscura(root))
        if not os.environ.get("OBD2DESK_SIN_COMPROBAR_VERSION"):
            comprobar_version(lambda tag, url: self.q.put(("update", (tag, url))))

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
        tit = ttk.Frame(left, style="Panel.TFrame")
        tit.pack(anchor="w")
        ttk.Label(tit, text=NOMBRE, style="Title.TLabel").pack(side="left")
        self.lang_var = tk.StringVar(value=idioma.IDIOMAS[idioma.actual()])
        self.lang_cb = ttk.Combobox(tit, textvariable=self.lang_var, values=list(idioma.IDIOMAS.values()),
                                    state="readonly", width=8, font=(FONT, 9))
        self.lang_cb.pack(side="left", padx=(12, 0))
        self.lang_cb.bind("<<ComboboxSelected>>", lambda e: self._cambiar_idioma())
        self.upd_lbl = ttk.Label(tit, text="", style="PanelMuted.TLabel", foreground=ACCENT, cursor="hand2")
        self.upd_lbl.pack(side="left", padx=(10, 0))
        st_row = ttk.Frame(left, style="Panel.TFrame")
        st_row.pack(anchor="w")
        self.status_dot = tk.Canvas(st_row, width=int(12 * s), height=int(12 * s), bg=PANEL, highlightthickness=0)
        self.status_dot.pack(side="left", padx=(0, 6))
        self.status_lbl = ttk.Label(st_row, text=tr("Desconectado"), style="PanelMuted.TLabel")
        self.status_lbl.pack(side="left")

        right = ttk.Frame(head, style="Panel.TFrame")
        right.pack(side="right")                    # antes que left: si falta sitio se recorta el estado
        left.pack(side="left", padx=(0, 24))
        ttk.Label(right, text=tr("Conexión"), style="PanelMuted.TLabel").grid(row=0, column=0, padx=(0, 6))
        self.mode_var = tk.StringVar(value=MODOS[KKL])
        self.mode_cb = ttk.Combobox(right, textvariable=self.mode_var, values=list(MODOS.values()),
                                    state="readonly", width=27)
        self.mode_cb.grid(row=0, column=1, padx=(0, 14))
        self.mode_cb.bind("<<ComboboxSelected>>", lambda e: self._apply_mode())

        ttk.Label(right, text=tr("Puerto"), style="PanelMuted.TLabel").grid(row=0, column=2, padx=(0, 6))
        self.port_var = tk.StringVar()
        self.port_cb = ttk.Combobox(right, textvariable=self.port_var, state="readonly", width=26)
        self.port_cb.grid(row=0, column=3)
        self.refresh_btn = ttk.Button(right, text="↻", width=3, command=self.refresh_ports)
        self.refresh_btn.grid(row=0, column=4, padx=(4, 14))

        self.mod_lbl = ttk.Label(right, text=tr("Módulo"), style="PanelMuted.TLabel")
        self.mod_lbl.grid(row=0, column=5, padx=(0, 6))
        self.mod_var = tk.StringVar()
        mods = [f"{a:02X} · {n}" for a, n in MODULOS.items()]
        self.mod_cb = ttk.Combobox(right, textvariable=self.mod_var, values=mods, state="readonly", width=22)
        self.mod_cb.current(0)
        self.mod_cb.grid(row=0, column=6, padx=(0, 14))
        self.conn_btn = ttk.Button(right, text=tr("Conectar"), style="Accent.TButton", width=14,
                                   command=self.toggle_connect)
        self.conn_btn.grid(row=0, column=7)

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True)
        self.tab_panel = ttk.Frame(self.nb, style="Panel.TFrame", padding=16)
        self.tab_cons = ttk.Frame(self.nb, style="Panel.TFrame", padding=16)
        self.tab_vals = ttk.Frame(self.nb, style="Panel.TFrame", padding=16)
        self.tab_dtc = ttk.Frame(self.nb, style="Panel.TFrame", padding=16)
        self.tab_ecu = ttk.Frame(self.nb, style="Panel.TFrame", padding=16)
        self.tab_log = ttk.Frame(self.nb, style="Panel.TFrame", padding=16)
        self.tab_ia = ttk.Frame(self.nb, style="Panel.TFrame", padding=16)
        self.tab_ayuda = ttk.Frame(self.nb, style="Panel.TFrame", padding=16)
        for t, n in ((self.tab_panel, tr("Panel")), (self.tab_vals, tr("Valores medidos")),
                     (self.tab_dtc, tr("Averías")), (self.tab_ecu, tr("Vehículo")),
                     (self.tab_cons, tr("Consumo y 0-100")),
                     (self.tab_ia, tr("✦ Asistente IA")), (self.tab_log, tr("Registro")),
                     (self.tab_ayuda, tr("Ayuda"))):
            self.nb.add(t, text=f"  {n}  ")
        self._build_panel()
        self._build_cons()
        self._build_vals()
        self._build_dtc()
        self._build_ecu()
        self._build_ia()
        self._build_log()
        self._build_ayuda()

        self.bar = ttk.Label(self.root, text=tr("Listo. Elige conexión y puerto, y pulsa Conectar."),
                             style="PanelMuted.TLabel", padding=(18, 6))
        self.bar.pack(fill="x", side="bottom")

    def _card(self, parent, **kw):
        return ttk.Frame(parent, style="Card.TFrame", padding=kw.pop("padding", 12), **kw)

    def _stats_row(self, parent, items, etiquetas=None):
        """Fila de tarjetas con un valor grande; en etiquetas (dict) deja los títulos para cambiarlos."""
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.pack(fill="x", pady=12)
        out = {}
        for i, (key, title) in enumerate(items):
            frame.columnconfigure(i, weight=1, uniform="stats")
            c = self._card(frame)
            c.grid(row=0, column=i, padx=6, sticky="ew")
            lbl = ttk.Label(c, text=title, style="Muted.TLabel")
            lbl.pack(anchor="w")
            if etiquetas is not None:
                etiquetas[key] = lbl
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
        self.panel_btn = ttk.Button(top, text=tr("▶  Iniciar lectura"), style="Accent.TButton",
                                    command=lambda: self.toggle_live("panel"))
        self.panel_btn.pack(side="right")

        # Panel VAG (KW1281)
        self.panel_vag = ttk.Frame(p, style="Panel.TFrame")
        self.g_rpm, self.g_iq, self.g_boost, self.g_temp = self._gauges_row(self.panel_vag, [
            (tr("Régimen"), "rpm", 0, 5000, 1000, 4500),
            (tr("Caudal inyectado"), "mg/H", 0, 60, 10, None, 1),
            (tr("Presión turbo"), "mbar", 0, 2500, 500, 2300),
            (tr("Refrigerante"), "°C", 0, 120, 20, 105)])
        self.vag_stats_lbl = {}
        self.vag_stats = self._stats_row(self.panel_vag, [
            ("n75", tr("Ciclo N75 (turbo)")), ("egr", tr("Ciclo válvula EGR")),
            ("volt", tr("Tensión dosificador")), ("maf", tr("Masa de aire real"))], self.vag_stats_lbl)
        self.ch_boost, self.ch_maf = self._charts_row(self.panel_vag, [
            (tr("Presión de turbo · G011"), "mbar", [(tr("Teórica"), BLUE), (tr("Real"), ACCENT)], 2000),
            (tr("Masa de aire · G003"), "mg/H", [(tr("Teórica"), BLUE), (tr("Real"), ACCENT)], 500)])

        # Panel VAG gasolina (grupos estándar 002, 003 y 004)
        self.panel_gas = ttk.Frame(p, style="Panel.TFrame")
        self.gg_rpm, self.gg_load, self.gg_temp, self.gg_iat = self._gauges_row(self.panel_gas, [
            (tr("Régimen"), "rpm", 0, 7000, 1000, 6200),
            (tr("Carga"), "%", 0, 100, 20, None),
            (tr("Refrigerante"), "°C", 0, 120, 20, 105),
            (tr("Temp. aire de admisión"), "°C", 0, 80, 20, None)])
        self.gas_stats = self._stats_row(self.panel_gas, [
            ("iny", tr("Tiempo de inyección medio")), ("aire", tr("Masa de aire (o presión colector)")),
            ("mar", tr("Ángulo de la mariposa")), ("avance", tr("Avance de encendido")), ("volt", tr("Tensión"))])
        self.ch_grpm, self.ch_gload = self._charts_row(self.panel_gas, [
            (tr("Régimen · G002"), "rpm", [("RPM", ACCENT)], 3000),
            (tr("Carga y mariposa · G002 / G003"), "%", [(tr("Carga"), ACCENT), (tr("Mariposa"), BLUE)], 100)])

        # Panel OBD2 (ELM327)
        self.panel_obd = ttk.Frame(p, style="Panel.TFrame")
        self.o_rpm, self.o_speed, self.o_temp, self.o_load = self._gauges_row(self.panel_obd, [
            (tr("Régimen"), "rpm", 0, 8000, 1000, 6500),
            (tr("Velocidad"), "km/h", 0, 240, 40, None),
            (tr("Refrigerante"), "°C", 0, 120, 20, 105),
            (tr("Carga del motor"), "%", 0, 100, 20, None)])
        self.obd_stats = self._stats_row(self.panel_obd, [
            ("iat", tr("Temp. aire admisión")), ("maf", tr("Caudal de aire (MAF)")),
            ("tps", tr("Posición mariposa")), ("volt", tr("Tensión centralita"))])
        self.ch_rpm, self.ch_load = self._charts_row(self.panel_obd, [
            (tr("Régimen motor"), "rpm", [("RPM", ACCENT)], 3000),
            (tr("Carga y mariposa"), "%", [(tr("Carga"), ACCENT), (tr("Mariposa"), BLUE)], 100)])

    def _build_cons(self):
        p, s = self.tab_cons, self.s
        top = ttk.Frame(p, style="Panel.TFrame")
        top.pack(fill="x")
        self.cons_btn = ttk.Button(top, text=tr("▶  Iniciar lectura"), style="Accent.TButton",
                                   command=lambda: self.toggle_live("cons"))
        self.cons_btn.pack(side="right")
        ttk.Button(top, text=tr("Reiniciar trayecto"), command=self._cons_reiniciar).pack(side="right", padx=(0, 10))
        aj = ttk.Frame(top, style="Panel.TFrame")
        aj.pack(side="right", padx=(0, 18))
        cfg = self.cfg.get("consumo", {})
        self.comb_lbl = ttk.Label(aj, text=tr("Combustible"), style="PanelMuted.TLabel")
        self.comb_var = tk.StringVar(value=self._nombre_comb(cfg.get("combustible", consumo.GASOLINA)))
        self.comb_cb = ttk.Combobox(aj, textvariable=self.comb_var, state="readonly", width=9,
                                    values=[self._nombre_comb(consumo.GASOLINA), self._nombre_comb(consumo.DIESEL)])
        self.comb_cb.bind("<<ComboboxSelected>>", lambda e: self._cons_ajuste())
        self.cil_lbl = ttk.Label(aj, text=tr("Cilindrada (L)"), style="PanelMuted.TLabel")
        self.cil_var = tk.StringVar(value=str(cfg.get("cilindrada", 1.6)))
        self.cil_entry = ttk.Entry(aj, textvariable=self.cil_var, width=5)
        self.ncil_lbl = ttk.Label(aj, text=tr("Cilindros"), style="PanelMuted.TLabel")
        self.ncil_var = tk.StringVar(value=str(cfg.get("cilindros", 4)))
        self.ncil_entry = ttk.Entry(aj, textvariable=self.ncil_var, width=3)
        for e in (self.cil_entry, self.ncil_entry):
            e.bind("<FocusOut>", lambda ev: self._cons_ajuste())
            e.bind("<Return>", lambda ev: self._cons_ajuste())
        self.cons_lbl = ttk.Label(p, text="", style="PanelMuted.TLabel", wraplength=int(1100 * s))
        self.cons_lbl.pack(fill="x", pady=(8, 0))

        self.cons_stats = self._stats_row(p, [
            ("inst", tr("Consumo instantáneo")), ("medio", tr("Consumo medio")),
            ("litros", tr("Combustible gastado")), ("km", tr("Distancia")), ("tiempo", tr("Tiempo"))])

        fila = ttk.Frame(p, style="Panel.TFrame")
        fila.pack(fill="x", pady=(0, 12))
        fila.columnconfigure(0, weight=3)
        fila.columnconfigure(1, weight=2)
        c = self._card(fila, padding=16)
        c.grid(row=0, column=0, padx=6, sticky="nsew")
        ttk.Label(c, text=tr("Cronómetro 0-100 km/h"), style="Card.TLabel", font=(FONT, 11, "bold")).pack(anchor="w")
        self.crono_var = tk.StringVar(value="--")
        ttk.Label(c, textvariable=self.crono_var, style="Card.TLabel", foreground=ACCENT,
                  font=(FONT, 34, "bold")).pack(anchor="w", pady=(4, 0))
        self.crono_est = ttk.Label(c, text="", style="Card.TLabel", wraplength=int(600 * s))
        self.crono_est.pack(anchor="w")
        self.crono_nota = ttk.Label(c, text="", style="Muted.TLabel", wraplength=int(600 * s))
        self.crono_nota.pack(anchor="w", pady=(6, 0))
        c = self._card(fila, padding=16)
        c.grid(row=0, column=1, padx=6, sticky="nsew")
        ttk.Label(c, text=tr("Últimas medidas"), style="Card.TLabel", font=(FONT, 11, "bold")).pack(anchor="w")
        self.crono_lista = ttk.Label(c, text="", style="Card.TLabel", font=(MONO, 10), justify="left")
        self.crono_lista.pack(anchor="w", pady=(6, 0))
        self.crono_mejor = ttk.Label(c, text="", style="Card.TLabel", foreground=OK, font=(FONT, 11, "bold"))
        self.crono_mejor.pack(anchor="w", pady=(8, 0))

        self.ch_cons, = self._charts_row(p, [(tr("Consumo instantáneo"), "L/h", [(tr("Consumo"), ACCENT)], 10)])

    @staticmethod
    def _nombre_comb(c):
        return tr("Diésel") if c == consumo.DIESEL else tr("Gasolina")

    def _cons_valores(self):
        """(combustible, cilindrada en L o None, cilindros) según los ajustes de la pestaña."""
        comb = consumo.DIESEL if self.comb_var.get() == tr("Diésel") else consumo.GASOLINA
        try:
            cil = float(self.cil_var.get().replace(",", "."))
            cil = cil if 0.3 <= cil <= 10 else None
        except ValueError:
            cil = None
        try:
            ncil = int(self.ncil_var.get())
            ncil = ncil if 1 <= ncil <= 16 else 4
        except ValueError:
            ncil = 4
        return comb, cil, ncil

    def _cons_guardar(self):
        comb, cil, ncil = self._cons_valores()
        nuevo = {"combustible": comb, "cilindrada": cil or 1.6, "cilindros": ncil}
        if self.cfg.get("consumo") != nuevo:
            self.cfg["consumo"] = nuevo
            try:
                ia.guardar_config(self.cfg)
            except OSError:
                pass

    def _cons_ajuste(self):
        self._cons_guardar()
        if self.live_source == "cons":            # pueden hacer falta otros PIDs: se vuelve a empezar
            self.toggle_live("cons")
            self.toggle_live("cons")
        self._cons_texto()

    def _cons_texto(self):
        """Cómo se calcula el consumo (debajo de los ajustes)."""
        comb, cil, _ = self._cons_valores()
        if not self.connected:
            t = tr("Conecta y pulsa Iniciar lectura. El consumo es una estimación (±10 %), como en cualquier programa OBD.")
        elif self._kkl_gasolina():
            t = tr("Gasolina por KKL: consumo con la masa de aire (grupo 002; si el motor tiene sensor de presión "
                   "en vez de caudalímetro, con la cilindrada) y velocidad del grupo 005. Son los grupos estándar de "
                   "VAG: si tu centralita no los tiene, no sale.")
        elif self.mode == KKL:
            t = tr("Calculado con el caudal inyectado y el régimen (grupo 001). La centralita no da la velocidad: "
                   "consumo en L/h y litros gastados.")
        else:
            m = consumo.metodo(self.supported, comb)
            if m == "5E":
                t = tr("Consumo que da la propia centralita (PID 5E).")
            elif m == "MAF":
                t = tr("Calculado con el caudalímetro (PID 10) y la mezcla aire/combustible.")
            elif m == "MAP" and cil:
                t = tr("Estimado con la presión del colector, el régimen y la cilindrada (el coche no tiene "
                       "caudalímetro): comprueba que la cilindrada es la de tu motor.")
            elif m == "MAP":
                t = tr("Escribe la cilindrada del motor: sin caudalímetro el consumo se estima con ella.")
            elif comb == consumo.DIESEL:
                t = tr("Este diésel no da el consumo (PID 5E) ni la sonda lambda de banda ancha: sin ellos no "
                       "se puede calcular con fiabilidad.")
            else:
                t = tr("El coche no da los valores necesarios para calcular el consumo.")
            if self.combustible_coche:
                t += " " + tr("Combustible según el coche: {comb}.", comb=self._nombre_comb(self.combustible_coche))
        self.cons_lbl.configure(text=t)

    def _cons_items(self):
        if self._kkl_gasolina():
            return [2, 5]                                   # aire (o presión) y velocidad
        if self.mode == KKL:
            return [1]
        comb, cil, _ = self._cons_valores()
        m = consumo.metodo(self.supported, comb)
        if (m is None or (m == "MAP" and not cil)) and 0x0D not in self.supported:
            return []                              # ni consumo ni 0-100
        return consumo.pids_necesarios(self.supported, comb)

    def _cons_reiniciar(self):
        self.trayecto.reiniciar()
        self.ch_cons.clear()
        self._cons_pintar()

    def _cons_muestra(self, t, data):
        self.cons_muestras.append(t)
        while self.cons_muestras and self.cons_muestras[0] < t - 3:
            self.cons_muestras.popleft()
        comb, cil, ncil = self._cons_valores()
        kmh = None
        if self._kkl_gasolina():
            g2, g5 = rows_of(data, 2), rows_of(data, 5)
            v = {}
            if len(g2) > 3 and g2[3][2] == "g/s":
                v[consumo.P_MAF] = num(g2, 3)
            elif len(g2) > 3 and g2[3][2] == "mbar" and num(g2, 3) is not None:
                v[consumo.P_MAP], v[consumo.P_RPM] = num(g2, 3) / 10, num(g2, 0)     # mbar -> kPa
            lh = consumo.litros_hora_obd(v, consumo.GASOLINA, cil) if v else None
            kmh = num(g5, 2) if len(g5) > 2 and g5[2][2] == "km/h" else None
            res = self.crono.muestra(t, kmh)
            if res is not None:
                parcial = self.crono.tiempos[0][1]
                self.log(tr("0-100 km/h: {s} s", s=f"{res:.2f}")
                         + (f" (0-50: {parcial:.2f} s)" if parcial else ""))
        elif self.mode == KKL:
            g1 = rows_of(data, 1)
            lh = (consumo.litros_hora_vag(num(g1, 1), num(g1, 0), ncil)
                  if len(g1) > 1 and g1[1][2] == "mg/H" else None)
        else:
            v = {p: num(rows) for p, rows in data.items() if isinstance(rows, list)}
            lh = consumo.litros_hora_obd(v, comb, cil)
            kmh = v.get(consumo.P_VELOCIDAD)
            res = self.crono.muestra(t, kmh)
            if res is not None:
                parcial = self.crono.tiempos[0][1]
                self.log(tr("0-100 km/h: {s} s", s=f"{res:.2f}")
                         + (f" (0-50: {parcial:.2f} s)" if parcial else ""))
        self.trayecto.muestra(t, lh, kmh)
        if lh is not None:
            self.ch_cons.add(t, {tr("Consumo"): lh})

    def _cons_pintar(self):
        st, tray = self.cons_stats, self.trayecto
        kkl = self.mode == KKL and not self._kkl_gasolina()     # KKL sin velocidad (TDI)
        lh, _ = tray.instantaneo()
        l100 = tray.l100_instantaneo()
        st["inst"].set(f"{l100:.1f} L/100 km" if l100 is not None else f"{lh:.1f} L/h" if lh is not None else "--")
        medio = tray.l100_medio()
        if medio is not None:
            st["medio"].set(f"{medio:.1f} L/100 km")
        elif tray.segundos >= 10:
            st["medio"].set(f"{tray.litros / tray.segundos * 3600:.1f} L/h")
        else:
            st["medio"].set("--")
        st["litros"].set(f"{tray.litros:.{2 if tray.litros >= 1 else 3}f} L" if tray.segundos else "--")
        st["km"].set("--" if kkl or not tray.segundos else f"{tray.km:.1f} km")
        seg = int(tray.segundos)
        st["tiempo"].set(f"{seg // 3600}:{seg // 60 % 60:02d}:{seg % 60:02d}" if seg else "--")
        self.ch_cons.redraw()

        cr = self.crono
        avisos = {"frenada": tr("Medida anulada: la velocidad bajó antes de llegar a 100."),
                  "parada": tr("Medida anulada: el coche se paró."),
                  "hueco": tr("Medida anulada: se cortaron las lecturas.")}
        nota = ""
        if kkl:
            grande, est = "--", tr("La centralita EDC15 no da la velocidad: el 0-100 necesita un ELM327 · OBD2.")
        elif self.mode == ELM and self.connected and 0x0D not in self.supported:
            grande, est = "--", tr("El coche no da la velocidad (PID 0D): no se puede medir el 0-100.")
        elif cr.estado == cr.MIDIENDO:
            grande = f"{cr.transcurrido():.1f} s"
            est = tr("Midiendo... {v} km/h", v=f"{cr.anterior[1]:.0f}")
        else:
            grande = f"{cr.tiempos[0][0]:.2f} s" if cr.tiempos else "0.00 s"
            if self.live_source != "cons":
                est = tr("Pulsa Iniciar lectura y para el coche: el cronómetro arranca solo al salir.")
            elif cr.estado == cr.LISTO:
                est = tr("Listo: el cronómetro arranca al empezar a moverte.")
            else:
                est = tr("Para el coche para empezar una medida.")
            if cr.aviso in avisos:
                est = avisos[cr.aviso] + " " + est
            elif cr.tiempos and cr.tiempos[0][1]:
                est = tr("0-50 km/h: {s} s.", s=f"{cr.tiempos[0][1]:.2f}") + " " + est
        if not kkl:
            if self.live_source == "cons" and len(self.cons_muestras) > 1:
                ritmo = (len(self.cons_muestras) - 1) / ((self.cons_muestras[-1] - self.cons_muestras[0]) or 1)
                nota = tr("Precisión de ±0,1-0,2 s: depende de las lecturas por segundo del adaptador "
                          "(ahora {n}/s). Mídelo solo en un circuito o lugar cerrado al tráfico.", n=f"{ritmo:.0f}")
            else:
                nota = tr("Mídelo solo en un circuito o lugar cerrado al tráfico.")
        self.crono_var.set(grande)
        self.crono_est.configure(text=est)
        self.crono_nota.configure(text=nota)
        self.crono_lista.configure(text="\n".join(
            f"{i + 1}.  {t:5.2f} s" + (f"   (0-50: {p:.2f} s)" if p else "")
            for i, (t, p) in enumerate(cr.tiempos)) or tr("(ninguna todavía)"))
        self.crono_mejor.configure(text=tr("Mejor: {s} s", s=f"{cr.mejor:.2f}") if cr.mejor else "")

    def _build_vals(self):
        p = self.tab_vals
        side = self._card(p, padding=14)
        side.pack(side="left", fill="y", padx=(0, 14))
        self.side_title = ttk.Label(side, text="", style="Card.TLabel", font=(FONT, 11, "bold"))
        self.side_title.pack(anchor="w", pady=(0, 8))

        # Selección VAG
        self.side_vag = ttk.Frame(side, style="Card.TFrame")
        ttk.Label(self.side_vag, text=tr("Motor"), style="Muted.TLabel").pack(anchor="w")
        self.motor = "edc15"
        self.motor_var = tk.StringVar(value=tr(MOTORES[self.motor][0]))
        self.motor_cb = ttk.Combobox(self.side_vag, textvariable=self.motor_var, state="readonly", width=28,
                                     values=[tr(m[0]) for m in MOTORES.values()])
        self.motor_cb.pack(anchor="w", fill="x", pady=(2, 8))
        self.motor_cb.bind("<<ComboboxSelected>>",
                           lambda e: self._poner_motor(list(MOTORES)[self.motor_cb.current()]))
        # «Otros grupos» abajo; las casillas ocupan el resto y se desplazan si no caben (gasolina: 15 grupos)
        self.extra_groups = ttk.Entry(self.side_vag, width=22)
        self.extra_groups.pack(side="bottom", anchor="w", fill="x")
        ttk.Label(self.side_vag, text=tr("Otros grupos (ej. 5, 20)"),
                  style="Muted.TLabel").pack(side="bottom", anchor="w", pady=(12, 4))
        zona = ttk.Frame(self.side_vag, style="Card.TFrame")
        zona.pack(fill="both", expand=True)
        cv = self.grupos_canvas = tk.Canvas(zona, bg=CARD, bd=0, highlightthickness=0, height=1)
        sb_g = ttk.Scrollbar(zona, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb_g.set)
        cv.pack(side="left", fill="both", expand=True)
        self.grupos_frame = ttk.Frame(cv, style="Card.TFrame")
        cv.create_window(0, 0, window=self.grupos_frame, anchor="nw")

        def ajustar(_e=None):
            cv.configure(scrollregion=(0, 0, self.grupos_frame.winfo_reqwidth(), self.grupos_frame.winfo_reqheight()),
                         width=self.grupos_frame.winfo_reqwidth())
            if self.grupos_frame.winfo_reqheight() > cv.winfo_height() > 1:
                sb_g.pack(side="right", fill="y", before=cv)
            else:
                sb_g.pack_forget()
                cv.yview_moveto(0)
        self.grupos_frame.bind("<Configure>", ajustar)
        cv.bind("<Configure>", ajustar)

        def rueda(e):
            w = cv.winfo_containing(e.x_root, e.y_root)
            if sb_g.winfo_ismapped() and w is not None and str(w).startswith(str(cv)):
                cv.yview_scroll(-1 if (e.num == 4 or (e.num != 5 and e.delta > 0)) else 1, "units")
        for s in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            cv.bind_all(s, rueda, add="+")
        self.group_vars = {}
        self._poner_motor(self.motor)

        # Selección OBD2
        self.side_obd = ttk.Frame(side, style="Card.TFrame")
        ttk.Label(self.side_obd, text=tr("Ctrl+clic para elegir varios"), style="Muted.TLabel").pack(anchor="w", pady=(0, 4))
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
        self.pid_list.insert("end", "  " + tr("(conecta para ver los PIDs)"))
        self.pid_order = []

        self.side_btns = ttk.Frame(side, style="Card.TFrame")
        self.side_btns.pack(side="bottom", fill="x")
        self.vals_btn = ttk.Button(self.side_btns, text=tr("▶  Iniciar lectura"), style="Accent.TButton",
                                   command=lambda: self.toggle_live("vals"))
        self.vals_btn.pack(fill="x", pady=(18, 6))
        self.rec_btn = ttk.Button(self.side_btns, text=tr("●  Grabar CSV"), command=self.toggle_rec)
        self.rec_btn.pack(fill="x")
        self.rec_lbl = ttk.Label(self.side_btns, text="", style="Muted.TLabel", wraplength=int(220 * self.s))
        self.rec_lbl.pack(anchor="w", pady=(8, 0))
        ttk.Button(self.side_btns, text=tr("Abrir CSV..."), command=self.abrir_csv).pack(fill="x", pady=(10, 0))

        derecha = ttk.Frame(p, style="Panel.TFrame")
        derecha.pack(side="left", fill="both", expand=True)
        self.ch_vals = Chart(derecha, "", "", [], ymin_top=1, s=self.s)
        self.ch_vals.mensaje = tr("Haz clic en una fila de la tabla para ver su gráfica (Ctrl+clic: hasta 4 valores).")
        self.ch_vals.pack(side="bottom", fill="x", pady=(12, 0))
        main = self._card(derecha, padding=0)
        main.pack(side="top", fill="both", expand=True)
        cols = ("grupo", "campo", "valor", "unidad")
        self.tree = ttk.Treeview(main, columns=cols, show="headings")
        for c, t, w, a in (("grupo", tr("GRUPO"), 90, "center"), ("campo", tr("CAMPO"), 320, "w"),
                           ("valor", tr("VALOR"), 140, "e"), ("unidad", tr("UNIDAD"), 110, "w")):
            self.tree.heading(c, text=t, anchor=a)
            self.tree.column(c, width=int(w * self.s), anchor=a, stretch=(c == "campo"))
        self.tree.tag_configure("err", foreground=ERR)
        self.tree.tag_configure("unk", foreground=WARN)
        self.tree.tag_configure("first", background=CARD2)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._vals_grafica())
        sb = ttk.Scrollbar(main, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _build_dtc(self):
        p = self.tab_dtc
        top = ttk.Frame(p, style="Panel.TFrame")
        top.pack(fill="x", pady=(0, 12))
        self.dtc_read_btn = ttk.Button(top, text=tr("Leer averías"), style="Accent.TButton", command=self.read_dtcs)
        self.dtc_read_btn.pack(side="left")
        self.dtc_clear_btn = ttk.Button(top, text=tr("Borrar averías"), style="Danger.TButton", command=self.clear_dtcs)
        self.dtc_clear_btn.pack(side="left", padx=10)
        self.scan_btn = ttk.Button(top, text=tr("Escanear todos los módulos"), command=self.scan_modules)
        self.scan_btn.pack(side="left")
        self.act_btn = ttk.Button(top, text=tr("Test de actuadores..."), command=self.test_actuadores)
        self.act_btn.pack(side="left", padx=(10, 0))
        self.ajustes_btn = ttk.Button(top, text=tr("Ajustes básicos..."), command=self.ajustes_basicos)
        self.ajustes_btn.pack(side="left", padx=(10, 0))
        self.adapt_btn = ttk.Button(top, text=tr("Adaptación..."), command=self.adaptacion)
        self.adapt_btn.pack(side="left", padx=(10, 0))
        self.report_btn = ttk.Button(top, text=tr("Generar informe"), command=self.make_report)
        self.report_btn.pack(side="right")
        ttk.Button(top, text=tr("Historial..."), command=self.ver_historial).pack(side="right", padx=(0, 10))
        self.dtc_lbl = ttk.Label(top, text="", style="Panel.TLabel", font=(FONT, 11, "bold"))
        self.dtc_lbl.pack(side="left", padx=10)
        self.hist_lbl = ttk.Label(p, text="", style="PanelMuted.TLabel", wraplength=int(1150 * self.s))
        self.hist_lbl.pack(fill="x", pady=(0, 10))

        body = ttk.Frame(p, style="Panel.TFrame")
        body.pack(fill="both", expand=True)
        card = self._card(body, padding=0)
        card.pack(side="left", fill="both", expand=True)
        cols = ("codigo", "comp", "tipo", "estado")
        self.dtc_tree = ttk.Treeview(card, columns=cols, show="headings")
        for c, t, w, st in (("codigo", tr("CÓDIGO"), 100, False), ("comp", tr("COMPONENTE"), 430, True),
                            ("tipo", tr("TIPO DE FALLO"), 300, True), ("estado", tr("ESTADO"), 130, False)):
            self.dtc_tree.heading(c, text=t, anchor="w")
            self.dtc_tree.column(c, width=int(w * self.s), stretch=st)
        self.dtc_tree.tag_configure("inter", foreground=WARN)
        self.dtc_tree.tag_configure("fixed", foreground=ERR)
        self.dtc_tree.tag_configure("perm", foreground=BLUE)
        self.dtc_tree.tag_configure("mod", foreground=ACCENT, font=(FONT, 10, "bold"))
        self.dtc_tree.pack(fill="both", expand=True)
        self.dtc_help = ttk.Label(p, text="", style="PanelMuted.TLabel")
        self.dtc_help.pack(anchor="w", pady=(10, 0))
        # Datos congelados (solo OBD2), a la derecha de la lista de averías
        self.ff_frame = self._card(body, padding=(14, 10, 14, 0))
        self.ff_lbl = ttk.Label(self.ff_frame, text=tr("Datos congelados"), style="Card.TLabel",
                                font=(FONT, 11, "bold"), wraplength=int(330 * self.s))
        self.ff_lbl.pack(anchor="w", pady=(0, 2))
        ttk.Label(self.ff_frame, text=tr("Valores del motor cuando se registró la avería"), style="Muted.TLabel",
                  ).pack(anchor="w", pady=(0, 8))
        self.ff_tree = ttk.Treeview(self.ff_frame, columns=("dato", "valor"), show="headings")
        for c, t, w, st in (("dato", tr("DATO"), 210, True), ("valor", tr("VALOR"), 110, False)):
            self.ff_tree.heading(c, text=t, anchor="w")
            self.ff_tree.column(c, width=int(w * self.s), stretch=st)
        self.ff_tree.pack(fill="both", expand=True)

    def _build_ecu(self):
        self.ecu_card = self._card(self.tab_ecu, padding=22)
        self.ecu_card.pack(side="left", fill="both", expand=True, anchor="n")
        self.ready_card = self._card(self.tab_ecu, padding=22)
        self._fill_ecu([])
        self._fill_readiness(None)

    def _fill_readiness(self, r):
        c = self.ready_card
        for w in c.winfo_children():
            w.destroy()
        if self.mode != ELM:
            c.pack_forget()
            return
        c.pack(side="left", fill="y", anchor="n", padx=(14, 0))
        ttk.Label(c, text=tr("Monitores de preparación (ITV)"), style="Card.TLabel",
                  font=(FONT, 13, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ancho = int(400 * self.s)
        if not r:
            ttk.Label(c, text=tr("Conecta para ver qué autodiagnósticos de emisiones están completos."),
                      style="Muted.TLabel", wraplength=ancho).grid(row=1, column=0, columnspan=2, sticky="w")
            return
        diesel, mons = r
        sin = sum(1 for _, ok in mons if not ok)
        ttk.Label(c, text=((tr("Motor diésel") if diesel else tr("Motor de gasolina")) + " · " +
                           (tr("{n} de {total} sin completar", n=sin, total=len(mons)) if sin
                            else tr("los {total} completos", total=len(mons)))),
                  style="Card.TLabel", foreground=WARN if sin else OK).grid(row=1, column=0, columnspan=2,
                                                                          sticky="w", pady=(0, 8))
        for i, (nombre, ok) in enumerate(mons):
            ttk.Label(c, text="✓" if ok else "✗", style="Card.TLabel", foreground=OK if ok else WARN,
                      font=(FONT, 11, "bold")).grid(row=2 + i, column=0, sticky="w", padx=(0, 10), pady=3)
            ttk.Label(c, text=nombre + ("" if ok else "  " + tr("(sin completar)")), style="Card.TLabel",
                      foreground=FG if ok else WARN).grid(row=2 + i, column=1, sticky="w")
        ttk.Label(c, text=tr("Tras borrar averías o desconectar la batería vuelven a «sin completar»: hacen falta "
                             "varios ciclos de conducción. En la ITV pueden rechazar el coche si falta alguno."),
                  style="Muted.TLabel", wraplength=ancho).grid(row=99, column=0, columnspan=2,
                                                              sticky="w", pady=(12, 0))

    def _fill_ecu(self, fields):
        for w in self.ecu_card.winfo_children():
            w.destroy()
        title = tr("Identificación de la centralita") if self.mode == KKL else tr("Datos del vehículo (OBD2)")
        ttk.Label(self.ecu_card, text=title, style="Card.TLabel",
                  font=(FONT, 13, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))
        if not fields:
            ttk.Label(self.ecu_card, text=tr("Conecta para ver los datos."), style="Muted.TLabel").grid(row=1, column=0, sticky="w")
            return
        for i, (k, v) in enumerate(fields, 1):
            ttk.Label(self.ecu_card, text=k, style="Muted.TLabel").grid(row=i, column=0, sticky="w", pady=5, padx=(0, 20))
            ttk.Label(self.ecu_card, text=v, style="Card.TLabel", font=(MONO, 11)).grid(row=i, column=1, sticky="w")

    def _build_log(self):
        p = self.tab_log
        top = ttk.Frame(p, style="Panel.TFrame")
        top.pack(fill="x", pady=(0, 10))
        self.debug_var = tk.BooleanVar(value=False)
        cb = tk.Checkbutton(top, text=tr("Mostrar comunicación detallada (depuración)"), variable=self.debug_var,
                            command=lambda: self.worker.submit("debug", self.debug_var.get()),
                            bg=PANEL, fg=FG, selectcolor=CARD2, activebackground=PANEL,
                            activeforeground=FG, font=(FONT, 10), bd=0, highlightthickness=0)
        cb.pack(side="left")
        ttk.Button(top, text=tr("Limpiar"), command=lambda: self.log_txt.delete("1.0", "end")).pack(side="right")
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

    # ---------------- ayuda ----------------
    def _build_ayuda(self):
        p, s = self.tab_ayuda, self.s
        side = self._card(p, padding=12)
        side.pack(side="left", fill="y", padx=(0, 14))
        ttk.Label(side, text=tr("Contenido"), style="Card.TLabel",
                  font=(FONT, 11, "bold")).pack(anchor="w", pady=(0, 8))
        self.ayuda_lista = tk.Listbox(side, bg=CARD, fg=FG, bd=0, highlightthickness=0,
                                      selectbackground=ACCENT, selectforeground="#111", activestyle="none",
                                      font=(FONT, 10), width=24, exportselection=False)
        self.ayuda_lista.pack(fill="y", expand=True)
        ttk.Label(side, text=f"{NOMBRE} v{VERSION}", style="Muted.TLabel", font=(FONT, 8)).pack(anchor="w", pady=(8, 0))

        card = self._card(p, padding=0)
        card.pack(side="left", fill="both", expand=True)
        t = self.ayuda_txt = tk.Text(card, bg=CARD, fg=FG, insertbackground=FG, font=(FONT, 10), bd=0,
                                     highlightthickness=0, padx=20, pady=14, wrap="word", spacing1=2, spacing3=4)
        sb = ttk.Scrollbar(card, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        t.tag_configure("h", font=(FONT, 13, "bold"), foreground=ACCENT, spacing1=16, spacing3=6)
        t.tag_configure("li", lmargin1=int(12 * s), lmargin2=int(26 * s))
        t.tag_configure("b", font=(FONT, 10, "bold"))
        for n, (titulo, parrafos) in enumerate(ayuda.secciones()):
            self.ayuda_lista.insert("end", titulo)
            t.mark_set(f"sec{n}", "end-1c")
            t.mark_gravity(f"sec{n}", "left")
            t.insert("end", titulo + "\n", "h")
            for par in parrafos:
                if par.startswith("• "):
                    t.insert("end", "•  ", ("li", "b"))
                    t.insert("end", par[2:] + "\n", "li")
                else:
                    t.insert("end", par + "\n")
        t.configure(state="disabled")

        def ir(_e=None):
            sel = self.ayuda_lista.curselection()
            if sel:
                t.yview(f"sec{sel[0]}")
        self.ayuda_lista.bind("<<ListboxSelect>>", ir)

    # ---------------- asistente IA ----------------
    def _build_ia(self):
        p, s = self.tab_ia, self.s
        side = self._card(p, padding=16)
        side.pack(side="left", fill="y", padx=(0, 14))
        ttk.Label(side, text=tr("Configuración de la IA"), style="Card.TLabel",
                  font=(FONT, 11, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(side, text=tr("Proveedor"), style="Muted.TLabel").pack(anchor="w")
        self.ai_prov_var = tk.StringVar()
        self.ai_prov_cb = ttk.Combobox(side, textvariable=self.ai_prov_var, state="readonly", width=26,
                                       values=[v["nombre"] for v in ia.PROVEEDORES.values()])
        self.ai_prov_cb.pack(anchor="w", fill="x", pady=(2, 10))
        self.ai_prov_cb.bind("<<ComboboxSelected>>", lambda e: self._ai_load_provider())
        ttk.Label(side, text=tr("Modelo"), style="Muted.TLabel").pack(anchor="w")
        self.ai_model = ttk.Entry(side, width=28)
        self.ai_model.pack(anchor="w", fill="x", pady=(2, 10))
        ttk.Label(side, text="API key", style="Muted.TLabel").pack(anchor="w")
        self.ai_key = ttk.Entry(side, width=28, show="•")
        self.ai_key.pack(anchor="w", fill="x", pady=(2, 4))
        self.ai_show = tk.BooleanVar(value=False)
        tk.Checkbutton(side, text=tr("Mostrar"), variable=self.ai_show,
                       command=lambda: self.ai_key.configure(show="" if self.ai_show.get() else "•"),
                       bg=CARD, fg=MUTED, selectcolor=CARD2, activebackground=CARD, activeforeground=FG,
                       font=(FONT, 9), bd=0, highlightthickness=0).pack(anchor="w")
        link = tk.Label(side, text=tr("Conseguir una API key ↗"), bg=CARD, fg=BLUE, cursor="hand2", font=(FONT, 9, "underline"))
        link.pack(anchor="w", pady=(4, 12))
        link.bind("<Button-1>", lambda e: webbrowser.open(ia.PROVEEDORES[self._ai_prov()]["url_clave"]))
        ttk.Button(side, text=tr("Guardar"), style="Accent.TButton", command=self._ai_save).pack(fill="x")
        self.ai_cfg_lbl = ttk.Label(side, text="", style="Muted.TLabel", wraplength=int(230 * s))
        self.ai_cfg_lbl.pack(anchor="w", pady=(8, 0))
        ttk.Label(side, text=(tr("La clave se guarda cifrada y solo funciona con tu usuario de Windows "
                                 "en este equipo.") if WINDOWS else
                              tr("La clave se guarda en ~/.config/{carpeta}, legible solo por tu usuario.",
                                 carpeta=NOMBRE))
                             + "\n\n" + tr("Al analizar se envían al proveedor elegido los datos "
                                            "del vehículo (incluido el VIN), las averías, los valores medidos y, si lo "
                                            "pides, el registro del programa."),
                  style="Muted.TLabel", wraplength=int(230 * s), font=(FONT, 8)).pack(side="bottom", anchor="w")

        main = ttk.Frame(p, style="Panel.TFrame")
        main.pack(side="left", fill="both", expand=True)
        top = ttk.Frame(main, style="Panel.TFrame")
        top.pack(fill="x", pady=(0, 10))
        self.ai_btn_dtc = ttk.Button(top, text=tr("Analizar averías del vehículo"), style="Accent.TButton",
                                     command=lambda: self._ai_analyze("vehiculo"))
        self.ai_btn_dtc.pack(side="left")
        self.ai_btn_log = ttk.Button(top, text=tr("Analizar errores del programa"),
                                     command=lambda: self._ai_analyze("programa"))
        self.ai_btn_log.pack(side="left", padx=8)
        self.ai_btn_stop = ttk.Button(top, text=tr("■ Detener"), command=self._ai_stop, state="disabled")
        self.ai_btn_stop.pack(side="right")
        ttk.Button(top, text=tr("Nueva conversación"), command=self._ai_new).pack(side="right", padx=8)

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
        self.ai_btn_send = ttk.Button(ask, text=tr("Enviar"), style="Accent.TButton", command=self._ai_ask)
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
        self.ai_cfg_lbl.configure(text=tr("Clave guardada.") if clave else tr("Sin API key para este proveedor."),
                                  foreground=OK if clave else WARN)

    def _ai_save(self):
        prov = self._ai_prov()
        modelo = self.ai_model.get().strip() or ia.PROVEEDORES[prov]["modelo"]
        try:
            ia.poner_clave(self.cfg, prov, self.ai_key.get().strip())
        except ia.IAError as e:
            messagebox.showerror(tr("Asistente IA"), str(e))
            return
        self.cfg["proveedor"] = prov
        self.cfg["modelos"][prov] = modelo
        ia.guardar_config(self.cfg)
        self.ai_cfg_lbl.configure(text=tr("Guardado · {proveedor} · {modelo}", proveedor=ia.PROVEEDORES[prov]["nombre"],
                                          modelo=modelo), foreground=OK)

    def _ai_context(self, incluir_log):
        partes = [tr("Fecha: {fecha}", fecha=f"{datetime.datetime.now():%Y-%m-%d %H:%M}"),
                  tr("Modo de conexión: {modo}", modo=MODOS[self.mode]),
                  tr("Estado: {estado}", estado=tr("conectado") if self.connected else tr("no conectado"))]
        if self.vehicle_fields:
            partes.append("\n## " + tr("Datos del vehículo / centralita"))
            partes += [f"- {k}: {v}" for k, v in self.vehicle_fields]
        partes.append("\n## " + tr("Averías"))
        partes.append(self.last_dtc_text or tr("No se han leído averías en esta sesión."))
        partes.append("\n## " + tr("Últimos valores medidos"))
        partes.append(self.last_live_text or tr("No se han leído valores medidos en esta sesión."))
        if incluir_log:
            lineas = self.log_txt.get("1.0", "end").strip().splitlines()[-150:]
            partes.append("\n## " + tr("Registro del programa (últimas líneas)"))
            partes.append("\n".join(lineas) if lineas else tr("(vacío)"))
        return "\n".join(partes)

    def _ai_analyze(self, tipo):
        if tipo == "vehiculo":
            visible = tr("Analiza las averías y los datos del vehículo.")
            peticion = (tr("Analiza mi vehículo: lee las averías (si no están leídas o son antiguas), haz las "
                           "comprobaciones de valores medidos que consideres necesarias y dime qué pasa, causas "
                           "probables y qué hacer.") + "\n\n" + tr("Contexto actual de la aplicación:") + "\n"
                        + self._ai_context(incluir_log=False))
        else:
            visible = tr("Analiza los errores del programa y de la comunicación.")
            peticion = (tr("Analiza el registro de la aplicación: ¿hay errores de comunicación con el coche o el "
                           "adaptador? ¿Qué significan y cómo los soluciono?") + "\n\n"
                        + self._ai_context(incluir_log=True))
        self._ai_send(peticion, visible + "  " + tr("(datos adjuntos)"))

    def _ai_ask(self):
        texto = self.ai_entry.get().strip()
        if not texto or self.ai_busy:
            return
        self.ai_entry.delete(0, "end")
        if self.ai_chat is None or self.ai_chat.vacia():   # primer mensaje: adjunta el contexto actual
            peticion = (texto + "\n\n---\n" + tr("Contexto actual de la aplicación:") + "\n"
                        + self._ai_context(incluir_log=False))
        else:
            peticion = texto
        self._ai_send(peticion, texto)

    def _ai_send(self, peticion, visible):
        if self.ai_busy:
            return
        prov = self._ai_prov()
        clave = self.ai_key.get().strip() or ia.leer_clave(self.cfg, prov)
        if not clave:
            messagebox.showinfo(tr("Asistente IA"), tr("Introduce y guarda una API key para {proveedor}.",
                                                       proveedor=ia.PROVEEDORES[prov]["nombre"]))
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
        t.insert("end", ("\n" if t.index("end-1c") != "1.0" else "") + tr("TÚ") + "\n", "who")
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
                    return (tr("Cancelado por el usuario."), True)

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
                                         or tr("(registro vacío)"), False), conv)
        elif nombre == "consultar_historial":
            res = self._ai_main(lambda: self._ai_historial(entrada), conv)
        elif nombre == "generar_informe":
            res = self._ai_main(lambda reply: self._ai_informe(entrada, reply), conv, asincrono=True)
        elif nombre in ("leer_averias", "leer_valores", "borrar_averias", "grabar_valores") and self.act_en_curso:
            res = (tr("Ahora no se puede: el usuario está haciendo un test de actuadores o un ajuste básico. "
                  "Espera a que lo termine."),
                   True)
        elif nombre in ("leer_averias", "leer_valores", "borrar_averias", "grabar_valores"):
            if nombre == "borrar_averias":
                ok = self._ai_main(lambda: (messagebox.askyesno(
                    tr("Asistente IA"), tr("La IA quiere borrar las averías de la centralita para ver si reaparecen.")
                    + "\n\n" + tr("¿Lo permites? (motor parado, contacto puesto)")), False), conv)
                if ok[0] is not True:
                    res = (tr("El usuario no ha permitido borrar las averías."), False)
                    self.q.put(("ai_tool_res", (conv, res[0])))
                    return res
            reply = queue.Queue()
            self.worker.submit("tool", nombre, entrada, reply)
            res = self._ai_wait(reply, conv)
        else:
            res = (tr("Herramienta desconocida: {nombre}", nombre=nombre), True)
        resumen = res[0].strip().splitlines()[0] if res[0].strip() else ""
        if nombre == "pedir_accion_usuario" or res[1]:
            self.q.put(("ai_tool_res", (conv, resumen)))
        return res

    def _ai_tool_desc(self, nombre, e):
        if nombre == "leer_valores":
            els = e.get("elementos") or []
            if not isinstance(els, list):
                els = [els]
            n = e.get("muestras", 1)
            extra = tr(" · {n} muestras", n=n) if isinstance(n, int) and n > 1 else ""
            lista = ", ".join(str(x) for x in els)
            return (tr("Leyendo grupos {lista}", lista=lista) if self.mode == KKL
                    else tr("Leyendo PIDs {lista}", lista=lista)) + extra
        if nombre == "grabar_valores":
            els = e.get("elementos") or []
            lista = ", ".join(str(x) for x in (els if isinstance(els, list) else [els]))
            return tr("Grabando {lista} durante {s} s", lista=lista, s=e.get("segundos", 10))
        return {"estado_conexion": tr("Consultando el estado de la conexión"),
                "consultar_historial": tr("Consultando el historial del coche"),
                "generar_informe": tr("Generando el informe"),
                "leer_averias": tr("Leyendo averías"),
                "borrar_averias": tr("Solicitando borrar averías"),
                "leer_registro": tr("Leyendo el registro del programa"),
                "pedir_accion_usuario": tr("Esperando al usuario: ") + str(e.get("instruccion", ""))}.get(nombre, nombre)

    def _ai_estado(self):
        lineas = [tr("Modo de conexión: {modo}", modo=MODOS[self.mode]),
                  tr("Conectado: {estado}", estado=tr("sí") if self.connected else "no")]
        if self.connected:
            lineas += [f"{k}: {v}" for k, v in self.vehicle_fields]
            if self.mode == KKL:
                nombre, grupos, _ = MOTORES[self.motor]
                lineas.append(tr("Motor elegido para nombrar los grupos: {motor}", motor=tr(nombre)))
                lineas.append(tr("Grupos habituales: ") + ", ".join(
                    f"{g:03d} {t}" for g, (t, _) in grupos.items())
                    + tr(". Se pueden pedir otros números de grupo (1-255); si no existen, la centralita lo indica."))
            else:
                lineas.append(tr("PIDs soportados: ") + ", ".join(f"{p:02X} {PIDS[p][0]}" for p in self.supported))
            lineas.append(tr("Coche en el historial: {coche}", coche=f"{self.coche[1]} ({self.coche[0]})")
                          if self.coche else tr("Coche en el historial: sin identificar (no da VIN)"))
        else:
            lineas.append(tr("Para conectar, el usuario debe elegir Conexión y Puerto arriba y pulsar Conectar."))
        return "\n".join(lineas), False

    def _ai_dialog(self, instruccion, reply):
        """Ventana no modal con la instrucción de la IA; responde a reply cuando el usuario decide."""
        if self.ai_dialog is not None:
            self.ai_dialog[0].destroy()
        w = tk.Toplevel(self.root, bg=CARD)
        w.title(tr("El asistente necesita tu ayuda"))
        w.attributes("-topmost", True)
        w.resizable(False, False)
        _poner_icono(w)
        f = ttk.Frame(w, style="Card.TFrame", padding=20)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text=tr("✦ Acción solicitada por la IA"), style="Card.TLabel",
                  font=(FONT, 11, "bold"), foreground=ACCENT).pack(anchor="w")
        ttk.Label(f, text=instruccion, style="Card.TLabel", font=(FONT, 11),
                  wraplength=int(420 * self.s)).pack(anchor="w", pady=(10, 14))
        ttk.Label(f, text=tr("Comentario opcional (qué has visto, por qué no puedes…)"),
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
            reply.put((texto + (tr(". Comentario del usuario: {c}", c=c) if c else ""), False))
            w.destroy()
        ttk.Button(btns, text=tr("Hecho"), style="Accent.TButton",
                   command=lambda: responder(tr("Hecho"))).pack(side="right")
        ttk.Button(btns, text=tr("No puedo"),
                   command=lambda: responder(tr("El usuario no puede hacerlo"))).pack(side="right", padx=8)
        w.protocol("WM_DELETE_WINDOW", lambda: responder(tr("El usuario cerró la ventana sin hacerlo")))
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
            reply.put((tr("Cancelado por el usuario."), True))
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
        t.insert("end", tr("Asistente de diagnóstico") + "\n", "h")
        t.insert("end", tr("Describe abajo lo que le pasa al coche (p. ej. «le falta potencia por encima de 3000 rpm "
                           "y echa humo negro») y la IA hará las comprobaciones que necesite: leer averías, valores "
                           "medidos y pedirte que arranques, aceleres, etc.") + "\n\n"
                 + tr("También puedes pulsar «Analizar averías del vehículo», o «Analizar errores del programa» "
                      "si algo falla al conectar.") + "\n", "muted")

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
        t.insert("end", tr("Pensando…"), "muted")
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
            t.insert("end", "\n" + tr("Error: {e}", e=error) + "\n", "err")
        elif not ok:
            t.insert("end", "\n" + tr("(detenido: esta respuesta no se recordará en la conversación)") + "\n", "muted")
        t.see("end")
        self._ai_close_dialog()
        self._ai_set_busy(False)

    # ---------------- modo ----------------
    def _apply_mode(self):
        self.mode = next(k for k, v in MODOS.items() if v == self.mode_var.get())
        kkl = self.mode == KKL
        self.mod_cb.configure(state="readonly" if kkl else "disabled")
        self._panel_segun_motor()
        self.side_vag.pack_forget()
        self.side_obd.pack_forget()
        (self.side_vag if kkl else self.side_obd).pack(fill="both", expand=True, before=self.side_btns)
        self.side_title.configure(text=tr("Grupos a leer") if kkl else tr("PIDs a leer"))
        self.tree.heading("grupo", text=tr("GRUPO") if kkl else "PID")
        self.dtc_tree.heading("tipo", text=tr("TIPO DE FALLO") if kkl else tr("TIPO"))
        self.dtc_help.configure(
            text=tr("Intermitente = el fallo apareció pero no está presente ahora. "
                    "Si tras borrar vuelve a aparecer, la avería sigue activa.") if kkl else
                 tr("Pendiente = detectado una vez, aún sin confirmar. Al borrar se apaga el testigo MIL "
                    "y se reinician los monitores de emisiones (la ITV puede rechazarlo hasta completar ciclos)."))
        self.dtc_tree.delete(*self.dtc_tree.get_children())
        self.dtc_lbl.configure(text="")
        self.trayecto.reiniciar()
        self.crono = consumo.Cronometro()
        self.combustible_coche = None
        self.ch_cons.clear()
        self._cons_pintar()
        self._cons_texto()
        if kkl:
            self.scan_btn.pack(side="left", after=self.dtc_clear_btn)
            self.act_btn.pack(side="left", padx=(10, 0), after=self.scan_btn)
            self.ajustes_btn.pack(side="left", padx=(10, 0), after=self.act_btn)
            self.adapt_btn.pack(side="left", padx=(10, 0), after=self.ajustes_btn)
            self.ff_frame.pack_forget()
        else:
            self.scan_btn.pack_forget()
            self.act_btn.pack_forget()
            self.ajustes_btn.pack_forget()
            self.adapt_btn.pack_forget()
            self.ff_frame.pack(side="right", fill="y", padx=(14, 0))
        self._fill_ff(None)
        self.hist_lbl.configure(text="")
        self.coche = self.vag_motor = None
        self._fill_ecu([])
        self._fill_readiness(None)
        self.vehicle_fields, self.last_dtc_text, self.last_live_text = [], None, None
        self.last_dtcs = self.scan_result = None
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
        if self.mode == ELM:
            items.append(WIFI)
        items.append(SIM)
        self.port_cb["values"] = items
        self.port_cb.configure(state=self._port_state())
        cur = self.port_var.get()
        prefer = ftdi if self.mode == KKL else (bt or ftdi)
        escrito = self.mode == ELM and wifi_destino(cur)      # dirección WiFi escrita a mano
        self.port_var.set(cur if (cur in items and cur != SIM) or escrito else (prefer or items[0]))

    def _port_state(self):
        """En OBD2 el puerto se puede escribir (dirección de un ELM327 WiFi)."""
        return "normal" if self.mode == ELM else "readonly"

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
        for b in (self.panel_btn, self.cons_btn, self.vals_btn, self.rec_btn, self.dtc_read_btn, self.dtc_clear_btn,
                  self.scan_btn, self.act_btn, self.ajustes_btn, self.adapt_btn, self.report_btn):
            b.configure(state=state)
        self.port_cb.configure(state="disabled" if on else self._port_state())
        self.mode_cb.configure(state="disabled" if on else "readonly")
        self.mod_cb.configure(state="disabled" if on or self.mode != KKL else "readonly")
        self.refresh_btn.configure(state="disabled" if on else "normal")
        if not on:
            self.scanning = False
            self.scan_btn.configure(text=tr("Escanear todos los módulos"), style="TButton")
        self.conn_btn.configure(text=tr("Desconectar") if on else tr("Conectar"),
                                style="TButton" if on else "Accent.TButton", state="normal")
        if on:
            self.status(info["status"], OK)
        else:
            self.status(tr("Desconectado"), MUTED)
            self._stop_live()
            self._stop_rec()
            for v in (self.ventana_act, self.ventana_ajustes, self.ventana_adapt):
                if v:
                    v.perdida()
        self._cons_texto()

    def _key_label(self, k):
        if isinstance(k, str):
            return k
        return f"{k:03d}" if self.mode == KKL else f"{k:02X}h"

    # ---------------- acciones ----------------
    def toggle_connect(self):
        if self.connected:
            self.worker.submit("disconnect")
            return
        port = self.port_var.get().strip()
        if self.mode == ELM and wifi_destino(port):
            port = "{}:{}".format(*wifi_destino(port))
        elif port != SIM:
            port = port.split(" · ")[0]
        addr = int(self.mod_var.get().split(" · ")[0], 16)
        self.conn_btn.configure(state="disabled")
        self.mode_cb.configure(state="disabled")
        if self.mode == KKL:
            self.status(tr("Conectando... (init 5 baudios)"), WARN)
            self.bar.configure(text=tr("Conectando: puede tardar hasta 6 s mientras prueba las velocidades."))
        else:
            self.status(tr("Conectando con el ELM327..."), WARN)
            self.bar.configure(text=tr("Conectando: la búsqueda del protocolo OBD2 puede tardar hasta 25 s."))
        self.worker.submit("connect", self.mode, port, addr)

    def _kkl_gasolina(self):
        return self.mode == KKL and self.motor == "gasolina"

    def _panel_groups(self):
        return PANEL_GROUPS_GASOLINA if self.motor == "gasolina" else PANEL_GROUPS

    def _panel_segun_motor(self):
        """Panel y ajustes de consumo según el modo y, en KKL, el tipo de motor."""
        kkl = self.mode == KKL
        for f in (self.panel_vag, self.panel_gas, self.panel_obd):
            f.pack_forget()
        (self.panel_obd if not kkl else self.panel_gas if self.motor == "gasolina" else self.panel_vag).pack(
            fill="both", expand=True)
        self.panel_lbl.configure(
            text=tr("Lectura en vivo de los grupos {lista}", lista=" · ".join(f"{g:03d}" for g in self._panel_groups()))
            if kkl else tr("Lectura en vivo de PIDs OBD2 estándar"))
        g1 = MOTORES[self.motor][1].get(1, (None, []))[1]
        self.vag_stats_lbl["volt"].configure(text=tr(g1[2]) if self.motor == "pd" and len(g1) > 2
                                             else tr("Tensión dosificador"))
        for w in (self.comb_lbl, self.comb_cb, self.cil_lbl, self.cil_entry, self.ncil_lbl, self.ncil_entry):
            w.pack_forget()
        visibles = ((self.cil_lbl, self.cil_entry) if self._kkl_gasolina() else
                    (self.ncil_lbl, self.ncil_entry) if kkl else
                    (self.comb_lbl, self.comb_cb, self.cil_lbl, self.cil_entry))
        for w in visibles:
            w.pack(side="left", padx=(0, 6) if isinstance(w, ttk.Label) else (0, 14))
        self._cons_texto()

    def _poner_motor(self, motor):
        """Elige el tipo de motor VAG: casillas de sus grupos y nombres de los campos."""
        nombre, grupos, defecto = MOTORES[motor]
        cambia = motor != getattr(self, "_motor_casillas", None)
        self.motor = motor
        self.motor_var.set(tr(nombre))
        self.worker.grupos = grupos
        if not cambia:
            return
        if self.live_source in ("panel", "cons"):           # los grupos que se leen cambian
            self._stop_live()
        if hasattr(self, "mode"):                          # (al construir la ventana lo hace _apply_mode)
            self._panel_segun_motor()
        self._motor_casillas = motor
        for w in self.grupos_frame.winfo_children():
            w.destroy()
        self.group_vars = {}
        for g, (t, _) in grupos.items():
            v = tk.BooleanVar(value=g in defecto)
            ttk.Checkbutton(self.grupos_frame, text=f"{g:03d}  {t}", variable=v).pack(anchor="w", pady=2)
            self.group_vars[g] = v

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
            items = self._panel_groups() if self.mode == KKL else [p for p in PANEL_PIDS if p in self.supported]
        elif source == "cons":
            self._cons_guardar()
            items = self._cons_items()
            if not items:
                messagebox.showinfo(tr("Consumo y 0-100"), self.cons_lbl.cget("text"))
                return
        else:
            items = self._selected_items()
        if not items:
            messagebox.showinfo(tr("Valores medidos"), tr("Selecciona al menos un grupo o PID."))
            return
        self._stop_rec()
        self.live_source = source
        self.live_gen += 1
        self.worker.submit("live", items, self.live_gen)
        self.panel_btn.configure(text=tr("■  Detener") if source == "panel" else tr("▶  Iniciar lectura"))
        self.vals_btn.configure(text=tr("■  Detener") if source == "vals" else tr("▶  Iniciar lectura"))
        self.cons_btn.configure(text=tr("■  Detener") if source == "cons" else tr("▶  Iniciar lectura"))
        if source == "cons":
            self.cons_muestras.clear()
            self._cons_pintar()
        elif source == "panel":
            for c in (self.ch_boost, self.ch_maf, self.ch_rpm, self.ch_load):
                c.clear()
        else:
            self.tree.delete(*self.tree.get_children())
            self.tree_items = {}
            self.vals_hist, self.vals_nombres = {}, {}
            self._vals_grafica()
        self.bar.configure(text=tr("Leyendo {lista}", lista=", ".join(self._key_label(k) for k in items)))

    def _stop_live(self):
        self.live_gen += 1
        if self.live_source:
            self.worker.submit("live", None, self.live_gen)
        self.live_source = None
        self.panel_btn.configure(text=tr("▶  Iniciar lectura"))
        self.vals_btn.configure(text=tr("▶  Iniciar lectura"))
        self.cons_btn.configure(text=tr("▶  Iniciar lectura"))
        self._stop_rec()
        self._cons_pintar()

    def toggle_rec(self):
        if self.csv_file:
            self._stop_rec()
            return
        if self.live_source != "vals":
            self.toggle_live("vals")
            if self.live_source != "vals":
                return
        name = os.path.join(CARPETA, f"log_{datetime.datetime.now():%Y%m%d_%H%M%S}.csv")
        try:
            os.makedirs(CARPETA, exist_ok=True)
            self.csv_file = open(name, "w", newline="", encoding="utf-8-sig")
        except OSError as e:
            messagebox.showerror(tr("Grabar CSV"), tr("No se pudo crear el archivo:") + f"\n{e}")
            return
        self.csv_writer = csv.writer(self.csv_file, delimiter=";")
        self.csv_header = None
        self.csv_n = 0
        self.csv_t0 = time.monotonic()
        self.rec_btn.configure(text=tr("■  Parar grabación"), style="Danger.TButton")
        self.rec_lbl.configure(text=tr("Grabando en {archivo}", archivo=os.path.basename(name)))
        self.log(tr("Grabando CSV: {archivo}", archivo=name))

    def _stop_rec(self):
        if not self.csv_file:
            return
        name = self.csv_file.name
        self.csv_file.close()
        self.csv_file = self.csv_writer = None
        self.rec_btn.configure(text=tr("●  Grabar CSV"), style="TButton")
        self.rec_lbl.configure(text=tr("Guardadas {n} muestras en {archivo}", n=self.csv_n, archivo=os.path.basename(name)))
        self.log(tr("CSV guardado ({n} muestras): {archivo}", n=self.csv_n, archivo=name))

    def read_dtcs(self):
        self.dtc_lbl.configure(text=tr("Leyendo..."), foreground=FG)
        self.worker.submit("dtcs")

    def clear_dtcs(self):
        if messagebox.askyesno(tr("Borrar averías"),
                               tr("¿Borrar las averías memorizadas en la centralita?") + "\n\n"
                               + tr("Hazlo con el motor parado y el contacto puesto.")):
            self.dtc_lbl.configure(text=tr("Borrando..."), foreground=FG)
            self.worker.submit("clear")

    def test_actuadores(self):
        if self.ventana_act and self.ventana_act.win.winfo_exists():
            self.ventana_act.win.lift()
            return
        self._stop_live()
        self.ventana_act = VentanaActuadores(self)

    def ajustes_basicos(self):
        if self.ventana_ajustes and self.ventana_ajustes.win.winfo_exists():
            self.ventana_ajustes.win.lift()
            return
        self._stop_live()
        self.ventana_ajustes = VentanaAjustes(self)

    def adaptacion(self):
        if self.ventana_adapt and self.ventana_adapt.win.winfo_exists():
            self.ventana_adapt.win.lift()
            return
        self._stop_live()
        self.ventana_adapt = VentanaAdaptacion(self)

    def _kkl_identificado(self, info):
        """Identificación de la centralita KKL: al conectar y tras cambiar la codificación."""
        self.kkl_ident = info.get("ident") or []
        self.kkl_codificacion = info.get("codificacion")
        self._fill_ecu(info["fields"])
        self.vehicle_fields = info["fields"]

    def scan_modules(self, direcciones=None, confirmar=True):
        if self.scanning:
            self.worker.scan_stop.set()
            self.scan_btn.configure(state="disabled", text=tr("Deteniendo..."))
            return
        direcciones = direcciones or list(MODULOS)
        if confirmar and not messagebox.askyesno(
                tr("Escanear todos los módulos"),
                tr("Se prueban {n} módulos uno a uno y se leen sus averías (no se borra nada).", n=len(direcciones))
                + "\n\n" + tr("Tarda de 1 a 4 minutos según cuántos tenga el coche. Pon el contacto con el motor "
                               "parado. Puedes detenerlo en cualquier momento.")):
            return
        self._stop_live()
        self.scanning = True
        for b in (self.panel_btn, self.cons_btn, self.vals_btn, self.rec_btn, self.dtc_read_btn, self.dtc_clear_btn,
                  self.act_btn, self.ajustes_btn, self.adapt_btn, self.report_btn, self.conn_btn):
            b.configure(state="disabled")
        self.scan_btn.configure(text=tr("■  Detener escaneo"), style="Danger.TButton")
        self.dtc_tree.delete(*self.dtc_tree.get_children())
        self.dtc_lbl.configure(text=tr("Escaneando..."), foreground=FG)
        self.worker.submit("scan", direcciones)

    def _show_scan(self, res):
        t = self.dtc_tree
        t.delete(*t.get_children())
        resp = [m for m in res if m["ok"]]
        total = 0
        for m in resp:
            ident = "  ·  ".join(x.strip() for x in m["ident"][:2] if x.strip())
            n = len(m["dtcs"]) if m["dtcs"] is not None else None
            total += n or 0
            t.insert("", "end", values=(f"[{m['addr']:02X}]", f"{MODULOS.get(m['addr'], tr('Módulo'))}  —  {ident}",
                                        "", tr("Error al leer") if n is None else
                                        (tr("Sin averías") if not n else tr("{n} avería(s)", n=n))), tags=("mod",))
            for code, ftype, inter in m["dtcs"] or []:
                tipo = f"{ftype:02d} · {FAULT_TYPES.get(ftype, tr('Desconocido')) or '—'}"
                t.insert("", "end", values=(f"   {code:05d}", vag_componente(code), tipo,
                                            tr("Intermitente") if inter else tr("Presente")),
                         tags=("inter",) if inter else ())
        txt = tr("Responden {n} de {total} módulos · {averias} avería(s)", n=len(resp), total=len(res), averias=total)
        self.dtc_lbl.configure(text=txt, foreground=WARN if total else OK)
        filas = [" — ".join(str(v).strip() for v in t.item(i, "values") if str(v).strip()) for i in t.get_children()]
        sin = ", ".join(f"{m['addr']:02X}" for m in res if not m["ok"])
        self.last_dtc_text = (tr("Escaneo de módulos VAG a las {hora}.", hora=f"{datetime.datetime.now():%H:%M:%S}")
                              + f" {txt}\n" + "\n".join(f"- {f}" for f in filas)
                              + ("\n" + tr("Sin respuesta: {lista}", lista=sin) if sin else ""))
        self.scan_result = res

    # ---------------- historial por coche ----------------
    def _identificar_coche(self, info):
        """(id, nombre) del coche para el historial: VIN, calibración o centralita de motor VAG."""
        if info.get("mode") == ELM:
            vin = info.get("vin")
            if vin:
                d = dict(decodificar_vin(vin))
                modelo = (d.get(tr("Modelo (código VAG)")) or "").split(" · ")[-1]
                fab = d.get(tr("Fabricante")) or ""
                anio = (d.get(tr("Año modelo")) or "").split(" ")[0]
                partes = [modelo if fab and modelo.startswith(fab) else " ".join(x for x in (fab, modelo) if x), anio]
                return vin, " · ".join(x for x in partes if x) or vin
            if info.get("calid"):
                cal = info["calid"][0]
                return f"CALID-{cal}", tr("Coche sin VIN (calibración {cal})", cal=cal)
            return None
        ident = info.get("ident") or []
        vin = historial.buscar_vin(ident)
        if vin:
            return vin, f"VAG · {vin}"
        addr = info.get("addr")
        if addr == 0x01 and ident:
            self.vag_motor = (f"VAG-{ident[0]}", "VAG · " + "  ".join(ident[:2]))
            return self.vag_motor
        if self.vag_motor:
            return self.vag_motor
        if ident:
            return f"VAG-{addr:02X}-{ident[0]}", f"VAG · {MODULOS.get(addr, addr)} · {ident[0]}"
        return None

    @staticmethod
    def _fecha_txt(iso):
        try:
            return datetime.datetime.fromisoformat(iso).strftime(tr("%d/%m/%Y %H:%M"))
        except (TypeError, ValueError):
            return iso or ""

    @staticmethod
    def _estado_txt(e):
        return {"presente": tr("Presente"), "intermitente": tr("Intermitente"), "memorizada": tr("Memorizada"),
                "pendiente": tr("Pendiente"), "permanente": tr("Permanente")}.get(e, e)

    @staticmethod
    def _tipo_txt(t):
        return {"lectura": tr("Lectura de averías"), "borrado": tr("Borrado de averías"),
                "escaneo": tr("Escaneo de módulos")}.get(t, t)

    def _registro(self, tipo, payload):
        """Registro del historial a partir de lo que devuelve el hilo de comunicación."""
        vag = lambda addr, code, inter: {"modulo": addr, "codigo": f"{code:05d}", "texto": vag_componente(code),
                                         "estado": "intermitente" if inter else "presente"}
        if tipo == "escaneo":
            leidos = [m for m in payload if m["ok"] and m["dtcs"] is not None]
            return {"tipo": tipo, "modulos": [m["addr"] for m in leidos], "mil": None,
                    "averias": [vag(m["addr"], c, i) for m in leidos for c, _, i in m["dtcs"]]}
        if self.mode == KKL:
            addr = int(self.mod_var.get().split(" · ")[0], 16)
            return {"tipo": tipo, "modulos": [addr], "mil": None, "averias": [vag(addr, c, i) for c, _, i in payload]}
        averias = [{"modulo": 0, "codigo": c, "texto": describe_obd_dtc(c), "estado": estado}
                   for clave, estado in (("stored", "memorizada"), ("pending", "pendiente"), ("permanent", "permanente"))
                   for c in payload.get(clave) or []]
        return {"tipo": tipo, "modulos": [0], "mil": payload.get("mil"), "averias": averias}

    def _hist_guardar(self, tipo, payload):
        if tipo == "escaneo" and not historial.buscar_vin([x for m in payload if m["ok"] for x in m["ident"]]):
            motor = next((m for m in payload if m["ok"] and m["addr"] == 0x01 and m["ident"]), None)
            if motor:                              # el escaneo dice cuál es la centralita de motor
                ident = [x.strip() for x in motor["ident"] if x.strip()]
                self.vag_motor = self.coche = (f"VAG-{ident[0]}", "VAG · " + "  ".join(ident[:2]))
        if not self.coche:
            self.hist_lbl.configure(text=tr("Historial: el coche no da el VIN ni otra identificación, así que "
                                            "esta lectura no se guarda."))
            return
        try:
            reg, ant = self.historial.guardar(*self.coche, self._registro(tipo, payload))
        except OSError as e:
            self.log(tr("Aviso: no se pudo guardar en el historial ({e})", e=e))
            return
        if ant is None:
            txt = tr("Guardado en el historial de {coche}. Aún no hay un diagnóstico anterior con el que compararlo.",
                     coche=self.coche[1])
        else:
            c = historial.comparar(ant, reg)
            lista = lambda xs: ", ".join(x["codigo"] for x in xs[:6]) + (" …" if len(xs) > 6 else "")
            partes = []
            if c["nuevas"]:
                partes.append(tr("{n} nueva(s): {lista}", n=len(c["nuevas"]), lista=lista(c["nuevas"])))
            if c["resueltas"]:
                partes.append(tr("{n} ya no aparece(n): {lista}", n=len(c["resueltas"]), lista=lista(c["resueltas"])))
            if c["repetidas"]:
                partes.append(tr("{n} se repite(n): {lista}", n=len(c["repetidas"]), lista=lista(c["repetidas"])))
            txt = (tr("Comparado con el diagnóstico del {fecha} ({tipo}):", fecha=self._fecha_txt(ant["fecha"]),
                      tipo=self._tipo_txt(ant["tipo"]).lower()) + " "
                   + (" · ".join(partes) if partes else tr("sin averías entonces ni ahora.")))
        self.hist_lbl.configure(text=txt)
        if self.last_dtc_text and ant is not None:
            self.last_dtc_text += "\n" + txt
        if self.ventana_historial and self.ventana_historial.win.winfo_exists():
            self.ventana_historial.recargar(self.coche[0])

    def ver_historial(self):
        if self.ventana_historial and self.ventana_historial.win.winfo_exists():
            self.ventana_historial.recargar(self.coche[0] if self.coche else None)
            self.ventana_historial.win.lift()
        else:
            self.ventana_historial = VentanaHistorial(self)
        return self.ventana_historial

    def _ai_historial(self, e):
        try:
            n = max(1, min(30, int(e.get("registros") or 10)))
        except (TypeError, ValueError):
            n = 10
        coches = self.historial.coches()
        ident = str(e.get("coche") or "").strip() or (self.coche[0] if self.coche else "")
        lista = "\n".join(f"- {i} · {nom} · " + tr("{n} diagnóstico(s)", n=k) + " · " + tr("último: {fecha}",
                          fecha=self._fecha_txt(f)) for i, nom, k, f in coches) or tr("(ninguno)")
        if not ident:
            return (tr("No hay un coche conectado e identificado. Coches con historial:") + "\n" + lista
                    + "\n" + tr("Puedes pedir uno con el parámetro 'coche'."), False)
        d = self.historial.cargar(ident)
        regs = d["registros"]
        if not regs:
            return (tr("Todavía no hay diagnósticos guardados de este coche ({coche}).", coche=ident)
                    + "\n" + tr("Coches con historial:") + "\n" + lista, False)
        inicio = max(0, len(regs) - n)
        out = [tr("Historial de {nombre} ({id}): {total} diagnóstico(s) guardado(s); se muestran los {n} últimos, "
                  "del más antiguo al más reciente.", nombre=d.get("nombre", ident), id=ident, total=len(regs),
                  n=len(regs) - inicio)]
        for j in range(inicio, len(regs)):
            r = regs[j]
            mods = ", ".join(f"{m:02X}" for m in r["modulos"] if m)
            cab = f"- {self._fecha_txt(r['fecha'])} · {self._tipo_txt(r['tipo'])}"
            if mods:
                cab += " · " + tr("módulos {lista}", lista=mods)
            if r.get("mil") is not None:
                cab += " · " + (tr("testigo MIL ENCENDIDO") if r["mil"] else tr("testigo MIL apagado"))
            averias = "; ".join((f"[{a['modulo']:02X}] " if a.get("modulo") else "") + f"{a['codigo']} "
                                f"({self._estado_txt(a['estado'])}) {a['texto']}" for a in r["averias"])
            out.append(cab + ": " + (averias or tr("sin averías")))
            ant = historial.anterior(regs, j)
            if ant is not None:
                c = historial.comparar(ant, r)
                cods = lambda xs: ", ".join(x["codigo"] for x in xs) or "—"
                out.append("  " + tr("Frente al anterior: nuevas {a}; ya no aparecen {b}; se repiten {c}",
                                     a=cods(c["nuevas"]), b=cods(c["resueltas"]), c=cods(c["repetidas"])))
        return "\n".join(out), False

    def _ai_informe(self, e, reply):
        if not self.connected:
            reply.put((tr("No hay conexión con el vehículo. Pide al usuario que conecte "
                          "(selector Conexión, Puerto y botón Conectar)."), True))
            return
        self.informe_ia = {"texto": str(e.get("diagnostico") or "").strip(), "reply": reply}
        self.make_report()

    def make_report(self):
        self.report_btn.configure(state="disabled")
        self.bar.configure(text=tr("Leyendo averías para el informe..."))
        self.worker.submit("report")

    def _save_report(self, d):
        self.report_btn.configure(state="normal" if self.connected else "disabled")
        ia_pend, self.informe_ia = self.informe_ia, None
        hist = str(self.hist_lbl.cget("text"))
        datos = {"modo": self.mode, "version": VERSION, "vehiculo": self.vehicle_fields,
                 "dtcs": d["dtcs"], "modulo": d.get("modulo", 1), "escaneo": self.scan_result,
                 "historial": hist if self.coche and hist else None,
                 "diagnostico_ia": ia_pend["texto"] if ia_pend else None}
        name = os.path.join(CARPETA, tr("informe") + f"_{datetime.datetime.now():%Y%m%d_%H%M%S}.html")
        try:
            os.makedirs(CARPETA, exist_ok=True)
            with open(name, "w", encoding="utf-8") as f:
                f.write(informe.generar(datos))
        except OSError as e:
            if ia_pend:
                ia_pend["reply"].put((tr("No se pudo crear el archivo:") + f" {e}", True))
                return
            messagebox.showerror(tr("Generar informe"), tr("No se pudo crear el archivo:") + f"\n{e}")
            return
        self.last_report = name
        if ia_pend:
            ia_pend["reply"].put((tr("Informe guardado en {archivo} y abierto en el navegador.", archivo=name), False))
        self.log(tr("Informe guardado: {archivo}", archivo=name))
        self.bar.configure(text=tr("Informe guardado en {archivo} (se abre en el navegador; desde ahí puedes "
                                   "imprimirlo o guardarlo como PDF).", archivo=name))
        try:
            import pathlib
            webbrowser.open(pathlib.Path(name).resolve().as_uri())
        except Exception as e:
            self.log(tr("Aviso: no se pudo abrir el navegador ({e})", e=e))

    def _fill_ff(self, ff):
        self.ff_tree.delete(*self.ff_tree.get_children())
        if not ff:
            self.ff_lbl.configure(text=tr("Datos congelados: ninguno guardado"))
            return
        self.ff_lbl.configure(text=tr("Datos congelados · {dtc} ({desc})", dtc=ff["dtc"], desc=describe_obd_dtc(ff["dtc"])))
        for _, nombre, valor, unidad in ff["values"]:
            self.ff_tree.insert("", "end", values=(nombre, f"{valor} {unidad}".strip()))

    def _show_dtcs(self, payload, after_clear=False):
        t = self.dtc_tree
        t.delete(*t.get_children())
        if self.mode == KKL:
            for code, ftype, inter in payload:
                comp = vag_componente(code)
                tipo = f"{ftype:02d} · {FAULT_TYPES.get(ftype, tr('Desconocido')) or '—'}"
                tag = "inter" if inter else ("fixed" if after_clear else "")
                t.insert("", "end", values=(f"{code:05d}", comp, tipo,
                                            tr("Intermitente") if inter else tr("Presente")), tags=(tag,))
            n = len(payload)
            if not n:
                txt, color = (tr("Averías borradas · no queda ninguna") if after_clear
                              else tr("Sin averías memorizadas")), OK
            elif after_clear:
                txt, color = tr("{n} avería(s) siguen presentes tras borrar", n=n), ERR
            else:
                txt, color = tr("{n} avería(s) memorizada(s)", n=n), WARN
        else:
            for clave, estado, codes in (("stored", tr("Memorizada"), payload["stored"]),
                                         ("pending", tr("Pendiente"), payload["pending"]),
                                         ("permanent", tr("Permanente"), payload.get("permanent") or [])):
                for code in codes:
                    tipo = tr("Genérico (SAE)") if code[1] in "02" else tr("Específico del fabricante")
                    tag = {"pending": "inter", "permanent": "perm"}.get(clave, "fixed" if after_clear else "")
                    t.insert("", "end", values=(code, describe_obd_dtc(code), tipo, estado), tags=(tag,))
            self._fill_ff(payload.get("ff"))
            if "readiness" in payload:
                self._fill_readiness(payload["readiness"])
            ns, npend, mil = len(payload["stored"]), len(payload["pending"]), payload["mil"]
            mil_txt = tr("testigo MIL ENCENDIDO") if mil else tr("testigo MIL apagado")
            if not ns and not npend:
                txt = (tr("Averías borradas · ") if after_clear else tr("Sin averías · ")) + mil_txt
                color = OK
            else:
                txt = tr("{ns} memorizada(s) · {np} pendiente(s) · {mil}", ns=ns, np=npend, mil=mil_txt)
                color = ERR if after_clear or mil else WARN
        self.dtc_lbl.configure(text=txt, foreground=color)
        # Contexto para el asistente IA
        filas = [" — ".join(str(v) for v in t.item(i, "values")) for i in t.get_children()]
        cab = (tr("Leídas a las {hora}", hora=f"{datetime.datetime.now():%H:%M:%S}")
               + (tr(" (justo después de borrar)") if after_clear else ""))
        self.last_dtc_text = cab + ". " + txt + "\n" + "\n".join(f"- {f}" for f in filas)
        if self.mode == ELM:
            self.last_dtc_text += f"\n{texto_ff(payload.get('ff'))}\n{texto_readiness(payload.get('readiness'))}"
        self.last_dtcs = payload

    def _live_to_text(self, data):
        lineas = []
        for k, rows in data.items():
            etiqueta = (f"G{k:03d}" if self.mode == KKL else f"PID {k:02X}h") if isinstance(k, int) else k
            if isinstance(rows, str):
                lineas.append(f"- {etiqueta}: {rows}")
                continue
            for nombre, valor, unidad, ok in rows:
                lineas.append(f"- {etiqueta} {nombre}: {valor} {unidad}".rstrip() + ("" if ok else tr(" (fórmula desconocida)")))
        return tr("Leídos a las {hora}", hora=f"{datetime.datetime.now():%H:%M:%S}") + "\n" + "\n".join(lineas)

    # ---------------- datos en vivo ----------------
    def _chart_add(self, t, data):
        if self._kkl_gasolina():
            g2, g3 = rows_of(data, 2), rows_of(data, 3)
            if g2:
                self.ch_grpm.add(t, {"RPM": num(g2, 0)})
            if g2 or g3:
                self.ch_gload.add(t, {tr("Carga"): num(g2, 1), tr("Mariposa"): num(g3, 2)})
        elif self.mode == KKL:
            g3, g11 = rows_of(data, 3), rows_of(data, 11)
            if g11:
                self.ch_boost.add(t, {tr("Teórica"): num(g11, 1), tr("Real"): num(g11, 2)})
            if g3:
                self.ch_maf.add(t, {tr("Teórica"): num(g3, 1), tr("Real"): num(g3, 2)})
        else:
            self.ch_rpm.add(t, {"RPM": num(rows_of(data, 0x0C))})
            self.ch_load.add(t, {tr("Carga"): num(rows_of(data, 0x04)), tr("Mariposa"): num(rows_of(data, 0x11))})

    def _update_panel(self, data):
        def fmt(rows, i=0):
            try:
                return f"{rows[i][1]} {rows[i][2]}"
            except IndexError:
                return "--"
        if self._kkl_gasolina():
            g2, g3, g4 = rows_of(data, 2), rows_of(data, 3), rows_of(data, 4)
            self.gg_rpm.set(num(g2, 0) if g2 else num(g3, 0))
            self.gg_load.set(num(g2, 1))
            self.gg_temp.set(num(g4, 2))
            self.gg_iat.set(num(g4, 3))
            self.gas_stats["iny"].set(fmt(g2, 2))
            self.gas_stats["aire"].set(fmt(g2, 3))
            self.gas_stats["mar"].set(fmt(g3, 2))
            self.gas_stats["avance"].set(fmt(g3, 3))
            self.gas_stats["volt"].set(fmt(g4, 1))
            self.ch_grpm.redraw()
            self.ch_gload.redraw()
        elif self.mode == KKL:
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

    def _vals_hist_add(self, t, data):
        for k, rows in data.items():
            if isinstance(rows, str):
                continue
            for i, (nombre, valor, unidad, _) in enumerate(rows):
                try:
                    v = float(valor)
                except ValueError:
                    continue
                d = self.vals_hist.setdefault((k, i), deque())
                d.append((t, v))
                while d and d[0][0] < t - 65:
                    d.popleft()
                self.vals_nombres[(k, i)] = (nombre, unidad)
        series = {name for name, _ in self.ch_vals.series}
        if series:
            self.ch_vals.add(t, {self.vals_serie[c]: d[-1][1] for c, d in self.vals_hist.items()
                                 if c in self.vals_serie and d and d[-1][0] == t and self.vals_serie[c] in series})

    def _vals_grafica(self):
        """Gráfica en vivo de las filas elegidas en la tabla (hasta 4)."""
        por_iid = {iid: c for c, iid in self.tree_items.items() if c[1] != "err"}
        elegidas = [por_iid[i] for i in self.tree.selection() if i in por_iid][:4]
        nombres = [self.vals_nombres.get(c, (self.tree.set(self.tree_items[c], "campo"),
                                             self.tree.set(self.tree_items[c], "unidad"))) for c in elegidas]
        repetidos = {n for n, _ in nombres if [x for x, _ in nombres].count(n) > 1}
        self.vals_serie = {}
        series, datos = [], {}
        for c, (n, u), color in zip(elegidas, nombres, COLORES_SERIE):
            etiqueta = f"{self._key_label(c[0])} {n}" if n in repetidos else n
            self.vals_serie[c] = etiqueta
            series.append((etiqueta, color))
            datos[etiqueta] = list(self.vals_hist.get(c, ()))
        unidades = " · ".join(dict.fromkeys(u for _, u in nombres if u))
        titulo = nombres[0][0] if len(nombres) == 1 else tr("{n} valores", n=len(nombres))
        self.ch_vals.configurar(titulo if nombres else "", unidades, series, datos)

    # ---------------- visor de CSV ----------------
    def abrir_csv(self, ruta=None):
        if ruta is None:
            ruta = filedialog.askopenfilename(
                parent=self.root, title=tr("Abrir grabación CSV"),
                initialdir=CARPETA if os.path.isdir(CARPETA) else os.path.expanduser("~"),
                filetypes=[(tr("Archivos CSV"), "*.csv"), (tr("Todos los archivos"), "*")])
            if not ruta:
                return None
        try:
            datos = csv_datos.leer(ruta)
        except (OSError, UnicodeDecodeError, ValueError) as e:
            messagebox.showerror(tr("Abrir CSV"), tr("No se pudo abrir {archivo}:", archivo=os.path.basename(ruta))
                                 + f"\n{e}", parent=self.root)
            return None
        v = VisorCSV(self, ruta, datos)
        self.visores = [x for x in self.visores if x.win.winfo_exists()] + [v]
        self.log(tr("Abierto en el visor: {archivo}", archivo=ruta))
        return v

    def _write_csv(self, data):
        if any(isinstance(v, str) for v in data.values()):
            return
        if self.csv_header is None:
            self.csv_header = cabecera_csv(self.mode, data)
            self.csv_writer.writerow(self.csv_header)
        self.csv_writer.writerow(fila_csv(time.monotonic() - self.csv_t0, data))
        self.csv_n += 1
        if self.csv_n % 10 == 0:
            self.csv_file.flush()
            self.rec_lbl.configure(text=tr("Grabando · {n} muestras", n=self.csv_n))

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
                    if self.live_source == "vals":
                        if self.csv_writer:
                            self._write_csv(data)
                        self._vals_hist_add(t, data)
                    elif self.live_source == "panel":
                        self._chart_add(t, data)
                    elif self.live_source == "cons":
                        self._cons_muestra(t, data)
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
                self.ch_vals.redraw()
            elif self.live_source == "cons":
                self._cons_pintar()
        self.root.after(50, self.poll)

    def _fill_pid_list(self, pids):
        self.pid_list.delete(0, "end")
        self.pid_order = list(pids)
        for i, p in enumerate(pids):
            self.pid_list.insert("end", f"  {p:02X}h   {PIDS[p][0]}")
            if p in PANEL_PIDS:
                self.pid_list.selection_set(i)
        if not pids:
            self.pid_list.insert("end", "  " + tr("(el vehículo no ofrece PIDs legibles)"))

    def _handle(self, kind, payload):
        if kind == "log":
            self.log(payload)
        elif kind == "connected":
            self.supported = payload.get("supported", [])
            self.coche = self._identificar_coche(payload)
            self.combustible_coche = payload.get("combustible")
            if self.combustible_coche:
                self.comb_var.set(self._nombre_comb(self.combustible_coche))
            if payload["mode"] == ELM:
                self._fill_pid_list(self.supported)
            elif payload.get("motor"):
                self._poner_motor(payload["motor"])
            self._set_connected(True, payload)
            if payload["mode"] == KKL:
                self._kkl_identificado(payload)
            self._fill_ecu(payload["fields"])
            self._fill_readiness(payload.get("readiness"))
            self.vehicle_fields = payload["fields"]
            self.bar.configure(text=tr("Conectado: {titulo}", titulo=payload.get("title", "")))
        elif kind == "act":
            if self.ventana_act:
                self.ventana_act.respuesta(payload)
        elif kind == "basic":
            if self.ventana_ajustes:
                self.ventana_ajustes.respuesta(payload)
        elif kind == "adapt":
            if self.ventana_adapt:
                self.ventana_adapt.respuesta(payload)
        elif kind == "disconnected":
            self._set_connected(False)
            self.bar.configure(text=tr("Desconectado."))
            if self.reiniciar:
                self.worker.submit("quit")             # cambio de idioma: se reconstruye la ventana
        elif kind == "lost":
            self._set_connected(False)
            self.status(tr("Conexión perdida"), ERR)
            self.bar.configure(text=tr("Conexión perdida: {motivo}. Pulsa Conectar para reintentar.", motivo=payload))
            self.log(tr("Error: conexión perdida ({motivo})", motivo=payload))
        elif kind == "error":
            if self.informe_ia:                         # el informe que pidió la IA no se pudo hacer
                self.informe_ia["reply"].put((tr("Error: {e}", e=payload), True))
                self.informe_ia = None
                self.report_btn.configure(state="normal" if self.connected else "disabled")
            if not self.connected:
                self._set_connected(False)
                self.status(tr("Error de conexión"), ERR)
                if self.mode == KKL:
                    ayuda = tr("Revisa: contacto puesto, puerto {puerto}, cable FTDI y que la radio no bloquee la línea K.",
                               puerto="COM" if WINDOWS else "(/dev/ttyUSB0)")
                elif WINDOWS:
                    ayuda = tr("Revisa: contacto puesto y puerto COM. Si el ELM327 es Bluetooth, "
                               "Windows crea dos puertos COM: prueba el otro.")
                else:
                    ayuda = tr("Revisa: contacto puesto y puerto. Un ELM327 Bluetooth debe estar enlazado "
                               "como /dev/rfcomm0 (sudo rfcomm bind 0 <MAC>).")
                if not WINDOWS and "ermission" in str(payload):
                    g = _grupo_puerto(self.port_var.get().split(" · ")[0])
                    ayuda += "\n\n" + tr("Sin permiso para el puerto: añade tu usuario al grupo {g} "
                                          "(sudo usermod -aG {g} $USER) y vuelve a iniciar sesión.", g=g)
                messagebox.showerror(tr("No se pudo conectar"), f"{payload}\n\n{ayuda}")
            else:
                self.dtc_lbl.configure(text="", foreground=FG)
                messagebox.showerror("Error", payload)
            self.bar.configure(text=tr("Error: {e}", e=payload))
        elif kind == "dtcs":
            self._show_dtcs(payload)
            self._hist_guardar("lectura", payload)
        elif kind == "cleared":
            self._show_dtcs(payload, after_clear=True)
            self._hist_guardar("borrado", payload)
        elif kind == "scan_progress":
            i, n, a = payload
            self.dtc_lbl.configure(text=tr("Escaneando {dir} · {nombre} ({i}/{n})...", dir=f"{a:02X}",
                                           nombre=MODULOS.get(a, "?"), i=i + 1, n=n), foreground=FG)
            self.bar.configure(text=tr("Escaneando módulos: los que no están instalados tardan unos segundos en descartarse."))
        elif kind == "scan_done":
            self.scanning = False
            self.scan_btn.configure(text=tr("Escanear todos los módulos"), style="TButton", state="disabled")
            self._show_scan(payload)
            self._hist_guardar("escaneo", payload)
            self.status(tr("Volviendo al módulo {dir}...", dir=self.mod_var.get().split(" · ")[0]), WARN)
            self.bar.configure(text=tr("Escaneo terminado. Volviendo a conectar con el módulo elegido..."))
        elif kind == "report":
            self._save_report(payload)
        elif kind == "update":
            tag, url = payload
            self.upd_lbl.configure(text=tr("↑ Nueva {version}", version=tag))
            self.upd_lbl.bind("<Button-1>", lambda e: webbrowser.open(url))
            self.log(tr("Hay una versión nueva: {version} ({url})", version=tag, url=url))
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
                reply.put((tr("Error: {e}", e=e), True))
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
            if self.reiniciar:
                self.reiniciar()
            else:
                self.root.destroy()

    def _cambiar_idioma(self):
        """Guarda el idioma elegido y reconstruye la ventana con él (sin cerrar el programa)."""
        nuevo = next(k for k, v in idioma.IDIOMAS.items() if v == self.lang_var.get())
        if nuevo == idioma.actual():
            return
        if self.scanning or self.ai_busy:
            self.lang_var.set(idioma.IDIOMAS[idioma.actual()])
            messagebox.showinfo(NOMBRE, tr("Espera a que termine el escaneo o la respuesta del asistente."))
            return
        cfg = ia.cargar_config()                       # la del disco: no pisa nada guardado entretanto
        cfg["idioma"] = nuevo
        ia.guardar_config(cfg)
        idioma.poner(nuevo)
        root = self.root

        def reconstruir():
            for w in root.winfo_children():
                w.destroy()
            root.app = App(root)
        self.reiniciar = reconstruir
        self._stop_rec()
        self._ai_new()
        if self.connected:
            self.worker.submit("disconnect")          # al desconectar se cierra el hilo y se reconstruye
        else:
            self.worker.submit("quit")

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
    root = tk.Tk(className=NOMBRE)              # WM_CLASS en Linux: «Obd2desk» (ver el .desktop)
    _elegir_fuentes(root)
    root.app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
