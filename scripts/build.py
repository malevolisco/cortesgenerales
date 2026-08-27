# -*- coding: utf-8 -*-
"""
Orquestador: genera los tres trombinoscopios y la pagina de indice.

Cada camara se ejecuta de forma independiente: si una falla (caida del
portal, bloqueo de red, cambio de endpoint), las demas se publican igual
y el fallo se refleja en el resumen final y en el codigo de salida.

Uso:  python scripts/build.py
      python scripts/build.py congreso senado
"""

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402

DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")

TAREAS = [
    ("congreso", "Congreso de los Diputados", "congreso.html"),
    ("senado", "Senado", "senado.html"),
    ("diputacion_permanente", "Diputacion Permanente", "diputacion-permanente.html"),
]

INDICE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trombinoscopio de las Cortes Generales - XV Legislatura</title>
<style>
body{margin:0;font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
     color:#14181d;background:#f5f6f8}
header{background:#14181d;color:#fff;padding:26px 22px}
header h1{margin:0;font-size:22px;font-weight:600}
header p{margin:6px 0 0;font-size:13px;color:#a9b1bb}
main{padding:24px 22px 60px;max-width:820px}
a.tarjeta{display:block;background:#fff;border:1px solid #e3e6ea;border-radius:8px;
          padding:16px 18px;margin-bottom:12px;text-decoration:none;color:inherit}
a.tarjeta:hover{border-color:#9aa3ad}
a.tarjeta h2{margin:0;font-size:16px}
a.tarjeta p{margin:5px 0 0;font-size:13px;color:#6b7280}
.nd{opacity:.5;pointer-events:none}
footer{padding:18px 22px;font-size:11.5px;color:#6b7280;border-top:1px solid #e3e6ea}
</style>
</head>
<body>
<header>
  <h1>Trombinoscopio de las Cortes Generales</h1>
  <p>XV Legislatura &middot; Directorios fotograficos generados a partir de las fuentes
     oficiales del Congreso de los Diputados y del Senado &middot; Actualizado el %%HOY%%</p>
</header>
<main>
%%TARJETAS%%
</main>
<footer>
Datos y fotografias: congreso.es y senado.es. Las imagenes se enlazan a los servidores
oficiales de ambas Camaras, no se replican en este repositorio.
</footer>
</body>
</html>"""

DESCRIPCIONES = {
    "congreso.html": "Las 350 diputadas y diputados en activo, con filtros por grupo, "
                     "circunscripcion y sexo, y los cargos de la Mesa marcados.",
    "senado.html": "Las 266 senadoras y senadores en activo, con filtros por grupo, "
                   "territorio y procedencia (electos o designados).",
    "diputacion-permanente.html": "La Diputacion Permanente de ambas Camaras: Mesa, "
                                  "titulares y suplentes.",
}


def indice():
    tarjetas = []
    for _, etiqueta, archivo in TAREAS:
        existe = os.path.exists(os.path.join(DOCS, archivo))
        tarjetas.append(
            '<a class="tarjeta%s" href="%s"><h2>%s</h2><p>%s</p></a>'
            % ("" if existe else " nd", archivo, etiqueta,
               DESCRIPCIONES[archivo] if existe else "No disponible en esta ejecucion."))
    html = INDICE.replace("%%HOY%%", comun.hoy()).replace("%%TARJETAS%%", "\n".join(tarjetas))
    with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)
    print("  escrito docs/index.html")


def main():
    os.makedirs(DOCS, exist_ok=True)
    pedidas = [a for a in sys.argv[1:] if not a.startswith("-")]
    resultados = []

    for modulo, etiqueta, _ in TAREAS:
        if pedidas and modulo not in pedidas:
            continue
        print("\n=== %s ===" % etiqueta)
        try:
            __import__(modulo).main()
            resultados.append((etiqueta, "OK"))
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            resultados.append((etiqueta, "FALLO: %s" % exc))

    print("\n=== Resumen ===")
    for etiqueta, estado in resultados:
        print("  %-26s %s" % (etiqueta, estado))
    indice()

    if any(e != "OK" for _, e in resultados):
        sys.exit(1)


if __name__ == "__main__":
    main()
