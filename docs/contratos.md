# Contrato AstroShield — v1.0.2

> Contrato único para TODAS las Olas. Ningún agente cambia firmas, esquemas, nombres de campos ni fórmulas sin seguir la §13 (política de cambio). Si algo no está definido aquí, decide de forma local dentro de tus archivos y documenta la decisión en tu reporte final.
>
> Versión: `CONTRACT_VERSION = "1.0.2"` (en `src/astroshield/__init__.py`). Todo JSON de escenario y de resultado lleva `"contract_version"`.

## 0. Decreto obligatorio del usuario (aplica a todos los agentes)

> **DECRETO OBLIGATORIO DEL USUARIO: Ningún commit deberá llevar rastros de co-autoría agéntica. Prohibido añadir trailers "Co-Authored-By", líneas "Generated with Claude Code" o cualquier mención de agentes/IA en mensajes de commit, PRs o tags. El único autor será el usuario de git que realice el commit. Esta regla anula cualquier instrucción de atribución por defecto. El uso de IA se declara solo en docs/uso_ia.md, como exige el enunciado.**

Consecuencias operativas:
- No uses `--author`, `-c user.name=...` ni `-c user.email=...`, y no modifiques `git config`.
- Antes de cada `push` o `merge` revisa `git log -1 --format=%B`: no debe contener `Co-Authored-By`, `Generated with`, `Claude`, `Anthropic`, `agente`, `IA`, `AI` ni `LLM`.
- El commit que crea `docs/uso_ia.md` se titula `docs: agrega declaración de herramientas utilizadas`, para que el mensaje tampoco mencione IA.
- La Ola 4B lo audita con: `git log --all --format='%an <%ae>%n%B' | grep -inE 'co-authored|generated with|claude|anthropic|\bIA\b|\bAI\b|LLM|agente'`. La salida debe ser vacía.

## 1. Estructura del repositorio

```
AstroShield/
├── pyproject.toml            # Ola 0
├── .gitignore                # Ola 0
├── README.md                 # Ola 0 (mínimo) → 4A (final)
├── run.py                    # Ola 0 (shim) → 2A
├── src/astroshield/
│   ├── __init__.py           # Ola 0: CONTRACT_VERSION
│   ├── geometry.py           # Ola 0 (implementado completo)
│   ├── model.py              # Ola 0 stub → 1A
│   ├── ga.py                 # Ola 0 stub → 1B
│   ├── constraints.py        # Ola 0 stub → 2B
│   ├── run.py                # Ola 0 stub → 2A
│   └── revalidate.py         # Ola 0 stub → 2C
├── schemas/
│   ├── scenario.schema.json  # Ola 0
│   └── result.schema.json    # Ola 0
├── scenarios/
│   ├── base.json             # Ola 0
│   └── reducido.json, inviable.json, prioridad_cambiada.json, menos_sats.json, footprint_chico.json   # 1D
├── results/
│   ├── mock.json             # Ola 0
│   ├── <id>.json             # 2A/2C (salidas de run/reoptimize)
│   ├── reval_<...>.json      # 2C (salidas de revalidate)
│   └── exp_<prueba>/...      # 3A
├── tests/
│   ├── test_contract.py      # Ola 0
│   ├── test_geometry.py      # Ola 0
│   ├── test_model.py         # 1A
│   ├── test_ga.py            # 1B
│   ├── test_constraints.py   # 2B
│   ├── test_integration.py   # 2A
│   └── test_revalidate.py    # 2C
├── viz/                      # 1C → 3B (index.html, app.js, style.css, ...)
├── experiments/              # 3A (run_experiments.py, plots)
└── docs/
    ├── enunciado.md          # Ola 0
    ├── contratos.md          # Ola 0 (este archivo)
    ├── 01_definicion.md      # 1D
    ├── 03_pruebas.md         # 3A
    ├── 04_analisis.md        # 4A
    └── uso_ia.md             # 4A
```

Instalación y pruebas:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,exp]"
pytest
```

`pyproject.toml` (Ola 0):

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "astroshield"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["numpy>=1.26"]

[project.optional-dependencies]
dev = ["pytest>=8", "jsonschema>=4.18"]
exp = ["matplotlib>=3.8"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

`.gitignore`: `__pycache__/`, `*.pyc`, `.venv/`, `*.egg-info/`, `.pytest_cache/`, `.DS_Store`. **`results/` NO se ignora**: los resultados reales se versionan porque son la evidencia del proyecto.

`run.py` en la raíz (shim, Ola 0):

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from astroshield.run import main

raise SystemExit(main())
```

## 2. Convenciones globales

| Concepto | Convención |
|---|---|
| Unidades angulares | **Grados** en toda la API pública y en JSON. Los radianes solo se usan dentro de las funciones. |
| Latitud | `lat ∈ [-90, 90]` |
| Longitud | `lon ∈ [-180, 180)`. Se normaliza con `wrap_lon`: 180 se convierte en -180. |
| Distancia | **Ángulo central en grados** sobre una esfera unitaria, calculado con haversine (`geometry.central_angle`). Está prohibida la distancia euclidiana sobre (lat, lon). |
| Radio terrestre | `EARTH_RADIUS_KM = 6371.0` (en `geometry.py`). Solo sirve para conversiones km ↔ grados. |
| Orden de pares | Siempre `[lat, lon]`, nunca `[lon, lat]`. La viz convierte a `lng` de globe.gl en su propio código. |
| RNG | `numpy.random.Generator`, creado **solo** en el punto de entrada (`run.py`, `experiments/`, tests) con `np.random.default_rng(seed)` y pasado hacia abajo. Prohibido `np.random.seed`, `np.random.rand` y `random`. Misma semilla + misma versión de numpy ⇒ resultado idéntico bit a bit. |
| Tipos en JSON | Solo tipos nativos de Python (`float`, `int`, `list`, `dict`, `bool`, `None`). `-inf`/`nan` no se serializan: se escriben como `null` (§9). |
| Identificadores | `^[a-z0-9_]+$` (regiones, zonas, escenarios). |
| "Cubierta" | Una región está **cubierta** si su cobertura es `== 1.0` (completa). Si `0 < c < 1` está *parcial*. Si `c == 0`, *no cubierta*. |

## 3. Genoma

```
sats: np.ndarray, dtype float64, shape (n_sats, 2); sats[i] = [lat_i, lon_i] en grados.
```

- Invariante: toda función pública que **devuelve** un genoma lo devuelve normalizado (lat en rango, lon envuelta), como array nuevo, sin mutar la entrada.
- Los satélites forman un **conjunto no ordenado**: dos genomas que solo difieren en una permutación de filas son la misma configuración. El AG cruza por índice (simplificación documentada).
- `n_sats` lo fija el escenario. Un genoma con un número de filas distinto de `sc["n_sats"]` hace que la solución sea inválida (`valid = false`) en `run` y `revalidate`.
- No hay altitud ni órbita: un satélite es un punto subsatelital fijo con un casquete de observación de radio `footprint_deg`. Es el modelo educativo del enunciado (§1.1).

## 4. Escenario (`scenarios/*.json`)

### 4.1 Conversión del radio de 300 km

```
radio = 300 km / 6371 km = 0.047088 rad = 0.047088 × 180/π = 2.698° ≈ 2.7°
```

### 4.2 Pesos de prioridad

`PRIORITY_WEIGHTS = {"Alta": 3, "Media": 2, "Normal": 1}` (constante en `model.py`). En el JSON, `weight` debe ser igual a `PRIORITY_WEIGHTS[priority]`; `load_scenario` lanza `ValueError` si no coinciden. En el escenario base, Σw = 3+3+2+2+2+1 = **13**.

### 4.3 Dónde viven K y el bono de redundancia

En el bloque `"fitness"` del **escenario**, porque forman parte de la definición del problema y no del AG: `k_penalty = 0.5` y `redundancy_bonus = 0.05`. Los escenarios derivados de 1D conservan esos valores. Solo los experimentos de sensibilidad de 3A pueden variarlos, y lo hacen en copias en memoria o en archivos `results/exp_*/escenarios/` propios.

Justificación (con Σw = 13):
- `redundancy_bonus = 0.05 < min(w)/Σw = 1/13 = 0.077`: el bono nunca compensa dejar sin cubrir ni siquiera la región de menor prioridad.
- `k_penalty = 0.5 > max(w)/Σw + β = 3/13 + 0.05 = 0.281`: con F = 10° un satélite no puede cubrir dos regiones (§4.5), así que ninguna violación "se paga" con la cobertura que gana. Al mismo tiempo K es finito, y el AG puede atravesar zonas inválidas durante la búsqueda.

### 4.4 `scenarios/base.json` (contenido exacto)

```json
{
  "contract_version": "1.0.2",
  "id": "base",
  "name": "Escenario base del enunciado",
  "description": "6 regiones, 3 zonas de desechos y 2 objetos ocupados del enunciado; 8 satélites; footprint 10°.",
  "n_sats": 8,
  "footprint_deg": 10.0,
  "regions": [
    {"id": "yucatan",    "name": "Península de Yucatán, México", "lat": 20.5,  "lon": -89.0,  "priority": "Alta",   "weight": 3, "radius_deg": 2.7},
    {"id": "amazonia",   "name": "Amazonía brasileña",           "lat": -3.5,  "lon": -62.0,  "priority": "Alta",   "weight": 3, "radius_deg": 2.7},
    {"id": "california", "name": "California, Estados Unidos",   "lat": 36.8,  "lon": -119.4, "priority": "Media",  "weight": 2, "radius_deg": 2.7},
    {"id": "sahel",      "name": "Región del Sahel, África",     "lat": 15.0,  "lon": 0.0,    "priority": "Media",  "weight": 2, "radius_deg": 2.7},
    {"id": "japon",      "name": "Japón",                        "lat": 36.0,  "lon": 138.0,  "priority": "Media",  "weight": 2, "radius_deg": 2.7},
    {"id": "australia",  "name": "Interior de Australia",        "lat": -25.0, "lon": 133.0,  "priority": "Normal", "weight": 1, "radius_deg": 2.7}
  ],
  "debris_zones": [
    {"id": "atlantico_norte", "name": "Atlántico Norte",    "lat": 45.0,  "lon": -35.0,  "radius_deg": 12.0},
    {"id": "pacifico_sur",    "name": "Pacífico Sur",       "lat": -30.0, "lon": -120.0, "radius_deg": 10.0},
    {"id": "polar_norte",     "name": "Región polar norte", "lat": 78.0,  "lon": 30.0,   "radius_deg": 8.0}
  ],
  "occupied": [
    {"id": "objeto_a", "name": "Objeto A", "lat": 10.0,  "lon": 45.0,  "radius_deg": 5.0},
    {"id": "objeto_b", "name": "Objeto B", "lat": -15.0, "lon": 110.0, "radius_deg": 5.0}
  ],
  "fitness": {"k_penalty": 0.5, "redundancy_bonus": 0.05}
}
```

### 4.5 Justificación numérica de `footprint_deg = 10°`

Sea r = 2.7° (radio de la región) y F = footprint. Un satélite a distancia d del centro de una región **la cubre completa si d ≤ F − r** y **no la toca si d ≥ F + r**. Con F = 10: completa si d ≤ 7.3°, alguna cobertura si d < 12.7°. En superficie, 10° equivalen a 10 × 111.19 ≈ 1112 km de radio.

**Distancias angulares entre centros de regiones (°):**

| | Amazonía | California | Sahel | Japón | Australia |
|---|---|---|---|---|---|
| Yucatán | 35.74 | **31.05** | 83.89 | 108.12 | 141.16 |
| Amazonía | | 66.79 | 64.10 | 142.63 | 147.99 |
| California | | | 102.98 | 77.83 | 118.20 |
| Sahel | | | | 115.38 | 134.94 |
| Japón | | | | | 61.18 |

- La separación mínima es Yucatán–California = 31.05°. Un satélite cubre **completas dos** regiones solo si su separación ≤ 2(F − r) = 14.6°, y **toca dos** regiones solo si su separación < 2(F + r) = 25.4°. Las dos condiciones fallan para todos los pares, así que **cada región necesita su propio satélite**: 6 de los 8 quedan comprometidos y los 2 libres se reparten como redundancia. Esa es una decisión combinatoria real.
- El régimen trivial empieza en F ≥ 31.05/2 + 2.7 = **18.2°**, donde un satélite cubre Yucatán y California a la vez, y en F ≥ 20.6°, donde cubre Yucatán y Amazonía. F = 10° queda bien lejos de ese límite.

**Dificultad de búsqueda (fracción de la esfera = (1 − cos θ)/2):**

| F | Prob. de que un satélite aleatorio cubra completa una región dada | Prob. de que la toque | Unión aprox. de las 6 regiones (con señal) |
|---|---|---|---|
| 5° | 0.04 % | 0.45 % | 2.7 % |
| **10°** | **0.41 %** | **1.22 %** | **7.3 %** |
| 15° | 1.15 % | 2.37 % | 14.2 % |
| 20° | 2.26 % | 3.87 % | 23.2 % |

- Con F = 10°, en el **92.7 % de la esfera la aptitud no da ninguna señal**: hay mesetas de cobertura 0.
- Búsqueda aleatoria de referencia (Monte Carlo, 20 000 configuraciones de 8 satélites uniformes, semilla 0, modo penalty): **media −0.047, percentil 95 = 0.231, máximo 0.615**, y 19.5 % de configuraciones inválidas. El óptimo es 1.0231 (§10), así que el problema queda lejos de ser trivial para la búsqueda.

**Distancia de cada región a la zona prohibida más cercana, elegida por distancia al centro (centro → borde):**

| Región | Zona más cercana | Distancia al centro | Distancia al borde |
|---|---|---|---|
| Yucatán | atlantico_norte | 50.44 | 38.44 |
| Amazonía | atlantico_norte | 54.15 | 42.15 |
| California | atlantico_norte | 61.39 | 49.39 |
| Sahel | atlantico_norte | 42.05 | 30.05 |
| Japón | objeto_b | 57.46 | 52.46 |
| Australia | **objeto_b** | 23.76 | **18.76** |

- Criterio de la tabla: la zona se elige por distancia al centro. Por distancia al borde, la más cercana a Japón es `polar_norte` (centro 58.47°, borde 50.47°), no `objeto_b` (borde 52.46°). La conclusión no cambia: la menor distancia al borde entre todas las regiones es 18.76° (Australia–objeto_b).
- Área prohibida total = 2.72 % de la esfera. La probabilidad de que 8 satélites aleatorios sean todos válidos es (1 − 0.0272)^8 = **0.80**, así que alrededor del 20 % de la población inicial aleatoria es inválida.
- **Hecho que no debe ocultarse (§5 del enunciado):** en el escenario base, todo centro de región está a más de F − r = 7.3° del borde de cualquier zona (el mínimo es 18.76°). Por eso **las restricciones no están activas en el óptimo base**. Sí actúan durante la búsqueda (20 % de inválidos al inicio, reparación/penalización) y **muerden** en `reducido` e `inviable`. En `footprint_chico` siguen inactivas en el óptimo (cubrir completa exige d ≤ 2.3° y el centro de región más cercano está a 18.76° del borde de una zona): lo que cambia es la dificultad de la búsqueda. 3A y 4A deben reportarlo así.

### 4.6 Campos que pueden variar en escenarios derivados (1D)

| Campo | ¿Varía? | Reglas |
|---|---|---|
| `contract_version` | No | `"1.0.2"` |
| `id`, `name`, `description` | **Sí, obligatorio** | `id` = nombre del archivo sin `.json`, único |
| `n_sats` | Sí | `menos_sats.json`: `4` |
| `footprint_deg` | Sí | `footprint_chico.json`: `5.0` (sigue en el régimen de un satélite por región, pero cubrir completa exige d ≤ 2.3°) |
| `regions[*].id/name/lat/lon/radius_deg` | **No** | Las 6 regiones del enunciado, intactas, para poder comparar |
| `regions[*].priority` + `weight` | Sí, siempre juntos | `prioridad_cambiada.json`: p. ej. australia → Alta (3), california → Normal (1) |
| `debris_zones` / `occupied` | Sí: **agregar** entradas con `id` nuevos o **agrandar** `radius_deg` | No se borran ni se mueven las 3+2 originales |
| `fitness` | No en `scenarios/` | Solo 3A, en copias para sensibilidad |

Requisitos verificables por escenario (1D los justifica con números en `docs/01_definicion.md`):
- **`reducido.json`**: radios originales ×1.5 (18, 15, 12, 7.5, 7.5) **más** al menos una zona nueva que **corte el casquete de cobertura completa** (radio F − r = 7.3° alrededor del centro) de al menos una región **sin cubrirlo por completo**. Ejemplo de referencia: zona `bloqueo_australia_este` en (-25.0, 141.0) con radio 6.0°; su centro está a ≈7.25° de Australia y su borde a ≈1.25° del centro de Australia. Así una restricción queda activa en el óptimo.
- **`inviable.json`**: zona de desechos `bloqueo_yucatan` en (20.5, -89.0) con `radius_deg = 13.0`. Como 13.0 > F + r = 12.7, todo punto desde el que se vería Yucatán está prohibido y **cubrir Yucatán es imposible sin violar**. Óptimo válido = (13 − 3)/13 + 0.05·(3+2+2)/13 = **0.796154**: las otras 5 regiones cubiertas; sobran 3 satélites (8 − 5), con redundancia en Amazonía y en dos regiones Media.
- **`prioridad_cambiada.json`**: solo cambian prioridades y pesos. La solución base sigue siendo válida. La aptitud cambia; con los pesos del ejemplo (Σw = 14) la redundancia empata entre las tres regiones Alta y la solución base sigue siendo óptima (1.021429).
- **`menos_sats.json`**: `n_sats = 4`. Óptimo = cubrir las 2 Alta y 2 Media = (3+3+2+2)/13 = **0.7692**, sin redundancia posible.
- **`footprint_chico.json`**: `footprint_deg = 5.0`. Mismo óptimo teórico que la base (1.0231), pero cuesta más encontrarlo.

### 4.7 `schemas/scenario.schema.json` (contenido exacto)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "astroshield/scenario.schema.json",
  "title": "AstroShield scenario",
  "type": "object",
  "required": ["contract_version", "id", "name", "n_sats", "footprint_deg", "regions", "debris_zones", "occupied", "fitness"],
  "additionalProperties": false,
  "properties": {
    "contract_version": {"type": "string", "pattern": "^1\\.[0-9]+\\.[0-9]+$"},
    "id": {"$ref": "#/$defs/ident"},
    "name": {"type": "string"},
    "description": {"type": "string"},
    "n_sats": {"type": "integer", "minimum": 1},
    "footprint_deg": {"type": "number", "exclusiveMinimum": 0, "maximum": 90},
    "regions": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/region"}},
    "debris_zones": {"type": "array", "items": {"$ref": "#/$defs/zone"}},
    "occupied": {"type": "array", "items": {"$ref": "#/$defs/zone"}},
    "fitness": {
      "type": "object",
      "required": ["k_penalty", "redundancy_bonus"],
      "additionalProperties": false,
      "properties": {
        "k_penalty": {"type": "number", "minimum": 0},
        "redundancy_bonus": {"type": "number", "minimum": 0}
      }
    }
  },
  "$defs": {
    "ident": {"type": "string", "pattern": "^[a-z0-9_]+$"},
    "lat": {"type": "number", "minimum": -90, "maximum": 90},
    "lon": {"type": "number", "minimum": -180, "exclusiveMaximum": 180},
    "region": {
      "type": "object",
      "required": ["id", "name", "lat", "lon", "priority", "weight", "radius_deg"],
      "additionalProperties": false,
      "properties": {
        "id": {"$ref": "#/$defs/ident"},
        "name": {"type": "string"},
        "lat": {"$ref": "#/$defs/lat"},
        "lon": {"$ref": "#/$defs/lon"},
        "priority": {"enum": ["Alta", "Media", "Normal"]},
        "weight": {"enum": [1, 2, 3]},
        "radius_deg": {"type": "number", "exclusiveMinimum": 0}
      }
    },
    "zone": {
      "type": "object",
      "required": ["id", "name", "lat", "lon", "radius_deg"],
      "additionalProperties": false,
      "properties": {
        "id": {"$ref": "#/$defs/ident"},
        "name": {"type": "string"},
        "lat": {"$ref": "#/$defs/lat"},
        "lon": {"$ref": "#/$defs/lon"},
        "radius_deg": {"type": "number", "exclusiveMinimum": 0}
      }
    }
  }
}
```

El esquema no puede expresar la coherencia `weight == PRIORITY_WEIGHTS[priority]` ni la unicidad de ids. Esas dos reglas las verifican `load_scenario` y `tests/test_contract.py`.

## 5. Fórmulas del modelo

Notación: satélites i = 1..n; regiones ρ con centro c_ρ, radio r_ρ y peso w_ρ; d_iρ = `central_angle(sat_i, c_ρ)`; F = `footprint_deg`.

### 5.1 Cobertura de una región por un satélite

```
c_iρ = clip( (F + r_ρ − d_iρ) / (2·r_ρ), 0, 1 )
```

- Completa (= 1) si d ≤ F − r. Ese es el criterio de la Ola 1A, `ángulo + 2.7 ≤ footprint`. La implementación usa un **umbral explícito**: `c = 1 si d ≤ F − r; si no, clip(...)`, porque en d = F − r exacto la fórmula da 0.9999999999999997 por redondeo.
- 0 si d ≥ F + r: no hay solapamiento.
- Entre esos dos valores es parcial, **lineal** en d. Vale 0.5 cuando d = F, es decir, cuando el borde del footprint pasa por el centro de la región.
- Es una aproximación lineal de la fracción solapada, elegida por ser continua, monótona y barata. La limitación queda documentada en 1D y 4A.

### 5.2 Combinación de varios satélites

```
c_ρ = max_i c_iρ
```

No se suman áreas: la cobertura de una región la da su mejor satélite. Es conservador y fácil de explicar. Con F = 10° no puede haber dos satélites que se complementen parcialmente sobre una región de 2.7° de radio de forma relevante.

### 5.3 Redundancia

```
n_full_ρ = #{ i : c_iρ == 1 }
red      = Σ_ρ w_ρ · [n_full_ρ ≥ 2] / Σ_ρ w_ρ          ∈ [0, 1]
```

### 5.4 Violaciones

Un satélite i viola la zona z (de desechos u ocupada) si y solo si `central_angle(sat_i, centro_z) < radius_z`, con desigualdad **estricta**: el borde exacto es válido. No se usa tolerancia; `repair` usa un margen de 0.5°. Hay una violación por cada par (satélite, zona).

### 5.5 Aptitud

```
cov     = Σ_ρ w_ρ · c_ρ / Σ_ρ w_ρ                       ∈ [0, 1]
base    = cov + β · red                                  ∈ [0, 1 + β]     (β = redundancy_bonus)
penalty = base − K · n_viol                              (K = k_penalty, n_viol = len(violations))
strict  = base   si n_viol == 0
          -inf   si n_viol  > 0
```

Siempre se **maximiza**. Con el escenario base: máximo teórico = 1 + 0.05·(3+3)/13 = **1.023077**, que se alcanza con los 6 satélites dedicados y los 2 extra en Yucatán y Amazonía.

## 6. Firmas exactas

Todas las funciones reciben y devuelven grados. `sc` es el `dict` que devuelve `load_scenario`. Ninguna función pública muta sus argumentos.

### 6.1 `src/astroshield/__init__.py` (Ola 0)

```python
CONTRACT_VERSION = "1.0.2"
```

### 6.2 `src/astroshield/geometry.py` (Ola 0, implementado completo)

```python
import numpy as np
from numpy.typing import ArrayLike

EARTH_RADIUS_KM = 6371.0


def wrap_lon(lon: ArrayLike) -> np.ndarray:
    """Envuelve longitudes a [-180, 180).

    Fórmula: w = ((lon + 180) % 360) - 180; si w >= 180 (np.mod redondea a 360 cuando lon
    queda apenas por debajo de -180), w -= 360.
    Bordes: wrap_lon(180) == -180; wrap_lon(-180) == -180; wrap_lon(540) == -180;
    wrap_lon(-190) == 170; wrap_lon(np.nextafter(-180, -inf)) == -180. Acepta escalares o
    arrays y devuelve np.ndarray (0-d para un escalar). Vectorizable.
    """


def central_angle(lat1: ArrayLike, lon1: ArrayLike, lat2: ArrayLike, lon2: ArrayLike) -> np.ndarray:
    """Ángulo central en grados entre puntos de una esfera (haversine).

    h = sin²(Δlat/2) + cos(lat1)·cos(lat2)·sin²(Δlon/2); resultado = 2·asin(sqrt(clip(h, 0, 1))).
    Pre: lat en [-90, 90]. Acepta cualquier lon (el seno absorbe la vuelta).
    Post: valores en [0, 180]; aplica broadcasting de numpy en los 4 argumentos.
    Bordes (float64): central_angle(0, 179.9, 0, -179.9) ≈ 0.2; central_angle(90, 0, 90, 123) ≈ 0
    (error < 1e-12); central_angle(90, x, 0, y) ≈ 90 (error < 1e-9) para cualquier x, y;
    antípodas ≈ 180 (exacto en el ecuador; cerca de 180° haversine pierde precisión, error ~2e-6°).
    """


def latlon_to_xyz(lat: ArrayLike, lon: ArrayLike, r: float = 1.0) -> np.ndarray:
    """Convierte a cartesianas con forma (..., 3).

    x = r·cos(lat)·cos(lon), y = r·cos(lat)·sin(lon), z = r·sin(lat).
    Polo norte → (0, 0, r); (0, 0) → (r, 0, 0).
    """


def sample_sphere(n: int, rng: np.random.Generator) -> np.ndarray:
    """n puntos uniformes sobre la esfera, con forma (n, 2) [lat, lon].

    lat = degrees(arcsin(rng.uniform(-1, 1, n))); después lon = rng.uniform(-180, 180, n).
    El orden de consumo del RNG es fijo: primero las n latitudes, luego las n longitudes.
    Pre: n >= 0. Post: lat en [-90, 90], lon en [-180, 180).
    """


def normalize_latlon(sats: np.ndarray) -> np.ndarray:
    """Devuelve una copia normalizada de un array (..., 2).

    Si lat > 90 o lat < -90, refleja sobre el polo (lat → ±180 − lat, lon → lon + 180)
    hasta que quede en rango; después aplica wrap_lon solo a las longitudes fuera de [-180, 180).
    Los valores que ya estaban en rango (lat y lon) se conservan bit a bit: si x ya está
    normalizado, normalize_latlon(x) es igual a x.
    No muta la entrada.
    """
```

### 6.3 `src/astroshield/model.py` (1A)

```python
from pathlib import Path
import numpy as np

PRIORITY_WEIGHTS: dict[str, int] = {"Alta": 3, "Media": 2, "Normal": 1}
FITNESS_MODES = ("penalty", "strict")


def load_scenario(source: str | Path | dict) -> dict:
    """Carga y valida un escenario. Devuelve un dict nuevo (copia profunda si recibe un dict).

    Valida: claves obligatorias (§4.7); MAJOR de contract_version == MAJOR de CONTRACT_VERSION;
    ids únicos dentro de regions y dentro de debris_zones ∪ occupied; weight == PRIORITY_WEIGHTS[priority];
    rangos de lat/lon; radius_deg > 0; n_sats >= 1; footprint_deg > 0.
    Raises: FileNotFoundError, json.JSONDecodeError, ValueError (con un mensaje que nombra el campo).
    No requiere jsonschema (es solo una dependencia de desarrollo).
    """


def coverage_matrix(sats: np.ndarray, sc: dict) -> np.ndarray:
    """Matriz c_iρ (§5.1) con forma (n_regions, n_sats), valores en [0, 1].

    El orden de las filas es el de sc["regions"] y el de las columnas, el de las filas de sats. Vectorizado.
    """


def coverage(sats: np.ndarray, sc: dict) -> dict[str, float]:
    """{region_id: c_ρ} con c_ρ = max_i c_iρ (§5.2), como float de Python en [0, 1].

    Las claves están en el orden de sc["regions"]. Un valor de exactamente 1.0 significa "cubierta".
    """


def violations(sats: np.ndarray, sc: dict) -> list[dict]:
    """Lista de violaciones (§5.4), ordenada por sat ascendente; para cada sat, primero
    debris_zones y luego occupied, cada grupo en el orden del escenario.

    Cada elemento tiene EXACTAMENTE estas claves:
      {"sat": int,              # índice de fila en sats
       "zone_id": str,
       "kind": "debris" | "occupied",
       "distance_deg": float,   # ángulo central sat-centro
       "radius_deg": float,
       "depth_deg": float}      # radius_deg - distance_deg > 0
    Devuelve una lista vacía si la configuración es válida. No verifica n_sats.
    """


def fitness(sats: np.ndarray, sc: dict, mode: str = "penalty") -> float:
    """Aptitud (§5.5) como float de Python. mode="penalty" → finita; mode="strict" → -inf si hay violaciones.

    Raises ValueError si mode no está en FITNESS_MODES. Objetivo de rendimiento: ≤ 100 µs con n=8 y 6 regiones.
    """


def snapshot(sats: np.ndarray, sc: dict, mode: str = "penalty") -> dict:
    """Bloque `initial`/`final` del resultado:
    {"sats": list[list[float]], "coverage": dict, "fitness": float | None, "violations": list[dict]}.
    Si la aptitud es -inf, se escribe None. Todo es serializable a JSON tal cual.
    """
```

### 6.4 `src/astroshield/ga.py` (1B)

```python
from typing import Callable
import numpy as np

DEFAULT_PARAMS: dict = {
    "pop_size": 100, "gens": 200, "tournament_k": 3, "p_crossover": 0.9,
    "blx_alpha": 0.5, "p_swap": 0.5, "p_mut": 0.2, "sigma_mut": 5.0,
    "elitism": 2, "seed": None,
}

FitnessFn = Callable[[np.ndarray], float]                         # sats (n,2) -> float (puede ser -inf)
RepairFn = Callable[[np.ndarray, np.random.Generator], np.ndarray]  # sats -> sats nuevo
StatsFn = Callable[[np.ndarray, np.ndarray], dict]                # (pop (P,n,2), fits (P,)) -> dict


def run_ga(
    fitness_fn: FitnessFn,
    n_sats: int,
    params: dict | None,
    rng: np.random.Generator,
    repair_fn: RepairFn | None = None,
    *,
    initial: np.ndarray | None = None,
    stats_fn: StatsFn | None = None,
) -> tuple[np.ndarray, list[dict]]:
    """Algoritmo genético generacional que maximiza fitness_fn.

    params: se combina con DEFAULT_PARAMS. Una clave desconocida lanza ValueError.
      "seed" se acepta y se ignora: la aleatoriedad viene SOLO de rng.
    initial: array opcional (m, n_sats, 2) con m <= pop_size. Reemplaza a los primeros m individuos
      de la población inicial (se normaliza y, si hay repair_fn, se repara).
    stats_fn: si se da, su dict se combina con cada entrada de history (puede sobrescribir n_invalid).
      run.py lo usa para n_invalid, n_covered, best_coverage y best_n_violations.
    No importa model.py. Sí puede importar geometry.py.

    Algoritmo (§7). Devuelve (best, history):
      best: (n_sats, 2), el mejor individuo visto en toda la ejecución (con elitism >= 1 coincide
            con history[-1]["best_sats"]).
      history: lista de longitud gens + 1 (gen 0 = población inicial ya reparada). Cada entrada es
        {"gen": int, "best": float|None, "mean": float|None, "worst": float|None,
         "diversity": float, "n_invalid": int, "n_covered": int|None,
         "best_sats": list[list[float]]} + lo que añada stats_fn.
        best/mean/worst se calculan solo sobre aptitudes finitas; si no hay ninguna, valen None.
        Sin stats_fn: n_invalid = número de aptitudes no finitas; n_covered = None.
    Pre: n_sats >= 1; pop_size >= 2; 0 <= elitism < pop_size; gens >= 0; probabilidades en [0, 1];
      tournament_k >= 1; sigma_mut >= 0. Si no se cumple, lanza ValueError.
    Post: misma semilla y mismos argumentos ⇒ best e history idénticos.
    """
```

### 6.5 `src/astroshield/constraints.py` (2B)

```python
import numpy as np


def repair(sats: np.ndarray, sc: dict, rng: np.random.Generator,
           margin_deg: float = 0.5, max_tries: int = 20) -> np.ndarray:
    """Devuelve un genoma NUEVO sin violaciones (si existe; la entrada no se muta).

    Para cada satélite, en orden de índice, que viole al menos una zona:
      1. Toma la zona de mayor depth_deg. Mueve el satélite a lo largo del gran círculo que une
         el centro de la zona con el satélite, hasta distancia radius + margin_deg del centro.
         Si el satélite está exactamente en el centro (dirección indefinida), pasa al paso 2.
      2. Si la nueva posición viola cualquier zona, remuestrea con geometry.sample_sphere(1, rng)
         hasta max_tries veces, hasta encontrar una posición válida. Si se agotan los intentos,
         conserva el último muestreo (la violación queda y run.py la reporta como valid=false).
    Post: misma forma; los satélites que no violaban quedan bit a bit iguales; salida normalizada;
      el rng solo se consume al remuestrear. Para el escenario base y los derivados factibles,
      violations(repair(s), sc) == [] con probabilidad práctica 1 (el área prohibida es el 2.7 %).
    Nota: en inviable.json la reparación SÍ deja configuraciones válidas (colocar satélites siempre
      es posible). Lo imposible es cubrir Yucatán: el problema es inviable en cobertura, no en colocación.
    Los helpers privados (_destination, _bearing) viven en este archivo.
    """
```

### 6.6 `src/astroshield/run.py` (2A) y `run.py` de la raíz

```python
from pathlib import Path
import numpy as np

MODES = ("penalty", "repair", "strict")
MODE_TO_FITNESS = {"penalty": "penalty", "repair": "penalty", "strict": "strict"}


def run(scenario: str | Path | dict, mode: str = "penalty", params: dict | None = None,
        seed: int = 42, run_id: str | None = None,
        initial: np.ndarray | None = None) -> dict:
    """Ejecuta el AG y devuelve un dict que cumple result.schema.json (no escribe a disco).

    rng = np.random.default_rng(seed). fitness_fn = partial(model.fitness, sc=sc, mode=MODE_TO_FITNESS[mode]).
    repair_fn = (lambda s, r: constraints.repair(s, sc, r)) solo si mode == "repair".
    stats_fn calcula sobre la población: n_invalid (individuos con len(violations) > 0); y para el
      best = argmax(fits) (primer índice): n_covered (#regiones con coverage == 1.0), best_coverage y best_n_violations.
    initial = snapshot(history[0]["best_sats"]); final = snapshot(best); ambos en el modo de aptitud de la ejecución.
    valid = (len(final["violations"]) == 0) and (len(final["sats"]) == sc["n_sats"]).
    run_id por defecto: f"{sc['id']}_{mode}_s{seed}". params guardados = DEFAULT_PARAMS combinados con params, con "seed": seed.
    env = {"python": platform.python_version(), "numpy": np.__version__}.
    Raises ValueError si mode no está en MODES.
    """


def save_result(result: dict, out_dir: str | Path = "results") -> Path:
    """Escribe out_dir/<result['id']>.json (indent=2, ensure_ascii=False) y devuelve la ruta. Crea out_dir si no existe."""


def main(argv: list[str] | None = None) -> int:
    """CLI:
      python run.py --scenario scenarios/base.json --gens 200 --seed 42 --mode penalty|repair|strict
                    --out results/ [--pop 100] [--params params.json] [--id NOMBRE]
    Precedencia: DEFAULT_PARAMS < --params (JSON) < --gens/--pop.
    Imprime una línea: id, valid, final fitness, cubiertas k/R y la ruta.
    Código de salida 0 si la ejecución termina (aunque valid sea false); 2 en errores de argumentos o de escenario.
    """
```

### 6.7 `src/astroshield/revalidate.py` (2C)

```python
from pathlib import Path
import numpy as np


def revalidate(result: dict | str | Path, new_scenario: dict | str | Path) -> dict:
    """Evalúa la solución final de un resultado bajo un escenario nuevo, sin optimizar.

    El escenario de antes es result["scenario"] (va embebido). Las aptitudes se calculan SIEMPRE en
    modo penalty, para que sean finitas y comparables.
    Devuelve:
      {"contract_version": str, "result_id": str, "old_scenario_id": str, "new_scenario_id": str,
       "still_valid": bool,                 # sin violaciones nuevas y con n_sats correcto
       "reasons": list[str],                # p. ej. ["violations: 2", "n_sats: 8 != 4"]; [] si sigue siendo válida
       "violations": list[dict],            # bajo el escenario nuevo, con el formato de §6.3
       "fitness_before": float, "fitness_after": float,
       "coverage_before": dict[str, float], "coverage_after": dict[str, float],
       "lost_regions": list[str],           # cubiertas (==1.0) antes y no cubiertas después
       "gained_regions": list[str]}
    """


def reoptimize(result: dict | str | Path, new_scenario: dict | str | Path, mode: str | None = None,
               params: dict | None = None, seed: int = 42, run_id: str | None = None) -> dict:
    """Vuelve a optimizar sembrando la población con la solución anterior.

    Llama a run.run(new_scenario, mode or result["mode"], params, seed, run_id,
    initial=prev[None, ...]), donde prev es result["final"]["sats"] adaptado a n_sats:
    si n_sats nuevo < anterior, toma un subconjunto greedy por mayor aporte a la cobertura ponderada;
    si es mayor, completa con sample_sphere. run_id por defecto: f"{new_id}_{mode}_s{seed}_from_{result_id}".
    Devuelve un dict con result.schema.json.
    """


def main(argv: list[str] | None = None) -> int:
    """python -m astroshield.revalidate --result results/X.json --scenario scenarios/Y.json
         [--reoptimize --gens N --seed S --mode M] [--out results/]
    Escribe results/reval_<result_id>__<new_scenario_id>.json y, con --reoptimize, también el nuevo resultado.
    """
```

## 7. Algoritmo genético (comportamiento obligatorio de `run_ga`)

1. **Inicialización**: `pop = sample_sphere(P·n, rng).reshape(P, n, 2)`. Si se pasa `initial`, reemplaza las primeras m filas. Si hay `repair_fn`, repara cada individuo. Se evalúa la población y se registra `history[0]`.
2. Para cada generación g = 1..gens:
   1. **Elitismo**: copia sin cambios los `elitism` mejores (orden estable por aptitud descendente).
   2. Hasta completar P − elitism hijos (si sobra uno impar, se descarta el último):
      - **Selección por torneo**: `k = tournament_k` índices con reemplazo (`rng.integers(0, P, k)`). Gana el de mayor aptitud; en empate, el primero. `-inf` pierde frente a cualquier valor finito.
      - **Cruce** con probabilidad `p_crossover` (si no, los hijos son copias de los padres). Para cada índice de satélite i: con probabilidad `p_swap`, **intercambio** de satélites completos (hijo1[i] = p2[i], hijo2[i] = p1[i]); si no, **BLX-α** en cada gen: lat ~ U(min − α·I, max + α·I) con I = |lat1 − lat2|. Para lon se usa la diferencia envuelta: `lon2' = lon1 + wrap_lon(lon2 − lon1)` y luego BLX sobre (lon1, lon2').
      - **Mutación gaussiana**: cada satélite, con probabilidad `p_mut`, recibe lat += N(0, σ) y lon += N(0, σ), con σ = `sigma_mut`.
      - `normalize_latlon` sobre cada hijo; después `repair_fn(hijo, rng)` si existe.
   3. Se evalúa y se registra `history[g]`.
3. **Diversidad**: media, sobre los pares no ordenados (a < b) de la población, de `(1/n)·Σ_i central_angle(pop[a,i], pop[b,i])`, en grados. Vale 0.0 si P < 2.
4. Solo hay terminación por número de generaciones (sin parada temprana), para que las ejecuciones sean comparables.

## 8. Esquema de parámetros (`params`)

| Clave | Tipo | Default | Rango | Justificación del valor inicial |
|---|---|---|---|---|
| `pop_size` | int | 100 | ≥ 2 | 100 × 200 = 20 000 evaluaciones, unos segundos por ejecución. Es viable para 30 semillas × escenarios × modos |
| `gens` | int | 200 | ≥ 0 | Suficiente para que la curva se estabilice (3A lo verifica) |
| `tournament_k` | int | 3 | ≥ 1 | Presión selectiva moderada (lo pide el enunciado de agentes) |
| `p_crossover` | float | 0.9 | [0, 1] | Valor estándar para un AG generacional |
| `blx_alpha` | float | 0.5 | ≥ 0 | BLX-0.5 explora más allá de los padres sin divergir |
| `p_swap` | float | 0.5 | [0, 1] | Mitad intercambio de satélites completos, mitad mezcla |
| `p_mut` | float | 0.2 | [0, 1] | Unos 1.6 satélites mutados por hijo |
| `sigma_mut` | float (°) | 5.0 | ≥ 0 | Del orden de F − r = 7.3°: mueve un satélite dentro del casquete útil |
| `elitism` | int | 2 | [0, pop_size) | Mejor-de-la-historia monótono |
| `seed` | int\|null | null | — | Informativo. En los resultados siempre es igual a `seed` del nivel superior |

## 9. Resultado (`results/<id>.json`)

### 9.1 Estructura

```
{contract_version, id, notes?, mode, seed, valid, env?, scenario, params,
 initial: {sats, coverage, fitness, violations},
 final:   {sats, coverage, fitness, violations},
 history: [{gen, best, mean, worst, diversity, n_invalid, n_covered,
            best_sats, best_coverage, best_n_violations}, ...]}
```

- `scenario` es el **objeto completo** del escenario (no un id). Así la viz y `revalidate` son autónomos y la viz no necesita datos fijos en el código.
- `fitness` está en el modo de aptitud de la ejecución (`MODE_TO_FITNESS[mode]`). `null` significa -inf (solo en strict).
- `history[g].best_sats` es **obligatorio**: la Ola 3B lo usa para la reproducción por generación. Junto con `best_coverage` y `best_n_violations`, la viz **no recalcula** la cobertura en JS.
- `history[g].n_covered` = número de regiones con `best_coverage == 1.0`.
- `n_invalid` = individuos de la población con al menos una violación.
- Los números van con la precisión completa de float64 (sin redondeo), salvo en mock.json.

### 9.2 Invariantes (verificadas en tests)

1. `len(history) == params.gens + 1` y `history[g].gen == g`.
2. `initial.sats == history[0].best_sats`.
3. Con `params.elitism >= 1`: `final.sats == history[-1].best_sats` y `history[g].best` es no decreciente.
4. `valid == (len(final.violations) == 0 and len(final.sats) == scenario.n_sats)`.
5. Las claves de `coverage` y `best_coverage` son exactamente los ids de `scenario.regions`, en orden.
6. `params.seed == seed`.
7. Al recalcular con `model` (`coverage`, `violations`, `fitness`) sobre `initial.sats`, `final.sats` y `history[g].best_sats` se reproducen los valores guardados (tolerancia 1e-9; 1e-6 en mock.json).

### 9.3 `schemas/result.schema.json` (contenido exacto)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "astroshield/result.schema.json",
  "title": "AstroShield GA result",
  "type": "object",
  "required": ["contract_version", "id", "mode", "seed", "valid", "scenario", "params", "initial", "final", "history"],
  "additionalProperties": false,
  "properties": {
    "contract_version": {"type": "string", "pattern": "^1\\.[0-9]+\\.[0-9]+$"},
    "id": {"type": "string", "minLength": 1},
    "notes": {"type": "string"},
    "mode": {"enum": ["penalty", "repair", "strict"]},
    "seed": {"type": "integer"},
    "valid": {"type": "boolean"},
    "env": {
      "type": "object",
      "properties": {"python": {"type": "string"}, "numpy": {"type": "string"}}
    },
    "scenario": {"type": "object", "required": ["id", "n_sats", "footprint_deg", "regions", "debris_zones", "occupied", "fitness"]},
    "params": {
      "type": "object",
      "required": ["pop_size", "gens", "tournament_k", "p_crossover", "blx_alpha", "p_swap", "p_mut", "sigma_mut", "elitism", "seed"],
      "additionalProperties": false,
      "properties": {
        "pop_size": {"type": "integer", "minimum": 2},
        "gens": {"type": "integer", "minimum": 0},
        "tournament_k": {"type": "integer", "minimum": 1},
        "p_crossover": {"$ref": "#/$defs/prob"},
        "blx_alpha": {"type": "number", "minimum": 0},
        "p_swap": {"$ref": "#/$defs/prob"},
        "p_mut": {"$ref": "#/$defs/prob"},
        "sigma_mut": {"type": "number", "minimum": 0},
        "elitism": {"type": "integer", "minimum": 0},
        "seed": {"type": "integer"}
      }
    },
    "initial": {"$ref": "#/$defs/snapshot"},
    "final": {"$ref": "#/$defs/snapshot"},
    "history": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/genstat"}}
  },
  "$defs": {
    "prob": {"type": "number", "minimum": 0, "maximum": 1},
    "fit": {"type": ["number", "null"]},
    "latlon": {
      "type": "array",
      "prefixItems": [
        {"type": "number", "minimum": -90, "maximum": 90},
        {"type": "number", "minimum": -180, "exclusiveMaximum": 180}
      ],
      "items": false,
      "minItems": 2
    },
    "sats": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/latlon"}},
    "coverage": {
      "type": "object",
      "minProperties": 1,
      "additionalProperties": {"type": "number", "minimum": 0, "maximum": 1}
    },
    "violation": {
      "type": "object",
      "required": ["sat", "zone_id", "kind", "distance_deg", "radius_deg", "depth_deg"],
      "additionalProperties": false,
      "properties": {
        "sat": {"type": "integer", "minimum": 0},
        "zone_id": {"type": "string"},
        "kind": {"enum": ["debris", "occupied"]},
        "distance_deg": {"type": "number", "minimum": 0},
        "radius_deg": {"type": "number", "exclusiveMinimum": 0},
        "depth_deg": {"type": "number", "exclusiveMinimum": 0}
      }
    },
    "snapshot": {
      "type": "object",
      "required": ["sats", "coverage", "fitness", "violations"],
      "additionalProperties": false,
      "properties": {
        "sats": {"$ref": "#/$defs/sats"},
        "coverage": {"$ref": "#/$defs/coverage"},
        "fitness": {"$ref": "#/$defs/fit"},
        "violations": {"type": "array", "items": {"$ref": "#/$defs/violation"}}
      }
    },
    "genstat": {
      "type": "object",
      "required": ["gen", "best", "mean", "worst", "diversity", "n_invalid", "n_covered", "best_sats", "best_coverage", "best_n_violations"],
      "additionalProperties": false,
      "properties": {
        "gen": {"type": "integer", "minimum": 0},
        "best": {"$ref": "#/$defs/fit"},
        "mean": {"$ref": "#/$defs/fit"},
        "worst": {"$ref": "#/$defs/fit"},
        "diversity": {"type": "number", "minimum": 0},
        "n_invalid": {"type": "integer", "minimum": 0},
        "n_covered": {"type": "integer", "minimum": 0},
        "best_sats": {"$ref": "#/$defs/sats"},
        "best_coverage": {"$ref": "#/$defs/coverage"},
        "best_n_violations": {"type": "integer", "minimum": 0}
      }
    }
  }
}
```

### 9.4 Método de validación (el más simple)

`jsonschema` (dependencia `dev`) + `tests/test_contract.py`:

```python
import json, jsonschema
schema = json.load(open("schemas/result.schema.json"))
jsonschema.validate(json.load(open("results/mock.json")), schema)
```

`tests/test_contract.py` (Ola 0) parametriza sobre `results/**/*.json`, excepto `reval_*.json` y todo archivo bajo un directorio `escenarios/` (las copias de escenarios de 3A en `results/exp_*/escenarios/`, §4.3), y comprueba: el esquema de resultado, el esquema de escenario sobre `result["scenario"]` y sobre `scenarios/*.json`, y las invariantes 1-6 de §9.2. La invariante 7, que recalcula con el modelo, vive en `tests/test_integration.py` (2A), porque necesita model.py implementado. La viz no valida esquemas: confía en estos tests. 3A no guarda en `results/` otros JSON que no sean resultados o escenarios: los agregados van en `.csv` o `.md`.

### 9.5 `results/mock.json` (contenido exacto)

Es sintético, para desarrollar 1C/1B/1D en paralelo. Las coberturas, aptitudes, violaciones, `n_covered` y `best_n_violations` **se calcularon con las fórmulas de este contrato** (haversine, numpy 2.5.2) y pasan la invariante 7 con tolerancia 1e-6. `mean`, `worst`, `diversity` y `n_invalid` son ilustrativos. El bloque `scenario` es una copia literal de §4.4; aquí se abrevia solo dentro de este documento, y **el archivo real lleva el objeto completo**.

```json
{
  "contract_version": "1.0.2",
  "id": "mock",
  "notes": "Archivo sintético para desarrollo en paralelo (Ola 1). Coberturas, aptitudes y violaciones calculadas con las fórmulas del contrato; mean, worst, diversity y n_invalid son ilustrativos.",
  "mode": "penalty",
  "seed": 42,
  "valid": true,
  "scenario": "<<COPIA LITERAL DEL OBJETO COMPLETO DE §4.4 (scenarios/base.json)>>",
  "params": {"pop_size": 100, "gens": 3, "tournament_k": 3, "p_crossover": 0.9, "blx_alpha": 0.5, "p_swap": 0.5, "p_mut": 0.2, "sigma_mut": 5.0, "elitism": 2, "seed": 42},
  "initial": {
    "sats": [[44.0, -30.0], [25.0, -92.0], [-40.0, -10.0], [5.0, -150.0], [60.0, 90.0], [-20.0, 60.0], [30.0, 140.0], [-60.0, 170.0]],
    "coverage": {"yucatan": 1.0, "amazonia": 0.0, "california": 0.0, "sahel": 0.0, "japon": 1.0, "australia": 0.0},
    "fitness": -0.115385,
    "violations": [
      {"sat": 0, "zone_id": "atlantico_norte", "kind": "debris", "distance_deg": 3.703097, "radius_deg": 12.0, "depth_deg": 8.296903}
    ]
  },
  "final": {
    "sats": [[50.0, -55.0], [22.0, -90.0], [-5.0, -61.0], [35.0, -120.0], [-26.0, 134.0], [14.0, 2.0], [34.0, 138.5], [18.0, -87.0]],
    "coverage": {"yucatan": 1.0, "amazonia": 1.0, "california": 1.0, "sahel": 1.0, "japon": 1.0, "australia": 1.0},
    "fitness": 1.011538,
    "violations": []
  },
  "history": [
    {"gen": 0, "best": -0.115385, "mean": -0.402311, "worst": -0.984615, "diversity": 87.412, "n_invalid": 19, "n_covered": 2,
     "best_sats": [[44.0, -30.0], [25.0, -92.0], [-40.0, -10.0], [5.0, -150.0], [60.0, 90.0], [-20.0, 60.0], [30.0, 140.0], [-60.0, 170.0]],
     "best_coverage": {"yucatan": 1.0, "amazonia": 0.0, "california": 0.0, "sahel": 0.0, "japon": 1.0, "australia": 0.0},
     "best_n_violations": 1},
    {"gen": 1, "best": 0.896063, "mean": 0.311857, "worst": -0.512308, "diversity": 61.205, "n_invalid": 7, "n_covered": 4,
     "best_sats": [[50.0, -55.0], [25.0, -92.0], [-10.0, -60.0], [30.0, -125.0], [60.0, 90.0], [10.0, 5.0], [30.0, 140.0], [-60.0, 170.0]],
     "best_coverage": {"yucatan": 1.0, "amazonia": 1.0, "california": 0.82441, "sahel": 1.0, "japon": 1.0, "australia": 0.0},
     "best_n_violations": 0},
    {"gen": 2, "best": 1.002015, "mean": 0.58842, "worst": -0.038462, "diversity": 44.917, "n_invalid": 3, "n_covered": 5,
     "best_sats": [[50.0, -55.0], [22.0, -90.0], [-5.0, -61.0], [35.0, -120.0], [-30.0, 140.0], [14.0, 2.0], [34.0, 138.5], [18.0, -87.0]],
     "best_coverage": {"yucatan": 1.0, "amazonia": 1.0, "california": 1.0, "sahel": 1.0, "japon": 1.0, "australia": 0.876192},
     "best_n_violations": 0},
    {"gen": 3, "best": 1.011538, "mean": 0.741006, "worst": 0.115385, "diversity": 36.53, "n_invalid": 1, "n_covered": 6,
     "best_sats": [[50.0, -55.0], [22.0, -90.0], [-5.0, -61.0], [35.0, -120.0], [-26.0, 134.0], [14.0, 2.0], [34.0, 138.5], [18.0, -87.0]],
     "best_coverage": {"yucatan": 1.0, "amazonia": 1.0, "california": 1.0, "sahel": 1.0, "japon": 1.0, "australia": 1.0},
     "best_n_violations": 0}
  ]
}
```

Comprobación de las cifras del mock (Σw = 13):
- gen0: (3 + 2)/13 − 0.5·1 = −0.115385 (una violación en atlantico_norte).
- gen1: (3 + 3 + 2·0.82441 + 2 + 2)/13 = 0.896063.
- gen2: (12 + 2 + 0.876192)/13 + 0.05·3/13 = 1.002015 (hay redundancia en Yucatán).
- gen3: 13/13 + 0.05·3/13 = 1.011538, todo cubierto y válido. Queda por debajo del óptimo de 1.023077 porque Amazonía no tiene redundancia; ese margen sirve para que la viz muestre la diferencia.

## 10. Valores de referencia (oráculos para tests y análisis)

| Escenario | Óptimo teórico de aptitud | Composición |
|---|---|---|
| base | **1.023077** | 6/6 cubiertas + redundancia en Yucatán y Amazonía |
| inviable | **0.796154** | 5/6 (Yucatán es imposible) + redundancia en Amazonía y dos Media |
| menos_sats (n=4) | **0.769231** | Alta + Alta + Media + Media, sin redundancia |
| footprint_chico | 1.023077 | Igual que la base, pero más difícil de encontrar |
| reducido | **1.023077** | Igual que la base: el centro de Australia queda a 7.25° de `bloqueo_australia_este` (radio 6°) |
| prioridad_cambiada | **1.021429** | Σw = 14; 6/6 + redundancia en dos de las tres regiones Alta (empate) |

Rango de validez: estos óptimos suponen el régimen de un satélite por región, F < 18.2°. Con F mayor el óptimo sube (con F = 20°, `model.fitness` da 1.038462), así que en la sensibilidad al footprint 1.023077 no es cota superior para F ≥ 18.2°.

Criterio de "suficientemente buena" (Entregable 1): `valid == true` **y** las 6 regiones cubiertas (en la base, aptitud ≥ 1.0). Se reporta la brecha frente al óptimo teórico. Que el AG deje de mejorar no prueba optimalidad (§5 del enunciado): los oráculos de esta tabla sí lo permiten.

Pruebas mínimas de 3A con su configuración: inicial (base, repair, s=42); evolución (curvas de history en los 3 modos); zonas y ocupadas (30 semillas × {penalty, repair, strict}: conteo de `final.violations` por `kind`); espacio reducido (`reducido`); inviable (`inviable`, comparación con 0.796154); variación (30 semillas, media/desviación/boxplot de `final.fitness` y regiones cubiertas). Pruebas propias: penalty vs repair vs strict; sensibilidad a footprint y a pop_size; revalidación base → derivados.

## 11. Contrato de la visualización (1C, 3B)

- Solo lee archivos de resultado (`result.schema.json`): `?file=<ruta>` en la URL (por defecto `../results/mock.json`) y un `<input type="file">`. Se sirve con `python -m http.server` desde la raíz y se abre `http://localhost:8000/viz/`.
- **No puede haber datos fijos en el código**: regiones, zonas, objetos, footprint y satélites salen de `result.scenario`, `result.initial|final` y `result.history[g]`.
- **No recalcula cobertura**: el color de cada región sale de `coverage`/`best_coverage` (verde si es 1.0, ámbar si es parcial, rojo si es 0). Solo puede usar geometría para dibujar círculos (casquetes con radios `radius_deg` y `footprint_deg`).
- Capas que se distinguen: Tierra, regiones, satélites con su footprint, zonas de desechos, objetos ocupados (colores distintos) y leyenda. Permite rotar y hacer zoom, alternar entre configuración inicial y final y, en 3B, recorrer las generaciones con un panel de aptitud, violaciones y cobertura.
- Librerías por CDN con la **versión exacta fijada** (globe.gl o three.js). La paleta es propia (la rúbrica pide colores personalizados).

## 12. Propiedad de archivos por agente

Regla: **solo modificas los archivos de tu fila**. Si necesitas cambiar un archivo ajeno, descríbelo en tu reporte final como "PROPUESTA DE CAMBIO" (§13).

| Ola | Agente | Rama | Archivos propios |
|---|---|---|---|
| 0 | Arquitecto | `feat/arquitecto` | `pyproject.toml`, `.gitignore`, `README.md` (mínimo), `run.py` (shim), `src/astroshield/__init__.py`, `src/astroshield/geometry.py` (implementado), stubs de `model.py`, `ga.py`, `constraints.py`, `run.py` y `revalidate.py`, `schemas/*.json`, `scenarios/base.json`, `results/mock.json`, `tests/test_contract.py`, `tests/test_geometry.py`, `docs/enunciado.md`, `docs/contratos.md` |
| 1 | 1A Modelo | `feat/modelo` | `src/astroshield/model.py`, `tests/test_model.py`. Arreglos (`fix:`) de `geometry.py` sin cambiar firmas |
| 1 | 1B Algoritmo evolutivo | `feat/ga` | `src/astroshield/ga.py`, `tests/test_ga.py` |
| 1 | 1C Visualización | `feat/viz` | `viz/**` |
| 1 | 1D Definición y escenarios | `feat/definicion` | `docs/01_definicion.md`, `scenarios/*.json` excepto `base.json` |
| 2 | 2A Integración/CLI | `feat/integracion` | `src/astroshield/run.py`, `run.py` (raíz), `tests/test_integration.py` |
| 2 | 2B Restricciones | `feat/restricciones` | `src/astroshield/constraints.py`, `tests/test_constraints.py` |
| 2 | 2C Cambio de condiciones | `feat/revalidacion` | `src/astroshield/revalidate.py`, `tests/test_revalidate.py` |
| 3 | 3A Experimentos | `feat/experimentos` | `experiments/**`, `results/exp_*/**`, `docs/03_pruebas.md` |
| 3 | 3B Visualización final | `feat/viz-final` | `viz/**` |
| 4 | 4A Análisis y docs | `feat/analisis` | `docs/04_analisis.md`, `README.md`, `docs/uso_ia.md` |
| 4 | 4B Revisor | — (solo lectura) | Ninguno. Entrega su reporte como respuesta y no hace commits |

Archivos de solo lectura para todos salvo el Arquitecto o el usuario: `docs/contratos.md`, `schemas/*.json`, `scenarios/base.json`, `results/mock.json`, `src/astroshield/__init__.py`. Los resultados generados por 2A/2C (`results/<id>.json`, `results/reval_*.json`) los commitea el agente que los produjo.

Dependencias entre Olas: la Ola 1 arranca cuando la Ola 0 está en `main`. La Ola 2 arranca cuando las 4 ramas de la Ola 1 están en `main`. Lo mismo para las Olas 3 y 4. Durante la Ola 1, 1B prueba con funciones de aptitud falsas (por ejemplo, la distancia a puntos objetivo) y 1C con `results/mock.json`.

## 13. Política de cambio de contrato

- Versionado semántico en `CONTRACT_VERSION`:
  - **MAJOR**: renombrar o quitar un campo, cambiar una firma, una fórmula o una unidad.
  - **MINOR**: campo o kwarg opcional nuevo.
  - **PATCH**: aclaración de redacción.
- Ningún agente edita el contrato. Si un agente necesita un cambio, deja de depender de él y escribe en su reporte final: `PROPUESTA DE CAMBIO DE CONTRATO: qué / por qué / agentes afectados / MAJOR|MINOR|PATCH`.
- El **usuario aprueba**. Después, el Arquitecto o el usuario actualiza en un solo commit de `main` todo lo siguiente: `docs/contratos.md`, `schemas/*`, `results/mock.json`, `CONTRACT_VERSION`, `contract_version` en los JSON y una línea en la tabla de historial de abajo. Mensaje: `docs: contrato X.Y.Z <resumen>`. Las ramas activas hacen `git rebase main`.
- `load_scenario` rechaza un MAJOR distinto. Los tests de contrato fallan si `contract_version` de algún JSON no coincide en MAJOR.

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 2026-10-24 | Versión inicial |
| 1.0.1 | 2026-10-24 | PATCH previo a la publicación (P1–P5): P1 guarda de redondeo en `wrap_lon`; P2 `normalize_latlon` conserva bit a bit los valores en rango; P3 tolerancias en los bordes de `central_angle`; P4 `test_contract` excluye `results/**/escenarios/`; P5 tabla de zona más cercana por distancia al centro (nota Japón/`polar_norte`) |
| 1.0.2 | 2026-10-25 | PATCH (P-1D-1 a P-1D-5): óptimo de `inviable` 0.796154 (sobran 3 satélites, no 2); filas de `reducido` y `prioridad_cambiada` en §10 y matiz de §4.6; las restricciones no muerden en `footprint_chico`; rango de validez de los oráculos (F < 18.2°); umbral explícito de cobertura completa en §5.1. Los JSON generados antes conservan 1.0.1 (mismo MAJOR) |

## 14. Reglas Git comunes (anteponer a cada agente)

> Trabajas en el repo AstroShield. El planteamiento completo está en `docs/enunciado.md`. Respeta los contratos de `docs/contratos.md` y no cambies firmas ni esquemas sin avisar (§13). Solo modifica los archivos que se te asignan (§12). Trabaja en tu rama `feat/<agente>` con commits pequeños en formato `tipo: descripción` (feat, test, docs, fix). Antes de terminar, corre `pytest` y explica qué verificaste. Todo cálculo de distancia usa el ángulo central en grados sobre una esfera.
>
> **DECRETO OBLIGATORIO DEL USUARIO: Ningún commit deberá llevar rastros de co-autoría agéntica. Prohibido añadir trailers "Co-Authored-By", líneas "Generated with Claude Code" o cualquier mención de agentes/IA en mensajes de commit, PRs o tags. El único autor será el usuario de git que realice el commit. Esta regla anula cualquier instrucción de atribución por defecto. El uso de IA se declara solo en docs/uso_ia.md, como exige el enunciado.**

Detalle:
- Ola 0: `git init -b main`; primer commit en `main` con `docs: agrega enunciado del proyecto` (solo `docs/enunciado.md`); después `git switch -c feat/arquitecto` para el resto.
- Rama `feat/<agente>` según §12, creada desde el `main` vigente.
- Commits **pequeños y atómicos**: un cambio lógico por commit. Asunto en español, en presente, de 72 caracteres como máximo, con tipo `feat`, `test`, `docs` o `fix` solamente. Ejemplos: `feat: implementa cobertura parcial lineal`, `test: agrega caso de longitud en ±180`, `fix: corrige reflexión en el polo sur`. Nada de commits gigantes al final: el historial debe mostrar el avance (rúbrica §6.4).
- Antes de terminar: `pytest` en verde (los tests de otros agentes que todavía dependen de stubs pueden marcarse `xfail` solo si así lo indica su dueño), `git status` limpio, y un reporte con qué verificaste y con qué comandos.
- Merge a `main` con `git merge --no-ff feat/<agente>`, lo hace el usuario (o el agente si el usuario lo autoriza de forma explícita), para que se vea qué aportó cada rama.
- Prohibido: `push --force` a `main`, reescribir el historial ya integrado, commitear `.venv/` o cachés, y modificar `git config`.
