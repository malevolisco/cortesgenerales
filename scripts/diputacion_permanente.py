# -*- coding: utf-8 -*-
"""
Trombinoscopio de la Diputacion Permanente de ambas Camaras (XV Legislatura).

Congreso: endpoint searchOrgano (organo 500), que devuelve Mesa, vocales y
          vocales suplentes con su grupo y su fecha de alta.
Senado:   pagina oficial de composicion de la Diputacion Permanente, que si
          incluye la fotografia junto a cada nombre (a diferencia del resto
          de listados de la Camara).

Genera docs/diputacion-permanente.html.

Uso:  python scripts/diputacion_permanente.py
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402
import congreso as c_congreso  # noqa: E402
import senado as c_senado  # noqa: E402

URL_DP_SENADO = (c_senado.BASE + "/web/composicionorganizacion/organossenado"
                 "/diputacionpermanente/composicion/index.html")

SIGLAS_SENADO = {
    "GPP": "Grupo Parlamentario Popular en el Senado",
    "GPS": "Grupo Parlamentario Socialista",
    "GPERB": "Grupo Parlamentario Izquierdas por la Independencia (ERC-EH Bildu)",
    "GPPLU": "Grupo Parlamentario Plural (Junts-CC-AHI-BNG)",
    "GPV": "Grupo Parlamentario Vasco en el Senado (EAJ-PNV)",
    "GPIC": "Grupo Parlamentario Izquierda Confederal",
    "GPMX": "Grupo Parlamentario Mixto",
}

# En la pagina del Senado cada miembro aparece como: <img foto> <a ficha> (SIGLAS).
# En vez de un unico patron con comodines glotones, que puede emparejar mal a
# traves de saltos grandes del documento, se localizan por separado y se casan
# por posicion: a cada enlace de ficha le corresponde la foto inmediatamente
# anterior y las siglas que aparecen justo despues.
RE_FOTO_DP = re.compile(r"/legis15/senadores/fotos/([A-Za-z0-9_]+)\.jpg", re.I)
RE_ANCLA_DP = re.compile(r"<a\b[^>]*fichasenador[^>]*>", re.I)
RE_ID1_DP = re.compile(r"[?&]id1=(\d+)")
RE_NOMBRE_DP = re.compile(r'title="Ficha de ([^"]+)"')
RE_SIGLAS_DP = re.compile(r"\((GP[A-Z]*)\)")

RE_SECCION = re.compile(
    r"(PRESIDENT[EA]|VICEPRESIDENT[EA] [A-ZÁÉÍÓÚ]+|SECRETARI[AO] [A-ZÁÉÍÓÚ]+"
    r"|MIEMBROS TITULARES|MIEMBROS SUPLENTES)", re.I)


def parte_congreso():
    s = c_congreso.sesion()
    print("Diputacion Permanente (Congreso): descargando...")
    bruto = c_congreso.organo(s, "diputacion-permanente", 500)
    constitucion = (bruto.get("fechaConstitucion") or {}).get("fechaConstitucion", "")
    personas = []
    for m in bruto["data"]:
        if m.get("fechaBajaFormat"):
            continue
        cod = c_congreso.cod_de(m)
        cargo = m["descCargo"]
        if "Suplente" in cargo:
            condicion, etiqueta = "Suplente", "Vocal suplente"
        elif cargo.startswith("Vocal"):
            condicion, etiqueta = "Titular", "Vocal"
        else:
            condicion, etiqueta = "Mesa", cargo
        persona = {
            "nombre": m["apellidosNombre"],
            "siglas": m["siglas"],
            "grupo": m["siglas"],
            "cargo": etiqueta,
            "condicion": condicion,
            "camara": "Congreso",
            "territorio": "",
            "detalle": "Alta: " + m.get("fechaAltaFormat", ""),
            "foto": c_congreso.FOTO % cod,
            "ficha": c_congreso.FICHA % cod,
        }
        persona["buscar"] = comun.norm(" ".join([persona["nombre"], m["siglas"], etiqueta]))
        personas.append(persona)
    print("  %d miembros" % len(personas))
    return personas, constitucion


def parte_senado():
    print("Diputacion Permanente (Senado): descargando...")
    html = c_senado.pedir(URL_DP_SENADO)
    constitucion = ""
    mc = re.search(r"Fecha de constituci[^:]*:\s*([^<\n]{1,40})", html)
    if mc:
        constitucion = mc.group(1).strip()

    fotos = [(m.start(), m.group(1)) for m in RE_FOTO_DP.finditer(html)]
    cortes = [(m.start(), m.group(1).upper()) for m in RE_SECCION.finditer(html)]

    def anterior(lista, pos, defecto=""):
        valor = defecto
        for p, v in lista:
            if p < pos:
                valor = v
            else:
                break
        return valor

    personas = []
    vistos = set()
    for m in RE_ANCLA_DP.finditer(html):
        ancla = m.group(0)
        mid = RE_ID1_DP.search(ancla)
        mno = RE_NOMBRE_DP.search(ancla)
        if not mid or not mno:
            continue
        idw = mid.group(1)
        seccion = anterior(cortes, m.start())
        clave = (idw, seccion)
        if clave in vistos:
            continue
        vistos.add(clave)

        codigo_foto = anterior(fotos, m.start())
        msi = RE_SIGLAS_DP.search(html, m.end(), m.end() + 600)
        siglas = msi.group(1).upper() if msi else "GPMX"

        if "SUPLENTES" in seccion:
            condicion, etiqueta = "Suplente", "Miembro suplente"
        elif "TITULARES" in seccion:
            condicion, etiqueta = "Titular", "Miembro titular"
        elif seccion:
            condicion, etiqueta = "Mesa", seccion.capitalize()
        else:
            condicion, etiqueta = "Titular", "Miembro titular"

        persona = {
            "nombre": mno.group(1).strip(),
            "siglas": siglas,
            "grupo": SIGLAS_SENADO.get(siglas, siglas),
            "cargo": etiqueta,
            "condicion": condicion,
            "camara": "Senado",
            "territorio": "",
            "detalle": "",
            "foto": (c_senado.BASE + "/legis15/senadores/fotos/%s.jpg" % codigo_foto)
                    if codigo_foto else "",
            "ficha": c_senado.RUTA_FICHA % idw,
        }
        persona["buscar"] = comun.norm(" ".join([persona["nombre"], siglas, etiqueta]))
        personas.append(persona)

    sin_foto = sum(1 for p in personas if not p["foto"])
    if sin_foto:
        print("  AVISO: %d miembros sin fotografia" % sin_foto)
    print("  %d miembros" % len(personas))
    return personas, constitucion


def filtros(personas):
    siglas = []
    for p in personas:
        clave = p["camara"] + " | " + p["siglas"]
        if clave not in siglas:
            siglas.append(clave)
    return (
        '<select id="camara"><option value="">Ambas camaras</option>'
        '<option>Congreso</option><option>Senado</option></select>'
        '<select id="condicion"><option value="">Mesa, titulares y suplentes</option>'
        '<option value="Mesa">Solo Mesa</option>'
        '<option value="Titular">Solo titulares</option>'
        '<option value="Suplente">Solo suplentes</option></select>'
        '<select id="orden"><option value="camara">Agrupar por camara</option>'
        '<option value="condicion">Agrupar por condicion</option>'
        '<option value="grupo">Agrupar por grupo</option>'
        '<option value="alfa">Orden alfabetico</option></select>'
    )


def main():
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
    os.makedirs(destino, exist_ok=True)

    c, fecha_c = parte_congreso()
    s, fecha_s = parte_senado()
    if not c or not s:
        raise SystemExit("ERROR: alguna de las dos camaras no ha devuelto miembros.")

    orden_cond = {"Mesa": 0, "Titular": 1, "Suplente": 2}
    personas = sorted(c + s, key=lambda p: (
        0 if p["camara"] == "Congreso" else 1,
        orden_cond.get(p["condicion"], 9),
        comun.norm(p["nombre"])))

    subtitulo = ("Congreso: %d miembros (constituida %s) &middot; "
                 "Senado: %d miembros (constituida %s) &middot; Datos extraidos el %s"
                 % (len(c), fecha_c or "s/d", len(s), fecha_s or "s/d", comun.hoy()))

    comun.render(
        ruta=os.path.join(destino, "diputacion-permanente.html"),
        titulo="Trombinoscopio - Diputacion Permanente - XV Legislatura",
        cabecera="Diputacion Permanente &mdash; Congreso y Senado",
        subtitulo=subtitulo,
        personas=personas,
        filtros_html=filtros(personas),
        agrupaciones=["camara", "condicion", "grupo", "alfa"],
        pie=("Fuente: Congreso de los Diputados (endpoint searchOrgano, organo 500) y "
             "Senado de Espana (pagina de composicion de la Diputacion Permanente). "
             "Fotografias enlazadas desde los servidores oficiales de ambas Camaras."),
        activo="diputacion-permanente.html",
    )

    with open(os.path.join(destino, "diputacion-permanente.json"), "w", encoding="utf-8") as fh:
        json.dump(personas, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
