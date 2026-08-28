# -*- coding: utf-8 -*-
"""
Plantilla compartida por los trombinoscopios de comisiones (Congreso y Senado).

A diferencia de comun.render, que pinta una sola rejilla de fichas, aqui la
pagina tiene dos modos: elegir una comision y ver su composicion agrupada por
cargo, o buscar una persona y ver de que comisiones forma parte.

El modelo de datos separa personas y comisiones para no repetir cada ficha en
cada comision a la que pertenece: una persona puede estar en diez.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402

# Orden en que se muestran los cargos dentro de una comision.
ORDEN_CARGO = [
    "Presidente", "Presidenta", "Coordinador: Presidente", "Coordinadora: Presidenta",
    "Vicepresidente Primero", "Vicepresidenta Primera",
    "Vicepresidente Segundo", "Vicepresidenta Segunda",
    "Vicepresidenta Tercera", "Vicepresidenta Cuarta", "Vicepresidente", "Vicepresidenta",
    "Secretario Primero", "Secretaria Primera", "Secretario Segundo", "Secretaria Segunda",
    "Secretario Tercero", "Secretaria Cuarta", "Secretario", "Secretaria",
    "Portavoz", "Portavoces", "Portavoz adjunto", "Portavoces adjuntos",
    "Ponente Coordinador", "Ponentes", "Ponentes Suplentes",
    "Vocal", "Vocales", "Vocales Suplentes",
    "Adscritos", "Adscrito", "Adscrita",
    "Letrado", "Letrada", "Letrados",
]
IDX_CARGO = {c: i for i, c in enumerate(ORDEN_CARGO)}


def orden_cargo(nombre):
    return IDX_CARGO.get(nombre, 90)


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
.barra input{min-width:250px}
.barra select#com{min-width:300px;max-width:520px}
#contador{margin-left:auto;font-size:12.5px;color:var(--gris)}
main{padding:16px 22px 60px}
h2.tit{font-size:17px;margin:6px 0 2px}
p.sub{margin:0 0 14px;font-size:12.5px;color:var(--gris)}
h3.sec{font-size:12.5px;text-transform:uppercase;letter-spacing:1.1px;color:var(--gris);margin:22px 0 9px;padding-bottom:5px;border-bottom:1px solid var(--linea)}
.rejilla{display:grid;grid-template-columns:repeat(auto-fill,minmax(158px,1fr));gap:12px}
.f{background:#fff;border:1px solid var(--linea);border-radius:7px;overflow:hidden;display:flex;flex-direction:column;text-decoration:none;color:inherit}
.f:hover{border-color:#9aa3ad}
.f .marco{aspect-ratio:3/4;background:#dfe3e8;overflow:hidden;display:flex;align-items:center;justify-content:center}
.f img{width:100%;height:100%;object-fit:cover;display:block}
.f .ini{font-size:30px;font-weight:600;color:#98a1ab}
.f .txt{padding:7px 8px 9px}
.f .nom{font-size:12.5px;font-weight:600;line-height:1.25}
.f .car{font-size:11px;color:#14181d;font-weight:600;margin-top:3px}
.f .cir{font-size:11px;color:var(--gris);margin-top:2px}
.tag{display:inline-block;margin-top:5px;padding:2px 6px;border-radius:3px;color:#fff;font-size:10px;font-weight:700;letter-spacing:.3px}
%%COLORES%%
.pers{background:#fff;border:1px solid var(--linea);border-radius:7px;padding:12px 14px;margin-bottom:10px;display:flex;gap:14px}
.pers .mini{width:62px;height:83px;flex:none;background:#dfe3e8;border-radius:4px;overflow:hidden}
.pers .mini img{width:100%;height:100%;object-fit:cover}
.pers h4{margin:0;font-size:14px}
.pers ul{margin:7px 0 0;padding-left:17px;font-size:12.5px;color:#374151}
.pers li{margin-bottom:2px}
footer{padding:18px 22px;font-size:11.5px;color:var(--gris);border-top:1px solid var(--linea)}
@media print{
 .barra,header nav{display:none} header{background:#fff;color:#000;border-bottom:2px solid #000}
 header p{color:#444} body{background:#fff}
 .rejilla{grid-template-columns:repeat(6,1fr);gap:6px}
 .f{break-inside:avoid;border:1px solid #bbb}
 h3.sec{break-after:avoid}
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
  <select id="com"><option value="">-- Elige una comision --</option>%%OPTS%%</select>
  <select id="tipo"><option value="">Todos los tipos</option>%%OPTSTIPO%%</select>
  <input type="search" id="q" placeholder="Buscar persona o comision...">
  <select id="cond"><option value="">Todos</option>%%OPTSCOND%%</select>
  <span id="contador"></span>
</div>
<main id="salida"></main>
<footer>%%PIE%%</footer>
<script>
const P = %%PERSONAS%%;
const C = %%COMISIONES%%;
const $ = s => document.querySelector(s);
const clase = s => 'b-' + (s.replace(/[^A-Za-z0-9]/g,'') || 'NA');
const norm = s => s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();
const esc = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');

function ficha(idx, cargo){
  const p = P[idx];
  const img = p.f ? '<img loading="lazy" src="' + p.f + '" alt="' + esc(p.n) + '">'
                  : '<span class="ini">' + esc(p.n.charAt(0)) + '</span>';
  const ini = p.u ? '<a class="f" href="' + p.u + '" target="_blank" rel="noopener">'
                  : '<div class="f">';
  const fin = p.u ? '</a>' : '</div>';
  return ini + '<div class="marco">' + img + '</div><div class="txt">' +
    '<div class="nom">' + esc(p.n) + '</div>' +
    (cargo ? '<div class="car">' + esc(cargo) + '</div>' : '') +
    '<div class="cir">' + esc(p.d) + '</div>' +
    '<span class="tag ' + clase(p.g) + '">' + esc(p.g || p.c) + '</span>' +
    '</div>' + fin;
}

function pintaComision(i, cond){
  const c = C[i];
  let out = '<h2 class="tit">' + esc(c.n) + '</h2><p class="sub">' + esc(c.t) +
            (c.fc ? ' &middot; Constituida el ' + esc(c.fc) : '') +
            ' &middot; ' + c.m.length + ' miembros</p>';
  const secs = {}, orden = [];
  let n = 0;
  c.m.forEach(m => {
    if (cond && P[m.p].c !== cond) return;
    if (!(m.r in secs)){ secs[m.r] = []; orden.push(m.r); }
    secs[m.r].push(m); n++;
  });
  orden.forEach(r => {
    out += '<h3 class="sec">' + esc(r) + ' (' + secs[r].length + ')</h3><div class="rejilla">' +
           secs[r].map(m => ficha(m.p, '')).join('') + '</div>';
  });
  $('#contador').textContent = n + ' miembros';
  return n ? out : '<p style="color:#6b7280">Sin resultados.</p>';
}

function pintaBusqueda(q, tipo, cond){
  const cs = C.map((c,i) => [c,i]).filter(([c]) => (!tipo || c.t === tipo));
  const permitidas = new Set(cs.map(([,i]) => i));
  const comsHit = cs.filter(([c]) => c.b.includes(q));
  const persHit = P.map((p,i) => [p,i])
    .filter(([p]) => p.b.includes(q) && (!cond || p.c === cond))
    .filter(([p]) => (p.cs || []).some(([ci]) => permitidas.has(ci)));

  let out = '';
  if (comsHit.length){
    out += '<h3 class="sec">Comisiones que coinciden (' + comsHit.length + ')</h3>';
    out += comsHit.map(([c,i]) =>
      '<div class="pers"><div><h4><a href="#" onclick="elegir(' + i + ');return false;">' +
      esc(c.n) + '</a></h4><ul><li>' + esc(c.t) + ' &middot; ' + c.m.length +
      ' miembros</li></ul></div></div>').join('');
  }
  if (persHit.length){
    out += '<h3 class="sec">Personas que coinciden (' + persHit.length + ')</h3>';
    out += persHit.map(([p]) => {
      const lis = (p.cs || []).filter(([ci]) => permitidas.has(ci))
        .map(([ci,r]) => '<li><a href="#" onclick="elegir(' + ci + ');return false;">' +
             esc(C[ci].n) + '</a> &mdash; ' + esc(r) + '</li>').join('');
      const img = p.f ? '<img loading="lazy" src="' + p.f + '" alt="">' : '';
      return '<div class="pers"><div class="mini">' + img + '</div><div>' +
             '<h4>' + esc(p.n) + ' <span class="tag ' + clase(p.g) + '">' +
             esc(p.g || p.c) + '</span></h4>' +
             '<div style="font-size:12px;color:#6b7280">' + esc(p.d) + '</div>' +
             '<ul>' + lis + '</ul></div></div>';
    }).join('');
  }
  $('#contador').textContent = comsHit.length + ' comisiones, ' + persHit.length + ' personas';
  return out || '<p style="color:#6b7280">Sin resultados.</p>';
}

function elegir(i){
  $('#com').value = String(i);
  $('#q').value = '';
  pinta();
  window.scrollTo(0,0);
}

function pinta(){
  const q = norm($('#q').value.trim()), tipo = $('#tipo').value,
        cond = $('#cond').value, sel = $('#com').value;
  if (q){ $('#salida').innerHTML = pintaBusqueda(q, tipo, cond); return; }
  if (sel !== ''){ $('#salida').innerHTML = pintaComision(+sel, cond); return; }
  let out = '', tActual = '', n = 0;
  C.forEach((c,i) => {
    if (tipo && c.t !== tipo) return;
    if (c.t !== tActual){ tActual = c.t; out += '<h3 class="sec">' + esc(tActual) + '</h3>'; }
    out += '<div class="pers"><div><h4><a href="#" onclick="elegir(' + i + ');return false;">' +
           (c.s ? '&rsaquo; ' : '') + esc(c.n) + '</a></h4>' +
           '<ul><li>' + c.m.length + ' miembros' +
           (c.fc ? ' &middot; constituida el ' + esc(c.fc) : '') + '</li></ul></div></div>';
    n++;
  });
  $('#contador').textContent = n + ' comisiones';
  $('#salida').innerHTML = out;
}

['#com','#tipo','#q','#cond'].forEach(s => $(s).addEventListener('input', pinta));
$('#tipo').addEventListener('change', () => { $('#com').value = ''; pinta(); });
pinta();
</script>
</body>
</html>"""


def render(ruta, titulo, cabecera, subtitulo, personas, comisiones,
           tipos, condiciones, pie, activo):
    """Escribe un trombinoscopio de comisiones completo en `ruta`."""
    opts = "".join('<option value="%d">%s</option>' % (i, c["n"])
                   for i, c in enumerate(comisiones))
    html = (PLANTILLA
            .replace("%%TITULO%%", titulo)
            .replace("%%CABECERA%%", cabecera)
            .replace("%%SUBTITULO%%", subtitulo)
            .replace("%%NAV%%", comun._nav(activo))
            .replace("%%COLORES%%", comun._css_colores() + "\n.b-NA{background:#b4bac1}")
            .replace("%%OPTS%%", opts)
            .replace("%%OPTSTIPO%%", "".join("<option>%s</option>" % t for t in tipos))
            .replace("%%OPTSCOND%%", "".join("<option>%s</option>" % c for c in condiciones))
            .replace("%%PERSONAS%%", json.dumps(personas, ensure_ascii=False, separators=(",", ":")))
            .replace("%%COMISIONES%%", json.dumps(comisiones, ensure_ascii=False, separators=(",", ":")))
            .replace("%%PIE%%", pie))
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("  escrito %s (%d comisiones, %d personas)"
          % (ruta, len(comisiones), len(personas)))


def mapa_fotos_senado(docs):
    """Nombre normalizado -> (url ficha, url foto) a partir de docs/senado.json.

    Lo genera senado.py. Sirve para poner cara a los senadores que aparecen en
    las comisiones mixtas del Congreso, que congreso.es publica sin fotografia.
    Si el fichero no existe todavia, se devuelve vacio y esas fichas salen con
    la inicial en vez de la foto.
    """
    ruta = os.path.join(docs, "senado.json")
    if not os.path.exists(ruta):
        return {}
    with open(ruta, encoding="utf-8") as fh:
        datos = json.load(fh)
    return {comun.norm(p["nombre"]): (p.get("ficha", ""), p.get("foto", ""))
            for p in datos}
