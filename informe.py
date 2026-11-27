"""
Informe de diagnóstico en HTML (un solo archivo, sin recursos externos).

Se abre en el navegador y desde ahí se puede imprimir o guardar como PDF.
"""
import datetime
import html
import re

import idioma
from idioma import tr
from obd_datos import describe_dtc as describe_obd_dtc
from vag_datos import FAULT_TYPES, MODULOS, componente

CSS = """
body{font-family:system-ui,"Segoe UI",Roboto,"DejaVu Sans",sans-serif;color:#1d232b;max-width:900px;margin:2em auto;padding:0 1.2em;line-height:1.45}
h1{font-size:1.6em;margin:0 0 .2em}h2{font-size:1.15em;margin:1.8em 0 .6em;padding-bottom:.25em;border-bottom:2px solid #ff7a29}
h3{font-size:1em;margin:1.2em 0 .4em}.sub{color:#5b6573;margin:0}
table{border-collapse:collapse;width:100%;margin:.3em 0 .8em;font-size:.95em}
th,td{text-align:left;padding:.35em .6em;border-bottom:1px solid #dde1e6;vertical-align:top}
th{background:#f3f5f7;font-weight:600}td.k{color:#5b6573;width:32%}
.ok{color:#17803d;font-weight:600}.mal{color:#c62828;font-weight:600}.aviso{color:#a86500;font-weight:600}
.nota{color:#5b6573;font-size:.9em}code{font-family:Consolas,"DejaVu Sans Mono",monospace}
.boton{margin:1.2em 0;padding:.5em 1em;border:0;border-radius:6px;background:#ff7a29;color:#111;font-weight:600;cursor:pointer}
@media print{.boton{display:none}body{margin:0;max-width:none}h2{break-after:avoid}tr{break-inside:avoid}}
"""


def _e(x):
    return html.escape(str(x))


def _markdown(texto):
    """Markdown sencillo (## títulos, listas con -, **negrita**) a HTML, escapando todo lo demás."""
    out, lista = [], False
    for linea in str(texto).splitlines():
        t = linea.strip()
        neg = lambda x: re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", _e(x))
        es_item = t.startswith(("- ", "* "))
        if lista and not es_item:
            out.append("</ul>")
            lista = False
        if t.startswith("#"):
            out.append(f"<h3>{neg(t.lstrip('#').strip())}</h3>")
        elif es_item:
            if not lista:
                out.append("<ul>")
                lista = True
            out.append(f"<li>{neg(t[2:].strip())}</li>")
        elif t:
            out.append(f"<p>{neg(t)}</p>")
    if lista:
        out.append("</ul>")
    return "".join(out)


def _tabla(cabecera, filas):
    out = ["<table><tr>" + "".join(f"<th>{_e(c)}</th>" for c in cabecera) + "</tr>"]
    for f in filas:
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in f) + "</tr>")
    return "".join(out) + "</table>"


def _campos(campos):
    return "<table>" + "".join(f"<tr><td class='k'>{_e(k)}</td><td>{_e(v)}</td></tr>"
                               for k, v in campos) + "</table>"


def _dtcs_vag(dtcs):
    if not dtcs:
        return f"<p class='ok'>{_e(tr('Sin averías memorizadas.'))}</p>"
    filas = []
    for code, ftype, inter in dtcs:
        tipo = f"{ftype:02d} · {FAULT_TYPES.get(ftype, tr('Desconocido')) or '—'}"
        estado = (f"<span class='aviso'>{_e(tr('Intermitente'))}</span>" if inter
                  else f"<span class='mal'>{_e(tr('Presente'))}</span>")
        filas.append((f"<code>{code:05d}</code>", _e(componente(code)), _e(tipo), estado))
    return _tabla((tr("Código"), tr("Componente"), tr("Tipo de fallo"), tr("Estado")), filas)


def _seccion_obd(d):
    out = []
    mil = d.get("mil")
    out.append(f"<p>{_e(tr('Testigo de avería (MIL)'))}: "
               + (f"<span class=mal>{_e(tr('ENCENDIDO'))}</span>" if mil else f"<span class=ok>{_e(tr('apagado'))}</span>")
               + "</p>")
    filas = []
    for clave, estado, css in (("stored", tr("Memorizada"), "mal"), ("pending", tr("Pendiente"), "aviso"),
                               ("permanent", tr("Permanente"), "aviso")):
        for code in d.get(clave) or []:
            filas.append((f"<code>{_e(code)}</code>", _e(describe_obd_dtc(code)),
                          f"<span class='{css}'>{_e(estado)}</span>"))
    out.append(_tabla((tr("Código"), tr("Descripción"), tr("Estado")), filas) if filas
               else f"<p class='ok'>{_e(tr('Sin averías memorizadas, pendientes ni permanentes.'))}</p>")
    ff = d.get("ff")
    out.append(f"<h2>{_e(tr('Datos congelados'))}</h2>")
    if ff:
        out.append("<p>" + tr("Valores del motor en el momento en que se registró la avería {dtc} ({desc}).",
                              dtc=f"<code>{_e(ff['dtc'])}</code>", desc=_e(describe_obd_dtc(ff["dtc"]))) + "</p>")
        out.append(_tabla((tr("Dato"), tr("Valor")),
                          [(_e(n), _e(f"{v} {u}".strip())) for _, n, v, u in ff["values"]]))
    else:
        out.append(f"<p class='nota'>{_e(tr('La centralita no tiene datos congelados guardados.'))}</p>")
    out.append(f"<h2>{_e(tr('Monitores de preparación (readiness)'))}</h2>")
    r = d.get("readiness")
    if r:
        diesel, mons = r
        filas = [(_e(n), f"<span class='ok'>{_e(tr('Completo'))}</span>" if ok
                  else f"<span class='aviso'>{_e(tr('Sin completar'))}</span>") for n, ok in mons]
        out.append("<p>" + _e((tr("Motor diésel") if diesel else tr("Motor de gasolina")) + ". "
                              + tr("{n} de {total} sin completar.", n=sum(1 for _, ok in mons if not ok),
                                   total=len(mons))) + "</p>")
        out.append(_tabla(("Monitor", tr("Estado")), filas))
        out.append("<p class='nota'>" + _e(tr("Tras borrar averías o desconectar la batería los monitores vuelven a "
                                               "«sin completar» y hacen falta varios ciclos de conducción. En la "
                                               "inspección de emisiones (ITV) pueden rechazar el coche si hay "
                                               "monitores sin completar.")) + "</p>")
    else:
        out.append(f"<p class='nota'>{_e(tr('No disponible.'))}</p>")
    return "".join(out)


def generar(datos):
    """datos: {"modo": "kkl"|"elm", "version", "vehiculo": [(campo, valor)],
    "dtcs": lista VAG o dict OBD, "modulo": dirección, "escaneo": resultados o None}."""
    ahora = datetime.datetime.now()
    kkl = datos["modo"] == "kkl"
    fecha = f"{ahora:%d/%m/%Y %H:%M}" if idioma.actual() == "es" else f"{ahora:%Y-%m-%d %H:%M}"
    titulo = _e(tr("Informe de diagnóstico"))
    out = [f"<!DOCTYPE html><html lang='{idioma.actual()}'><head><meta charset='utf-8'>"
           f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>{titulo} · {fecha}</title><style>{CSS}</style></head><body>",
           f"<h1>{titulo}</h1>",
           f"<p class='sub'>{fecha} · OBD2Desk {_e(datos.get('version', ''))} · "
           f"{'KKL · VAG KW1281' if kkl else 'ELM327 · OBD2'}</p>",
           f"<button class='boton' onclick='window.print()'>{_e(tr('Imprimir o guardar como PDF'))}</button>",
           f"<h2>{_e(tr('Vehículo'))}</h2>",
           _campos(datos.get("vehiculo") or [(tr("Datos"), tr("no disponibles"))])]
    if kkl:
        esc = datos.get("escaneo")
        if esc:
            resp = [m for m in esc if m["ok"]]
            total = sum(len(m["dtcs"] or []) for m in resp)
            out.append(f"<h2>{_e(tr('Escaneo de módulos'))}</h2><p>"
                       + _e(tr("Responden {n} de {total} módulos probados · {averias} avería(s) en total.",
                               n=len(resp), total=len(esc), averias=total)) + "</p>")
            for m in resp:
                ident = " · ".join(x.strip() for x in m["ident"][:2] if x.strip())
                out.append(f"<h3>{m['addr']:02X} · {_e(MODULOS.get(m['addr'], tr('Módulo')))}"
                           f"{' — ' + _e(ident) if ident else ''}</h3>")
                out.append(_dtcs_vag(m["dtcs"]) if m["dtcs"] is not None
                           else "<p class='mal'>" + _e(tr("No se pudieron leer las averías: {e}", e=m["error"])) + "</p>")
            sin = [f"{m['addr']:02X}" for m in esc if not m["ok"]]
            if sin:
                out.append("<p class='nota'>" + _e(tr("Sin respuesta (no instalados o no accesibles por línea K): "
                                                      "{lista}.", lista=", ".join(sin))) + "</p>")
        if datos.get("dtcs") is not None:
            addr = datos.get("modulo", 1)
            out.append("<h2>" + _e(tr("Averías · módulo {dir} ({nombre})", dir=f"{addr:02X}",
                                      nombre=MODULOS.get(addr, "?"))) + "</h2>"
                       + (f"<p class='nota'>{_e(tr('Lectura hecha al generar el informe.'))}</p>" if esc else ""))
            out.append(_dtcs_vag(datos["dtcs"]))
    else:
        out.append(f"<h2>{_e(tr('Averías'))}</h2>")
        out.append(_seccion_obd(datos.get("dtcs") or {}))
    if datos.get("historial"):
        out.append(f"<h2>{_e(tr('Comparación con el diagnóstico anterior'))}</h2><p>{_e(datos['historial'])}</p>")
    if datos.get("diagnostico_ia"):
        out.append(f"<h2>{_e(tr('Diagnóstico del asistente IA'))}</h2>" + _markdown(datos["diagnostico_ia"])
                   + f"<p class='nota'>{_e(tr('Redactado por la IA a partir de los datos leídos del coche. Es orientativo: confírmalo antes de cambiar piezas.'))}</p>")
    out.append(f"<h2>{_e(tr('Notas'))}</h2><ul class='nota'>"
               f"<li>{_e(tr('Borrar un código no repara la avería: si la causa sigue, vuelve a aparecer.'))}</li>"
               f"<li>{_e(tr('Las descripciones de los códigos son orientativas; confírmalas con la documentación del fabricante.'))}</li></ul>"
               f"<p class='nota'>{_e(tr('Generado con OBD2Desk'))} · https://obd2desk.com</p></body></html>")
    return "".join(out)
