"""
Idioma de la interfaz: español (textos originales del código) o inglés.

    from idioma import tr
    tr("Conectado a {baud} baudios", baud=10400)

Los textos se escriben en español en el código y tr() devuelve la traducción
del diccionario de textos_en.py cuando el idioma es inglés (si falta una
traducción, se deja el texto en español; tests/prueba_idioma.py lo detecta).

Las tablas de datos (averías, PIDs, módulos...) se registran con tabla() y se
traducen en su sitio al cambiar de idioma, conservando el original.
"""
import locale
import os
import sys

IDIOMAS = {"es": "Español", "en": "English"}
_actual = "es"
_tablas = []            # (diccionario, copia original, función que traduce un valor)
faltan = set()          # textos pedidos en inglés sin traducción (lo revisan las pruebas)


def _en():
    from textos_en import EN
    return EN


def tr(texto, **datos):
    """Texto traducido al idioma actual; con datos, se rellena con str.format."""
    if _actual == "en":
        en = _en()
        if texto in en:
            texto = en[texto]
        else:
            faltan.add(texto)
    return texto.format(**datos) if datos else texto


def actual():
    return _actual


def detectar():
    """Idioma del sistema: «es» si es español (o catalán, gallego, euskera); si no, «en»."""
    candidatos = [os.environ.get(v, "") for v in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE")]
    if sys.platform == "win32":
        try:
            import ctypes
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            candidatos.insert(0, locale.windows_locale.get(lcid, ""))
        except Exception:
            pass
    try:
        candidatos.append(locale.getlocale()[0] or "")
    except ValueError:
        pass
    for c in candidatos:
        c = c.lower()
        if not c or c in ("c", "posix") or c.startswith("c."):
            continue
        return "es" if c.startswith(("es", "ca", "gl", "eu", "spanish", "catalan", "galician", "basque")) else "en"
    return "es"


def poner(idioma):
    """Cambia el idioma y traduce las tablas registradas."""
    global _actual
    _actual = idioma if idioma in IDIOMAS else "es"
    for d, original, fn in _tablas:
        for k, v in original.items():
            d[k] = fn(v)


def tabla(d, fn=None):
    """Registra un diccionario de datos cuyos valores (textos en español) hay que traducir.

    fn(valor) traduce un valor que no es un texto simple (p. ej. una tupla); por defecto tr()."""
    _tablas.append((d, dict(d), fn or (lambda v: tr(v) if isinstance(v, str) and v else v)))
    poner(_actual)


# Por defecto: OBD2DESK_IDIOMA (pruebas y capturas) o el del sistema. La interfaz
# lo cambia después según la configuración guardada.
poner(os.environ.get("OBD2DESK_IDIOMA") or detectar())
