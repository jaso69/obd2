"""
Historial de diagnósticos por coche (sin interfaz; se prueba en tests/prueba_historial.py).

Cada coche es un archivo JSON en la carpeta de configuración (historial/<id>.json):

    {"id": "VSSZZZ6KZYR000001", "nombre": "SEAT · 2000", "registros": [registro, ...]}

    registro = {"fecha": "2026-11-27T21:30:00", "tipo": "lectura" | "borrado" | "escaneo",
                "modulos": [1] (KKL: direcciones leídas; OBD2: [0]),
                "averias": [{"modulo": 1, "codigo": "00553", "texto": "...", "estado": "presente"}],
                "mil": true/false/null}

Estados: presente, intermitente (VAG); memorizada, pendiente, permanente (OBD2).
Al comparar dos registros solo cuentan los módulos leídos en los dos (una lectura del
motor no dice nada de las averías del ABS que salieron en un escaneo).
"""
import datetime
import json
import os
import re

TIPOS = ("lectura", "borrado", "escaneo")
REPETIDA_MIN = 30           # misma lectura antes de 30 min: se actualiza la fecha, no se duplica
_VIN = re.compile(r"\b(?=[A-HJ-NPR-Z0-9]*\d)(?=[A-HJ-NPR-Z0-9]*[A-Z])[A-HJ-NPR-Z0-9]{17}\b")


def buscar_vin(textos):
    """Un VIN dentro de textos de identificación (algunas centralitas VAG lo incluyen)."""
    for t in textos:
        m = _VIN.search((t or "").upper())
        if m:
            return m.group(0)
    return None


def id_seguro(ident):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", ident).strip("_")[:80] or "coche"


class Historial:
    def __init__(self, carpeta):
        self.carpeta = carpeta

    def _ruta(self, ident):
        return os.path.join(self.carpeta, id_seguro(ident) + ".json")

    def cargar(self, ident):
        try:
            with open(self._ruta(ident), encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d.get("registros"), list):
                return d
        except (OSError, ValueError, AttributeError):
            pass
        return {"id": ident, "nombre": ident, "registros": []}

    def _escribir(self, d):
        os.makedirs(self.carpeta, exist_ok=True)
        ruta = self._ruta(d["id"])
        tmp = ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, ruta)

    def guardar(self, ident, nombre, registro, ahora=None):
        """Añade un registro (o actualiza el último si es la misma lectura de hace poco).

        Devuelve (registro guardado, registro anterior con el que compararlo o None)."""
        ahora = ahora or datetime.datetime.now()
        registro = dict(registro, fecha=ahora.isoformat(timespec="seconds"))
        d = self.cargar(ident)
        d["id"], d["nombre"] = ident, nombre or d.get("nombre") or ident
        regs = d["registros"]
        ultimo = regs[-1] if regs else None
        if (ultimo and registro["tipo"] != "borrado" and ultimo["tipo"] == registro["tipo"]
                and ultimo["modulos"] == registro["modulos"] and _claves(ultimo) == _claves(registro)
                and ahora - _fecha(ultimo) < datetime.timedelta(minutes=REPETIDA_MIN)):
            regs[-1] = registro
        else:
            regs.append(registro)
        self._escribir(d)
        return registro, anterior(regs, len(regs) - 1)

    def borrar_registro(self, ident, indice):
        d = self.cargar(ident)
        if 0 <= indice < len(d["registros"]):
            del d["registros"][indice]
            if d["registros"]:
                self._escribir(d)
            else:
                try:
                    os.remove(self._ruta(ident))
                except OSError:
                    pass

    def coches(self):
        """[(id, nombre, nº de registros, fecha del último)] ordenados del más reciente al más antiguo."""
        out = []
        try:
            nombres = os.listdir(self.carpeta)
        except OSError:
            return out
        for n in nombres:
            if not n.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.carpeta, n), encoding="utf-8") as f:
                    d = json.load(f)
                regs = d["registros"]
                if regs:
                    out.append((d["id"], d.get("nombre") or d["id"], len(regs), regs[-1]["fecha"]))
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return sorted(out, key=lambda c: c[3], reverse=True)


def _fecha(registro):
    try:
        return datetime.datetime.fromisoformat(registro["fecha"])
    except (KeyError, ValueError):
        return datetime.datetime.min


def _claves(registro, modulos=None):
    return {(a.get("modulo", 0), a["codigo"]) for a in registro["averias"]
            if modulos is None or a.get("modulo", 0) in modulos}


def anterior(registros, i):
    """El registro anterior al i que leyó alguno de sus módulos; None si no hay."""
    mods = set(registros[i]["modulos"])
    for r in reversed(registros[:i]):
        if mods & set(r["modulos"]):
            return r
    return None


def comparar(antes, ahora):
    """{"nuevas": [...], "resueltas": [...], "repetidas": [...]} (averías como en los registros)."""
    comunes = set(antes["modulos"]) & set(ahora["modulos"])
    a, b = _claves(antes, comunes), _claves(ahora, comunes)
    por_clave = lambda r: {(x.get("modulo", 0), x["codigo"]): x for x in r["averias"]}
    pa, pb = por_clave(antes), por_clave(ahora)
    orden = lambda claves, p: [p[k] for k in sorted(claves)]
    return {"nuevas": orden(b - a, pb), "resueltas": orden(a - b, pa), "repetidas": orden(a & b, pb)}
