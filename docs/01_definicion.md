# Entregable 1 — Definición del problema

Este documento recoge las decisiones con las que el escenario de AstroShield (`docs/enunciado.md`) se convierte en un problema computacional que un algoritmo evolutivo puede resolver. Responde a las siete preguntas del Entregable 1 y añade los supuestos del modelo, los escenarios derivados con sus óptimos teóricos y las limitaciones conocidas.

Las fórmulas, nombres y valores coinciden con `docs/contratos.md` (v1.0.1) y con el código de `src/astroshield/`. Todas las cifras se recalcularon con `astroshield.geometry` y `astroshield.model` (Python 3.14.8, numpy 2.5.4). Donde el cálculo no coincide con el contrato, se indica de forma explícita.

## 0. Resumen y supuestos del modelo

**Resumen.** Una configuración son 8 puntos (latitud, longitud) sobre una esfera. Cada punto observa un casquete de 10° de radio angular. Con ese radio, ningún satélite puede cubrir dos regiones a la vez, así que 6 de los 8 satélites quedan comprometidos, uno por región, y los 2 restantes se reparten como redundancia. Todo eso hay que conseguirlo sin colocar ningún satélite dentro de una zona de desechos o de un objeto ocupado. La aptitud premia la cobertura ponderada por prioridad, da un bono pequeño por la redundancia y resta una penalización por cada violación. El óptimo teórico del escenario base es **1.023077**.

Supuestos del modelo:

- **Simulación educativa** (§1.1 del enunciado). No hay mecánica orbital, altitud ni tiempo. Un satélite es un punto subsatelital fijo con un casquete de observación de radio angular `footprint_deg` (F).
- **La Tierra es una esfera unitaria.** Toda distancia es el ángulo central en grados, calculado con haversine (`geometry.central_angle`). La distancia euclidiana sobre (lat, lon) no se usa en ningún sitio. El radio terrestre (6371 km) solo sirve para convertir kilómetros en grados.
- **Regiones, zonas de desechos y objetos ocupados** son casquetes esféricos definidos por un centro y un radio angular. Las regiones se observan; las zonas y los objetos están prohibidos.
- **Unidades y orden.** Grados en toda la API y en los JSON; los pares van siempre como `[lat, lon]`, con lat ∈ [−90, 90] y lon ∈ [−180, 180).
- **Un solo objetivo escalar que se maximiza** (§3). Las restricciones entran en la aptitud según el modo (§4).
- **Reproducibilidad.** Cada ejecución crea un único `numpy.random.Generator` a partir de su semilla y lo pasa hacia abajo. Con la misma semilla y la misma versión de numpy, el resultado es idéntico bit a bit.
- **El escenario es un dato, no código.** Regiones, zonas, número de satélites, footprint, K y β viven en `scenarios/*.json` (validados por `schemas/scenario.schema.json` y por `model.load_scenario`). Los escenarios derivados de la §8 solo cambian esos archivos.

## 1. Representación de una configuración

**Genoma.** Una configuración es un arreglo `numpy` de `float64` con forma `(n_sats, 2)`. La fila `i` es `[lat_i, lon_i]` en grados: el punto subsatelital del satélite `i`. En el escenario base `n_sats = 8`. El número de satélites lo fija el escenario, no el código (en `menos_sats.json` vale 4).

Ejemplo (configuración final de `results/mock.json`):

```
[[50.0, -55.0], [22.0, -90.0], [-5.0, -61.0], [35.0, -120.0],
 [-26.0, 134.0], [14.0, 2.0], [34.0, 138.5], [18.0, -87.0]]
```

**Qué contiene y qué no.** Solo posiciones: 16 números reales. La cobertura, las violaciones y la aptitud se *derivan* de esas posiciones con `model.coverage`, `model.violations` y `model.fitness`. No se guardan en el genoma, así que no pueden quedar desincronizadas con él.

**Rangos y normalización.** lat ∈ [−90, 90] y lon ∈ [−180, 180). Después de cada cruce o mutación, `geometry.normalize_latlon` hace dos cosas:

- Si la latitud se sale de rango, refleja el punto sobre el polo: lat → ±180 − lat y lon → lon + 180.
- Envuelve la longitud con `wrap_lon`, de modo que 180 pasa a −180.

Los valores que ya están en rango se conservan bit a bit. Toda función pública que devuelve un genoma lo devuelve normalizado, como un arreglo nuevo, sin mutar la entrada.

**Conjunto no ordenado.** Dos genomas que solo difieren en el orden de sus filas representan la misma constelación: los satélites son intercambiables. El algoritmo evolutivo, sin embargo, cruza por índice, satélite `i` con satélite `i`. Es una simplificación deliberada; su costo se discute en la §9.

**Número de filas.** Un genoma con un número de filas distinto de `sc["n_sats"]` hace inválida la solución (§4).

**Por qué esta representación.** Es la codificación directa del problema: no hay que decodificar nada, los operadores continuos (BLX-α y mutación gaussiana, §5) actúan sobre ella sin más, y su tamaño es mínimo. Se descartaron dos alternativas:

- **Una rejilla discreta de posiciones.** Pierde precisión justo donde importa, porque cubrir una región completa exige acercarse a menos de 7.3° de su centro.
- **Coordenadas cartesianas (x, y, z).** Obligan a mantener la restricción de norma 1 después de cada operador.

## 2. Qué significa que una región esté cubierta

### 2.1 Radio de una región

El enunciado fija un radio de observación de 300 km alrededor del centro de cada región. Sobre la esfera:

```
r = 300 km / 6371 km = 0.047088 rad = 2.698° ≈ 2.7°
```

Cada región es un casquete de radio angular r = 2.7° (`radius_deg` en el escenario).

### 2.2 Footprint de un satélite: F = 10°

Cada satélite observa un casquete de radio angular F = `footprint_deg` = 10°, unos 1112 km sobre la superficie. Sea d la distancia angular entre el satélite y el centro de una región:

- La región queda **completa** dentro del casquete si d ≤ F − r = 7.3°.
- **No se toca** si d ≥ F + r = 12.7°.

El valor de 10° se eligió mirando las distancias entre los centros de las regiones (en grados, con `geometry.central_angle`):

| | Amazonía | California | Sahel | Japón | Australia |
|---|---|---|---|---|---|
| Yucatán | 35.74 | **31.05** | 83.89 | 108.12 | 141.16 |
| Amazonía | | 66.79 | 64.10 | 142.63 | 147.99 |
| California | | | 102.98 | 77.83 | 118.20 |
| Sahel | | | | 115.38 | 134.94 |
| Japón | | | | | 61.18 |

- La separación mínima es la de Yucatán y California: 31.05°.
- Un satélite cubre completas dos regiones solo si su separación es ≤ 2(F − r) = 14.6°.
- Un satélite toca dos regiones solo si su separación es < 2(F + r) = 25.4°.
- Ningún par cumple ninguna de las dos condiciones. Por eso **cada región necesita su propio satélite**: 6 de los 8 quedan comprometidos y los 2 libres se reparten como redundancia. Esa es una decisión combinatoria real.
- El problema se vuelve trivial a partir de F ≥ 31.05/2 + 2.7 = **18.2°**, cuando un satélite cubre a la vez Yucatán y California. F = 10° queda lejos de ese régimen.

Con F = 10° el problema también es difícil para una búsqueda a ciegas. La fracción de la esfera dentro de un casquete de radio θ es (1 − cos θ)/2. Así:

- Un satélite aleatorio cubre completa una región dada con probabilidad **0.41 %**.
- La toca con probabilidad **1.22 %**.
- La unión aproximada de las 6 zonas con señal es **7.3 %** de la esfera. En el 92.7 % restante, mover un satélite no cambia la cobertura: hay mesetas de aptitud.

Con F = 5° (escenario `footprint_chico`, §8) esas cifras bajan a 0.040 %, 0.45 % y 2.7 %.

### 2.3 Cobertura de una región por un satélite

```
c_iρ = clip( (F + r_ρ − d_iρ) / (2·r_ρ), 0, 1 )
```

donde d_iρ = `central_angle(sat_i, centro_ρ)`. La cobertura vale 1 cuando la región cabe completa en el casquete, 0 cuando no hay solapamiento, y es **lineal** en d entre esos dos extremos. Es una aproximación de la fracción solapada: continua, monótona y barata de calcular. Con F = 10° y r = 2.7°:

| d (°) | 0 | 7.3 | 8.65 | 10 | 11.35 | 12.7 |
|---|---|---|---|---|---|---|
| c | 1 | 1 | 0.75 | 0.5 | 0.25 | 0 |

La parte parcial no es un adorno: le da al algoritmo una pendiente para pasar de "toca la región" a "la cubre completa".

### 2.4 Varios satélites sobre la misma región

```
c_ρ = max_i c_iρ
```

La cobertura de una región la aporta su mejor satélite. No se suman áreas: es una regla conservadora y fácil de explicar. Con F = 10° tampoco hay casos relevantes en que dos satélites parciales se complementen sobre una región de 2.7°.

### 2.5 Criterio de cubierta

Una región está **cubierta** si y solo si c_ρ == 1.0. Si 0 < c_ρ < 1 está *parcial*, y si c_ρ = 0, *no cubierta*. La función `model.coverage` devuelve `{region_id: c_ρ}`, y el resultado de cada ejecución guarda esas coberturas para la configuración inicial, la final y el mejor individuo de cada generación (`best_coverage`).

Nota numérica: la implementación aplica la fórmula tal cual (`model.coverage_matrix`). En el borde exacto d = F − r, el redondeo en coma flotante da 0.9999999999999997 en vez de 1.0, así que un satélite situado justo en ese borde cuenta como cobertura parcial. En la práctica, cubrir una región exige quedar a menos de 7.3° de su centro; con el satélite sobre el centro, c = 1.0 exacto. Ver la §9.

## 3. Calidad de una configuración y prioridades

### 3.1 Pesos de prioridad

Las prioridades se traducen en pesos lineales: `PRIORITY_WEIGHTS = {"Alta": 3, "Media": 2, "Normal": 1}` (constante en `model.py`). Cada región del escenario guarda su `priority` y su `weight`, y `load_scenario` rechaza el escenario si no coinciden. En la base:

```
Σw = 3 + 3 + 2 + 2 + 2 + 1 = 13
```

Esta escala respeta el orden del enunciado y es fácil de leer: una región Alta vale lo mismo que una Media más una Normal. Las prioridades entran en la aptitud de dos maneras: deciden qué región conviene cubrir cuando no se pueden cubrir todas (§8, `menos_sats` e `inviable`) y a qué regiones conviene darles redundancia.

### 3.2 Aptitud

Notación: d_iρ es la distancia del satélite i al centro de la región ρ; c_ρ es la cobertura de §2.4; n_full_ρ es el número de satélites con c_iρ = 1; β = `redundancy_bonus` y K = `k_penalty` vienen del bloque `fitness` del escenario.

```
cov     = Σ_ρ w_ρ · c_ρ / Σ_ρ w_ρ                     ∈ [0, 1]
red     = Σ_ρ w_ρ · [n_full_ρ ≥ 2] / Σ_ρ w_ρ          ∈ [0, 1]
base    = cov + β · red                                ∈ [0, 1 + β]
penalty = base − K · n_viol                            (n_viol = número de violaciones, §4)
strict  = base  si n_viol = 0;   −∞  si n_viol > 0
```

Siempre se **maximiza**. `model.fitness(sats, sc, mode)` devuelve `penalty` o `strict`, según el modo (§4.3).

- **cov** es la cobertura ponderada por prioridad. Es el término principal.
- **red** premia tener al menos dos satélites que cubran completa una misma región (tolerancia a fallos), también ponderado por prioridad.

### 3.3 Por qué β = 0.05 y K = 0.5

Los dos valores están en el escenario, no en el código, porque forman parte de la definición del problema. Se eligieron para que dos desigualdades se cumplan con holgura:

- **β = 0.05 < min(w)/Σw = 1/13 = 0.077.** El bono de redundancia nunca compensa dejar sin cubrir ni siquiera la región de menor prioridad. Primero se cubre todo lo que se pueda, después se duplica.
- **K = 0.5 > max(w)/Σw + β = 3/13 + 0.05 = 0.281.** Con F = 10° un satélite no cubre dos regiones (§2.2), así que lo máximo que una violación puede ganar es una región Alta con su redundancia. Ninguna violación "se paga" con la cobertura que consigue. Al mismo tiempo, K es finito, y en modo penalty el algoritmo puede atravesar zonas inválidas mientras busca.

Las dos desigualdades se siguen cumpliendo en todos los escenarios derivados (en `prioridad_cambiada`, Σw = 14: 0.05 < 1/14 = 0.071 y 0.5 > 3/14 + 0.05 = 0.264).

### 3.4 Óptimo teórico del escenario base

Con 8 satélites, la mejor configuración pone uno sobre cada región (cov = 1) y dedica los 2 sobrantes a las dos regiones de mayor peso, Yucatán y Amazonía:

```
óptimo = 1 + 0.05 · (3 + 3)/13 = 1.023077
```

No se puede superar: cov ≤ 1, cada satélite cubre completa a lo sumo una región, y 2 satélites extra dan redundancia, como mucho, a 2 regiones. Comprobado con `model.fitness` sobre esa configuración (los satélites sobre los centros de las regiones): 1.023077, sin violaciones.

### 3.5 Ejemplo numérico

Las cuatro generaciones de `results/mock.json`, recalculadas con `model.fitness` sobre el escenario base (Σw = 13):

| Gen | Situación del mejor individuo | Aptitud |
|---|---|---|
| 0 | Yucatán y Japón cubiertas; un satélite dentro de `atlantico_norte` | (3 + 2)/13 − 0.5·1 = **−0.115385** |
| 1 | 5 cubiertas, California parcial (0.82441), Australia en 0; válido | (3 + 3 + 2·0.82441 + 2 + 2)/13 = **0.896063** |
| 2 | 5 cubiertas, Australia parcial (0.876192), redundancia en Yucatán | (12 + 0.876192)/13 + 0.05·3/13 = **1.002015** |
| 3 | 6/6 cubiertas, redundancia solo en Yucatán | 13/13 + 0.05·3/13 = **1.011538** |

La generación 3 ya cumple el criterio de "suficientemente buena" (§7), pero queda 0.011538 por debajo del óptimo porque Amazonía no tiene redundancia.

## 4. Condiciones de invalidez

_Pendiente._

## 5. Estrategia evolutiva

_Pendiente._

## 6. Parámetros y valores iniciales

_Pendiente._

## 7. Criterio de solución suficientemente buena

_Pendiente._

## 8. Escenarios derivados y sus óptimos

_Pendiente._

## 9. Limitaciones conocidas

_Pendiente._
