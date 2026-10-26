# AstroShield

Algoritmo evolutivo que coloca 8 satélites para observar seis regiones de la Tierra sin invadir zonas de desechos ni posiciones ocupadas, con visualización en un globo 3D. El planteamiento completo está en [`docs/enunciado.md`](docs/enunciado.md). El detalle técnico está en [`docs/contratos.md`](docs/contratos.md) (formatos, fórmulas y oráculos) y en [`docs/01_definicion.md`](docs/01_definicion.md) (definición extendida, citada como «Def. §n»).

Las cifras de las tablas de este documento las inserta `python experiments/report.py` desde `results/exp_tablas/`. Ninguna se escribe a mano.

---

# Definición del problema

### Representación de una configuración

Una configuración es un arreglo `numpy` de forma `(8, 2)`. La fila `i` es `[lat, lon]` en grados del punto bajo el satélite `i`, con lat ∈ [−90, 90] y lon ∈ [−180, 180). Solo contiene posiciones. La cobertura, las violaciones y la aptitud se calculan a partir de ellas (`model.coverage`, `model.violations` y `model.fitness`), así que nunca pueden quedar desincronizadas. El número de satélites lo fija el escenario (`n_sats`), no el código (Def. §1).

El modelo es una simulación educativa, como permite el enunciado (§1.1): la Tierra es una esfera, no hay mecánica orbital y toda distancia es el ángulo central en grados calculado con haversine (`geometry.central_angle`).

### Cuándo una región está cubierta

- **Radio de región.** Los 300 km del enunciado equivalen a r = 300 / 6371 rad ≈ **2.7°** (Def. §2.1).
- **Footprint de un satélite.** Cada satélite observa un casquete de radio F = **10°**. Se eligió así porque las dos regiones más cercanas, Yucatán y California, están a 31.05°: con F = 10° ningún satélite puede cubrir dos regiones a la vez. Por eso cada región necesita su propio satélite y el problema no es trivial. Se vuelve trivial a partir de F ≥ 18.2° (Def. §2.2).
- **Cobertura de una región por un satélite** a distancia d de su centro: `c = 1` si d ≤ F − r (la región cabe completa), `c = 0` si d ≥ F + r, y lineal entre esos dos valores. Para varios satélites se toma el máximo.
- **Criterio.** Una región está **cubierta** si c == 1.0, **parcial** si 0 < c < 1 y **no cubierta** si c = 0 (Def. §2.3–2.5).

### Calidad de una configuración y prioridades

Las prioridades se traducen en pesos: Alta = 3, Media = 2, Normal = 1. En el escenario base suman Σw = 13 (Def. §3.1). La aptitud se maximiza:

```
cov     = Σ w·c / Σw                                cobertura ponderada por prioridad
red     = Σ w·[≥2 satélites la cubren completa] / Σw   redundancia ponderada
penalty = cov + β·red − K·n_violaciones
strict  = cov + β·red  si no hay violaciones;  −∞  si las hay
```

β = 0.05 y K = 0.5 viven en el escenario (`fitness`), y se eligieron para que se cumplan dos desigualdades (Def. §3.3):
- β < 1/13: la redundancia nunca compensa dejar sin cubrir ni la región de menor peso.
- K > 3/13 + β: ninguna violación se paga con la cobertura que gana.

El óptimo teórico del escenario base es 1 + 0.05·(3+3)/13 = **1.023077**: las 6 regiones cubiertas y los 2 satélites sobrantes como redundancia de las dos regiones Alta (Def. §3.4).

### Condiciones de invalidez

Una configuración es **inválida** en dos casos (Def. §4):
- Algún satélite queda a una distancia menor que el radio de una zona de desechos o de un objeto ocupado. La desigualdad es estricta, así que el borde es válido. Cada par (satélite, zona) cuenta como una violación.
- Su número de satélites no coincide con el `n_sats` del escenario.

Dejar una región sin cubrir **no** la invalida; solo baja su aptitud. Durante la búsqueda, las configuraciones inválidas se tratan según uno de tres modos:

| Modo | Tratamiento |
|---|---|
| `penalty` | Sigue en la población, con −K por cada violación |
| `repair` | Antes de evaluarlo, cada satélite que viola se mueve por el gran círculo hasta 0.5° fuera del borde de la zona. Si cae en otra zona, se remuestrea hasta 20 veces |
| `strict` | Aptitud −∞: pierde contra cualquier configuración válida |

### Estrategia evolutiva

Algoritmo genético generacional (`ga.run_ga`, Def. §5):

1. **Inicialización:** población uniforme sobre la esfera.
2. **Selección:** torneo de tamaño 3.
3. **Cruce satélite a satélite:** se intercambia el satélite completo (para conservar bloques como «un satélite sobre Yucatán») o se mezclan coordenadas con BLX-α, usando la vuelta de longitud en ±180°.
4. **Mutación gaussiana:** σ = 5°.
5. **Normalización** a los rangos válidos y, en modo repair, **reparación**.
6. **Elitismo:** los 2 mejores pasan intactos, así que el mejor nunca empeora.

Termina después de un número fijo de generaciones. Toda la aleatoriedad sale de un único `numpy.random.Generator` creado con la semilla, así que la misma semilla da el mismo resultado.

### Parámetros y valores iniciales

| Parámetro | Valor | Justificación (Def. §6) |
|---|---|---|
| Población × generaciones | 100 × 200 | 20 100 evaluaciones por ejecución: en las pruebas la mejor aptitud se estabiliza antes de la generación 200 (P2) |
| Torneo, cruce, BLX-α, intercambio | 3, 0.9, 0.5, 0.5 | Valores estándar: presión selectiva moderada |
| Mutación por satélite, σ | 0.2, 5° | σ del orden de F − r = 7.3°: mueve un satélite dentro de la zona útil sin mandarlo al otro lado del mundo |
| Elitismo | 2 | Conserva el mejor de la historia |
| F, r, β, K, n_sats | 10°, 2.7°, 0.05, 0.5, 8 | Ver arriba; viven en `scenarios/*.json` |
| Margen y reintentos de reparación | 0.5°, 20 | Ver la tabla de modos |

Todos se pueden cambiar sin tocar código: `--gens`, `--pop` y `--params` en la CLI, o editando el escenario.

### Cuándo una solución es suficientemente buena

Una solución es **suficientemente buena** si es **válida** y **cubre todas las regiones que el escenario permite cubrir**. En la base, eso son 6/6 con aptitud ≥ 1.0. Que el algoritmo deje de mejorar no prueba nada (enunciado §5). Por eso cada escenario tiene un **óptimo teórico**, calculado a mano y comprobado con `model.fitness` (Def. §7–8, contrato §10), y cada resultado se reporta junto con su brecha frente a ese óptimo:

| Escenario | Cambio respecto a base | Umbral | Óptimo |
|---|---|---|---|
| `base` | — | 6/6 | 1.023077 |
| `reducido` | zonas ×1.5 + `bloqueo_australia_este` | 6/6 | 1.023077 |
| `inviable` | `bloqueo_yucatan` de 13° (> F + r = 12.7°: Yucatán imposible) | 5/5 cubribles | 0.796154 |
| `prioridad_cambiada` | Australia → Alta, California → Normal | 6/6 | 1.021429 |
| `menos_sats` | 4 satélites | 2 Alta + 2 Media | 0.769231 |
| `footprint_chico` | F = 5° | 6/6 | 1.023077 |

---

# Implementación funcional

### Instalar

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev,exp]"                      # numpy; pytest y jsonschema; matplotlib
pytest                                           # debe terminar con "passed" y sin fallos
```

### Generar, evaluar y evolucionar configuraciones

```bash
python run.py --scenario scenarios/base.json --gens 200 --seed 42 --mode repair --out results/
```

Imprime una línea con la ejecución, si es válida, su aptitud, las regiones cubiertas y la ruta del resultado:

```
base_repair_s42 | valid=True | fitness=1.007692 | covered=6/6 | results/base_repair_s42.json
```

- **Generar:** la generación 0 es una población aleatoria uniforme. Con `--gens 0` solo se genera y evalúa la población inicial.
- **Evaluar:** cada configuración se evalúa con `model.fitness`. Para evaluar una configuración ya existente bajo otro escenario:
  ```bash
  python -m astroshield.revalidate --result results/base_repair_s42.json --scenario scenarios/inviable.json --out results/
  ```
  Reporta si sigue siendo válida, la aptitud antes y después y las regiones perdidas. Con `--reoptimize --gens 200 --mode repair` además vuelve a optimizar partiendo de esa solución.
- **Iteraciones:** `--gens N` fija el número de generaciones y `--pop P` el tamaño de población. `--params archivo.json` cambia cualquier otro parámetro.
- **Restricciones:** cada escenario de `scenarios/` define sus zonas de desechos y objetos ocupados. `--mode penalty|repair|strict` elige cómo se tratan. Si la solución final viola algo, el resultado lleva `"valid": false`.

### Conservar información para el análisis

Cada ejecución guarda `results/<escenario>_<modo>_s<semilla>.json` (esquema en `schemas/result.schema.json`) con:
- `initial` y `final`: satélites, cobertura por región, aptitud y violaciones. La inicial es el mejor individuo de la generación 0.
- `history[g]` para cada generación: mejor, media y peor aptitud, diversidad, número de inválidos, regiones cubiertas, y satélites y cobertura del mejor.
- El escenario, los parámetros, la semilla y el entorno (versiones de Python y numpy).

### Mostrar la configuración y sus resultados

```bash
python -m http.server 8000        # desde la raíz del repositorio
```

Abrir `http://localhost:8000/viz/` y elegir un resultado en el desplegable, o pasarlo con `?file=../results/base_repair_s42.json`. El globo muestra:
- las regiones en verde, ámbar o rojo según la cobertura que guarda el JSON;
- los satélites con su footprint;
- las zonas de desechos y los objetos ocupados;
- un panel con la aptitud y las violaciones.

Además permite comparar la configuración inicial con la final y reproducir la evolución generación por generación (ver [`viz/README.md`](viz/README.md)).

### Reproducir las pruebas de este documento

```bash
python experiments/run_experiments.py --only base,reducido,inviable,prioridad_cambiada,menos_sats,footprint_chico,aleatoria --seeds 3 --jobs 16
python experiments/report.py              # vuelve a insertar las tablas en este README
pytest && pytest experiments && node --test viz/tests/
```

Con 16 procesos tarda unos 4 minutos. La primera línea escribe en `results/exp_*`. La igualdad bit a bit con los datos versionados solo se garantiza con la misma versión de numpy (ver `results/exp_meta/entorno.txt`).

---

# Pruebas y validación

### Condiciones comunes

- **Configuraciones:** 6 escenarios × 3 modos (`penalty`, `repair`, `strict`) × 3 semillas (42, 43, 44) = **54 ejecuciones**, con los parámetros por defecto (población 100, 200 generaciones).
- **Comparación de modos:** se usa la aptitud *penalty* de la configuración final (`model.fitness(final, sc, "penalty")`).
- **Éxito:** solución válida y todas las regiones cubiertas (6/6).
- **Brecha:** óptimo teórico − aptitud final.
- **Intervalos:** Wilson al 95 % para proporciones; bootstrap para diferencias de medianas.
- **Alcance:** con 3 semillas por configuración los intervalos son anchos. Las pruebas muestran comportamiento, no estimaciones precisas.
- **Datos completos:** `results/exp_runs/*.csv` (una fila por ejecución) y `results/exp_json/` (resultados completos de las ejecuciones representativas, que se pueden abrir en el visor).

<!-- tabla:tiempos -->
| campaña | ejecuciones | Σ tiempo por ejecución (s) | s por ejecución (media) | reloj total (s) | procesos |
|---|---|---|---|---|---|
| base | 9 | 372.2 | 41.36 | — | — |
| reducido | 9 | 431.2 | 47.91 | — | — |
| inviable | 9 | 429.9 | 47.76 | — | — |
| prioridad_cambiada | 9 | 379.6 | 42.18 | — | — |
| menos_sats | 9 | 211.6 | 23.51 | — | — |
| footprint_chico | 9 | 294.1 | 32.68 | — | — |
| aleatoria | 3 | 56.0 | 18.65 | — | — |
| TOTAL base+reducido+inviable+prioridad_cambiada+menos_sats+footprint_chico+aleatoria | 57 | 2174.6 | — | 146.3 | 16 |
| representativas base+reducido+inviable+prioridad_cambiada+menos_sats+footprint_chico+aleatoria | 35 | — | — | 99.5 | 16 |
<!-- /tabla -->

### P1 · Escenario inicial

**Condiciones.** `base`, modo repair, semilla 42.

<!-- tabla:p1_config -->
| sat | lat | lon | cubre completa | cubre parcial (c) |
|---|---|---|---|---|
| 0 | -28.029 | 128.535 | australia | — |
| 1 | -4.329 | -62.497 | amazonia | — |
| 2 | 41.340 | 139.385 | japon | — |
| 3 | 12.845 | -6.179 | sahel | — |
| 4 | -74.802 | -55.991 | — | — |
| 5 | 22.681 | -86.118 | yucatan | — |
| 6 | 14.372 | -6.359 | sahel | — |
| 7 | 43.568 | -118.747 | california | — |

| región | prioridad | cobertura final | cobertura inicial |
|---|---|---|---|
| yucatan | Alta | 1.000000 | 0.000000 |
| amazonia | Alta | 1.000000 | 1.000000 |
| california | Media | 1.000000 | 1.000000 |
| sahel | Media | 1.000000 | 0.000000 |
| japon | Media | 1.000000 | 0.502017 |
| australia | Normal | 1.000000 | 0.000000 |

| valid | cubiertas | aptitud inicial | aptitud final | óptimo (§10) | brecha | violaciones finales |
|---|---|---|---|---|---|---|
| sí | 6/6 | 0.461849 | 1.007692 | 1.023077 | 0.015385 | 0 |

Comparación con `results/base_repair_s42.json` (Ola 2, numpy 2.5.4): misma configuración final y aptitud = **sí**.
<!-- /tabla -->

![P1: configuración inicial y final](results/exp_figuras/p1_mapa.png)

**Interpretación.** Las 6 regiones quedan cubiertas sin violaciones. La aptitud sube de 0.461849, donde solo 2 regiones estaban cubiertas, a 1.007692. La brecha de 0.015385 se explica con la tabla:
- dos satélites (3 y 6) cubren Sahel, una región Media, y dan la única redundancia: 0.05·2/13 = 0.007692;
- el satélite 4 queda en (−74.8, −56.0), lejos de toda región, y no aporta nada.

El óptimo pondría esos dos satélites sobre las regiones Alta.

### P2 · Evolución

**Condiciones.** `base` × 3 modos × 3 semillas. Como línea base se usa una búsqueda aleatoria uniforme con el mismo presupuesto: 20 100 configuraciones por semilla.

<!-- tabla:p2_resumen -->
| config | best med. g0 | best med. g10 | best med. g25 | best med. g50 | best med. g100 | best med. g200 | gen_99 med. | gen 6/6 válida med. | alcanzan 6/6 válida | AG > aleatoria (misma semilla) |
|---|---|---|---|---|---|---|---|---|---|---|
| base_penalty | 0.3785 | 0.7692 | 1.0000 | 1.0038 | 1.0115 | 1.0154 | 95.0 | 21.0 | 3/3 | 3/3 |
| base_repair | 0.3785 | 0.6630 | 0.9760 | 1.0077 | 1.0077 | 1.0077 | 27.0 | 25.0 | 2/3 | 3/3 |
| base_strict | 0.3785 | 0.7692 | 1.0000 | 1.0115 | 1.0115 | 1.0154 | 33.0 | 21.0 | 3/3 | 3/3 |

| línea base | n semillas | evaluaciones | máx. mediano | máx. de máx. | media de p95 | media de la media | éxito 6/6 |
|---|---|---|---|---|---|---|---|
| aleatoria uniforme (penalty) | 3 | 20100 | 0.6154 | 0.6583 | 0.2308 | -0.0478 | 0/3 |
<!-- /tabla -->

![P2: curvas de aptitud](results/exp_figuras/p2_curvas_base.png)

![P2: diversidad](results/exp_figuras/p2_diversidad.png) ![P2: inválidos](results/exp_figuras/p2_invalidos.png)

**Interpretación.**
- **Frente al azar:** el AG supera a la búsqueda aleatoria en 3/3 semillas en los tres modos. La aleatoria no pasa de un máximo mediano de 0.6154 y nunca cubre 6/6.
- **Velocidad:** la mediana del mejor pasa de 0.3785 en la generación 0 a 1.0 en la 25 en penalty y strict (0.9760 en repair). La primera solución válida con 6/6 aparece en la mediana entre las generaciones 21 y 25.
- **Después:** la aptitud solo mejora en pasos pequeños de redundancia, y la diversidad cae a medida que la población converge.

### P3 · Zonas de desechos y P4 · Posiciones ocupadas

**Condiciones.** `base` y `reducido` (zonas ×1.5 más una zona nueva junto a Australia) × 3 modos × 3 semillas. El margen es la distancia del satélite al borde de la zona más cercana, de cualquier tipo.

<!-- tabla:p3_violaciones -->
| config | ejecuciones | violaciones finales (debris) | ejecuciones con ≥1 | inválidos gen 0 (media de 100) | margen mín. mediano (°) | margen mín. menor (°) |
|---|---|---|---|---|---|---|
| base_penalty | 3 | 0 | 0 | 17.7 | 21.10 | 18.85 |
| base_repair | 3 | 0 | 0 | 0.0 | 16.56 | 12.92 |
| base_strict | 3 | 0 | 0 | 17.7 | 18.85 | 16.41 |
| reducido_penalty | 3 | 0 | 0 | 40.7 | 3.70 | 2.84 |
| reducido_repair | 3 | 0 | 0 | 0.0 | 0.50 | 0.50 |
| reducido_strict | 3 | 0 | 0 | 40.7 | 2.68 | 0.20 |
<!-- /tabla -->

<!-- tabla:p4_violaciones -->
| config | ejecuciones | violaciones finales (occupied) | ejecuciones con ≥1 | inválidos gen 0 (media de 100) | margen mín. mediano (°) | margen mín. menor (°) |
|---|---|---|---|---|---|---|
| base_penalty | 3 | 0 | 0 | 17.7 | 21.10 | 18.85 |
| base_repair | 3 | 0 | 0 | 0.0 | 16.56 | 12.92 |
| base_strict | 3 | 0 | 0 | 17.7 | 18.85 | 16.41 |
| reducido_penalty | 3 | 0 | 0 | 40.7 | 3.70 | 2.84 |
| reducido_repair | 3 | 0 | 0 | 0.0 | 0.50 | 0.50 |
| reducido_strict | 3 | 0 | 0 | 40.7 | 2.68 | 0.20 |
<!-- /tabla -->

![P3/P4: satélites finales sobre zonas y objetos (base)](results/exp_figuras/p3_mapa_finales.png)

**Interpretación.** **PASA**: ninguna de las 18 soluciones finales viola una zona de desechos ni un objeto ocupado.
- **Las restricciones sí actúan durante la búsqueda:** en la generación 0, de cada 100 individuos son inválidos 17.7 en base y 40.7 en reducido. En repair son 0, porque se reparan antes de evaluarse.
- **Base:** el margen mínimo mediano es de 16.56° a 21.10°. Las soluciones quedan lejos de toda zona, como se esperaba (Def. §4.4).
- **Limitación de la figura:** el mapa solo dibuja base.

### P5 · Espacio reducido

**Condiciones.** `reducido` comparado con `base`, mismas semillas. Se considera que la restricción está *activa* si el margen mediano es menor que 1° en reducido y mayor que 10° en base.

<!-- tabla:p5_resumen -->
| modo | margen mín. mediano reducido (°) | margen mín. mediano base (°) | restricción activa (< 1° vs > 10°) | éxito reducido [IC 95 %] | éxito base | aptitud mediana reducido | aptitud mediana base | caída de la mediana | violaciones finales | 0 violaciones (repair/strict) |
|---|---|---|---|---|---|---|---|---|---|---|
| penalty | 3.70 | 21.10 | FALLA | 2/3 [0.21, 0.94] | 3/3 | 1.0038 | 1.0154 | 0.0115 | 0 | — |
| repair | 0.50 | 16.56 | PASA | 3/3 [0.44, 1.00] | 2/3 | 1.0192 | 1.0077 | -0.0115 | 0 | PASA |
| strict | 2.68 | 18.85 | FALLA | 3/3 [0.44, 1.00] | 3/3 | 1.0115 | 1.0154 | 0.0038 | 0 | PASA |

| config | n | media | sd | mediana | IQR | mín | máx | éxito k/n [IC Wilson 95 %] |
|---|---|---|---|---|---|---|---|---|
| reducido_penalty | 3 | 0.9577 | 0.0833 | 1.0038 | 0.9327–1.0058 | 0.8615 | 1.0077 | 2/3 [0.21, 0.94] |
| reducido_repair | 3 | 1.0179 | 0.0022 | 1.0192 | 1.0173–1.0192 | 1.0154 | 1.0192 | 3/3 [0.44, 1.00] |
| reducido_strict | 3 | 1.0103 | 0.0059 | 1.0115 | 1.0077–1.0135 | 1.0038 | 1.0154 | 3/3 [0.44, 1.00] |

| config | alcanzan el óptimo (brecha < 1e-6) | brecha mediana | brecha máx. |
|---|---|---|---|
| reducido_penalty | 0/3 | 0.019231 | 0.161539 |
| reducido_repair | 0/3 | 0.003846 | 0.007692 |
| reducido_strict | 0/3 | 0.011539 | 0.019231 |
<!-- /tabla -->

<!-- tabla:p5_zonas -->
| config | zona que fija el margen mínimo | ejecuciones | margen mediano (°) | margen menor (°) | < 1° |
|---|---|---|---|---|---|
| reducido_penalty | bloqueo_australia_este | 3 | 3.70 | 2.84 | 0 |
| reducido_repair | bloqueo_australia_este | 3 | 0.50 | 0.50 | 2 |
| reducido_strict | bloqueo_australia_este | 3 | 2.68 | 0.20 | 1 |
<!-- /tabla -->

![P5: aptitud base vs reducido](results/exp_figuras/p5_boxplot.png)

![P5: margen mínimo](results/exp_figuras/p5_margen.png)

**Interpretación.**
- **La zona nueva fija el margen:** en las 9 ejecuciones el margen mínimo lo fija `bloqueo_australia_este`. El margen mediano baja de 16.56°–21.10° en base a 0.50°–3.70° en reducido.
- **Repair:** el margen queda en 0.50°, justo el margen con que la reparación saca a un satélite de una zona. La restricción está activa y la reparación la resuelve dejando el satélite pegado al borde.
- **Penalty y strict:** se alejan más de la zona y no cumplen el umbral de 1°.
- **Aptitud:** el espacio reducido no impide cubrir 6/6, que se logra en 8 de 9 ejecuciones, y la aptitud mediana cambia como mucho 0.0115. El óptimo sigue siendo alcanzable (Def. §8.2).

### P6 · Condición difícil o inviable

**Condiciones.** `inviable` × 3 modos × 3 semillas. Cubrir Yucatán es imposible sin violar una zona; el óptimo válido es 0.796154.

<!-- tabla:p6_resumen -->
| modo | ejecuciones | válidas | válidas con cov_yucatan = 0 | aptitud penalty máx. | ≤ 0.796154 | brecha < 0.01 [IC 95 %] | éxito 6/6 | veredicto |
|---|---|---|---|---|---|---|---|---|
| penalty | 3 | 3/3 | 3/3 | 0.792308 | 3/3 | 2/3 [0.21, 0.94] | 0/3 | PASA |
| repair | 3 | 3/3 | 3/3 | 0.796154 | 3/3 | 2/3 [0.21, 0.94] | 0/3 | PASA |
| strict | 3 | 3/3 | 3/3 | 0.792308 | 3/3 | 3/3 [0.44, 1.00] | 0/3 | PASA |

| config | n | media | sd | mediana | IQR | mín | máx | éxito k/n [IC Wilson 95 %] |
|---|---|---|---|---|---|---|---|---|
| inviable_penalty | 3 | 0.7885 | 0.0038 | 0.7885 | 0.7865–0.7904 | 0.7846 | 0.7923 | 0/3 [0.00, 0.56] |
| inviable_repair | 3 | 0.7859 | 0.0118 | 0.7885 | 0.7808–0.7923 | 0.7731 | 0.7962 | 0/3 [0.00, 0.56] |
| inviable_strict | 3 | 0.7897 | 0.0022 | 0.7885 | 0.7885–0.7904 | 0.7885 | 0.7923 | 0/3 [0.00, 0.56] |

| config | alcanzan el óptimo (brecha < 1e-6) | brecha mediana | brecha máx. |
|---|---|---|---|
| inviable_penalty | 0/3 | 0.007692 | 0.011539 |
| inviable_repair | 1/3 | 0.007692 | 0.023077 |
| inviable_strict | 0/3 | 0.007692 | 0.007692 |
<!-- /tabla -->

![P6: aptitud en inviable](results/exp_figuras/p6_boxplot.png)

**Interpretación.** **PASA.** Las 9 soluciones son válidas, ninguna cubre Yucatán y ninguna supera el óptimo teórico, que una ejecución (repair, semilla 44) alcanza exactamente. Ninguna ejecución cumple 6/6, lo cual es esperado: no es un fallo del sistema sino del escenario. Ni siquiera en modo penalty el algoritmo «compra» Yucatán con una violación, porque costaría K = 0.5 y como mucho ganaría 3/13 + 0.05·3/13 ≈ 0.242 (Def. §8.3).

### P7 · Variación entre ejecuciones

**Condiciones.** Las mismas configuraciones con 3 semillas distintas.

<!-- tabla:p7_variacion -->
| config | n | media | sd | mediana | IQR | mín | máx | éxito k/n [IC Wilson 95 %] |
|---|---|---|---|---|---|---|---|---|
| base_penalty | 3 | 1.0154 | 0.0038 | 1.0154 | 1.0135–1.0173 | 1.0115 | 1.0192 | 3/3 [0.44, 1.00] |
| base_repair | 3 | 0.9615 | 0.0867 | 1.0077 | 0.9346–1.0115 | 0.8615 | 1.0154 | 2/3 [0.21, 0.94] |
| base_strict | 3 | 1.0154 | 0.0038 | 1.0154 | 1.0135–1.0173 | 1.0115 | 1.0192 | 3/3 [0.44, 1.00] |

| config | alcanzan el óptimo (brecha < 1e-6) | brecha mediana | brecha máx. |
|---|---|---|---|
| base_penalty | 0/3 | 0.007692 | 0.011539 |
| base_repair | 0/3 | 0.015385 | 0.161539 |
| base_strict | 0/3 | 0.007692 | 0.011539 |
<!-- /tabla -->

<!-- tabla:p7_redundancia -->
| config | regiones con ≥2 satélites que las cubren completas | semillas |
|---|---|---|
| base_penalty | amazonia+japon | 1 |
| base_penalty | sahel+australia | 1 |
| base_penalty | yucatan+australia | 1 |
| base_repair | amazonia+australia | 2 |
| base_repair | sahel | 1 |
| base_strict | sahel+australia | 1 |
| base_strict | yucatan+australia | 1 |
| base_strict | yucatan+sahel | 1 |
<!-- /tabla -->

<!-- tabla:regiones_cubiertas -->
| escenario | modo | yucatan | amazonia | california | sahel | japon | australia | 6/6 cubiertas |
|---|---|---|---|---|---|---|---|---|
| base | penalty | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 3/3 |
| base | repair | 100 % (1.000) | 100 % (1.000) | 67 % (0.667) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 2/3 |
| base | strict | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 3/3 |
| reducido | penalty | 100 % (1.000) | 100 % (1.000) | 67 % (0.667) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 2/3 |
| reducido | repair | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 3/3 |
| reducido | strict | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 3/3 |
| inviable | penalty | 0 % (0.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 0/3 |
| inviable | repair | 0 % (0.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 0/3 |
| inviable | strict | 0 % (0.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 0/3 |
| prioridad_cambiada | penalty | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 67 % (0.667) | 100 % (1.000) | 100 % (1.000) | 2/3 |
| prioridad_cambiada | repair | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 3/3 |
| prioridad_cambiada | strict | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 67 % (0.667) | 100 % (1.000) | 100 % (1.000) | 2/3 |
| menos_sats | penalty | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 0 % (0.000) | 0 % (0.000) | 0/3 |
| menos_sats | repair | 67 % (0.667) | 100 % (1.000) | 33 % (0.333) | 67 % (0.667) | 67 % (0.667) | 67 % (0.667) | 0/3 |
| menos_sats | strict | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 0 % (0.000) | 0 % (0.000) | 0/3 |
| footprint_chico | penalty | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 33 % (0.333) | 1/3 |
| footprint_chico | repair | 100 % (1.000) | 67 % (0.667) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 2/3 |
| footprint_chico | strict | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 67 % (0.667) | 2/3 |
<!-- /tabla -->

<!-- tabla:otros_escenarios -->
| config | n | media | sd | mediana | IQR | mín | máx | éxito k/n [IC Wilson 95 %] |
|---|---|---|---|---|---|---|---|---|
| prioridad_cambiada_penalty | 3 | 0.9726 | 0.0845 | 1.0214 | 0.9482–1.0214 | 0.8750 | 1.0214 | 2/3 [0.21, 0.94] |
| prioridad_cambiada_repair | 3 | 1.0202 | 0.0021 | 1.0214 | 1.0196–1.0214 | 1.0179 | 1.0214 | 3/3 [0.44, 1.00] |
| prioridad_cambiada_strict | 3 | 0.9679 | 0.0805 | 1.0107 | 0.9429–1.0143 | 0.8750 | 1.0179 | 2/3 [0.21, 0.94] |

| config | alcanzan el óptimo (brecha < 1e-6) | brecha mediana | brecha máx. |
|---|---|---|---|
| prioridad_cambiada_penalty | 2/3 | 0.000000 | 0.146429 |
| prioridad_cambiada_repair | 2/3 | 0.000000 | 0.003572 |
| prioridad_cambiada_strict | 0/3 | 0.010715 | 0.146429 |

| config | n | media | sd | mediana | IQR | mín | máx | éxito k/n [IC Wilson 95 %] |
|---|---|---|---|---|---|---|---|---|
| menos_sats_penalty | 3 | 0.7692 | 0.0000 | 0.7692 | 0.7692–0.7692 | 0.7692 | 0.7692 | 0/3 [0.00, 0.56] |
| menos_sats_repair | 3 | 0.6923 | 0.0769 | 0.6923 | 0.6538–0.7308 | 0.6154 | 0.7692 | 0/3 [0.00, 0.56] |
| menos_sats_strict | 3 | 0.7692 | 0.0000 | 0.7692 | 0.7692–0.7692 | 0.7692 | 0.7692 | 0/3 [0.00, 0.56] |

| config | alcanzan el óptimo (brecha < 1e-6) | brecha mediana | brecha máx. |
|---|---|---|---|
| menos_sats_penalty | 3/3 | 0.000000 | 0.000000 |
| menos_sats_repair | 1/3 | 0.076923 | 0.153846 |
| menos_sats_strict | 3/3 | 0.000000 | 0.000000 |

| config | n | media | sd | mediana | IQR | mín | máx | éxito k/n [IC Wilson 95 %] |
|---|---|---|---|---|---|---|---|---|
| footprint_chico_penalty | 3 | 0.9590 | 0.0456 | 0.9346 | 0.9327–0.9731 | 0.9308 | 1.0115 | 1/3 [0.06, 0.79] |
| footprint_chico_repair | 3 | 0.9333 | 0.1355 | 1.0077 | 0.8923–1.0115 | 0.7769 | 1.0154 | 2/3 [0.21, 0.94] |
| footprint_chico_strict | 3 | 0.9846 | 0.0433 | 1.0077 | 0.9712–1.0096 | 0.9346 | 1.0115 | 2/3 [0.21, 0.94] |

| config | alcanzan el óptimo (brecha < 1e-6) | brecha mediana | brecha máx. |
|---|---|---|---|
| footprint_chico_penalty | 0/3 | 0.088462 | 0.092308 |
| footprint_chico_repair | 0/3 | 0.015385 | 0.246154 |
| footprint_chico_strict | 0/3 | 0.015385 | 0.088462 |
<!-- /tabla -->

![P7: aptitud final por modo](results/exp_figuras/p7_boxplot.png)

**Interpretación.**
- **Base, penalty y strict:** varían poco (desviación de 0.0038) y las 3 semillas cubren 6/6.
- **Base, repair:** una semilla (44) se queda en 0.861538 con California sin cubrir. Ninguna ejecución de base alcanza el óptimo.
- **Redundancia:** cambia de semilla a semilla. Por eso varía la aptitud final aunque se cubra lo mismo.
- **Los otros escenarios repiten el patrón:**
  - en `menos_sats`, penalty y strict alcanzan el óptimo en 3/3, mientras repair lo hace en 1/3;
  - en `footprint_chico`, con un footprint de la mitad, ninguna ejecución llega al óptimo y el éxito baja a entre 1/3 y 2/3;
  - en `prioridad_cambiada`, repair cubre 6/6 en 3/3.

### P8 · Prueba adicional: penalty vs repair vs strict

**Condiciones.** Las mismas que la prueba P8 de la campaña anterior: `base`, `reducido` e `inviable` × 3 modos, con la diferencia de medianas frente a penalty y su intervalo bootstrap del 95 %. Aquí con 3 semillas en lugar de 30.

<!-- tabla:p8_modos -->
| escenario | modo | éxito [IC 95 %] | aptitud penalty mediana | media | válidas | gen 6/6 válida mediana | Δ mediana vs penalty [IC bootstrap 95 %] |
|---|---|---|---|---|---|---|---|
| base | penalty | 3/3 [0.44, 1.00] | 1.0154 | 1.0154 | 3/3 | 21.0 | — |
| base | repair | 2/3 [0.21, 0.94] | 1.0077 | 0.9615 | 3/3 | 25.0 | -0.0077 [-0.1577, +0.0038] |
| base | strict | 3/3 [0.44, 1.00] | 1.0154 | 1.0154 | 3/3 | 21.0 | +0.0000 [-0.0077, +0.0077] |
| reducido | penalty | 2/3 [0.21, 0.94] | 1.0038 | 0.9577 | 3/3 | 35.0 | — |
| reducido | repair | 3/3 [0.44, 1.00] | 1.0192 | 1.0179 | 3/3 | 27.0 | +0.0154 [+0.0077, +0.1577] |
| reducido | strict | 3/3 [0.44, 1.00] | 1.0115 | 1.0103 | 3/3 | 28.0 | +0.0077 [-0.0038, +0.1538] |
| inviable | penalty | 0/3 [0.00, 0.56] | 0.7885 | 0.7885 | 3/3 | — | — |
| inviable | repair | 0/3 [0.00, 0.56] | 0.7885 | 0.7859 | 3/3 | — | +0.0000 [-0.0192, +0.0115] |
| inviable | strict | 0/3 [0.00, 0.56] | 0.7885 | 0.7897 | 3/3 | — | +0.0000 [-0.0038, +0.0077] |
<!-- /tabla -->

**Interpretación.**
- **Base:** strict empata con penalty; repair queda por debajo (−0.0077), pero el intervalo incluye 0.
- **Reducido:** repair supera a penalty en +0.0154, y es el único intervalo que excluye 0. Strict también mejora, sin diferencia clara.
- **Inviable:** no hay diferencia entre modos.

Conclusión: con restricciones que recortan el espacio, reparar ayuda. Sin ellas, los tres modos son equivalentes. Con 3 semillas es una tendencia, no una conclusión firme.

---

# Análisis de resultados

### ¿Qué tan bien se observan las regiones en la configuración final?

En `base`, 8 de 9 ejecuciones cubren las 6 regiones sin violaciones (tabla `regiones_cubiertas`). La aptitud mediana es 1.0154 en penalty y strict, a 0.0077 del óptimo 1.023077 (P7). La diferencia no es cobertura sino redundancia: los satélites sobrantes duplican regiones de menor peso que las dos Alta (tabla `p7_redundancia`). La ejecución que falla (repair, semilla 44) deja California sin cubrir.

### ¿Cómo cambió la calidad durante el proceso evolutivo?

En la mediana, el mejor individuo pasa de 0.3785 en la generación 0 a 1.0 en la generación 25 en penalty y strict, y a entre 1.0077 y 1.0154 en la 200 (tabla `p2_resumen`). La mayor parte de la mejora ocurre en las primeras 25 generaciones. Después solo se ajusta la redundancia y la diversidad cae (figura P2). La mejor aptitud nunca baja, por el elitismo.

### ¿Qué diferencias hubo entre ejecuciones?

- **En la base:** penalty y strict varían poco (desviación de 0.0038). Repair tiene una semilla atascada en 0.861538, una meseta con 5/6 cubiertas (P7).
- **Entre semillas:** cambia sobre todo qué regiones reciben la redundancia.
- **Entre escenarios:** `footprint_chico` es el más variable (éxito de 1/3 a 2/3), porque la zona útil alrededor de cada región es mucho más pequeña (Def. §8.6).

### ¿Qué efecto tuvieron las restricciones espaciales?

- **En base:** no están activas en la solución, porque el margen mediano al borde de toda zona es de 16.56° a 21.10°. Sí actúan durante la búsqueda: 17.7 de cada 100 individuos iniciales son inválidos (P3/P4).
- **En `reducido`:** los inválidos iniciales suben a 40.7 de cada 100, y la zona nueva obliga a acercarse a menos de 4° de su borde, 0.5° en repair (P5). Aun así, la aptitud mediana cambia como mucho 0.0115.
- **En `inviable`:** quitan una región entera y bajan el techo a 0.796154 (P6).
- **Cambio de condiciones:** al revalidar la solución de base contra cada escenario sin volver a optimizar, se ve cuáles siguen siendo válidas:

<!-- tabla:p11_revalidacion -->
| escenario nuevo | still_valid | razones | zonas violadas | aptitud antes | aptitud después | perdidas | ganadas | coherente con §4.6 |
|---|---|---|---|---|---|---|---|---|
| reducido | sí | — | — | 1.007692 | 1.007692 | — | — | PASA |
| inviable | no | violations: 1 | bloqueo_yucatan | 1.007692 | 0.507692 | — | — | PASA |
| prioridad_cambiada | sí | — | — | 1.007692 | 1.007143 | — | — | PASA |
| menos_sats | no | n_sats: 8 != 4 | — | 1.007692 | 1.007692 | — | — | PASA |
| footprint_chico | sí | — | — | 1.007692 | 0.583835 | yucatan california sahel japon australia | — | PASA |
<!-- /tabla -->

### ¿Qué sucede cuando el sistema no puede satisfacer todas las condiciones?

El sistema prefiere seguir siendo válido y sacrifica la cobertura de menor valor:
- **`inviable`:** las 9 soluciones son válidas, renuncian a Yucatán y cubren las otras 5 regiones. Una de ellas llega al óptimo de 0.796154 (P6).
- **`menos_sats`:** con 4 satélites, penalty y strict cubren las 2 regiones Alta y 2 Media, y dejan fuera a Australia (Normal) y a Japón. Es el óptimo de 0.769231 que dictan los pesos (tablas `regiones_cubiertas` y `otros_escenarios`).

En ningún caso el algoritmo «compra» cobertura con una violación, porque K = 0.5 lo hace siempre más caro.

### ¿Qué limitaciones tiene el criterio de evaluación?

- **La cobertura parcial es una aproximación lineal,** no el área solapada real, y varios satélites no suman cobertura: se toma el mejor (Def. §9.2).
- **La penalización cuenta violaciones, no su profundidad.** Rozar una zona cuesta lo mismo que estar en su centro (Def. §9.4).
- **El bono de redundancia es pequeño a propósito** (β = 0.05). Por eso soluciones con la misma cobertura difieren apenas en 0.0077 o 0.0154. Es poco para distinguir calidad, pero es lo que separa «suficientemente buena» de «óptima».
- **Los óptimos teóricos solo valen con F < 18.2°,** el régimen de un satélite por región (Def. §9.7).
- **Con 3 semillas por configuración,** los intervalos de éxito van, por ejemplo, de 0.44 a 1.00 para 3/3 (tabla `p8_modos`). Las diferencias entre modos son tendencias, no resultados significativos, salvo repair en `reducido`.

### ¿Qué evidencia permite afirmar que una solución es mejor que otra?

En orden:
1. **Validez:** una solución inválida no se compara.
2. **Cobertura** de las regiones cubribles.
3. **Brecha frente al óptimo teórico,** calculada a mano y comprobada con `model.fitness`. Es una referencia absoluta, no relativa a otras ejecuciones.
4. **Repetibilidad** entre semillas, con intervalos.
5. **Comparación con el azar:** el algoritmo supera a la búsqueda aleatoria con el mismo presupuesto en 3/3 semillas (P2).

Todo sale de los JSON y CSV de `results/`, no de la visualización. Los tests (`test_integration.py` y `experiments/test_experiments.py`) recalculan con el modelo la cobertura, la aptitud y las violaciones guardadas en cada resultado y comprueban que coinciden.

---

## Estructura

```
src/astroshield/   geometría, modelo, algoritmo genético, restricciones, CLI y revalidación
run.py             lanzador de la CLI
tests/             pruebas (pytest)
schemas/           esquemas JSON de escenario y resultado
scenarios/         escenario base y derivados
results/           resultados, revalidaciones y campaña de pruebas (exp_*)
experiments/       campañas, tablas, figuras e inserción de tablas en este README
viz/               visualización 3D (globe.gl)
docs/              enunciado, contrato y definición extendida
```
