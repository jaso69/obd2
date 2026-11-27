"""
Lectura de grabaciones CSV para el visor (sin interfaz; se prueba en tests/prueba_csv.py).

Lee las que graba el programa (separador «;», coma decimal, primera columna «t (s)»,
columnas «nombre (unidad)») y también CSV de otros programas: separador «,» o «;»,
y si la primera columna no es un tiempo, el eje X es el número de muestra.
"""
import csv
import io
import re

from idioma import tr

_UNIDAD = re.compile(r"^(.*\S)\s*\(([^()]*)\)$")


def _numero(texto, coma_decimal):
    t = texto.strip()
    if coma_decimal:
        t = t.replace(".", "").replace(",", ".") if t.count(",") == 1 and t.count(".") >= 1 else t.replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return None
    return v if v == v and abs(v) != float("inf") else None


def nombre_y_unidad(cabecera):
    m = _UNIDAD.match(cabecera.strip())
    return (m.group(1), m.group(2)) if m else (cabecera.strip(), "")


def leer(ruta):
    """Devuelve {"eje": "s" o "muestra", "n": filas, "columnas": [(nombre, unidad, [(x, valor)])]}.

    Lanza ValueError con un mensaje para el usuario si el archivo no sirve."""
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        texto = f.read()
    linea = texto.lstrip().split("\n", 1)[0]
    delim = max((";", ",", "\t"), key=linea.count)        # a igualdad, «;» (el del programa)
    filas = [f for f in csv.reader(io.StringIO(texto), delimiter=delim) if any(c.strip() for c in f)]
    if len(filas) < 2:
        raise ValueError(tr("El archivo no tiene datos (hace falta una fila de cabecera y al menos una de valores)."))
    cabecera, filas = filas[0], filas[1:]
    coma = delim != ","
    tiempo = None
    if cabecera and re.match(r"^\s*(t|time|tiempo)\b", cabecera[0], re.I):
        tiempo = [_numero(f[0], coma) if f else None for f in filas]
        if sum(v is not None for v in tiempo) < len(filas) / 2:
            tiempo = None
    columnas = []
    for j in range(1 if tiempo else 0, len(cabecera)):
        puntos = []
        for i, f in enumerate(filas):
            if j >= len(f):
                continue
            x = tiempo[i] if tiempo else i + 1
            v = _numero(f[j], coma)
            if x is not None and v is not None:
                puntos.append((x, v))
        if puntos:
            nombre, unidad = nombre_y_unidad(cabecera[j] or tr("Columna {n}", n=j + 1))
            columnas.append((nombre, unidad, puntos))
    if not columnas:
        raise ValueError(tr("El archivo no tiene columnas con números."))
    return {"eje": "s" if tiempo else "muestra", "n": len(filas), "columnas": columnas}


def resumen(puntos, x0=None, x1=None):
    """(mínimo, media, máximo) de los puntos entre x0 y x1; None si no hay ninguno."""
    vs = [v for x, v in puntos if (x0 is None or x >= x0) and (x1 is None or x <= x1)]
    if not vs:
        return None
    return min(vs), sum(vs) / len(vs), max(vs)


def reducir(puntos, n_max):
    """Menos puntos para dibujar sin perder los picos: mínimo y máximo de cada tramo."""
    if len(puntos) <= n_max:
        return puntos
    tramo = len(puntos) / (n_max / 2)
    out = []
    i = 0.0
    while int(i) < len(puntos):
        trozo = puntos[int(i):max(int(i + tramo), int(i) + 1)]
        a = min(trozo, key=lambda p: p[1])
        b = max(trozo, key=lambda p: p[1])
        out += [a, b] if a[0] <= b[0] else [b, a]
        i += tramo
    return out
