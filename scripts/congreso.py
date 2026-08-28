# -*- coding: utf-8 -*-
"""
Trombinoscopio del Congreso de los Diputados (XV Legislatura).

Fuentes oficiales (endpoints AJAX del portal Liferay de congreso.es):
  - searchDiputados : listado completo de diputados en activo
  - searchOrgano    : composicion de un organo (100 = Mesa, 500 = Dip. Permanente)

Genera docs/congreso.html.

Uso:  python scripts/congreso.py
"""

import json
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402

BASE = "https://www.congreso.es"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

SIGLAS = {
    "Grupo Parlamentario Popular en el Congreso": "GP",
    "Grupo Parlamentario Socialista": "GS",
    "Grupo Parlamentario VOX": "GVOX",
    "Grupo Parlamentario Plurinacional SUMAR": "GSUMAR",
    "Grupo Parlamentario Republicano": "GR",
    "Grupo Parlamentario Junts per Catalunya": "GJxCAT",
    "Grupo Parlamentario Euskal Herria Bildu": "GEH Bildu",
    "Grupo Parlamentario Vasco (EAJ-PNV)": "GV (EAJ-PNV)",
    "Grupo Parlamentario Mixto": "GMx",
}

FOTO = BASE + "/docu/imgweb/diputados/%d_15.jpg"
FICHA = (BASE + "/es/busqueda-de-diputados?p_p_id=diputadomodule"
         "&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&mostrarFicha=true"
         "&codParlamentario=%d&idLegislatura=XV")


def sesion():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9"})
    s.get(BASE + "/es/busqueda-de-diputados", timeout=30)
    return s


def diputados(s):
    """Listado completo de diputados en activo."""
    url = (BASE + "/es/busqueda-de-diputados?p_p_id=diputadomodule"
           "&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view"
           "&p_p_resource_id=searchDiputados&p_p_cacheability=cacheLevelPage")
    datos = {
        "_diputadomodule_idLegislatura": "15",
        "_diputadomodule_genero": "0",
        "_diputadomodule_grupo": "all",
        "_diputadomodule_tipo": "0",
        "_diputadomodule_nombre": "",
        "_diputadomodule_apellidos": "",
        "_diputadomodule_formacion": "all",
        "_diputadomodule_filtroProvincias": "[]",
        "_diputadomodule_nombreCircunscripcion": "",
    }
    r = s.post(url, data=datos, timeout=60,
               headers={"X-Requested-With": "XMLHttpRequest",
                        "Referer": BASE + "/es/busqueda-de-diputados"})
    r.raise_for_status()
    return r.json()["data"]


def organo(s, pagina, codigo):
    """Composicion de un organo: 100 = Mesa, 500 = Diputacion Permanente."""
    url = (BASE + "/es/" + pagina + "?p_p_id=organos&p_p_lifecycle=2"
           "&p_p_state=normal&p_p_mode=view&p_p_resource_id=searchOrgano"
           "&p_p_cacheability=cacheLevelPage")
    datos = {
        "_organos_selectedLegislatura": "XV",
        "_organos_compoHistorica": "false",
        "_organos_selectedOrganoSup": str(codigo),
        "_organos_selectedSuborgano": "",
    }
    r = s.post(url, data=datos, timeout=60,
               headers={"X-Requested-With": "XMLHttpRequest",
                        "Referer": BASE + "/es/" + pagina})
    r.raise_for_status()
    return r.json()


def cod_de(registro):
    url = registro["urlFichaDiputado"]
    return int(url.split("codParlamentario=")[1].split("&")[0])


def construir(lista, mesa):
    personas = []
    for d in lista:
        if d.get("fchBaja"):
            continue
        cod = d["codParlamentario"]
        sig = SIGLAS.get(d["grupo"], "GMx")
        circ = d.get("nombreCircunscripcion", "") or ""
        partido = d.get("formacion", "") or ""
        persona = {
            "nombre": d["apellidosNombre"],
            "siglas": sig,
            "grupo": d["grupo"],
            "cargo": mesa.get(cod, ""),
            "territorio": circ,
            "detalle": circ + ((" \u00b7 " + partido) if partido else ""),
            "sexo": "Diputada" if d.get("genero") == 2 else "Diputado",
            "foto": FOTO % cod,
            "ficha": FICHA % cod,
        }
        persona["buscar"] = comun.norm(" ".join(
            [persona["nombre"], sig, circ, partido, persona["cargo"]]))
        personas.append(persona)

    orden = comun.ORDEN_CONGRESO
    personas.sort(key=lambda p: (orden.index(p["siglas"]) if p["siglas"] in orden else 99,
                                 comun.norm(p["nombre"])))
    return personas


def filtros(personas):
    grupos = "".join(
        '<option value="%s">%s (%d)</option>' % (s, s, sum(1 for p in personas if p["siglas"] == s))
        for s in comun.ORDEN_CONGRESO
        if any(p["siglas"] == s for p in personas))
    circs = sorted({p["territorio"] for p in personas if p["territorio"]}, key=comun.norm)
    return (
        '<select id="grupo"><option value="">Todos los grupos</option>' + grupos + '</select>'
        '<select id="territorio"><option value="">Todas las circunscripciones</option>'
        + "".join("<option>%s</option>" % c for c in circs) + '</select>'
        '<select id="sexo"><option value="">Ambos</option>'
        '<option value="Diputada">Solo diputadas</option>'
        '<option value="Diputado">Solo diputados</option></select>'
        '<select id="orden"><option value="grupo">Agrupar por grupo</option>'
        '<option value="alfa">Orden alfabetico</option>'
        '<option value="territorio">Agrupar por circunscripcion</option></select>'
    )


def main():
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
    os.makedirs(destino, exist_ok=True)

    s = sesion()
    print("Congreso: descargando listado de diputados...")
    lista = diputados(s)
    print("  %d registros" % len(lista))
    if len(lista) < 300:
        raise SystemExit("ERROR: el listado devuelve %d diputados, se esperaban ~350. "
                         "El endpoint puede haber cambiado." % len(lista))

    print("Congreso: descargando la Mesa...")
    mesa = {}
    for m in organo(s, "mesa", 100)["data"]:
        if not m.get("fechaBajaFormat"):
            mesa[cod_de(m)] = m["descCargo"]
    print("  %d cargos" % len(mesa))

    personas = construir(lista, mesa)
    mujeres = sum(1 for p in personas if p["sexo"] == "Diputada")
    subtitulo = ("%d diputadas y diputados en activo &middot; %d diputadas y %d diputados "
                 "&middot; Datos extraidos el %s"
                 % (len(personas), mujeres, len(personas) - mujeres, comun.hoy()))

    comun.render(
        ruta=os.path.join(destino, "congreso.html"),
        titulo="Trombinoscopio - Congreso de los Diputados - XV Legislatura",
        cabecera="Congreso de los Diputados &mdash; XV Legislatura",
        subtitulo=subtitulo,
        personas=personas,
        filtros_html=filtros(personas),
        agrupaciones=["grupo", "alfa", "territorio"],
        pie=("Fuente: Congreso de los Diputados (congreso.es), endpoints oficiales "
             "searchDiputados y searchOrgano. Fotografias enlazadas desde el servidor "
             "oficial de la Camara: se requiere conexion a internet para visualizarlas."),
        activo="congreso.html",
    )

    with open(os.path.join(destino, "congreso.json"), "w", encoding="utf-8") as fh:
        json.dump(personas, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
