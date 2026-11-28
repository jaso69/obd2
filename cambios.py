"""
Registro de los cambios escritos en las centralitas VAG (canales de adaptación y codificación),
con el valor de antes para poder volver a él. Sin interfaz; se prueba en tests/prueba_historial.py.

Un archivo JSON Lines en la carpeta de configuración (cambios_centralita.jsonl), un cambio por línea:

    {"fecha": "2026-11-28T18:30:00", "modulo": 1, "referencia": "038906018FQ",
     "tipo": "adaptacion" | "codificacion", "canal": 1 (o null), "antes": 128, "despues": 130,
     "taller": 8704}

Se añade y no se reescribe nunca: si el programa se cierra a mitad, lo ya apuntado se conserva.
"""
import datetime
import json
import os

ARCHIVO = "cambios_centralita.jsonl"
TIPOS = ("adaptacion", "codificacion")


class Cambios:
    def __init__(self, carpeta):
        self.ruta = os.path.join(carpeta, ARCHIVO)

    def registrar(self, modulo, referencia, tipo, canal, antes, despues, taller=0, fecha=None):
        if tipo not in TIPOS:
            raise ValueError(tipo)
        r = {"fecha": (fecha or datetime.datetime.now()).isoformat(timespec="seconds"), "modulo": modulo,
             "referencia": (referencia or "").strip(), "tipo": tipo, "canal": canal, "antes": antes,
             "despues": despues, "taller": taller}
        os.makedirs(os.path.dirname(self.ruta), exist_ok=True)
        cortada = False                          # última línea a medio escribir: se empieza en otra
        try:
            with open(self.ruta, "rb") as f:
                f.seek(0, os.SEEK_END)
                if f.tell():
                    f.seek(-1, os.SEEK_END)
                    cortada = f.read(1) != b"\n"
        except OSError:
            pass
        with open(self.ruta, "a", encoding="utf-8") as f:
            f.write(("\n" if cortada else "") + json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return r

    def todos(self):
        out = []
        try:
            with open(self.ruta, encoding="utf-8") as f:
                for linea in f:
                    try:
                        r = json.loads(linea)
                    except ValueError:
                        continue                 # línea a medio escribir: se ignora
                    if isinstance(r, dict) and r.get("tipo") in TIPOS:
                        out.append(r)
        except OSError:
            pass
        return out

    def de(self, modulo, referencia):
        """Cambios de una centralita (módulo y referencia), del más reciente al más antiguo."""
        ref = (referencia or "").strip()
        return [r for r in reversed(self.todos()) if r.get("modulo") == modulo and r.get("referencia") == ref]
