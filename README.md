# Trombinoscopio de las Cortes Generales — XV Legislatura

Directorios fotográficos del Congreso de los Diputados y del Senado, generados
automáticamente a partir de las fuentes oficiales de ambas Cámaras.

Tres salidas en `docs/`:

| Archivo | Contenido |
|---|---|
| `congreso.html` | 350 diputadas y diputados en activo, con los cargos de la Mesa marcados |
| `senado.html` | 266 senadoras y senadores en activo, electos y designados |
| `diputacion-permanente.html` | Diputación Permanente de ambas Cámaras: Mesa, titulares y suplentes |

Cada página lleva buscador sin acentos, filtros por grupo y territorio, varios
modos de agrupación y hoja de estilo de impresión a seis columnas.

Junto a cada HTML se escribe el `.json` equivalente, por si interesa reutilizar
los datos en otra herramienta.

## Puesta en marcha

1. Crea un repositorio en GitHub (público o privado) y sube este contenido.
2. En **Settings → Pages**, en «Build and deployment», elige **GitHub Actions**
   como origen.
3. En **Actions**, lanza a mano el workflow *Actualizar trombinoscopios* la
   primera vez. Después se ejecuta solo los lunes por la mañana.
4. El sitio queda en `https://<usuario>.github.io/<repositorio>/`.

## Ejecución local

```bash
pip install -r requirements.txt
python scripts/build.py                 # las tres
python scripts/build.py congreso        # solo una
python scripts/senado.py --sin-cache    # ignorar la caché de fichas
```

## Fuentes y método

**Congreso.** Dos endpoints AJAX del portal Liferay, que devuelven JSON:

- `searchDiputados` → listado completo de diputados en activo, con grupo,
  circunscripción, formación electoral y sexo.
- `searchOrgano` → composición de un órgano. Se usan el 100 (Mesa) y el 500
  (Diputación Permanente).

Las fotografías siguen el patrón `docu/imgweb/diputados/<cod>_15.jpg`, derivable
del código de parlamentario, así que no hace falta visitar ninguna ficha.

**Senado.** Aquí no hay atajo, y conviene saber por qué. El código de la
fotografía (`S15NNN`) **no se deduce** del identificador de ficha (`id1`):
19063→S15201, 18865→S15004, 19817→S15097. Son numeraciones independientes. Los
listados que publican los 266 senadores (por grupo, por género, por procedencia
geográfica) traen nombre, grupo e `id1`, pero no la foto. La única página que
empareja las dos cosas es la ficha individual.

De ahí el proceso en dos pasos de `senado.py`:

1. Catorce páginas de listado por grupo parlamentario (electos por
   circunscripción y designados por parlamentos autonómicos) dan el censo
   completo de `id1`. Como se recorre grupo a grupo, las siglas no hay que
   deducirlas del HTML.
2. Una petición por ficha para extraer la URL de la foto y la procedencia.

Las fichas se cachean en `.cache/` (ignorada por git), así que la primera
ejecución tarda unos minutos y las siguientes son inmediatas.

## Notas técnicas

**El cacheo de sesión de senado.es.** El portal reutiliza el `JSESSIONID` de
forma agresiva y llega a devolver la misma ficha repetida si se mantiene la
conexión. Por eso cada petición al Senado abre una `requests.Session()` nueva y
hace un GET semilla a la portada para obtener un identificador de sesión fresco.
No es una optimización: sin eso, los datos salen mal.

**El WAF de senado.es.** senado.es está detrás de Akamai y devuelve 403 a
peticiones desde parte de los rangos de centros de datos. Si el workflow falla
en la parte del Senado con 403, no es un fallo del script: el paso *Comprobar
acceso a las fuentes oficiales* lo deja registrado al principio del log. En ese
caso ejecuta `python scripts/senado.py` desde tu máquina y commitea el `docs/`
resultante; el Congreso y el índice se seguirán actualizando solos.

**Fotografías.** Se enlazan a los servidores oficiales, no se replican aquí.
Eso mantiene el repositorio ligero y evita redistribuir material de las Cámaras,
pero implica que las páginas necesitan conexión para mostrar las imágenes.

**Cambios en los portales.** Los scripts abortan con un mensaje explícito si el
Congreso devuelve menos de 300 diputados o el Senado menos de 200 senadores.
Es preferible a publicar un directorio incompleto sin que se note.

## Estructura

```
├── .github/workflows/actualizar.yml   # cron semanal + publicación en Pages
├── requirements.txt
├── scripts/
│   ├── comun.py                       # plantilla HTML y utilidades compartidas
│   ├── congreso.py
│   ├── senado.py
│   ├── diputacion_permanente.py
│   └── build.py                       # orquestador + índice
└── docs/                              # salida publicada por GitHub Pages
```
