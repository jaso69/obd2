"""
Informe de diagnóstico en HTML (un solo archivo, sin recursos externos).

Se abre en el navegador y desde ahí se puede imprimir o guardar como PDF.
"""
import datetime
import html

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
        return "<p class='ok'>Sin averías memorizadas.</p>"
    filas = []
    for code, ftype, inter in dtcs:
        tipo = f"{ftype:02d} · {FAULT_TYPES.get(ftype, 'Desconocido') or '—'}"
        estado = "<span class='aviso'>Intermitente</span>" if inter else "<span class='mal'>Presente</span>"
        filas.append((f"<code>{code:05d}</code>", _e(componente(code)), _e(tipo), estado))
    return _tabla(("Código", "Componente", "Tipo de fallo", "Estado"), filas)


def _seccion_obd(d):
    out = []
    mil = d.get("mil")
    out.append(f"<p>Testigo de avería (MIL): "
               f"{'<span class=mal>ENCENDIDO</span>' if mil else '<span class=ok>apagado</span>'}</p>")
    filas = []
    for clave, estado, css in (("stored", "Memorizada", "mal"), ("pending", "Pendiente", "aviso"),
                               ("permanent", "Permanente", "aviso")):
        for code in d.get(clave) or []:
            filas.append((f"<code>{_e(code)}</code>", _e(describe_obd_dtc(code)),
                          f"<span class='{css}'>{estado}</span>"))
    out.append(_tabla(("Código", "Descripción", "Estado"), filas) if filas
               else "<p class='ok'>Sin averías memorizadas, pendientes ni permanentes.</p>")
    ff = d.get("ff")
    out.append("<h2>Datos congelados</h2>")
    if ff:
        out.append(f"<p>Valores del motor en el momento en que se registró la avería "
                   f"<code>{_e(ff['dtc'])}</code> ({_e(describe_obd_dtc(ff['dtc']))}).</p>")
        out.append(_tabla(("Dato", "Valor"), [(_e(n), _e(f"{v} {u}".strip())) for _, n, v, u in ff["values"]]))
    else:
        out.append("<p class='nota'>La centralita no tiene datos congelados guardados.</p>")
    out.append("<h2>Monitores de preparación (readiness)</h2>")
    r = d.get("readiness")
    if r:
        diesel, mons = r
        filas = [(_e(n), "<span class='ok'>Completo</span>" if ok else "<span class='aviso'>Sin completar</span>")
                 for n, ok in mons]
        out.append(f"<p>Motor {'diésel' if diesel else 'de gasolina'}. "
                   f"{sum(1 for _, ok in mons if not ok)} de {len(mons)} sin completar.</p>")
        out.append(_tabla(("Monitor", "Estado"), filas))
        out.append("<p class='nota'>Tras borrar averías o desconectar la batería los monitores vuelven a "
                   "«sin completar» y hacen falta varios ciclos de conducción. En la inspección de emisiones "
                   "(ITV) pueden rechazar el coche si hay monitores sin completar.</p>")
    else:
        out.append("<p class='nota'>No disponible.</p>")
    return "".join(out)


def generar(datos):
    """datos: {"modo": "kkl"|"elm", "version", "vehiculo": [(campo, valor)],
    "dtcs": lista VAG o dict OBD, "modulo": dirección, "escaneo": resultados o None}."""
    ahora = datetime.datetime.now()
    kkl = datos["modo"] == "kkl"
    out = [f"<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>"
           f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>Informe de diagnóstico · {ahora:%d/%m/%Y %H:%M}</title><style>{CSS}</style></head><body>",
           "<h1>Informe de diagnóstico</h1>",
           f"<p class='sub'>{ahora:%d/%m/%Y %H:%M} · Toledo Diagnosis {_e(datos.get('version', ''))} · "
           f"{'KKL · VAG KW1281' if kkl else 'ELM327 · OBD2'}</p>",
           "<button class='boton' onclick='window.print()'>Imprimir o guardar como PDF</button>",
           "<h2>Vehículo</h2>", _campos(datos.get("vehiculo") or [("Datos", "no disponibles")])]
    if kkl:
        esc = datos.get("escaneo")
        if esc:
            resp = [m for m in esc if m["ok"]]
            total = sum(len(m["dtcs"] or []) for m in resp)
            out.append(f"<h2>Escaneo de módulos</h2><p>Responden {len(resp)} de {len(esc)} módulos probados · "
                       f"{total} avería(s) en total.</p>")
            for m in resp:
                ident = " · ".join(x.strip() for x in m["ident"][:2] if x.strip())
                out.append(f"<h3>{m['addr']:02X} · {_e(MODULOS.get(m['addr'], 'Módulo'))}"
                           f"{' — ' + _e(ident) if ident else ''}</h3>")
                out.append(_dtcs_vag(m["dtcs"]) if m["dtcs"] is not None
                           else f"<p class='mal'>No se pudieron leer las averías: {_e(m['error'])}</p>")
            sin = [f"{m['addr']:02X}" for m in esc if not m["ok"]]
            if sin:
                out.append(f"<p class='nota'>Sin respuesta (no instalados o no accesibles por línea K): "
                           f"{', '.join(sin)}.</p>")
        if datos.get("dtcs") is not None:
            addr = datos.get("modulo", 1)
            out.append(f"<h2>Averías · módulo {addr:02X} ({_e(MODULOS.get(addr, '?'))})</h2>"
                       + ("<p class='nota'>Lectura hecha al generar el informe.</p>" if esc else ""))
            out.append(_dtcs_vag(datos["dtcs"]))
    else:
        out.append("<h2>Averías</h2>")
        out.append(_seccion_obd(datos.get("dtcs") or {}))
    out.append("<h2>Notas</h2><ul class='nota'><li>Borrar un código no repara la avería: si la causa sigue, "
               "vuelve a aparecer.</li><li>Las descripciones de los códigos son orientativas; confírmalas con "
               "la documentación del fabricante.</li></ul>"
               "<p class='nota'>Generado con Toledo Diagnosis · https://www.jasodev.es</p></body></html>")
    return "".join(out)
