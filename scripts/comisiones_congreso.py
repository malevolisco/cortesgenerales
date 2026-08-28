# -*- coding: utf-8 -*-
"""
Trombinoscopio de las comisiones del Congreso de los Diputados (XV Legislatura).

Dos pasos:
  1. La pagina /es/comisiones lista todas las comisiones y subcomisiones con su
     codigo interno (_organos_codComision) y su tipo. Se descarta el bloque de
     comisiones disueltas.
  2. Por cada codigo, el endpoint searchOrgano devuelve la composicion. El
     parametro que manda es _organos_selectedSuborgano; _organos_selectedOrganoSup
     es indiferente.

Las comisiones mixtas incluyen senadores (siglas con prefijo S: SGPP, SGPS...).
congreso.es los publica sin ficha ni fotografia, asi que su foto se resuelve
por nombre contra docs/senado.json, que genera senado.py. Si ese fichero no
existe todavia, esas fichas salen con la inicial.

Genera docs/comisiones-congreso.html.

Uso:  python scripts/comisiones_congreso.py
"""

import html as H
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402
import comun_comisiones as cc  # noqa: E402
import congreso as c_congreso  # noqa: E402

URL_LISTA = c_congreso.BASE + "/es/comisiones"
URL_ORGANO = (c_congreso.BASE + "/es/comisiones?p_p_id=organos&p_p_lifecycle=2"
              "&p_p_state=normal&p_p_mode=view&p_p_resource_id=searchOrgano"
              "&p_p_cacheability=cacheLevelPage")

ORDEN_TIPO = ["Comisiones Permanentes Legislativas",
              "Comisiones Permanentes no Legislativas",
              "Comisiones de Investigación",
              "Comisiones Mixtas Permanentes"]

RE_DISUELTAS = re.compile(r"<h2[^>]*>[^<]*isuelt[^<]*</h2>", re.I)
RE_TIPO = re.compile(r"<h3>([^<]+)</h3>")
RE_COMISION = re.compile(
    r'<a href="[^"]*_organos_codComision=(\d+)"\s*\n?\s*'
    r'class="(isComision|isSubComision) linkPc">([^<]+)</a>')


def lista_comisiones(s):
    r = s.get(URL_LISTA, timeout=60)
    r.raise_for_status()
    html = r.text
    corte = RE_DISUELTAS.search(html)
    activo = html[:corte.start()] if corte else html
    tipos = [(m.start(), H.unescape(m.group(1)).strip()) for m in RE_TIPO.finditer(activo)]

    vistas, orden = {}, []
    for m in RE_COMISION.finditer(activo):
        cod, clase, nombre = m.group(1), m.group(2), H.unescape(m.group(3)).strip()
        if cod in vistas:
            continue
        tipo = ""
        for pos, t in tipos:
            if pos < m.start():
                tipo = t
        vistas[cod] = {"cod": cod, "nombre": nombre,
                       "sub": clase == "isSubComision", "tipo": tipo}
        orden.append(cod)
    return [vistas[c] for c in orden]


def composicion(s, cod):
    datos = {
        "_organos_selectedLegislatura": "XV",
        "_organos_compoHistorica": "false",
        "_organos_selectedOrganoSup": "200",
        "_organos_selectedSuborgano": str(cod),
    }
    r = s.post(URL_ORGANO, data=datos, timeout=60,
               headers={"X-Requested-With": "XMLHttpRequest", "Referer": URL_LISTA})
    r.raise_for_status()
    d = r.json()
    activos = [x for x in d["data"] if not x.get("fechaBajaFormat")]
    return activos, (d.get("fechaConstitucion") or {}).get("fechaConstitucion", "")


def main():
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
    os.makedirs(destino, exist_ok=True)

    s = c_congreso.sesion()
    print("Comisiones del Congreso: listando organos...")
    lista = lista_comisiones(s)
    print("  %d comisiones y subcomisiones activas" % len(lista))
    if len(lista) < 20:
        raise SystemExit("ERROR: solo se han encontrado %d comisiones, se esperaban unas 50. "
                         "La pagina /es/comisiones puede haber cambiado." % len(lista))

    dips = {d["codParlamentario"]: d for d in c_congreso.diputados(s)}
    fotos_sen = cc.mapa_fotos_senado(destino)
    if not fotos_sen:
        print("  AVISO: no hay docs/senado.json todavia; los senadores de las "
              "comisiones mixtas saldran sin fotografia. Ejecuta antes senado.py.")

    personas, indice = [], {}

    def alta(m):
        url = m.get("urlFichaDiputado", "")
        mm = re.search(r"codParlamentario=(\d+)", url)
        clave = ("D", int(mm.group(1))) if mm else ("X", comun.norm(m["apellidosNombre"]))
        if clave in indice:
            return indice[clave]
        sig = m["siglas"]
        if clave[0] == "D":
            cod = clave[1]
            d = dips.get(cod, {})
            circ = d.get("nombreCircunscripcion", "") or ""
            part = d.get("formacion", "") or ""
            p = {"n": m["apellidosNombre"], "g": sig, "c": "Diputado/a",
                 "d": circ + ((" \u00b7 " + part) if part else ""),
                 "f": c_congreso.FOTO % cod, "u": c_congreso.FICHA % cod}
        else:
            cond = "Letrado/a" if sig == "" else "Senador/a"
            ficha_url, foto = "", ""
            if cond == "Senador/a":
                par = fotos_sen.get(comun.norm(m["apellidosNombre"]))
                if par:
                    ficha_url, foto = par
            p = {"n": m["apellidosNombre"], "g": sig, "c": cond,
                 "d": "Senado" if cond == "Senador/a" else "Servicios juridicos de la Camara",
                 "f": foto, "u": ficha_url}
        p["b"] = comun.norm(p["n"] + " " + sig + " " + p["d"])
        indice[clave] = len(personas)
        personas.append(p)
        return indice[clave]

    comisiones = []
    for c in lista:
        miembros, constitucion = composicion(s, c["cod"])
        filas = [{"p": alta(m), "r": m["descCargo"]} for m in miembros]
        filas.sort(key=lambda x: (cc.orden_cargo(x["r"]), comun.norm(personas[x["p"]]["n"])))
        comisiones.append({"cod": c["cod"], "n": c["nombre"], "t": c["tipo"], "s": c["sub"],
                           "fc": constitucion, "m": filas,
                           "b": comun.norm(c["nombre"] + " " + c["tipo"])})
        print("  %-7s %3d  %s" % (c["cod"], len(filas), c["nombre"][:55]))
        time.sleep(0.2)

    comisiones.sort(key=lambda c: (ORDEN_TIPO.index(c["t"]) if c["t"] in ORDEN_TIPO else 9,
                                   comun.norm(c["n"])))
    for i, c in enumerate(comisiones):
        for m in c["m"]:
            personas[m["p"]].setdefault("cs", []).append([i, m["r"]])

    n_dip = sum(1 for p in personas if p["c"] == "Diputado/a")
    n_sen = sum(1 for p in personas if p["c"] == "Senador/a")
    n_let = sum(1 for p in personas if p["c"] == "Letrado/a")
    n_ads = sum(len(c["m"]) for c in comisiones)
    sin_foto = sum(1 for p in personas if not p["f"])

    subtitulo = ("%d comisiones y subcomisiones activas &middot; %d adscripciones &middot; "
                 "%d diputados, %d senadores (comisiones mixtas) y %d letrados &middot; "
                 "Datos extraidos el %s"
                 % (len(comisiones), n_ads, n_dip, n_sen, n_let, comun.hoy()))

    cc.render(
        ruta=os.path.join(destino, "comisiones-congreso.html"),
        titulo="Trombinoscopio - Comisiones del Congreso - XV Legislatura",
        cabecera="Comisiones del Congreso de los Diputados &mdash; XV Legislatura",
        subtitulo=subtitulo,
        personas=personas,
        comisiones=comisiones,
        tipos=[t for t in ORDEN_TIPO if any(c["t"] == t for c in comisiones)],
        condiciones=["Diputado/a", "Senador/a", "Letrado/a"],
        pie=("Fuente: Congreso de los Diputados (congreso.es), endpoint oficial searchOrgano "
             "por codigo de comision. Las fotografias de los senadores de las comisiones "
             "mixtas proceden de senado.es, cruzadas por nombre. Los letrados aparecen sin "
             "fotografia: las Camaras no publican su imagen."),
        activo="comisiones-congreso.html",
    )
    if sin_foto:
        print("  %d personas sin fotografia" % sin_foto)

    with open(os.path.join(destino, "comisiones-congreso.json"), "w", encoding="utf-8") as fh:
        json.dump({"personas": personas, "comisiones": comisiones}, fh, ensure_ascii=False)


if __name__ == "__main__":
    main()
