# -*- coding: utf-8 -*-
"""
Modulo comun del trombinoscopio de las Cortes Generales.

Contiene:
  - normalizacion de texto para busqueda sin acentos
  - colores corporativos por grupo parlamentario
  - la plantilla HTML compartida por los tres trombinoscopios

No hace peticiones de red. Lo importan congreso.py, senado.py y
diputacion_permanente.py.
"""

import datetime
import json
import re
import unicodedata

# --------------------------------------------------------------------------
# Colores por grupo parlamentario (siglas oficiales de cada camara)
# --------------------------------------------------------------------------
COLORES = {
    # Congreso
    "GP": "#0056a3",
    "GS": "#e30613",
    "GVOX": "#5ac035",
    "GSUMAR": "#e5007d",
    "GR": "#ffb400",
    "GJxCAT": "#00c3b2",
    "GEH Bildu": "#a3c940",
    "GV (EAJ-PNV)": "#009540",
    "GMx": "#8a8a8a",
    # Senado
    "GPP": "#0056a3",
    "GPS": "#e30613",
    "GPERB": "#ffb400",
    "GPPLU": "#00c3b2",
    "GPV": "#009540",
    "GPIC": "#e5007d",
    "GPMX": "#8a8a8a",
}

ORDEN_CONGRESO = ["GP", "GS", "GVOX", "GSUMAR", "GR", "GJxCAT",
                  "GEH Bildu", "GV (EAJ-PNV)", "GMx"]
ORDEN_SENADO = ["GPP", "GPS", "GPERB", "GPPLU", "GPV", "GPIC", "GPMX"]


def norm(texto):
    """Minusculas sin acentos, para busquedas y ordenaciones."""
    return "".join(
        c for c in unicodedata.normalize("NFD", (texto or "").lower())
        if unicodedata.category(c) != "Mn"
    )


def hoy():
    return datetime.date.today().strftime("%d/%m/%Y")


def _css_colores():
    return "\n".join(
        ".b-%s{background:%s}" % (re.sub(r"[^A-Za-z0-9]", "", k), v)
        for k, v in COLORES.items()
    )


PLANTILLA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%%TITULO%%</title>
<style>
:root{--tinta:#14181d;--gris:#6b7280;--linea:#e3e6ea;--fondo:#f5f6f8;}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--tinta);background:var(--fondo)}
header{background:#14181d;color:#fff;padding:18px 22px}
header h1{margin:0;font-size:19px;font-weight:600;letter-spacing:.2px}
header p{margin:5px 0 0;font-size:12.5px;color:#a9b1bb}
header nav{margin-top:9px;font-size:12.5px}
header nav a{color:#a9b1bb;text-decoration:none;margin-right:14px;border-bottom:1px solid transparent}
header nav a:hover{color:#fff;border-bottom-color:#fff}
header nav a.activo{color:#fff;font-weight:600}
.barra{position:sticky;top:0;z-index:20;background:#fff;border-bottom:1px solid var(--linea);padding:10px 22px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.barra input,.barra select{font:inherit;font-size:13px;padding:6px 9px;border:1px solid var(--linea);border-radius:5px;background:#fff}
.barra input{min-width:230px}
#contador{margin-left:auto;font-size:12.5px;color:var(--gris)}
main{padding:16px 22px 50px}
h2.sec{font-size:13px;text-transform:uppercase;letter-spacing:1.1px;color:var(--gris);margin:26px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--linea)}
.rejilla{display:grid;grid-template-columns:repeat(auto-fill,minmax(158px,1fr));gap:12px}
.f{background:#fff;border:1px solid var(--linea);border-radius:7px;overflow:hidden;display:flex;flex-direction:column;text-decoration:none;color:inherit}
.f:hover{border-color:#9aa3ad}
.f .marco{aspect-ratio:3/4;background:#dfe3e8;overflow:hidden}
.f img{width:100%;height:100%;object-fit:cover;display:block}
.f .txt{padding:7px 8px 9px}
.f .nom{font-size:12.5px;font-weight:600;line-height:1.25}
.f .car{font-size:11px;color:#14181d;font-weight:600;margin-top:3px}
.f .cir{font-size:11px;color:var(--gris);margin-top:2px}
.tag{display:inline-block;margin-top:5px;padding:2px 6px;border-radius:3px;color:#fff;font-size:10px;font-weight:700;letter-spacing:.3px}
%%COLORES%%
footer{padding:18px 22px;font-size:11.5px;color:var(--gris);border-top:1px solid var(--linea)}
@media print{
 .barra,header nav{display:none} header{background:#fff;color:#000;border-bottom:2px solid #000}
 header p{color:#444} body{background:#fff}
 .rejilla{grid-template-columns:repeat(6,1fr);gap:6px}
 .f{break-inside:avoid;border:1px solid #bbb}
 h2.sec{break-after:avoid}
}
</style>
</head>
<body>
<header>
  <h1>%%CABECERA%%</h1>
  <p>%%SUBTITULO%%</p>
  <nav>%%NAV%%</nav>
</header>
<div class="barra">
  <input type="search" id="q" placeholder="Buscar por nombre, grupo, partido o territorio...">
  %%FILTROS%%
  <span id="contador"></span>
</div>
<main id="salida"></main>
<footer>%%PIE%%</footer>
<script>
const D = %%DATOS%%;
const AGRUPACIONES = %%AGRUPACIONES%%;
const $ = s => document.querySelector(s);
const clase = s => 'b-' + s.replace(/[^A-Za-z0-9]/g,'');
const norm = s => s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();

function valor(id){ const e = $(id); return e ? e.value : ''; }

function pinta(){
  const q = norm(valor('#q').trim());
  const filtros = ['#grupo','#territorio','#sexo','#condicion','#camara']
        .filter(id => $(id)).map(id => [id.slice(1), valor(id)]);
  const lista = D.filter(p => {
    if (q && !p.buscar.includes(q)) return false;
    for (const [campo, v] of filtros){
      if (!v) continue;
      if (campo === 'grupo'      && p.siglas    !== v) return false;
      if (campo === 'territorio' && p.territorio!== v) return false;
      if (campo === 'sexo'       && p.sexo      !== v) return false;
      if (campo === 'condicion'  && p.condicion !== v) return false;
      if (campo === 'camara'     && p.camara    !== v) return false;
    }
    return true;
  });
  const modo = valor('#orden') || AGRUPACIONES[0];
  let out = '';
  if (modo === 'alfa'){
    const orden = [...lista].sort((a,b) => norm(a.nombre) < norm(b.nombre) ? -1 : 1);
    out = '<h2 class="sec">Orden alfabetico (' + orden.length + ')</h2>' +
          '<div class="rejilla">' + orden.map(ficha).join('') + '</div>';
  } else {
    const secs = {}, orden = [];
    lista.forEach(p => {
      const k = p[modo] || 'Sin asignar';
      if (!(k in secs)){ secs[k] = []; orden.push(k); }
      secs[k].push(p);
    });
    if (modo === 'territorio') orden.sort((a,b) => norm(a) < norm(b) ? -1 : 1);
    orden.forEach(k => {
      out += '<h2 class="sec">' + k + ' (' + secs[k].length + ')</h2>' +
             '<div class="rejilla">' + secs[k].map(ficha).join('') + '</div>';
    });
  }
  $('#salida').innerHTML = out || '<p style="color:#6b7280">Sin resultados.</p>';
  $('#contador').textContent = lista.length + ' de ' + D.length + ' fichas';
}

function ficha(p){
  const img = p.foto
    ? '<img loading="lazy" src="' + p.foto + '" alt="' + p.nombre + '">'
    : '';
  return '<a class="f" href="' + p.ficha + '" target="_blank" rel="noopener">' +
    '<div class="marco">' + img + '</div>' +
    '<div class="txt"><div class="nom">' + p.nombre + '</div>' +
    (p.cargo ? '<div class="car">' + p.cargo + '</div>' : '') +
    (p.detalle ? '<div class="cir">' + p.detalle + '</div>' : '') +
    '<span class="tag ' + clase(p.siglas) + '" title="' + p.grupo + '">' + p.siglas + '</span>' +
    '</div></a>';
}

['#q','#grupo','#territorio','#sexo','#condicion','#camara','#orden']
  .forEach(s => { const e = $(s); if (e) e.addEventListener('input', pinta); });
pinta();
</script>
</body>
</html>"""


NAV_ITEMS = [
    ("index.html", "Inicio"),
    ("congreso.html", "Congreso"),
    ("senado.html", "Senado"),
    ("diputacion-permanente.html", "Diputacion Permanente"),
    ("comisiones-congreso.html", "Comisiones Congreso"),
    ("comisiones-senado.html", "Comisiones Senado"),
]


def _nav(activo):
    partes = []
    for href, etiqueta in NAV_ITEMS:
        cls = ' class="activo"' if href == activo else ""
        partes.append('<a href="%s"%s>%s</a>' % (href, cls, etiqueta))
    return "".join(partes)


def render(ruta, titulo, cabecera, subtitulo, personas, filtros_html,
           agrupaciones, pie, activo):
    """Escribe un trombinoscopio completo en `ruta`.

    personas: lista de dicts con las claves
      nombre, siglas, grupo, cargo, detalle, foto, ficha, buscar
      y, opcionalmente, territorio / sexo / condicion / camara.
    agrupaciones: lista de campos por los que se puede agrupar
      ('grupo', 'territorio', 'condicion', 'camara', 'alfa').
    """
    html = (PLANTILLA
            .replace("%%TITULO%%", titulo)
            .replace("%%CABECERA%%", cabecera)
            .replace("%%SUBTITULO%%", subtitulo)
            .replace("%%NAV%%", _nav(activo))
            .replace("%%COLORES%%", _css_colores())
            .replace("%%FILTROS%%", filtros_html)
            .replace("%%AGRUPACIONES%%", json.dumps(agrupaciones))
            .replace("%%DATOS%%", json.dumps(personas, ensure_ascii=False))
            .replace("%%PIE%%", pie))
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("  escrito %s (%d fichas)" % (ruta, len(personas)))
