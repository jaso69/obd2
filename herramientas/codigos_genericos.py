"""
Genera obd_codigos.py: los 9533 códigos de avería genéricos OBD2 (SAE J2012: P0, P2, P3, B0, C0,
U0 y U3) con su título en inglés (OBDex, datos CC0) y en español (traductor_dtc.py).

Uso: python3 herramientas/codigos_genericos.py
Los títulos en inglés están en herramientas/obdex_titulos.json (para actualizarlos, volver a
bajarlos de https://foerbsnavi.github.io/OBDex/generic.min.json).
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import traductor_dtc  # noqa: E402


def main():
    datos = json.load(open(os.path.join(AQUI, "obdex_titulos.json"), encoding="utf-8"))
    titulos = datos["titulos"]
    lineas = []
    sin_traducir = 0
    for codigo, en in sorted(titulos.items()):
        es = traductor_dtc.traducir(en)
        if es is None:
            sin_traducir += 1
        lineas.append(f"    {codigo!r}: ({en!r}, {es!r}),")
    destino = os.path.join(os.path.dirname(AQUI), "obd_codigos.py")
    with open(destino, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f'''"""
Códigos de avería genéricos OBD2 (SAE J2012: P0, P2, P3, B0, C0, U0 y U3): código -> (inglés, español).

Generado por herramientas/codigos_genericos.py: no editar a mano.
Títulos en inglés: OBDex (https://github.com/foerbsnavi/OBDex, commit {datos["commit"][:7]}), datos CC0 1.0.
Español: traducción automática por diccionario (herramientas/traductor_dtc.py); None si no se pudo
traducir entero (entonces se muestra el inglés). Las descripciones revisadas a mano de
obd_datos.DTCS tienen prioridad.
"""

CODIGOS = {{
''')
        fh.write("\n".join(lineas))
        fh.write("\n}\n")
    total = len(titulos)
    print(f"{total} códigos; traducidos al español {total - sin_traducir} ({(total - sin_traducir) / total * 100:.1f} %); "
          f"escrito {destino} ({os.path.getsize(destino) // 1024} KB)")


if __name__ == "__main__":
    main()
