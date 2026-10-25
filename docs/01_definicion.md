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

### 4.1 Qué hace inválida una configuración

Una configuración es **inválida** si se cumple cualquiera de estas dos condiciones:

1. **Al menos un satélite viola una zona prohibida.** El satélite i viola la zona z (de desechos u ocupada) si y solo si

   ```
   central_angle(sat_i, centro_z) < radius_z
   ```

   La desigualdad es **estricta**: un satélite exactamente sobre el borde es válido. No se usa tolerancia. Cada par (satélite, zona) cuenta como una violación, así que un satélite dentro de dos zonas solapadas suma 2. Las zonas de desechos (`kind = "debris"`) y los objetos ocupados (`kind = "occupied"`) son restricciones igual de duras; solo se distinguen para el análisis y la visualización. `model.violations` devuelve, por cada violación, el satélite, la zona, el tipo, la distancia, el radio y la profundidad (`depth_deg` = radio − distancia).
2. **El número de satélites no coincide con `n_sats` del escenario.** Esto ocurre al revalidar una solución bajo un escenario con otro `n_sats`, por ejemplo de 8 a 4 en `menos_sats`.

En el resultado de cada ejecución, `valid = (no hay violaciones en la configuración final) y (len(final.sats) == n_sats)`.

### 4.2 Qué no hace inválida una configuración

Dejar una región sin cubrir **no** invalida la configuración; solo baja su aptitud. Esa separación es la que da sentido al escenario `inviable` (§8): siempre es posible colocar los satélites sin violar nada, aunque sea imposible cubrir Yucatán. El problema es inviable en cobertura, no en colocación.

### 4.3 Tratamiento durante la búsqueda: tres modos

| Modo | Aptitud que ve el AG | Qué pasa con un individuo inválido |
|---|---|---|
| `penalty` | `base − K·n_viol` (finita) | Sigue en la población, castigado con 0.5 por violación. El AG puede atravesar zonas prohibidas para llegar a otra parte. |
| `repair` | `base − K·n_viol` | `constraints.repair` corrige cada hijo **antes** de evaluarlo. Cada satélite que viola algo se mueve por el gran círculo que lo une con el centro de la zona más profunda hasta quedar a radio + 0.5° del centro. Si la nueva posición sigue violando otra zona, se remuestrea uniformemente hasta 20 veces. Si queda alguna violación residual, la penalización la castiga. |
| `strict` | `base` si es válida, `−∞` si no | Pierde cualquier torneo contra un individuo válido y no entra en las estadísticas de la generación (best, mean y worst se calculan sobre aptitudes finitas). |

Comparar los tres modos es una de las pruebas propias del Entregable 3. La solución que se reporta es siempre la final, con su `valid` explícito: el modo penalty puede devolver una configuración inválida si no encontró nada mejor, y en ese caso se informa así.

### 4.4 ¿Las restricciones están activas?

Este hecho no debe ocultarse (§5 del enunciado):

- **En el escenario base, las restricciones no están activas en el óptimo.** Para cubrir completa una región basta con quedar a menos de 7.3° de su centro, y el centro de región más cercano al borde de una zona prohibida está a **18.76°** (Australia y `objeto_b`). El óptimo base se alcanza sin acercarse a ninguna zona.
- **Sí actúan durante la búsqueda.** El área prohibida es el 2.73 % de la esfera (estimación de Monte Carlo con 2·10⁶ puntos). La probabilidad de que 8 satélites aleatorios sean todos válidos es (1 − 0.0273)⁸ = **0.80**, así que cerca del 20 % de la población inicial es inválida.
- **Muerden en los escenarios derivados `reducido` e `inviable`** (§8):
  - En `reducido`, la zona nueva queda a 1.25° del centro de Australia y elimina el 29 % del casquete desde el que se la puede cubrir completa.
  - En `inviable`, cubrir Yucatán es imposible sin violar.
  - En `footprint_chico` las restricciones **siguen inactivas en el óptimo**: con F = 5°, cubrir completa exige d ≤ 2.3°, muy lejos del mínimo de 18.76°. Lo que cambia ahí es la dificultad de la búsqueda, no las restricciones.

## 5. Estrategia evolutiva

Se usa un algoritmo genético generacional con elitismo, implementado en `ga.run_ga`. El AG no conoce el problema: recibe una función de aptitud y, de forma opcional, una función de reparación. `ga.py` no importa `model.py`.

```
            ┌───────────────────────────────────────────────┐
            │ Inicialización: P configuraciones uniformes    │
            │ sobre la esfera (sample_sphere); opcionalmente │
            │ sembradas con una solución previa (initial)    │
            └──────────────────────┬────────────────────────┘
                                   │  reparar (solo en modo repair)
                                   ▼
            ┌───────────────────────────────────────────────┐
     ┌─────►│ Evaluar aptitud y registrar history[g]        │
     │      │ (best, mean, worst, diversidad, inválidos,    │
     │      │  cobertura y sats del mejor)                  │
     │      └──────────────────────┬────────────────────────┘
     │                             │ ¿g == gens? ── sí ──► devolver el mejor
     │                             ▼ no
     │      ┌───────────────────────────────────────────────┐
     │      │ Elitismo: copiar los 2 mejores sin cambios    │
     │      └──────────────────────┬────────────────────────┘
     │                             ▼  hasta completar P
     │      ┌───────────────────────────────────────────────┐
     │      │ Torneo k = 3 (dos veces) → padres p1, p2      │
     │      │ Cruce (p = 0.9), satélite a satélite:         │
     │      │   intercambio completo (p = 0.5) o BLX-0.5    │
     │      │ Mutación gaussiana (p = 0.2 por satélite,     │
     │      │   σ = 5° en lat y lon)                        │
     │      │ Normalizar (reflexión polar + wrap_lon)       │
     │      │ Reparar (solo en modo repair)                 │
     │      └──────────────────────┬────────────────────────┘
     └─────────────────────────────┘  g ← g + 1
```

Cada paso, y por qué está ahí:

- **Inicialización uniforme sobre la esfera.** Se toma lat = asin(U(−1, 1)) y lon = U(−180, 180). Un muestreo uniforme en (lat, lon) amontonaría puntos en los polos. Al re-optimizar tras un cambio de condiciones (§8), la población se siembra con la solución anterior (`initial`).
- **Selección por torneo de tamaño 3.** Se eligen k índices con reemplazo y gana el de mayor aptitud (en empate, el primero). Un `−∞` pierde contra cualquier valor finito. La presión selectiva queda moderada y no hace falta escalar la aptitud, que puede ser negativa.
- **Cruce por satélite.** Para cada índice i:
  - Con probabilidad 0.5, los hijos **intercambian el satélite completo**. Esto transmite bloques de construcción del tipo "un satélite sobre Yucatán" sin romperlos.
  - Si no, se aplica **BLX-α** (α = 0.5) en cada coordenada. En longitud se usa la diferencia envuelta (`lon2' = lon1 + wrap_lon(lon2 − lon1)`), para que dos padres a ambos lados de ±180° no produzcan hijos al otro lado del planeta. BLX afina posiciones y explora un poco más allá de los padres.
- **Mutación gaussiana.** Cada satélite, con probabilidad 0.2, recibe un desplazamiento N(0, 5°) en lat y en lon. σ = 5° es del orden de F − r = 7.3°: mueve un satélite dentro del casquete útil sin saltar al otro lado del mundo.
- **Normalización y reparación.** Después de cada operador, los hijos vuelven a rango (§1). En modo repair, `constraints.repair` los corrige (§4.3).
- **Elitismo de 2 individuos.** Los mejores pasan intactos, así que la curva del mejor por generación es no decreciente y la solución final es la mejor vista en toda la ejecución.
- **Diversidad.** En cada generación se registra la media, sobre todos los pares de individuos, de la distancia angular media entre sus satélites del mismo índice (en grados). Sirve para detectar convergencia prematura.
- **Terminación.** Solo por número de generaciones, sin parada temprana, para que todas las ejecuciones sean comparables con el mismo presupuesto de evaluaciones.
- **Reproducibilidad.** Toda la aleatoriedad sale del único generador que crea el punto de entrada (`run.py` o `experiments/`) con la semilla. La misma semilla da el mismo `history` y la misma solución.

Todo lo necesario para analizar la evolución queda en el resultado (`results/<id>.json`, §9 del contrato): aptitudes por generación, diversidad, inválidos, cobertura y satélites del mejor de cada generación. Eso permite estudiar la convergencia y reproducir la evolución en el visor 3D.

## 6. Parámetros y valores iniciales

### 6.1 Parámetros del algoritmo (`ga.DEFAULT_PARAMS`)

| Parámetro | Valor inicial | De dónde sale |
|---|---|---|
| `pop_size` | 100 | 100 × (200 + 1) = 20 100 evaluaciones por ejecución: suficiente para converger y viable para 30 semillas × varios escenarios × 3 modos |
| `gens` | 200 | Margen para que la curva del mejor se estabilice. El Entregable 3 lo comprueba con las curvas de `history` |
| `tournament_k` | 3 | Presión selectiva moderada, valor estándar |
| `p_crossover` | 0.9 | Valor estándar en un AG generacional |
| `blx_alpha` | 0.5 | BLX-0.5 explora más allá del segmento entre los padres sin divergir |
| `p_swap` | 0.5 | La mitad de los satélites se intercambian completos y la otra mitad se mezclan con BLX |
| `p_mut` | 0.2 | Unos 1.6 satélites mutados por hijo (0.2 × 8) |
| `sigma_mut` | 5.0° | Del orden de F − r = 7.3° (§5) |
| `elitism` | 2 | Garantiza que el mejor de la historia no se pierda |
| `seed` | 42 en la CLI | Informativa: el resultado guarda la semilla con la que se creó el generador |

Los parámetros se pueden cambiar sin tocar código: `python run.py --scenario ... --gens N --pop P --params params.json --seed S --mode M`.

### 6.2 Parámetros del escenario (`scenarios/*.json`)

| Parámetro | Valor base | De dónde sale |
|---|---|---|
| `n_sats` | 8 | Enunciado §1.1 |
| `regions[*].radius_deg` | 2.7° | 300 km del enunciado (§2.1) |
| `regions[*].weight` | 3/2/1 | Prioridades Alta/Media/Normal (§3.1) |
| `footprint_deg` | 10.0° | Un satélite por región, lejos del régimen trivial (≥ 18.2°) y con 7.3 % de la esfera con señal (§2.2) |
| `fitness.redundancy_bonus` (β) | 0.05 | β < 1/13 (§3.3) |
| `fitness.k_penalty` (K) | 0.5 | K > 3/13 + β (§3.3) |
| `debris_zones`, `occupied` | 3 + 2 casquetes | Enunciado §3.1 y §3.2 |

### 6.3 Parámetros de la reparación (`constraints.repair`)

`margin_deg = 0.5°` deja el satélite reparado un poco fuera del borde, para que una mutación pequeña no lo devuelva a la zona. `max_tries = 20` remuestreos: con un área prohibida del 2.7 % al 6.4 % (§8), fallar 20 veces seguidas tiene una probabilidad del orden de 0.064²⁰ ≈ 10⁻²⁴.

### 6.4 Qué se varía en las pruebas

Los valores iniciales no se dan por buenos sin más. El Entregable 3 (`experiments/`) prueba:

- 30 semillas por configuración;
- los 3 modos de restricción;
- la sensibilidad al footprint (5°, 7.5°, 10°, 12.5°, 15° y 20°);
- la sensibilidad al tamaño de población (20, 50, 100 y 200) con presupuesto fijo de unas 20 000 evaluaciones;
- una búsqueda aleatoria con el mismo presupuesto como línea de referencia.

K y β solo se varían en copias en memoria, nunca en `scenarios/`.

## 7. Criterio de solución suficientemente buena

### 7.1 Criterio

Una solución es **suficientemente buena** para un escenario si cumple las dos condiciones siguientes:

1. **Es válida**: `valid == true`, es decir, no tiene violaciones y tiene `n_sats` satélites (§4.1).
2. **Cubre todas las regiones que el escenario permite cubrir.** En la base son las 6 regiones con c = 1.0; equivale a una aptitud ≥ 1.0.

La redundancia no es parte del criterio: es lo que separa una solución suficientemente buena (≥ 1.0) del óptimo (1.023077). Por eso, junto a cada solución se reporta su **brecha frente al óptimo teórico**:

```
brecha = óptimo − aptitud_final
```

### 7.2 Por qué no basta con "el AG dejó de mejorar"

Que la curva del mejor se aplane no prueba que se haya llegado al óptimo (§5 del enunciado): el AG puede haber quedado atascado en una meseta (§2.2) o en un óptimo local. Por eso cada escenario tiene un **oráculo**: un óptimo teórico calculado a mano y comprobado con `model.fitness` sobre una configuración explícita (§8). Con él, la calidad se mide en términos absolutos.

Como segunda referencia está la búsqueda aleatoria. Con 20 000 configuraciones de 8 satélites uniformes (semilla 0, modo penalty, escenario base), la aptitud tiene media −0.045, percentil 95 de 0.231 y máximo de 0.614, y el 19.2 % de las configuraciones son inválidas. Una solución que cumple el criterio (≥ 1.0) está muy lejos de lo que logra el azar.

### 7.3 Umbral y óptimo por escenario

| Escenario | Regiones cubribles | Umbral de "suficientemente buena" (válida y…) | Óptimo teórico |
|---|---|---|---|
| `base` | 6 | 6/6 cubiertas, aptitud ≥ 1.0 | **1.023077** |
| `reducido` | 6 | 6/6 cubiertas, aptitud ≥ 1.0 | **1.023077** |
| `footprint_chico` | 6 | 6/6 cubiertas, aptitud ≥ 1.0 | **1.023077** |
| `prioridad_cambiada` | 6 | 6/6 cubiertas, aptitud ≥ 1.0 | **1.021429** |
| `inviable` | 5 (todas menos Yucatán) | Las 5 cubiertas, aptitud ≥ 10/13 = 0.769231 | **0.796154** |
| `menos_sats` | 4 de 6 (solo hay 4 satélites) | 2 Alta + 2 Media cubiertas, aptitud ≥ 0.769231 | **0.769231** |

Como el algoritmo es estocástico, el criterio se evalúa por ejecución. El Entregable 3 reporta qué fracción de 30 semillas lo cumple, además de la media, la desviación y la brecha de la aptitud final.

## 8. Escenarios derivados y sus óptimos

Los escenarios derivados sirven para las pruebas de condiciones límite y de cambio de condiciones (§3.3 del enunciado). Cada uno es una copia literal de `scenarios/base.json` con cambios mínimos, y todos cumplen las reglas de §4.6 del contrato:

- Las 6 regiones (id, nombre, centro y radio) quedan intactas, para poder comparar.
- Las 3 zonas de desechos y los 2 objetos originales no se borran ni se mueven; solo se agrandan o se añaden zonas nuevas.
- `fitness` (K = 0.5 y β = 0.05) y `contract_version` = "1.0.1" no cambian.

Todos validan contra `schemas/scenario.schema.json` y se cargan con `model.load_scenario`.

### 8.1 Resumen

| Archivo | Cambio respecto a base | Óptimo teórico | Composición del óptimo | Prueba del Entregable 3 |
|---|---|---|---|---|
| `reducido.json` | Radios de las 5 zonas ×1.5 y zona nueva `bloqueo_australia_este` | **1.023077** | 6/6 + redundancia en Yucatán y Amazonía | P5 Espacio reducido; P3/P4/P8 con restricción activa; P11 |
| `inviable.json` | Zona nueva `bloqueo_yucatan` de 13° sobre Yucatán | **0.796154** | 5/6 (Yucatán imposible) + redundancia en Amazonía y en dos Media | P6 Condición inviable; P11 |
| `prioridad_cambiada.json` | Australia → Alta (3), California → Normal (1) | **1.021429** | 6/6 + redundancia en dos de las tres Alta | P11 Revalidación (cambio de prioridades) |
| `menos_sats.json` | `n_sats` = 4 | **0.769231** | 2 Alta + 2 de las 3 Media, sin redundancia | P11 (una solución de 8 satélites deja de ser válida) |
| `footprint_chico.json` | `footprint_deg` = 5.0 | **1.023077** | Igual que la base, más difícil de encontrar | P11; contrasta con P9 (sensibilidad al footprint) |

Cada óptimo se comprobó evaluando con `model.fitness` una configuración explícita: un satélite sobre el centro de cada región que se cubre y los satélites sobrantes sobre los centros de las regiones que reciben redundancia. En todos los casos la configuración es válida (0 violaciones) y da la cifra de la tabla con 6 decimales, tanto en modo penalty como en strict.

### 8.2 `reducido.json` — espacio reducido

**Cambios.** `atlantico_norte` pasa a 18.0°, `pacifico_sur` a 15.0°, `polar_norte` a 12.0°, y `objeto_a` y `objeto_b` a 7.5° (todos ×1.5). Además se añade la zona de desechos `bloqueo_australia_este`, centrada en (−25.0, 141.0) con radio 6.0°.

**Efecto:**

- El área prohibida pasa del 2.73 % al **6.38 %** de la esfera, y la probabilidad de que 8 satélites aleatorios sean todos válidos baja de 0.80 a **0.59**. Habrá más inválidos en la población inicial y la reparación trabajará más.
- El centro de `bloqueo_australia_este` está a 7.25° del centro de Australia, y su borde, a **1.25°**. La zona corta el casquete de cobertura completa de Australia (radio F − r = 7.3° alrededor del centro) sin taparlo entero: elimina el **29 %** de las posiciones desde las que se cubre Australia completa (estimación de Monte Carlo). Así se cumple el requisito de §4.6 del contrato y una restricción queda **activa** cerca del óptimo: el satélite de Australia tiene que quedar en el lado oeste.
- Las zonas agrandadas no alcanzan ningún casquete útil: el centro de región más cercano a una de ellas es Australia, a 16.26° del borde de `objeto_b`.

**Óptimo.** El centro de Australia sigue siendo válido (7.25° > 6.0°), así que el óptimo no cambia: **1.023077**. El escenario no reduce lo alcanzable, pero sí el espacio donde buscarlo.

### 8.3 `inviable.json` — condición inviable

**Cambio.** Se añade la zona de desechos `bloqueo_yucatan`, centrada en Yucatán (20.5, −89.0) con radio 13.0°.

**Por qué es inviable.** Para que un satélite aporte cualquier cobertura a Yucatán tiene que estar a menos de F + r = 12.7° de su centro. Todo ese casquete está dentro de la zona prohibida (12.7 < 13.0). Cubrir Yucatán, aunque sea en parte, exige violar una restricción.

**El resto sigue siendo cubrible.** El borde de `bloqueo_yucatan` queda a 22.74° de Amazonía y a 18.05° de California, ambos por encima de 7.3°. El área prohibida es el 4.02 % de la esfera, y la probabilidad de que 8 satélites aleatorios sean válidos es 0.72.

**Óptimo válido.** 5 satélites cubren las otras 5 regiones y quedan **3** sobrantes para la redundancia, que va a las tres regiones de mayor peso entre las cubribles: Amazonía (3) y dos de las Media (2 + 2):

```
óptimo = (13 − 3)/13 + 0.05 · (3 + 2 + 2)/13 = 0.769231 + 0.026923 = 0.796154
```

En modo penalty tampoco compensa violar: cubrir Yucatán dentro de la zona gana como mucho 3/13 + 0.05·3/13 = 0.242 y cuesta K = 0.5.

> **Discrepancia con el contrato.** §4.6 y §10 de `docs/contratos.md` dan 0.788462 = 10/13 + 0.05·(3 + 2)/13, con redundancia solo en Amazonía y una Media. Ese cálculo cuenta 2 satélites sobrantes, pero en `inviable` sobran 3 (8 − 5). La configuración del contrato vale 0.788462 con `model.fitness`; la de arriba, válida y sin violaciones, vale **0.796154**. Este documento usa 0.796154. La corrección del contrato y de los consumidores de ese oráculo queda propuesta al coordinador.

### 8.4 `prioridad_cambiada.json` — prioridades cambiadas

**Cambio.** Australia pasa de Normal (1) a Alta (3) y California, de Media (2) a Normal (1). Nada más cambia: ni las zonas, ni `n_sats`, ni el footprint.

**Óptimo.** Σw = 3 + 3 + 1 + 2 + 2 + 3 = 14. Las tres regiones Alta (Yucatán, Amazonía y Australia) empatan para la redundancia, y cualquier par de ellas da:

```
óptimo = 1 + 0.05 · (3 + 3)/14 = 1.021429
```

Las desigualdades de §3.3 se mantienen: β = 0.05 < 1/14 = 0.071 y K = 0.5 > 3/14 + 0.05 = 0.264.

**Qué cambia y qué no:**

- Una solución válida de la base **sigue siendo válida**, porque solo cambian los pesos.
- Lo que cambia es su aptitud. Por ejemplo, la configuración final de `mock.json` pasa de 1.011538 a 1.010714.
- Con estos pesos, el óptimo de la base (redundancia en Yucatán y Amazonía) **sigue siendo óptimo**: vale 1.021429, lo mismo que poner la redundancia en Australia y Amazonía. La asignación de la redundancia *puede* cambiar, pero no *tiene* que hacerlo.
- Si se quiere un caso en el que la solución base deje de ser óptima, el contrato permite otros pesos ("p. ej."). Con Australia → Alta y Yucatán → Media, la base vale 1.017857 frente a un óptimo de 1.021429. Se optó por el ejemplo literal del contrato, que es el mismo que ya usan los tests de restricciones.

### 8.5 `menos_sats.json` — cuatro satélites

**Cambio.** `n_sats` = 4.

**Óptimo.** Con 4 satélites y un satélite por región (§2.2), se cubren como mucho 4 regiones. Las prioridades deciden cuáles: las 2 Alta y 2 de las 3 Media.

```
óptimo = (3 + 3 + 2 + 2)/13 = 0.769231
```

No hay redundancia posible: duplicar una región Alta (0.05·3/13 = 0.012) vale menos que cubrir una Media (2/13 = 0.154). Hay tres óptimos equivalentes, según qué Media se deje fuera.

**Revalidación.** Cualquier solución de 8 satélites queda inválida bajo este escenario por número de satélites (8 ≠ 4), aunque no viole ninguna zona.

### 8.6 `footprint_chico.json` — footprint de 5°

**Cambio.** `footprint_deg` = 5.0.

**Efecto:**

- Cubrir completa una región exige d ≤ F − r = 2.3°, y tocarla, d < 7.7°.
- Como 2(F + r) = 15.4° < 31.05°, sigue rigiendo el principio de un satélite por región.
- Para un satélite aleatorio, la probabilidad de tocar una región dada baja de 1.22 % a **0.45 %**, y la de cubrirla completa, de 0.41 % a **0.040 %**.
- La zona con señal pasa del 7.3 % al 2.7 % de la esfera: hay más mesetas y la búsqueda es más difícil.

**Óptimo.** Es el mismo de la base, **1.023077**, con los satélites sobre los centros de las regiones. Las restricciones siguen inactivas en el óptimo (§4.4).

### 8.7 Ejemplo de revalidación

Como ejemplo del cambio de condiciones (§3.3 del enunciado), esta es la configuración final de `results/mock.json` (válida en la base, aptitud 1.011538, 6/6 cubiertas), evaluada sin re-optimizar con `model.fitness` (modo penalty) y `model.violations` bajo cada escenario:

| Escenario | Aptitud | Violaciones | ¿Sigue siendo válida? |
|---|---|---|---|
| `base` | 1.011538 | 0 | Sí |
| `reducido` | 0.511538 | 1: el satélite 0 cae 3.65° dentro de `atlantico_norte` agrandada | No |
| `inviable` | 0.011538 | 2: los satélites 1 y 7, los dos de Yucatán, caen dentro de `bloqueo_yucatan` | No |
| `prioridad_cambiada` | 1.010714 | 0 | Sí, con otra aptitud |
| `menos_sats` | 1.011538 | 0 | No: tiene 8 satélites y el escenario exige 4 |
| `footprint_chico` | 1.000000 | 0 | Sí. Mantiene 6/6, pero pierde la redundancia de Yucatán (el satélite 7 queda a más de 2.3°) |

La revalidación sistemática de soluciones reales y la re-optimización sembrada con ellas (`revalidate.revalidate` y `revalidate.reoptimize`) forman la prueba P11 del Entregable 3.

## 9. Limitaciones conocidas

1. **Sin mecánica orbital.** Un satélite es un punto fijo con un casquete de radio constante. No hay altitud, movimiento, tiempo de revisita ni interferencias entre satélites. Dos satélites pueden incluso ocupar el mismo punto: las "posiciones ocupadas" del enunciado son objetos externos, no los propios satélites. Es el modelo educativo que permite el enunciado (§1.1).
2. **La cobertura parcial es una aproximación.** La fórmula lineal de §2.3 no calcula el área solapada real entre dos casquetes, y la combinación por `max` no suma las contribuciones parciales de varios satélites. Con F = 10° el efecto práctico es nulo (§2.4), pero la cifra de cobertura parcial es indicativa, no física.
3. **Borde numérico de la cobertura completa.** La implementación evalúa la fórmula tal cual. En d = F − r exacto, el redondeo da 0.9999999999999997 y la región cuenta como parcial, aunque el contrato (§5.1) diga "completa si d ≤ F − r". Solo afecta a posiciones justo en el borde. La corrección (un umbral explícito) corresponde al dueño de `model.py`.
4. **La penalización cuenta violaciones, no su profundidad.** En modo penalty, un satélite que apenas roza una zona cuesta lo mismo que uno metido en su centro, y la aptitud no da pendiente para salir de la zona. El modo repair cubre ese hueco moviendo el satélite de forma explícita.
5. **El cruce es por índice sobre un conjunto no ordenado.** Dos padres buenos con sus satélites en distinto orden (por ejemplo, el satélite 0 sobre Yucatán en uno y sobre Japón en otro) pueden producir con BLX hijos a medio camino entre las dos regiones. El intercambio de satélites completos (`p_swap` = 0.5) y el elitismo atenúan el problema, pero no lo eliminan. Una alternativa sería alinear los satélites antes de cruzar, con el costo de más complejidad.
6. **Las restricciones no están activas en el óptimo base** (§4.4). El escenario base solo prueba que las restricciones se respetan durante la búsqueda. Para ver su efecto sobre la solución hacen falta `reducido` e `inviable`.
7. **Los oráculos valen solo en el régimen de un satélite por región.** Todos los óptimos de §8 suponen que ningún satélite cubre completas dos regiones, lo que exige F < 18.2°. Fuera de ese régimen el óptimo es mayor. Por ejemplo, con F = 20° dos satélites en el punto medio entre Yucatán y California cubren ambas con redundancia, y `model.fitness` da 1.038462 para la configuración (2 en Yucatán–California, 2 en Amazonía, 2 en Sahel, 1 en Japón y 1 en Australia). En la prueba de sensibilidad al footprint, 1.023077 no es una cota superior para F = 20°.
8. **Los pesos 3/2/1 son una decisión del equipo.** Otra escala (por ejemplo, una lexicográfica) daría el mismo óptimo en la base. Solo cambiaría las decisiones cuando no se puede cubrir todo (`menos_sats`, `inviable`) o al repartir la redundancia.
9. **Costo de evaluación.** El contrato fija un objetivo de ≤ 100 µs por evaluación de `model.fitness` (8 satélites, 6 regiones). En el código actual mide unos 370 µs (media de 2000 llamadas en la máquina de desarrollo), porque las violaciones se construyen con un bucle de Python. No cambia ningún resultado, pero encarece las campañas de 30 semillas.

## Trazabilidad: viñetas del Entregable 1

| Viñeta del enunciado (§4, Entregable 1) | Sección |
|---|---|
| Cómo se representa una configuración de los 8 satélites y qué información contiene | §1 |
| Qué significa que una región esté cubierta y cómo se determina | §2 |
| Cómo se evaluará la calidad de una configuración y cómo se considerarán las prioridades | §3 |
| Qué condiciones hacen que una configuración sea inválida | §4 |
| Qué estrategia general utilizará el algoritmo evolutivo | §5 |
| Qué parámetros necesitará el sistema y cómo se determinarán sus valores iniciales | §6 |
| Qué condiciones se usarán para considerar que una solución es suficientemente buena | §7 |
| Supuestos del modelo | §0 |
| Escenarios derivados (cambio de condiciones, espacio reducido, condición inviable) y sus oráculos | §8 |
| Limitaciones | §9 |
