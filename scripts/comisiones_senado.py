# -*- coding: utf-8 -*-
"""
Trombinoscopio de las comisiones del Senado (XV Legislatura).

Dos pasos:
  1. El indice de comisiones se sirve por letra inicial
     (comisionessenado/index.html?id=<LETRA>&legis=15). Recorriendo la A-Z y
     uniendo resultados se obtiene el listado completo con su identificador
     (S011xxx) y si es mixta.
  2. Por cada comision, la pagina de composicion da nombre, grupo y cargo de
     cada miembro.

Las fotografias no estan en esas paginas: se resuelven por nombre contra
docs/senado.json, que genera senado.py. Ejecuta antes senado.py o usa
build.py, que respeta el orden.

Genera docs/comisiones-senado.html.

Uso:  python scripts/comisiones_senado.py
"""

import html as H
import json
import os
import re
import string
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402
import comun_comisiones as cc  # noqa: E402
import senado as c_senado  # noqa: E402

URL_INDICE = (c_senado.BASE + "/web/actividadparlamentaria/sesionescomision"
              "/comisionessenado/index.html?id=%s&legis=15")
URL_COMPOSICION = (c_senado.BASE + "/web/actividadparlamentaria/sesionescomision"
                   "/detallecomisiones/composicion/index.html?id=%s&legis=15&esMixta=%s")

RE_ENLACE = re.compile(
    r'<a\b[^>]*detallecomisiones[^>]*[?&]id=([A-Z]\d+)[^>]*>(.*?)</a>', re.I | re.S)
RE_ESMIXTA = re.compile(r"[?&]esMixta=([SN])", re.I)
RE_ETIQUETAS = re.compile(r"<[^>]+>")
RE_CONSTITUCION = re.compile(r"Fecha de constituci[^:]*:\s*([^<\n\r]{1,40})", re.I)

# En la pagina de composicion cada miembro es:
#   <img foto> <a ficha>NOMBRE (Camara)(SIGLAS)</a>CARGO
# El Senado sirve las fotos de AMBAS Camaras: /legis15/senadores/fotos/S15NNN.jpg
# para los senadores y /legis15/diputados/NNN_15.jpg para los diputados de las
# comisiones mixtas. La imagen va justo antes del enlace, asi que se emparejan
# por posicion en el documento en vez de con un patron con comodines.
RE_FOTO = re.compile(
    r"/legis15/(senadores/fotos/[A-Za-z0-9_]+|diputados/\d+_15)\.jpg", re.I)
RE_ANCLA = re.compile(r"<a\b[^>]*(?:fichasenador|busqueda-de-diputados)[^>]*>", re.I)
RE_ID1 = re.compile(r"[?&]id1=(\d+)")
RE_COD_DIP = re.compile(r"codParlamentario=(\d+)")
# Los parentesis finales se capturan con avidez para no partir "GV (EAJ-PNV)".
RE_TITULO = re.compile(
    r'title="\s*Ficha de (.+?)\s*(?:\((Senador|Senadora|Diputado|Diputada)\)\s*)?'
    r'\((.+)\)\s*"', re.I | re.S)
RE_TITULO_SIMPLE = re.compile(r'title="\s*Ficha de ([^"]+)"', re.I)
RE_SIGLAS = re.compile(r"\((GP[A-Z]*)\)")
RE_CARGO = re.compile(
    r"\b(PRESIDENT[EA]|VICEPRESIDENT[EA](?:\s+\w+)?|SECRETARI[AO](?:\s+\w+)?"
    r"|VICEPORTAVOZ|PORTAVOZ(?:\s+ADJUNT[OA])?|VOCAL|LETRAD[OA])\b", re.I)

TIPO_PERMANENTE = "Comisiones del Senado"
TIPO_MIXTA = "Comisiones Mixtas"


def limpio(texto):
    return H.unescape(RE_ETIQUETAS.sub(" ", texto)).strip()


def indice_comisiones():
    """Recorre el indice letra a letra y devuelve la union de comisiones."""
    vistas, orden = {}, []
    for letra in string.ascii_uppercase:
        try:
            html = c_senado.pedir(URL_INDICE % letra)
        except Exception as exc:  # noqa: BLE001
            print("  aviso: letra %s no disponible (%s)" % (letra, exc))
            continue
        nuevas = 0
        for m in RE_ENLACE.finditer(html):
            idc, nombre = m.group(1), limpio(m.group(2))
            if not nombre or idc in vistas:
                continue
            # El enlace dice si es mixta; el prefijo del id lo confirma
            # (S011xxx = comision del Senado, G0xxxxx = mixta).
            me = RE_ESMIXTA.search(m.group(0))
            mixta = (me.group(1).upper() == "S") if me else idc.startswith("G")
            vistas[idc] = {"id": idc, "nombre": nombre, "mixta": mixta,
                           "tipo": TIPO_MIXTA if mixta else TIPO_PERMANENTE}
            orden.append(idc)
            nuevas += 1
        print("  letra %s: %d nuevas (acumulado %d)" % (letra, nuevas, len(vistas)))
        time.sleep(0.3)
    return [vistas[i] for i in orden]


def composicion(comision):
    html = c_senado.pedir(URL_COMPOSICION % (comision["id"], "S" if comision["mixta"] else "N"))
    mc = RE_CONSTITUCION.search(html)
    fotos = [(m.start(), m.group(1)) for m in RE_FOTO.finditer(html)]

    def foto_antes(pos):
        valor = ""
        for p, v in fotos:
            if p < pos:
                valor = v
            else:
                break
        return valor

    miembros, vistos = [], set()
    for m in RE_ANCLA.finditer(html):
        ancla = m.group(0)
        mid, mdip = RE_ID1.search(ancla), RE_COD_DIP.search(ancla)
        if not mid and not mdip:
            continue
        clave = ("S", mid.group(1)) if mid else ("D", mdip.group(1))
        if clave in vistos:
            continue
        vistos.add(clave)

        mt = RE_TITULO.search(ancla)
        if mt:
            nombre = H.unescape(mt.group(1)).strip()
            camara = (mt.group(2) or "").capitalize()
            siglas = H.unescape(mt.group(3)).strip()
        else:
            mts = RE_TITULO_SIMPLE.search(ancla)
            msi = RE_SIGLAS.search(ancla)
            nombre = H.unescape(mts.group(1)).strip() if mts else ""
            camara, siglas = "", (msi.group(1) if msi else "")
        if not nombre:
            continue
        if not camara:
            camara = "Senador" if clave[0] == "S" else "Diputado"

        mca = RE_CARGO.search(html[m.end():m.end() + 600])
        ruta = foto_antes(m.start())
        miembros.append({
            "clave": "%s%s" % clave,
            "id1": clave[1] if clave[0] == "S" else "",
            "nombre": nombre,
            "camara": camara,
            "siglas": siglas,
            "cargo": mca.group(1).strip().capitalize() if mca else "Vocal",
            "foto": (c_senado.BASE + "/legis15/%s.jpg" % ruta) if ruta else "",
        })
    return miembros, (mc.group(1).strip() if mc else "")


def main():
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
    os.makedirs(destino, exist_ok=True)

    print("Comisiones del Senado: recorriendo el indice...")
    lista = indice_comisiones()
    print("  %d comisiones encontradas" % len(lista))
    if len(lista) < 10:
        raise SystemExit("ERROR: solo se han encontrado %d comisiones, se esperaban unas 30. "
                         "El indice de senado.es puede haber cambiado." % len(lista))

    fotos = cc.mapa_fotos_senado(destino)
    if not fotos:
        print("  AVISO: no hay docs/senado.json; las fichas saldran sin fotografia. "
              "Ejecuta antes senado.py.")

    personas, indice = [], {}

    def alta(m):
        if m["clave"] in indice:
            return indice[m["clave"]]
        # La propia pagina ya trae la foto; el censo solo es respaldo.
        foto, ficha_url = m["foto"], ""
        if m["id1"]:
            ficha_url, foto_censo = fotos.get(comun.norm(m["nombre"]), ("", ""))
            if not foto:
                foto = foto_censo
            if not ficha_url:
                ficha_url = c_senado.RUTA_FICHA % m["id1"]
        p = {"n": m["nombre"], "g": m["siglas"], "c": m["camara"],
             "d": "Senado" if m["camara"].startswith("Senador") else "Congreso",
             "f": foto, "u": ficha_url}
        p["b"] = comun.norm(" ".join([p["n"], p["g"], p["c"]]))
        indice[m["clave"]] = len(personas)
        personas.append(p)
        return indice[m["clave"]]

    comisiones = []
    for c in lista:
        try:
            miembros, constitucion = composicion(c)
        except Exception as exc:  # noqa: BLE001
            print("  aviso: %s sin composicion (%s)" % (c["nombre"][:45], exc))
            continue
        filas = [{"p": alta(m), "r": m["cargo"]} for m in miembros]
        filas.sort(key=lambda x: (cc.orden_cargo(x["r"]), comun.norm(personas[x["p"]]["n"])))
        comisiones.append({"cod": c["id"], "n": c["nombre"], "t": c["tipo"], "s": False,
                           "fc": constitucion, "m": filas,
                           "b": comun.norm(c["nombre"] + " " + c["tipo"])})
        print("  %-9s %3d  %s" % (c["id"], len(filas), c["nombre"][:55]))
        time.sleep(0.3)

    comisiones.sort(key=lambda c: (0 if c["t"] == TIPO_PERMANENTE else 1, comun.norm(c["n"])))
    for i, c in enumerate(comisiones):
        for m in c["m"]:
            personas[m["p"]].setdefault("cs", []).append([i, m["r"]])

    n_ads = sum(len(c["m"]) for c in comisiones)
    sin_foto = sum(1 for p in personas if not p["f"])
    n_sen = sum(1 for p in personas if p["c"].startswith("Senador"))
    subtitulo = ("%d comisiones &middot; %d adscripciones &middot; %d senadores y "
                 "%d diputados (comisiones mixtas) &middot; Datos extraidos el %s"
                 % (len(comisiones), n_ads, n_sen, len(personas) - n_sen, comun.hoy()))

    cc.render(
        ruta=os.path.join(destino, "comisiones-senado.html"),
        titulo="Trombinoscopio - Comisiones del Senado - XV Legislatura",
        cabecera="Comisiones del Senado &mdash; XV Legislatura",
        subtitulo=subtitulo,
        personas=personas,
        comisiones=comisiones,
        tipos=[t for t in (TIPO_PERMANENTE, TIPO_MIXTA)
               if any(c["t"] == t for c in comisiones)],
        condiciones=["Senador", "Senadora", "Diputado", "Diputada"],
        pie=("Fuente: Senado de Espana (senado.es), indice de comisiones y paginas de "
             "composicion. Las fotografias se cruzan por nombre con el censo de senadores "
             "y se enlazan al servidor oficial de la Camara."),
        activo="comisiones-senado.html",
    )
    if sin_foto:
        print("  %d senadores sin fotografia" % sin_foto)

    with open(os.path.join(destino, "comisiones-senado.json"), "w", encoding="utf-8") as fh:
        json.dump({"personas": personas, "comisiones": comisiones}, fh, ensure_ascii=False)


if __name__ == "__main__":
    main()
