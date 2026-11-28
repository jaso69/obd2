"""
Genera las páginas secundarias de la web, en español e inglés:
- códigos de avería VAG (/averias-vag/, /en/vag-fault-codes/) a partir de las tablas del programa
  (vag_datos.py, vag_p1.py, obd_datos.py y las traducciones de textos_en.py), con su índice para
  el buscador (codigos.json);
- guías (/guias/, /en/guides/), con el texto de guias.py;
- la página 404 (404.html) y el sitemap.xml completo.

Uso: python3 web/generar_paginas.py   (volver a ejecutarlo si cambian las tablas o las guías)
No se publica (publicar.sh excluye los .py).
"""
import html
import json
import os
import re
import sys

WEB = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(WEB))

import obd_datos  # noqa: E402
import vag_datos  # noqa: E402
import vag_p1  # noqa: E402
from textos_en import EN  # noqa: E402
from guias import GUIAS  # noqa: E402
from obd_codigos import CODIGOS  # noqa: E402

DOMINIO = "https://www.obd2desk.com"
FECHA = "2026-11-28"
e = html.escape


def en(texto):
    """Traducción inglesa de un texto de las tablas del programa (debe existir)."""
    if texto not in EN:
        raise SystemExit(f"Falta la traducción inglesa de: {texto!r}")
    return EN[texto]


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------
# Códigos clásicos por sistema, según los comentarios de vag_datos.DTCS
SISTEMAS_EN = {
    "Cambio automático": "Automatic transmission",
    "Motor y comunes": "Engine and common",
    "Bus de datos (CAN de tracción)": "Data bus (powertrain CAN)",
    "ABS": "ABS",
    "Airbag": "Airbag",
    "Cuadro de instrumentos e inmovilizador": "Instrument cluster and immobilizer",
    "Confort / cierre centralizado": "Convenience / central locking",
    "Radio": "Radio",
    "Otros": "Other",
}


def clasicos_por_sistema():
    fuente = open(os.path.join(os.path.dirname(WEB), "vag_datos.py"), encoding="utf-8").read()
    bloque = fuente[fuente.index("DTCS = {"):]
    bloque = bloque[:bloque.index("\n}\n")]
    sistemas, actual = [], "Otros"
    for linea in bloque.splitlines()[1:]:
        linea = linea.strip()
        m = re.match(r"#\s*(.+)", linea)
        if m:
            actual = m.group(1).strip()
            sistemas.append((actual, []))
            continue
        m = re.match(r"(\d+):", linea)
        if m:
            codigo = int(m.group(1))
            if codigo == 65535:          # «Unidad de control averiada»: vale para todas
                continue
            if not sistemas or sistemas[-1][0] != actual:
                sistemas.append((actual, []))
            sistemas[-1][1].append(codigo)
    sistemas.append(("Otros", [65535]))
    total = sum(len(c) for _, c in sistemas)
    assert total == len(vag_datos.DTCS), (total, len(vag_datos.DTCS))
    return sistemas


def vag_de_p(p):
    """Código VAG de 5 cifras de un código OBD P0xxx/P1xxx (inverso de vag_datos.codigo_obd)."""
    n = int(p[1:])
    v = 16384 + n if p.startswith("P0") else 16408 + n
    assert vag_datos.codigo_obd(v) == p, (p, v)
    return v


# Grupos de P1 por centenas: (título es, título en)
P1_TEMAS = {
    11: ("Sondas lambda, mezcla y carga", "O2 sensors, fuel trim and load"),
    12: ("Inyectores, comienzo de inyección, turbo y refrigeración", "Injectors, injection timing, turbo and cooling"),
    13: ("Encendido, picado y fallos de combustión", "Ignition, knock and misfires"),
    14: ("EGR, EVAP y temperatura de escape", "EGR, EVAP and exhaust temperature"),
    15: ("Ralentí, mariposa, presión de turbo, levas y relés", "Idle, throttle, boost pressure, camshaft and relays"),
    16: ("Alimentación, pedal, testigo MIL, centralita y bus de datos", "Power supply, pedal, MIL, control unit and data bus"),
    17: ("Cambio automático", "Automatic transmission"),
    18: ("Cambio automático y bus de datos", "Automatic transmission and data bus"),
}
assert {k // 100 for k in vag_p1.P1} == set(P1_TEMAS)


def desc_generica(p):
    """(español, inglés) de un código genérico: primero la descripción revisada del programa."""
    if p in obd_datos.DTCS:
        return obd_datos.DTCS[p], en(obd_datos.DTCS[p])
    en_, es_ = CODIGOS[p]
    return es_ or en_, en_


def familias():
    """Lista de páginas de códigos: dict con slug, títulos, filas [(vag, p, es, en)]."""
    fams = []
    filas = []
    sistemas = []
    for sistema, codigos in clasicos_por_sistema():
        sistemas.append((sistema, SISTEMAS_EN[sistema],
                         [(c, None, vag_datos.DTCS[c], en(vag_datos.DTCS[c])) for c in sorted(codigos)]))
        filas += sistemas[-1][2]
    fams.append(dict(slug_es="clasicos", slug_en="classic", corto_es="Clásicos 00xxx-01xxx", corto_en="Classic 00xxx-01xxx",
                     tema_es="motor, cambio, ABS, airbag, cuadro, confort y radio",
                     tema_en="engine, transmission, ABS, airbag, cluster, convenience and radio",
                     rango="{:05d}-{:05d}".format(min(r[0] for r in filas), max(r[0] for r in filas if r[0] != 65535)), filas=filas, sistemas=sistemas, tipo="clasico"))
    assert all(p.startswith("P0") for p in obd_datos.DTCS)
    p0 = sorted(set(obd_datos.DTCS) | {c for c in CODIGOS if c.startswith("P0") and c[2:].isdigit()})
    fams.append(dict(slug_es="p0", slug_en="p0", corto_es="16xxx = P0xxx", corto_en="16xxx = P0xxx",
                     tema_es="códigos OBD2 genéricos en formato VAG", tema_en="generic OBD2 codes in VAG format",
                     rango="16384-17383",
                     filas=[(vag_de_p(p), p, *desc_generica(p)) for p in p0], tipo="p0"))
    for c in sorted(P1_TEMAS):
        ks = sorted(k for k in vag_p1.P1 if k // 100 == c)
        fams.append(dict(slug_es=f"p{c}xx", slug_en=f"p{c}xx", corto_es=f"P{c}xx", corto_en=f"P{c}xx",
                         tema_es=P1_TEMAS[c][0], tema_en=P1_TEMAS[c][1],
                         rango=f"{16408 + c * 100}-{16408 + c * 100 + 99}",
                         filas=[(vag_de_p(f"P{k}"), f"P{k}", vag_p1.P1[k][0], vag_p1.P1[k][1]) for k in ks], tipo="p1"))
    return fams


# ---------------------------------------------------------------------------
# Textos de cada idioma
# ---------------------------------------------------------------------------
L = {
    "es": dict(
        base="/averias-vag/", inicio="/", otro="en", otro_nombre="English", otro_corto="EN",
        menu="Abrir menú", nav="Principal", saltar="Saltar al contenido",
        nav_links=[("/#funciones", "Funciones"), ("/#hardware", "Qué cable"), ("/#descargar", "Descargar")],
        nav_averias="Averías VAG", migas="Ruta", migas_inicio="Inicio",
        indice_titulo="Códigos de avería VAG: lista y significado",
        indice_title="Códigos de avería VAG (SEAT, VW, Audi, Skoda): lista y significado · OBD2Desk",
        indice_desc="Significado de {n} códigos de avería VAG de SEAT, Volkswagen, Audi y Skoda: clásicos de 5 cifras, 16xxx (P0) y 17xxx-18xxx (P1), con buscador y tipos de fallo.",
        fam_h1="Códigos de avería VAG {corto}: {tema}",
        fam_title="Averías VAG {corto} ({rango}): {tema} · OBD2Desk",
        fam_desc="Significado de los {n} códigos de avería VAG {corto} ({rango}) de SEAT, Volkswagen, Audi y Skoda: {tema}. Con el código OBD equivalente y buscador.",
        buscar="Buscar un código", buscar_ph="Ej.: 17978, P1570, 00532 o «turbo»",
        buscar_ayuda="Escribe el código de 5 cifras, el código P o una palabra de la descripción.",
        sin_js="El buscador necesita JavaScript; puedes recorrer las listas de abajo.",
        col_vag="Código VAG", col_obd="Código OBD", col_desc="Descripción",
        familias="Listas de códigos", codigos="{n} códigos",
        otras="Otras listas de códigos VAG",
        descarga_h="Lee y borra estas averías con OBD2Desk",
        descarga_p="OBD2Desk es un programa gratuito y de código abierto para Windows y Linux. Con un cable KKL lee las averías de los VAG antiguos (KW1281) de todas las centralitas; con un ELM327, las de cualquier coche OBD2, y describe los P1 de VAG si el VIN es de SEAT, VW, Audi o Skoda.",
        descarga_boton="Descargar OBD2Desk", descarga_mas="Ver qué hace",
        aviso="Descripciones orientativas sacadas de documentación pública de VAG. El significado exacto puede variar según la centralita y el año: confírmalo con el manual de taller de tu coche.",
        pie_licencia='<strong>OBD2Desk</strong> es software libre bajo <a href="https://github.com/jaso69/obd2/blob/main/LICENSE">licencia MIT</a>. Código en <a href="https://github.com/jaso69/obd2">github.com/jaso69/obd2</a>.',
        pie_legal="Proyecto independiente, sin relación con SEAT, Volkswagen Group ni Bosch. Las marcas pertenecen a sus propietarios. La información se ofrece tal cual, sin garantía; para reparar, sigue el manual de taller.",
        tabla_region="Tabla de códigos",
        guias="/guias/", nav_guias="Guías",
        guias_titulo="Guías de diagnóstico", guias_title="Guías de diagnóstico del coche: cable KKL, ELM327 y 1.9 TDI · OBD2Desk",
        guias_desc="Guías prácticas para diagnosticar tu coche desde el portátil: qué cable KKL comprar para VAG, cómo conectar un ELM327 Bluetooth o WiFi y qué grupos mirar en un 1.9 TDI.",
        guias_intro="Guías prácticas para diagnosticar tu coche desde el portátil, escritas a partir de lo que hemos aprendido desarrollando y probando OBD2Desk.",
        guias_codigos="¿Buscas qué significa un código? Mira la <a href=\"/averias-vag/\">lista de códigos de avería VAG</a>.",
        grupo="Grupo", muestra="Qué muestra",
        obd="/codigos-obd2/", nav_obd="Códigos OBD2",
        obd_titulo="Códigos de avería OBD2: lista completa y significado",
        obd_title="Códigos de avería OBD2 (P0, P2, B, C, U): lista y significado en español · OBD2Desk",
        obd_desc="Significado en español de los {n} códigos de avería OBD2 genéricos (P0xxx, P2xxx, P34xx, B0, C0, U0 y U3), válidos para cualquier marca, con buscador.",
        obd_h1="Códigos OBD2 {g}: {tema}",
        obd_ftitle="Códigos OBD2 {g}: {tema} · OBD2Desk",
        obd_fdesc="Significado de los {n} códigos de avería OBD2 {g} ({tema}), válidos para cualquier marca con OBD2. Con buscador.",
        obd_buscar_ph="Ej.: P0420, U0100, P2463 o «catalizador»",
        obd_buscar_ayuda="Escribe el código (P0420) o una palabra de la descripción.",
        col_codigo="Código", obd_otras="Otras listas de códigos OBD2",
    ),
    "en": dict(
        base="/en/vag-fault-codes/", inicio="/en/", otro="es", otro_nombre="Español", otro_corto="ES",
        menu="Open menu", nav="Main", saltar="Skip to content",
        nav_links=[("/en/#funciones", "Features"), ("/en/#hardware", "Which cable"), ("/en/#descargar", "Download")],
        nav_averias="VAG fault codes", migas="Breadcrumb", migas_inicio="Home",
        indice_titulo="VAG fault codes: list and meaning",
        indice_title="VAG fault codes (VW, Audi, SEAT, Skoda): list and meaning · OBD2Desk",
        indice_desc="Meaning of {n} VAG fault codes for Volkswagen, Audi, SEAT and Skoda: classic 5-digit codes, 16xxx (P0) and 17xxx-18xxx (P1), with search and fault types.",
        fam_h1="VAG fault codes {corto}: {tema}",
        fam_title="VAG fault codes {corto} ({rango}): {tema} · OBD2Desk",
        fam_desc="Meaning of the {n} VAG fault codes {corto} ({rango}) for Volkswagen, Audi, SEAT and Skoda: {tema}. With the matching OBD code and search.",
        buscar="Search for a code", buscar_ph="E.g. 17978, P1570, 00532 or “boost”",
        buscar_ayuda="Type the 5-digit code, the P code or a word from the description.",
        sin_js="Search needs JavaScript; you can browse the lists below.",
        col_vag="VAG code", col_obd="OBD code", col_desc="Description",
        familias="Code lists", codigos="{n} codes",
        otras="Other VAG code lists",
        descarga_h="Read and clear these faults with OBD2Desk",
        descarga_p="OBD2Desk is a free, open-source program for Windows and Linux. With a KKL cable it reads the fault codes of older VAG cars (KW1281) from every control unit; with an ELM327, those of any OBD2 car, and it describes VAG P1 codes when the VIN is from VW, Audi, SEAT or Skoda.",
        descarga_boton="Download OBD2Desk", descarga_mas="See what it does",
        aviso="Descriptions are for guidance and come from public VAG documentation. The exact meaning can vary with the control unit and year: check it against your car's workshop manual.",
        pie_licencia='<strong>OBD2Desk</strong> is free software under the <a href="https://github.com/jaso69/obd2/blob/main/LICENSE">MIT license</a>. Source code at <a href="https://github.com/jaso69/obd2">github.com/jaso69/obd2</a>.',
        pie_legal="Independent project, not affiliated with Volkswagen Group, SEAT or Bosch. Trademarks belong to their owners. Information is provided as is, without warranty; to repair, follow the workshop manual.",
        tabla_region="Code table",
        guias="/en/guides/", nav_guias="Guides",
        guias_titulo="Diagnostic guides", guias_title="Car diagnostic guides: KKL cable, ELM327 and 1.9 TDI · OBD2Desk",
        guias_desc="Practical guides to diagnose your car from a laptop: which KKL cable to buy for VAG cars, how to connect a Bluetooth or WiFi ELM327 and which groups to check on a 1.9 TDI.",
        guias_intro="Practical guides to diagnose your car from a laptop, written from what we have learned building and testing OBD2Desk.",
        guias_codigos="Looking up what a code means? See the <a href=\"/en/vag-fault-codes/\">list of VAG fault codes</a>.",
        grupo="Group", muestra="What it shows",
        obd="/en/obd2-codes/", nav_obd="OBD2 codes",
        obd_titulo="OBD2 fault codes: full list and meaning",
        obd_title="OBD2 fault codes (P0, P2, B, C, U): full list and meaning · OBD2Desk",
        obd_desc="Meaning of the {n} generic OBD2 fault codes (P0xxx, P2xxx, P34xx, B0, C0, U0 and U3), valid for any make, with search.",
        obd_h1="OBD2 codes {g}: {tema}",
        obd_ftitle="OBD2 codes {g}: {tema} · OBD2Desk",
        obd_fdesc="Meaning of the {n} OBD2 fault codes {g} ({tema}), valid for any make with OBD2. With search.",
        obd_buscar_ph="E.g. P0420, U0100, P2463 or “catalyst”",
        obd_buscar_ayuda="Type the code (P0420) or a word from the description.",
        col_codigo="Code", obd_otras="Other OBD2 code lists",
    ),
}


def url_fam(lang, f):
    return L[lang]["base"] + (f["slug_es"] if lang == "es" else f["slug_en"]) + "/"


# ---------------------------------------------------------------------------
# Plantilla
# ---------------------------------------------------------------------------
def pagina(lang, ruta, ruta_otro, title, desc, migas, cuerpo, articulo=None):
    t = L[lang]
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": DOMINIO + u} for i, (n, u) in enumerate(migas)]}
    if articulo:
        ld = [ld, {"@context": "https://schema.org", "@type": "TechArticle", "headline": articulo, "inLanguage": lang,
                   "description": desc, "url": DOMINIO + ruta, "dateModified": FECHA,
                   "author": {"@type": "Organization", "name": "OBD2Desk", "url": DOMINIO + "/"},
                   "publisher": {"@type": "Organization", "name": "OBD2Desk", "url": DOMINIO + "/"}}]
    es_url, en_url = (ruta, ruta_otro) if lang == "es" else (ruta_otro, ruta)
    migas_html = " <span aria-hidden=\"true\">›</span> ".join(
        f'<a href="{u}">{e(n)}</a>' if i < len(migas) - 1 else f'<span aria-current="page">{e(n)}</span>'
        for i, (n, u) in enumerate(migas))
    nav = "\n      ".join(f'<a href="{u}">{e(n)}</a>' for u, n in t["nav_links"])
    actual = ' aria-current="page"' if ruta == t["base"] else ""
    actual_g = ' aria-current="page"' if ruta == t["guias"] else ""
    actual_o = ' aria-current="page"' if ruta == t["obd"] else ""
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="theme-color" content="#111418">
<link rel="icon" type="image/png" href="/img/icono.png">
<link rel="apple-touch-icon" href="/img/icono.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="OBD2Desk">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{DOMINIO}/img/{'' if lang == 'es' else 'en/'}og.jpg">
<meta property="og:url" content="{DOMINIO}{ruta}">
<meta property="og:locale" content="{'es_ES' if lang == 'es' else 'en_US'}">
<link rel="canonical" href="{DOMINIO}{ruta}">
<link rel="alternate" hreflang="es" href="{DOMINIO}{es_url}">
<link rel="alternate" hreflang="en" href="{DOMINIO}{en_url}">
<link rel="alternate" hreflang="x-default" href="{DOMINIO}{es_url}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False)}
</script>
<link rel="stylesheet" href="/estilo.css">
</head>
<body>

<a class="saltar" href="#contenido">{t['saltar']}</a>

<header class="cabecera">
  <div class="contenedor cabecera-fila">
    <a class="marca" href="{t['inicio']}"><img src="/img/icono.png" alt="" width="32" height="32"> OBD2Desk</a>
    <button class="menu-boton" type="button" aria-label="{t['menu']}" aria-expanded="false" aria-controls="menu">☰</button>
    <nav id="menu" class="menu" aria-label="{t['nav']}">
      {nav}
      <a href="{t['obd']}"{actual_o}>{t['nav_obd']}</a>
      <a href="{t['base']}"{actual}>{t['nav_averias']}</a>
      <a href="{t['guias']}"{actual_g}>{t['nav_guias']}</a>
      <a class="idioma" href="{ruta_otro}" hreflang="{t['otro']}" lang="{t['otro']}" data-idioma="{t['otro']}" title="{t['otro_nombre']}">{t['otro_corto']}</a>
      <a class="boton boton-secundario boton-peque" href="https://github.com/jaso69/obd2">GitHub</a>
    </nav>
  </div>
</header>

<main id="contenido">
<div class="contenedor contenedor-codigos">
<nav class="migas" aria-label="{t['migas']}">{migas_html}</nav>
{cuerpo}
</div>
</main>

<footer class="pie">
  <div class="contenedor">
    <p>{t['pie_licencia']}</p>
    <p class="legal">{t['pie_legal']}</p>
  </div>
</footer>

<script src="/averias.js"></script>
</body>
</html>
"""


def buscador(lang, obd=False):
    t = L[lang]
    indice = (t["obd"] if obd else t["base"]) + "codigos.json"
    ph = t["obd_buscar_ph"] if obd else t["buscar_ph"]
    ayuda = t["obd_buscar_ayuda"] if obd else t["buscar_ayuda"]
    return f"""<div class="buscador" role="search">
  <label for="buscar">{t['buscar']}</label>
  <input id="buscar" type="search" placeholder="{e(ph)}" autocomplete="off" spellcheck="false"
    aria-describedby="buscar-ayuda" data-indice="{indice}">
  <p id="buscar-ayuda" class="pequeno">{ayuda}</p>
  <noscript><p class="pequeno">{t['sin_js']}</p></noscript>
  <div id="resultados" class="resultados" aria-live="polite"></div>
</div>"""


def descarga(lang):
    t = L[lang]
    return f"""<section class="tarjeta tarjeta-grande descarga-codigos" aria-labelledby="descarga-h">
  <h2 id="descarga-h">{t['descarga_h']}</h2>
  <p>{t['descarga_p']}</p>
  <div class="botones botones-izq">
    <a class="boton boton-principal" href="{t['inicio']}#descargar">{t['descarga_boton']}</a>
    <a class="boton boton-secundario" href="{t['inicio']}#funciones">{t['descarga_mas']}</a>
  </div>
</section>"""


def tabla(lang, filas, con_obd, id_tabla):
    t = L[lang]
    cab = f"<th scope=\"col\">{t['col_vag']}</th>" + (f"<th scope=\"col\">{t['col_obd']}</th>" if con_obd else "") + \
        f"<th scope=\"col\">{t['col_desc']}</th>"
    cuerpo = []
    for v, p, des_es, des_en in filas:
        d = des_es if lang == "es" else des_en
        celda_p = f'<td><span id="{p}">{p}</span></td>' if con_obd else ""
        cuerpo.append(f'<tr id="{v:05d}"><th scope="row">{v:05d}</th>{celda_p}<td>{e(d)}</td></tr>')
    return (f'<div class="tabla-scroll" tabindex="0" role="region" aria-labelledby="{id_tabla}">'
            f'<table class="tabla tabla-codigos"><thead><tr>{cab}</tr></thead><tbody>\n'
            + "\n".join(cuerpo) + "\n</tbody></table></div>")


def otras(lang, fams, actual):
    t = L[lang]
    items = "".join(
        f'<li><a href="{url_fam(lang, f)}">{e(f["corto_" + lang])}</a> · {e(f["tema_" + lang])}</li>'
        for f in fams if f is not actual)
    return f'<section aria-labelledby="otras-h"><h2 id="otras-h">{t["otras"]}</h2><ul class="lista-familias">{items}</ul></section>'


# ---------------------------------------------------------------------------
# Textos explicativos (contenido propio de cada página)
# ---------------------------------------------------------------------------
def intro_indice(lang, n):
    if lang == "es":
        return f"""<p class="intro">Los coches del grupo Volkswagen (SEAT, Volkswagen, Audi y Skoda) guardan las averías con un número de 5 cifras. Aquí tienes el significado de <strong>{n} códigos</strong>, sacados de las mismas tablas que usa OBD2Desk para describirlos.</p>
<h2>Cómo se leen los códigos VAG</h2>
<ul class="lista-ok">
<li><strong>00xxx-01xxx · clásicos.</strong> Los de los VAG anteriores al OBD2 (protocolo KW1281). El mismo número significa lo mismo en todas las centralitas: 00532 es la tensión de alimentación tanto en el motor como en el ABS.</li>
<li><strong>16xxx · OBD2 genéricos.</strong> Son los P0xxx escritos a la manera de VAG: <code>código VAG = 16384 + número del P0</code>. Por ejemplo, 16684 = P0300 (fallos de combustión).</li>
<li><strong>17xxx-18xxx · propios de VAG.</strong> Son los P1xxx: <code>código VAG = 16408 + número del P1</code>. Por ejemplo, 17978 = P1570 (centralita del motor bloqueada por el inmovilizador).</li>
</ul>
<p>Un lector OBD2 con ELM327 los muestra como P0xxx y P1xxx; un programa que hable KW1281 con cable KKL, con las 5 cifras. OBD2Desk muestra los dos.</p>"""
    return f"""<p class="intro">Volkswagen Group cars (Volkswagen, Audi, SEAT and Skoda) store fault codes as a 5-digit number. Here is the meaning of <strong>{n} codes</strong>, taken from the same tables OBD2Desk uses to describe them.</p>
<h2>How VAG codes work</h2>
<ul class="lista-ok">
<li><strong>00xxx-01xxx · classic.</strong> Used by VAG cars from before OBD2 (KW1281 protocol). The same number means the same in every control unit: 00532 is the supply voltage in the engine as well as in the ABS.</li>
<li><strong>16xxx · generic OBD2.</strong> These are P0xxx codes written the VAG way: <code>VAG code = 16384 + P0 number</code>. For example, 16684 = P0300 (misfire detected).</li>
<li><strong>17xxx-18xxx · VAG-specific.</strong> These are the P1xxx codes: <code>VAG code = 16408 + P1 number</code>. For example, 17978 = P1570 (engine control unit locked by the immobilizer).</li>
</ul>
<p>An OBD2 reader with an ELM327 shows them as P0xxx and P1xxx; a program that speaks KW1281 with a KKL cable shows the 5 digits. OBD2Desk shows both.</p>"""


def tipos_fallo(lang):
    filas = "\n".join(
        f'<tr><th scope="row">{k:02d}</th><td>{e(v if lang == "es" else en(v))}</td></tr>'
        for k, v in sorted(vag_datos.FAULT_TYPES.items()) if k)
    if lang == "es":
        h, p, c1, c2, p2 = ("Tipo de fallo: el número que va detrás",
                            f"Además del código, la centralita da un <strong>tipo de fallo</strong> que dice qué le pasa al componente. OBD2Desk lo muestra entre corchetes: <code>00522 {e(vag_datos.DTCS[522])} [05 - {e(vag_datos.FAULT_TYPES[5])}]</code>.",
                            "Tipo", "Significado",
                            "Si además pone <strong>intermitente</strong>, el fallo apareció y desapareció: suele ser un contacto flojo o un cable que roza. Un cortocircuito o un circuito abierto apuntan primero al cableado y al conector antes que a la pieza.")
    else:
        h, p, c1, c2, p2 = ("Fault type: the number that follows",
                            f"Besides the code, the control unit gives a <strong>fault type</strong> that says what is wrong with the component. OBD2Desk shows it in brackets: <code>00522 {e(en(vag_datos.DTCS[522]))} [05 - {e(en(vag_datos.FAULT_TYPES[5]))}]</code>.",
                            "Type", "Meaning",
                            "If it also says <strong>intermittent</strong>, the fault came and went: usually a loose contact or a chafed wire. A short or an open circuit points first to the wiring and connector rather than the part itself.")
    return f"""<h2 id="tipos">{h}</h2>
<p>{p}</p>
<div class="tabla-scroll" tabindex="0" role="region" aria-label="{c1}">
<table class="tabla tabla-codigos tabla-tipos"><thead><tr><th scope="col">{c1}</th><th scope="col">{c2}</th></tr></thead><tbody>
{filas}
</tbody></table></div>
<p>{p2}</p>"""


def intro_familia(lang, f):
    n = len(f["filas"])
    if f["tipo"] == "clasico":
        if lang == "es":
            return f"""<p class="intro">Los {n} códigos de avería VAG de 5 cifras más habituales de los coches anteriores al OBD2 (protocolo KW1281): SEAT, Volkswagen, Audi y Skoda hasta ~2004. El mismo número significa lo mismo en cualquier centralita.</p>
<p>Se leen con un cable KKL; un lector OBD2 con ELM327 no los ve. Detrás del código, la centralita indica el <a href="{L[lang]['base']}#tipos">tipo de fallo</a> (cortocircuito, circuito abierto, señal demasiado alta…).</p>"""
        return f"""<p class="intro">The {n} most common 5-digit VAG fault codes of cars from before OBD2 (KW1281 protocol): Volkswagen, Audi, SEAT and Skoda up to ~2004. The same number means the same in any control unit.</p>
<p>They are read with a KKL cable; an OBD2 reader with an ELM327 does not see them. After the code, the control unit gives the <a href="{L[lang]['base']}#tipos">fault type</a> (short circuit, open circuit, signal too high…).</p>"""
    if f["tipo"] == "p0":
        if lang == "es":
            return f"""<p class="intro">Los VAG con OBD escriben los códigos genéricos P0xxx con 5 cifras: <code>código VAG = 16384 + número del P0</code>. Por ejemplo, 16684 es P0300. Aquí tienes los {n} códigos P0 con número.</p>
<p>Significan lo mismo en cualquier marca: un lector OBD2 con ELM327 los muestra como P0xxx, y un programa VAG con las 5 cifras.</p>"""
        return f"""<p class="intro">VAG cars with OBD write the generic P0xxx codes with 5 digits: <code>VAG code = 16384 + P0 number</code>. For example, 16684 is P0300. Here are all {n} numeric P0 codes.</p>
<p>They mean the same for any make: an OBD2 reader with an ELM327 shows them as P0xxx, and a VAG program shows the 5 digits.</p>"""
    c = f["corto_es"]
    if lang == "es":
        return f"""<p class="intro">Los {n} códigos {c} propios del grupo VAG (SEAT, Volkswagen, Audi y Skoda) que conoce OBD2Desk: {e(f['tema_es'])}. En las herramientas VAG salen con 5 cifras, del {f['rango'].replace('-', ' al ')}: <code>código VAG = 16408 + número del P1</code>.</p>
<p>Un lector OBD2 genérico los muestra solo como «código del fabricante»; OBD2Desk los describe también por OBD2 si el VIN es de un VAG.</p>"""
    return f"""<p class="intro">The {n} VAG-specific {c} codes (Volkswagen, Audi, SEAT and Skoda) that OBD2Desk knows: {e(f['tema_en'])}. VAG tools show them with 5 digits, from {f['rango'].replace('-', ' to ')}: <code>VAG code = 16408 + P1 number</code>.</p>
<p>A generic OBD2 reader only shows them as a “manufacturer code”; OBD2Desk also describes them over OBD2 when the VIN is from a VAG car.</p>"""


def consejos(lang):
    if lang == "es":
        return """<section aria-labelledby="consejos-h">
<h2 id="consejos-h">Antes de cambiar piezas</h2>
<ul class="lista-ok">
<li><strong>Apunta las averías antes de borrarlas</strong>, con el tipo de fallo y, en OBD2, los datos congelados (régimen, temperatura y carga en el momento del fallo).</li>
<li><strong>Borra y comprueba si vuelve.</strong> Una avería que no reaparece tras varios arranques puede ser antigua; una que vuelve enseguida es actual.</li>
<li><strong>Mira el cableado y los conectores primero</strong> cuando el fallo es cortocircuito, circuito abierto o intermitente.</li>
<li><strong>Mira los valores medidos</strong> del componente con el motor en marcha: un transmisor que da un valor absurdo (−40 °C de refrigerante, por ejemplo) confirma el fallo.</li>
</ul>
</section>"""
    return """<section aria-labelledby="consejos-h">
<h2 id="consejos-h">Before replacing parts</h2>
<ul class="lista-ok">
<li><strong>Write the faults down before clearing them</strong>, with the fault type and, on OBD2, the freeze frame data (engine speed, temperature and load when the fault happened).</li>
<li><strong>Clear them and see whether they come back.</strong> A fault that does not return after several starts may be old; one that comes back straight away is current.</li>
<li><strong>Check the wiring and connectors first</strong> when the fault is a short, an open circuit or intermittent.</li>
<li><strong>Look at the component's measured values</strong> with the engine running: a sender giving an absurd value (−40 °C coolant, for example) confirms the fault.</li>
</ul>
</section>"""


# ---------------------------------------------------------------------------
# Generación
# ---------------------------------------------------------------------------
def escribir(ruta_web, contenido):
    destino = os.path.join(WEB, ruta_web.strip("/"), "index.html")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(contenido)


def url_guia(lang, g):
    return L[lang]["guias"] + g["slug_" + lang] + "/"


def tabla_grupos(lang, grupos, nombre):
    t = L[lang]
    tr_ = (lambda s: s) if lang == "es" else en
    filas = "\n".join(
        f'<tr><th scope="row">{n:03d}</th><td><strong>{e(tr_(titulo))}</strong><br>{" · ".join(e(tr_(c)) for c in campos)}</td></tr>'
        for n, (titulo, campos) in sorted(grupos.items()))
    return (f'<div class="tabla-scroll" tabindex="0" role="region" aria-label="{e(nombre)}">'
            f'<table class="tabla tabla-codigos"><thead><tr><th scope="col">{t["grupo"]}</th><th scope="col">{t["muestra"]}</th></tr></thead>'
            f'<tbody>\n{filas}\n</tbody></table></div>')


def guias(lang):
    """Escribe las guías y su índice; devuelve las parejas de URL (es, en) para el sitemap."""
    t = L[lang]
    otro = "en" if lang == "es" else "es"
    urls = []
    for g in GUIAS:
        cuerpo = g[lang]
        cuerpo = cuerpo.replace("{GRUPOS_EDC15}", tabla_grupos(lang, vag_datos.GRUPOS_EDC15, "TDI EDC15V"))
        cuerpo = cuerpo.replace("{GRUPOS_PD}", tabla_grupos(lang, vag_datos.GRUPOS_PD, "TDI PD"))
        for otra in GUIAS:
            cuerpo = cuerpo.replace("{guia:" + otra["slug_es"] + "}", url_guia(lang, otra))
        assert "{" not in cuerpo, (g["slug_es"], cuerpo[cuerpo.index("{"):][:40])
        mas = "".join(f'<li><a href="{url_guia(lang, o)}">{e(o["h1_" + lang])}</a></li>' for o in GUIAS if o is not g)
        cuerpo = f"""<article>
<h1>{e(g['h1_' + lang])}</h1>
{cuerpo}
<p class="aclaracion">{t['guias_codigos']}</p>
</article>
{descarga(lang)}
<section aria-labelledby="mas-h"><h2 id="mas-h">{t['nav_guias']}</h2><ul class="lista-familias">{mas}</ul></section>"""
        ruta = url_guia(lang, g)
        escribir(ruta, pagina(lang, ruta, url_guia(otro, g), g["title_" + lang], g["desc_" + lang],
                              [(t["migas_inicio"], t["inicio"]), (t["nav_guias"], t["guias"]), (g["corto_" + lang], ruta)],
                              cuerpo, articulo=g["h1_" + lang]))
        urls.append((url_guia("es", g), url_guia("en", g)))
    tarjetas = "\n".join(
        f'<li class="tarjeta"><a href="{url_guia(lang, g)}"><strong>{e(g["h1_" + lang])}</strong></a><span>{e(g["resumen_" + lang])}</span></li>'
        for g in GUIAS)
    cuerpo = f"""<h1>{t['guias_titulo']}</h1>
<p class="intro">{t['guias_intro']}</p>
<ul class="familias">
{tarjetas}
</ul>
<p class="aclaracion">{t['guias_codigos']}</p>
{descarga(lang)}"""
    escribir(t["guias"], pagina(lang, t["guias"], L[otro]["guias"], t["guias_title"], t["guias_desc"],
                                [(t["migas_inicio"], t["inicio"]), (t["nav_guias"], t["guias"])], cuerpo))
    return [(L["es"]["guias"], L["en"]["guias"])] + urls


# ---------------------------------------------------------------------------
# Códigos OBD2 genéricos (obd_codigos.py)
# ---------------------------------------------------------------------------
_TEMA_P0 = {
    "0": ("Aire, combustible y control auxiliar de emisiones", "Fuel and air metering and auxiliary emission controls"),
    "1": ("Medición de aire y combustible", "Fuel and air metering"),
    "2": ("Medición de aire y combustible (circuito de inyectores)", "Fuel and air metering (injector circuit)"),
    "3": ("Encendido y fallos de combustión", "Ignition system and misfire"),
    "4": ("Control auxiliar de emisiones", "Auxiliary emission controls"),
    "5": ("Velocidad, ralentí y entradas auxiliares", "Vehicle speed, idle control and auxiliary inputs"),
    "6": ("Centralita y salidas auxiliares", "Computer and auxiliary outputs"),
    "7": ("Cambio", "Transmission"), "8": ("Cambio", "Transmission"), "9": ("Cambio", "Transmission"),
}
_TEMA_P2 = {
    "0": _TEMA_P0["0"], "1": _TEMA_P0["0"], "2": _TEMA_P0["0"],
    "3": ("Encendido y fallos de combustión", "Ignition system and misfire"),
    "4": ("Control auxiliar de emisiones", "Auxiliary emission controls"),
    "5": ("Entradas auxiliares", "Auxiliary inputs"),
    "6": ("Centralita y salidas auxiliares", "Computer and auxiliary outputs"),
    "7": ("Cambio", "Transmission"), "8": ("Cambio y embragues", "Transmission and clutches"),
}
_HIBRIDO = ("Propulsión híbrida y eléctrica", "Hybrid and electric propulsion")
_AMPLIACION = ("Motor, emisiones e híbridos (ampliación)", "Engine, emissions and hybrid (extension)")
_U = {
    "0": ("Buses de comunicación (CAN)", "Communication buses (CAN)"),
    "1": ("Sin comunicación con módulos", "Lost communication with modules"),
    "2": ("Sin comunicación con módulos", "Lost communication with modules"),
    "3": ("Software incompatible", "Software incompatibility"),
    "4": ("Datos no válidos recibidos", "Invalid data received"),
    "5": ("Datos no válidos recibidos", "Invalid data received"),
    "6": ("Sin comunicación con sensores y módulos", "Lost communication with sensors and modules"),
}


def grupos_obd():
    """Listas de códigos genéricos: [dict(slug, g (rótulo), tema_es, tema_en, codigos)]."""
    por = {}
    for c in sorted(CODIGOS):
        if c[:2] in ("P0", "P2"):
            k = c[:3] if c[:3] != "P0F" else "P0E"
            k = "U06" if c.startswith("U09") else k
        elif c.startswith("U0"):
            k = "U06" if c[2] == "9" else c[:3]
        elif c.startswith("U3"):
            k = "U3"
        else:
            k = c[:2]              # P3, B0, C0
        por.setdefault(k, []).append(c)
    grupos = []
    for k, cs in sorted(por.items()):
        if k.startswith("P0"):
            tema = _TEMA_P0.get(k[2], _HIBRIDO)
            g = f"{k}xx" + ("-P0Fxx" if k == "P0E" else "")
        elif k.startswith("P2"):
            tema = _TEMA_P2.get(k[2], _AMPLIACION)
            g = f"{k}xx"
        elif k == "P3":
            tema, g = ("Desactivación de cilindros y control de válvulas", "Cylinder deactivation and valve control"), "P34xx"
        elif k == "B0":
            tema, g = ("Carrocería: airbags, asientos, luces y confort", "Body: airbags, seats, lighting and comfort"), "B0xxx"
        elif k == "C0":
            tema, g = ("Chasis: frenos, ABS, ruedas y suspensión", "Chassis: brakes, ABS, wheels and suspension"), "C0xxx"
        elif k == "U3":
            tema, g = ("Red: alta tensión, pila de combustible y otros", "Network: high voltage, fuel cell and more"), "U3xxx"
        else:
            tema = _U[k[2]]
            g = f"{k}xx" + ("-U09xx" if k == "U06" and any(c.startswith("U09") for c in cs) else "")
        grupos.append(dict(slug=g.lower().replace("-", "-"), g=g, tema_es=tema[0], tema_en=tema[1], codigos=cs))
    assert sum(len(x["codigos"]) for x in grupos) == len(CODIGOS)
    return grupos


def url_obd(lang, grupo):
    return L[lang]["obd"] + grupo["slug"] + "/"


def texto_obd(lang, c):
    """(texto, es_ingles): descripción del código en ese idioma; en español, la revisada si la hay."""
    en_, es_ = CODIGOS[c]
    if lang == "en":
        return en_, False
    if c in obd_datos.DTCS:
        return obd_datos.DTCS[c], False
    return (es_, False) if es_ else (en_, True)


def tabla_obd(lang, codigos):
    t = L[lang]
    filas = []
    for c in codigos:
        texto, ingles = texto_obd(lang, c)
        celda = f'<td lang="en">{e(texto)}</td>' if ingles else f"<td>{e(texto)}</td>"
        filas.append(f'<tr id="{c}"><th scope="row">{c}</th>{celda}</tr>')
    return (f'<div class="tabla-scroll" tabindex="0" role="region" aria-labelledby="lista">'
            f'<table class="tabla tabla-codigos"><thead><tr><th scope="col">{t["col_codigo"]}</th>'
            f'<th scope="col">{t["col_desc"]}</th></tr></thead><tbody>\n' + "\n".join(filas) + "\n</tbody></table></div>")


def intro_obd(lang, n):
    vag = L[lang]["base"]
    if lang == "es":
        return f"""<p class="intro">Los códigos de avería OBD2 son los que da cualquier coche con OBD2/EOBD (en Europa, gasolina desde 2001 y diésel desde 2003-2004) a un lector como el ELM327. Aquí tienes el significado de los <strong>{n} códigos genéricos</strong>, los que significan lo mismo en todas las marcas.</p>
<h2>Cómo se lee un código OBD2</h2>
<ul class="lista-ok">
<li><strong>La letra</strong> dice el sistema: <strong>P</strong> motor y cambio, <strong>B</strong> carrocería (airbags, asientos, luces), <strong>C</strong> chasis (frenos, ABS, suspensión) y <strong>U</strong> red de comunicación entre centralitas.</li>
<li><strong>La primera cifra</strong> dice quién lo define: <strong>0</strong> (y también P2, P34 y U3) son genéricos de la norma SAE J2012, iguales en todas las marcas; <strong>1</strong> y <strong>2</strong> (salvo P2) son propios de cada fabricante.</li>
<li><strong>El resto</strong> dice el subsistema y el fallo. En los P0, la segunda cifra agrupa: 1 y 2 aire y combustible, 3 encendido, 4 emisiones, 5 velocidad y ralentí, 6 centralita, 7 a 9 cambio, y A a E híbridos y eléctricos.</li>
</ul>
<p>Los códigos del fabricante (P1xxx, B1xxx…) cambian de una marca a otra y no están en esta lista. Para SEAT, Volkswagen, Audi y Skoda tienes la <a href="{vag}">lista de códigos de avería VAG</a>.</p>"""
    return f"""<p class="intro">OBD2 fault codes are the ones any car with OBD2/EOBD (in Europe, petrol cars from 2001 and diesels from 2003-2004) gives to a reader such as an ELM327. Here is the meaning of the <strong>{n} generic codes</strong>, the ones that mean the same for every make.</p>
<h2>How to read an OBD2 code</h2>
<ul class="lista-ok">
<li><strong>The letter</strong> gives the system: <strong>P</strong> powertrain (engine and transmission), <strong>B</strong> body (airbags, seats, lighting), <strong>C</strong> chassis (brakes, ABS, suspension) and <strong>U</strong> the network between control units.</li>
<li><strong>The first digit</strong> says who defines it: <strong>0</strong> (and also P2, P34 and U3) are generic codes from the SAE J2012 standard, the same for every make; <strong>1</strong> and <strong>2</strong> (except P2) are manufacturer-specific.</li>
<li><strong>The rest</strong> gives the subsystem and the fault. In P0 codes the second digit groups them: 1 and 2 fuel and air, 3 ignition, 4 emissions, 5 speed and idle, 6 computer, 7 to 9 transmission, and A to E hybrid and electric.</li>
</ul>
<p>Manufacturer codes (P1xxx, B1xxx…) differ from one make to another and are not in this list. For Volkswagen, Audi, SEAT and Skoda see the <a href="{vag}">list of VAG fault codes</a>.</p>"""


def fuente_obd(lang):
    if lang == "es":
        return ('<p class="aclaracion">Títulos de <a href="https://github.com/foerbsnavi/OBDex">OBDex</a>, una base de datos abierta '
                '(dominio público, CC0). La traducción al español es automática; en los códigos más comunes, revisada a mano. '
                'Si ves alguna rara, cuéntalo en <a href="https://github.com/jaso69/obd2/issues">GitHub</a>. '
                'Los pocos títulos que no se han podido traducir aparecen en inglés.</p>')
    return ('<p class="aclaracion">Titles from <a href="https://github.com/foerbsnavi/OBDex">OBDex</a>, an open database '
            '(public domain, CC0). If you spot a mistake, please report it on <a href="https://github.com/jaso69/obd2/issues">GitHub</a>.</p>')


def obd2(lang):
    """Escribe las páginas de códigos OBD2 genéricos y su codigos.json; devuelve los pares de URL."""
    t = L[lang]
    otro = "en" if lang == "es" else "es"
    grupos = grupos_obd()
    tema = "tema_" + lang
    for g in grupos:
        fmt = dict(g=g["g"], tema=g[tema], n=len(g["codigos"]))
        h1 = t["obd_h1"].format(**fmt)
        otras = "".join(f'<li><a href="{url_obd(lang, o)}">{o["g"]}</a> · {e(o[tema])}</li>' for o in grupos if o is not g)
        cuerpo = f"""<h1>{e(h1)}</h1>
<p class="intro">{e(t['obd_fdesc'].format(**fmt))}</p>
{buscador(lang, obd=True)}
<h2 id="lista" class="sr">{e(h1)}</h2>
{tabla_obd(lang, g['codigos'])}
{fuente_obd(lang)}
{consejos(lang)}
{descarga(lang)}
<section aria-labelledby="otras-h"><h2 id="otras-h">{t['obd_otras']}</h2><ul class="lista-familias">{otras}</ul></section>"""
        ruta = url_obd(lang, g)
        escribir(ruta, pagina(lang, ruta, url_obd(otro, g), t["obd_ftitle"].format(**fmt), t["obd_fdesc"].format(**fmt),
                              [(t["migas_inicio"], t["inicio"]), (t["nav_obd"], t["obd"]), (g["g"], ruta)], cuerpo))
    tarjetas = "\n".join(
        f'<li class="tarjeta"><a href="{url_obd(lang, g)}"><strong>{g["g"]}</strong></a><span>{e(g[tema])}</span>'
        f'<span class="pequeno">{t["codigos"].format(n=len(g["codigos"]))}</span></li>' for g in grupos)
    cuerpo = f"""<h1>{t['obd_titulo']}</h1>
{intro_obd(lang, len(CODIGOS))}
{buscador(lang, obd=True)}
<h2>{t['familias']}</h2>
<ul class="familias">
{tarjetas}
</ul>
{fuente_obd(lang)}
{consejos(lang)}
{descarga(lang)}"""
    escribir(t["obd"], pagina(lang, t["obd"], L[otro]["obd"], t["obd_title"], t["obd_desc"].format(n=len(CODIGOS)),
                             [(t["migas_inicio"], t["inicio"]), (t["nav_obd"], t["obd"])], cuerpo))
    datos = []
    for g in grupos:
        for c in g["codigos"]:
            datos.append(["", c, texto_obd(lang, c)[0], g["slug"] + "/#" + c])   # enlace relativo al índice
    with open(os.path.join(WEB, t["obd"].strip("/"), "codigos.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(datos, fh, ensure_ascii=False, separators=(",", ":"))
    return [(L["es"]["obd"], L["en"]["obd"])] + [(url_obd("es", g), url_obd("en", g)) for g in grupos]


def pagina_404():
    """404.html bilingüe (Vercel la sirve para cualquier ruta que no exista)."""
    contenido = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Página no encontrada · Page not found · OBD2Desk</title>
<meta name="robots" content="noindex">
<meta name="theme-color" content="#111418">
<link rel="icon" type="image/png" href="/img/icono.png">
<link rel="stylesheet" href="/estilo.css">
</head>
<body>
<header class="cabecera">
  <div class="contenedor cabecera-fila">
    <a class="marca" href="/"><img src="/img/icono.png" alt="" width="32" height="32"> OBD2Desk</a>
  </div>
</header>
<main id="contenido">
<div class="contenedor contenedor-codigos pagina-404">
<p class="etiqueta">Error 404</p>
<h1>Esta página no existe</h1>
<p class="intro">Puede que el enlace esté mal escrito o que la página se haya movido.</p>
<ul class="lista-familias">
<li><a href="/">Página principal de OBD2Desk</a></li>
<li><a href="/codigos-obd2/">Códigos de avería OBD2</a></li>
<li><a href="/averias-vag/">Códigos de avería VAG</a></li>
<li><a href="/guias/">Guías de diagnóstico</a></li>
<li><a href="/#descargar">Descargar el programa</a></li>
</ul>
<div lang="en">
<h2>This page does not exist</h2>
<p>The link may be mistyped or the page may have moved.</p>
<ul class="lista-familias">
<li><a href="/en/">OBD2Desk home page</a></li>
<li><a href="/en/obd2-codes/">OBD2 fault codes</a></li>
<li><a href="/en/vag-fault-codes/">VAG fault codes</a></li>
<li><a href="/en/guides/">Diagnostic guides</a></li>
<li><a href="/en/#descargar">Download the program</a></li>
</ul>
</div>
</div>
</main>
</body>
</html>
"""
    with open(os.path.join(WEB, "404.html"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(contenido)


def main():
    fams = familias()
    total = sum(len(f["filas"]) for f in fams)
    urls = [("/", "/en/")]
    for lang in ("es", "en"):
        t = L[lang]
        otro = "en" if lang == "es" else "es"
        # índice
        tarjetas = "\n".join(
            f'<li class="tarjeta"><a href="{url_fam(lang, f)}"><strong>{e(f["corto_" + lang])}</strong></a>'
            f'<span>{e(f["tema_" + lang])}</span><span class="pequeno">{t["codigos"].format(n=len(f["filas"]))} · {f["rango"]}</span></li>'
            for f in fams)
        cuerpo = f"""<h1>{t['indice_titulo']}</h1>
{intro_indice(lang, total)}
{buscador(lang)}
<h2>{t['familias']}</h2>
<ul class="familias">
{tarjetas}
</ul>
{tipos_fallo(lang)}
{consejos(lang)}
<p class="aclaracion">{t['aviso']}</p>
{descarga(lang)}"""
        escribir(t["base"], pagina(lang, t["base"], L[otro]["base"], t["indice_title"],
                                   t["indice_desc"].format(n=total),
                                   [(t["migas_inicio"], t["inicio"]), (t["nav_averias"], t["base"])], cuerpo))
        # familias
        for f in fams:
            fmt = dict(corto=f["corto_" + lang], tema=f["tema_" + lang], rango=f["rango"], n=len(f["filas"]))
            h1 = t["fam_h1"].format(**fmt)
            if f["tipo"] == "clasico":
                partes = []
                for i, (s_es, s_en, filas) in enumerate(f["sistemas"]):
                    nombre = s_es if lang == "es" else s_en
                    partes.append(f'<h2 id="sistema-{i + 1}">{e(nombre)}</h2>\n' + tabla(lang, filas, False, f"sistema-{i + 1}"))
                tablas = "\n".join(partes)
            else:
                tablas = f'<h2 id="lista" class="sr">{e(h1)}</h2>\n' + tabla(lang, f["filas"], True, "lista")
            cuerpo = f"""<h1>{e(h1)}</h1>
{intro_familia(lang, f)}
{buscador(lang)}
{tablas}
<p class="aclaracion">{t['aviso']}</p>
{consejos(lang)}
{descarga(lang)}
{otras(lang, fams, f)}"""
            ruta = url_fam(lang, f)
            escribir(ruta, pagina(lang, ruta, url_fam(otro, f), t["fam_title"].format(**fmt),
                                  t["fam_desc"].format(**fmt),
                                  [(t["migas_inicio"], t["inicio"]), (t["nav_averias"], t["base"]),
                                   (f["corto_" + lang], ruta)], cuerpo))
        # índice del buscador
        datos = []
        for f in fams:
            for v, p, des_es, des_en in f["filas"]:
                datos.append([f"{v:05d}", p or "", des_es if lang == "es" else des_en, url_fam(lang, f) + f"#{v:05d}"])
        destino = os.path.join(WEB, t["base"].strip("/"), "codigos.json")
        with open(destino, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(datos, fh, ensure_ascii=False, separators=(",", ":"))
    for lang in ("es", "en"):
        pares_guias = guias(lang)
        pares_obd = obd2(lang)
    pagina_404()
    urls.append((L["es"]["base"], L["en"]["base"]))
    urls += [(url_fam("es", f), url_fam("en", f)) for f in fams]
    urls += pares_guias
    urls += pares_obd
    # sitemap completo
    entradas = []
    for es_u, en_u in urls:
        for u in (es_u, en_u):
            entradas.append(f"""  <url>
    <loc>{DOMINIO}{u}</loc>
    <lastmod>{FECHA}</lastmod>
    <xhtml:link rel="alternate" hreflang="es" href="{DOMINIO}{es_u}"/>
    <xhtml:link rel="alternate" hreflang="en" href="{DOMINIO}{en_u}"/>
  </url>""")
    with open(os.path.join(WEB, "sitemap.xml"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                 'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(entradas) + "\n</urlset>\n")
    print(f"{total} códigos VAG en {len(fams)} listas, {len(CODIGOS)} OBD2 en {len(pares_obd) - 1}, {len(GUIAS)} guías, "
          f"español e inglés, 404.html; "
          f"sitemap con {len(urls) * 2} URL.")


if __name__ == "__main__":
    main()
