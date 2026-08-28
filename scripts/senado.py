# -*- coding: utf-8 -*-
"""
Trombinoscopio del Senado (XV Legislatura).

El Senado no publica un listado unico que empareje senador y fotografia:
el codigo de la foto (S15NNN) NO se deduce del identificador de ficha (id1).
Por eso el proceso es en dos pasos:

  1. Listados por grupo parlamentario (electos por circunscripcion y
     designados por parlamentos autonomicos) -> id1 + nombre + grupo.
     Son 14 paginas y por construccion suman el total de la Camara.
  2. Una peticion por ficha para extraer la URL de la foto y la procedencia.

senado.es cachea la sesion de forma agresiva y devuelve la misma ficha
repetida si se reutiliza la conexion, asi que cada ficha se pide con una
requests.Session() nueva y un GET semilla que obtiene un JSESSIONID fresco.

Las fichas se cachean en .cache/ para que las reejecuciones sean rapidas.

Genera docs/senado.html.

Uso:  python scripts/senado.py
      python scripts/senado.py --sin-cache
"""

import json
import os
import re
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402

BASE = "https://www.senado.es"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

CABECERAS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

# Codigos internos de los grupos parlamentarios del Senado en la XV Legislatura
GRUPOS = {
    801: ("GPP", "Grupo Parlamentario Popular en el Senado"),
    800: ("GPS", "Grupo Parlamentario Socialista"),
    805: ("GPERB", "Grupo Parlamentario Izquierdas por la Independencia (ERC-EH Bildu)"),
    807: ("GPPLU", "Grupo Parlamentario Plural (Junts-CC-AHI-BNG)"),
    803: ("GPV", "Grupo Parlamentario Vasco en el Senado (EAJ-PNV)"),
    804: ("GPIC", "Grupo Parlamentario Izquierda Confederal"),
    806: ("GPMX", "Grupo Parlamentario Mixto"),
}

RUTA_ELECTOS = (BASE + "/web/composicionorganizacion/senadores/composicionsenado"
                "/consultagrupoparlamentario/listadodetallegruposcircuns/index.html"
                "?id1=%d&id2=POR_CIRC")
RUTA_DESIGNADOS = (BASE + "/web/composicionorganizacion/senadores/composicionsenado"
                   "/consultagrupoparlamentario/listadogruposcomunidad/index.html"
                   "?id1=%d&id2=POR_CA")
RUTA_FICHA = (BASE + "/web/composicionorganizacion/senadores/composicionsenado"
              "/fichasenador/index.html?id1=%s&legis=15")

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".cache")

RE_ANCLA = re.compile(r"<a\b[^>]*fichasenador[^>]*>", re.I)
RE_ID1 = re.compile(r"[?&]id1=(\d+)")
RE_TITULO = re.compile(r'title="Ficha de ([^"]+)"')
RE_FOTO = re.compile(r"/legis15/senadores/fotos/([A-Za-z0-9_]+)\.jpg", re.I)
RE_PROCED = re.compile(r"(Electo|Electa|Designado|Designada)\s*:\s*([^<\n\r]{1,70})")


def pedir(url, intentos=3, pausa=1.0):
    """GET con sesion nueva y semilla, para esquivar el cacheo de senado.es."""
    ultimo = None
    for n in range(intentos):
        try:
            s = requests.Session()
            s.headers.update(CABECERAS)
            s.get(BASE + "/web/index.html", timeout=30)  # semilla: JSESSIONID fresco
            r = s.get(url, timeout=60)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except Exception as exc:  # noqa: BLE001
            ultimo = exc
            time.sleep(pausa * (n + 1))
        finally:
            try:
                s.close()
            except Exception:  # noqa: BLE001
                pass
    raise RuntimeError("No se pudo descargar %s (%s)" % (url, ultimo))


def censo():
    """Devuelve {id1: {'nombre', 'siglas', 'grupo', 'condicion'}} para toda la Camara."""
    gente = {}
    for codigo, (siglas, nombre_grupo) in GRUPOS.items():
        for ruta, condicion in ((RUTA_ELECTOS, "Electo por circunscripcion"),
                                (RUTA_DESIGNADOS, "Designado por parlamento autonomico")):
            html = pedir(ruta % codigo)
            hallados = 0
            for m in RE_ANCLA.finditer(html):
                ancla = m.group(0)
                mid = RE_ID1.search(ancla)
                mti = RE_TITULO.search(ancla)
                if not mid or not mti:
                    continue
                idw = mid.group(1)
                if idw in gente:
                    continue
                gente[idw] = {
                    "nombre": mti.group(1).strip(),
                    "siglas": siglas,
                    "grupo": nombre_grupo,
                    "condicion": condicion,
                }
                hallados += 1
            print("  %-6s %-38s %3d" % (siglas, condicion.split()[0], hallados))
            time.sleep(0.4)
    return gente


def ficha(idw, usar_cache=True):
    os.makedirs(CACHE, exist_ok=True)
    destino = os.path.join(CACHE, "s%s.html" % idw)
    if usar_cache and os.path.exists(destino):
        with open(destino, encoding="utf-8") as fh:
            return fh.read()
    html = pedir(RUTA_FICHA % idw)
    with open(destino, "w", encoding="utf-8") as fh:
        fh.write(html)
    time.sleep(0.3)
    return html


def construir(gente, usar_cache=True):
    personas = []
    sin_foto = []
    total = len(gente)
    for n, (idw, d) in enumerate(sorted(gente.items(), key=lambda kv: comun.norm(kv[1]["nombre"])), 1):
        html = ficha(idw, usar_cache)
        mf = RE_FOTO.search(html)
        mp = RE_PROCED.search(html)
        foto = (BASE + "/legis15/senadores/fotos/%s.jpg" % mf.group(1)) if mf else ""
        if not mf:
            sin_foto.append(d["nombre"])
        territorio = mp.group(2).strip() if mp else ""
        detalle = ("%s: %s" % (mp.group(1), territorio)) if mp else ""
        persona = {
            "nombre": d["nombre"],
            "siglas": d["siglas"],
            "grupo": d["grupo"],
            "cargo": "",
            "condicion": d["condicion"],
            "territorio": territorio,
            "detalle": detalle,
            "foto": foto,
            "ficha": RUTA_FICHA % idw,
        }
        persona["buscar"] = comun.norm(" ".join(
            [persona["nombre"], d["siglas"], territorio, d["condicion"]]))
        personas.append(persona)
        if n % 25 == 0 or n == total:
            print("  fichas %d/%d" % (n, total))

    orden = comun.ORDEN_SENADO
    personas.sort(key=lambda p: (orden.index(p["siglas"]) if p["siglas"] in orden else 99,
                                 comun.norm(p["nombre"])))
    return personas, sin_foto


def filtros(personas):
    grupos = "".join(
        '<option value="%s">%s (%d)</option>' % (s, s, sum(1 for p in personas if p["siglas"] == s))
        for s in comun.ORDEN_SENADO
        if any(p["siglas"] == s for p in personas))
    territorios = sorted({p["territorio"] for p in personas if p["territorio"]}, key=comun.norm)
    return (
        '<select id="grupo"><option value="">Todos los grupos</option>' + grupos + '</select>'
        '<select id="territorio"><option value="">Todos los territorios</option>'
        + "".join("<option>%s</option>" % t for t in territorios) + '</select>'
        '<select id="condicion"><option value="">Electos y designados</option>'
        '<option value="Electo por circunscripcion">Solo electos</option>'
        '<option value="Designado por parlamento autonomico">Solo designados</option></select>'
        '<select id="orden"><option value="grupo">Agrupar por grupo</option>'
        '<option value="alfa">Orden alfabetico</option>'
        '<option value="territorio">Agrupar por territorio</option>'
        '<option value="condicion">Agrupar por procedencia</option></select>'
    )


def main():
    usar_cache = "--sin-cache" not in sys.argv
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
    os.makedirs(destino, exist_ok=True)

    print("Senado: censo por grupos parlamentarios...")
    gente = censo()
    print("  total %d senadores" % len(gente))
    if len(gente) < 200:
        raise SystemExit("ERROR: el censo devuelve %d senadores, se esperaban ~266. "
                         "Las paginas de listado pueden haber cambiado." % len(gente))

    print("Senado: descargando fichas (fotografias y procedencia)...")
    personas, sin_foto = construir(gente, usar_cache)
    if sin_foto:
        print("  AVISO: %d sin fotografia: %s" % (len(sin_foto), ", ".join(sin_foto[:10])))

    subtitulo = ("%d senadoras y senadores en activo &middot; %d con fotografia "
                 "&middot; Datos extraidos el %s"
                 % (len(personas), sum(1 for p in personas if p["foto"]), comun.hoy()))

    comun.render(
        ruta=os.path.join(destino, "senado.html"),
        titulo="Trombinoscopio - Senado - XV Legislatura",
        cabecera="Senado de Espana &mdash; XV Legislatura",
        subtitulo=subtitulo,
        personas=personas,
        filtros_html=filtros(personas),
        agrupaciones=["grupo", "alfa", "territorio", "condicion"],
        pie=("Fuente: Senado de Espana (senado.es), listados por grupo parlamentario y "
             "fichas individuales de senador. Fotografias enlazadas desde el servidor "
             "oficial de la Camara: se requiere conexion a internet para visualizarlas."),
        activo="senado.html",
    )

    with open(os.path.join(destino, "senado.json"), "w", encoding="utf-8") as fh:
        json.dump(personas, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
