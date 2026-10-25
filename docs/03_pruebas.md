# Entregable 3 · Pruebas y validación

> Todas las tablas de este documento se generan con `experiments/` y se insertan con
> `python experiments/report.py` entre marcadores `<!-- tabla:… -->`. Ninguna cifra de una tabla
> se escribe a mano; en la prosa solo se citan cifras copiadas de esas tablas.
> `python experiments/report.py --check` falla si el documento quedó desactualizado.

## 1. Cómo reproducir

```bash
pip install -e ".[dev,exp]"
python experiments/run_experiments.py --bench               # mide y proyecta el tiempo (exp_meta/bench.csv)
python experiments/run_experiments.py --all --jobs 16       # campañas + representativas + tablas + figuras
python experiments/report.py                                # inserta las tablas en este documento
python experiments/run_experiments.py --all --verify        # re-ejecuta y compara sha256 de exp_runs/*.csv
pytest && pytest experiments                                # suite del repo + tests de los experimentos
```

Salidas (todas bajo `results/`, prefijo `exp_`):

| Carpeta | Contenido |
|---|---|
| `exp_runs/` | una fila por ejecución (`base.csv`, `footprint.csv`, `poblacion.csv`, `aleatoria.csv`), curvas agregadas por configuración y generación (`curvas_*.csv`) y satélites finales de todas las ejecuciones (`finales_*.csv`) |
| `exp_json/` | resultados completos representativos (cumplen `result.schema.json` y los valida `tests/test_contract.py`) |
| `exp_tablas/` | tablas Markdown generadas (las de este documento) |
| `exp_figuras/` | figuras PNG |
| `exp_meta/` | `entorno.txt` (versiones, commit, comando), `sha256.txt`, `tiempos.csv`, `bench.csv`, `representativas.csv` |

Reproducibilidad: cada ejecución es una función pura de (escenario, modo, parámetros, semilla), porque
`run()` crea `np.random.default_rng(seed)` dentro; la búsqueda aleatoria crea su propio
`default_rng(seed)` en `experiments/`. El resultado no depende de `--jobs` (lo verifica
`test_quick_parallel_equals_serial`). Las ejecuciones representativas se re-ejecutan y se exige igualdad
bit a bit con la primera pasada; si no coincide, el programa aborta con código 3. Los CSV usan `repr`
(17 cifras) y su sha256 se calcula con fin de línea LF. La igualdad bit a bit solo se garantiza con la
misma versión de numpy (contrato §2): la versión usada está en `exp_meta/entorno.txt`.

Tiempo de cómputo medido en esta máquina (Windows 11, 16 procesadores lógicos; versiones en
`exp_meta/entorno.txt`). **Nota:** desde poco después del primer `--bench`, tres procesos ajenos al
proyecto (un navegador) ocupaban casi toda la CPU de la máquina, durante la corrida completa y durante
los `--bench` posteriores. Por eso solo las tres primeras filas del **primer** `--bench` (una ejecución
100 × 200 por modo, en un proceso) sirven como referencia de rendimiento. La fila "aleatoria" de ese
primer bench, el último bench y los tiempos por ejecución de la corrida completa están inflados por esa
contención, varias veces por encima de lo normal. Aun con esa proyección inflada, el primer bench
quedó por debajo de 30 min de reloj con 16 procesos, así que no se aplicó la regla de corte. Los
resultados numéricos no dependen de esto: son deterministas.

<!-- tabla:tiempos -->
| campaña | ejecuciones | Σ tiempo por ejecución (s) | s por ejecución (media) | reloj total (s) | procesos |
|---|---|---|---|---|---|
| base | 90 | 10485.5 | 116.51 | — | — |
| footprint | 180 | 13913.7 | 77.30 | — | — |
| poblacion | 120 | 16828.5 | 140.24 | — | — |
| aleatoria | 30 | 1767.9 | 58.93 | — | — |
| TOTAL | 420 | 42995.5 | — | 2849.5 | 16 |
| representativas | 20 | — | — | 231.9 | 16 |

| primer --bench (1 proceso, exp_meta/bench_inicial.txt) | segundos |
|---|---|
| run base penalty 100x200 | 9.5 |
| run base repair 100x200 | 16.1 |
| run base strict 100x200 | 14.2 |
| aleatoria 20100 | 449.8 |
| proyeccion cpu --all (s) | 18075.7 |
| proyeccion reloj --all con 16 procesos (s) | 1129.7 |

| último --bench (1 proceso, exp_meta/bench.csv) | segundos |
|---|---|
| run base penalty 100x200 | 2178.5 |
| run base repair 100x200 | 1370.4 |
| run base strict 100x200 | 40.3 |
| aleatoria 20100 | 32.9 |
| proyeccion cpu --all (s) | 397005.4 |
| proyeccion reloj --all con 16 procesos (s) | 24812.8 |
<!-- /tabla -->

## 2. Condiciones comunes

- Semillas 42–71 (30), las mismas en todos los escenarios y modos (números aleatorios comunes: reducen la
  varianza de las comparaciones entre modos).
- Parámetros del AG: `DEFAULT_PARAMS` del contrato (§8: P = 100, 200 generaciones, torneo 3, cruce 0.9,
  BLX-0.5, p_swap 0.5, p_mut 0.2, σ = 5°, elitismo 2), salvo donde la prueba diga otra cosa.
- Escenario `scenarios/base.json` (§4.4): 6 regiones, 3 zonas de desechos, 2 objetos ocupados, 8 satélites,
  footprint 10°, K = 0.5, β = 0.05.
- Oráculos (§10): base 1.023077 (6/6 + redundancia en Yucatán y Amazonía), inviable 0.788462.
- Criterio de "suficientemente buena" (Entregable 1, §10): `valid == true` y 6/6 regiones cubiertas
  (c == 1.0). Se informa además la brecha frente al óptimo. "Éxito" en las tablas es ese criterio.
- Para comparar modos se usa la aptitud **penalty** de la configuración final
  (`final_penalty_fitness = model.fitness(final.sats, sc, "penalty")`): en strict válido coincide con la
  aptitud base y en penalty/repair es la aptitud guardada.
- Intervalos: Wilson al 95 % para proporciones; bootstrap percentil (5000 réplicas, `default_rng(0)`) para
  diferencias de medianas.

### Pruebas bloqueadas

Los escenarios derivados de la Ola 1D (`reducido.json`, `inviable.json`, `prioridad_cambiada.json`,
`menos_sats.json`, `footprint_chico.json`) **no existen en esta rama**. El código de esas campañas está
implementado y probado (`campaign_tasks` las omite si falta el archivo, y sus tests quedan en `skip`), pero
P5, P6, P11 y la parte de P3, P4 y P8 que depende de ellos quedan **bloqueadas por 1D (escenario no
disponible)**. Se describen sus condiciones y su criterio; no se da ninguna cifra.

## 3. Pruebas obligatorias

### P1 · Escenario inicial

**Condiciones.** `scenarios/base.json`, modo `repair`, semilla 42, `DEFAULT_PARAMS` (100 × 200).
Resultado completo en `results/exp_json/base_repair_s42.json`.

**Resultados.** Configuración final (qué región sirve cada satélite), cobertura por región y aptitud:

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

Comparación con `results/base_repair_s42.json` (Ola 2, numpy 2.3.4): misma configuración final y aptitud = **sí**.
<!-- /tabla -->

![P1: inicial vs final](../results/exp_figuras/p1_mapa.png)

**Interpretación.** La solución es válida y cubre las 6 regiones, así que cumple el criterio de
suficiencia; la aptitud pasa de 0.461849 (mejor individuo de la generación 0) a 1.007692. Cada región
tiene su propio satélite, como exige la geometría (§4.5: ningún par de regiones cabe en un footprint de
10°). La brecha de 0.015385 frente al óptimo se explica en la tabla: los dos satélites libres no se usan
como el óptimo los usaría. Uno se duplica sobre Sahel (prioridad Media) y el otro queda en
(-74.802, -55.991), donde no cubre nada. El óptimo pondría los dos extra en Yucatán y Amazonía (Alta).
Esta ejecución reproduce exactamente `results/base_repair_s42.json` de la Ola 2, generado con otra
versión de numpy (última línea de la tabla).

**Fallos y efecto sobre la validez.** Ninguno en validez ni en cobertura (0 violaciones finales). La
solución no es óptima: la redundancia está en una región de prioridad Media y sobra un satélite. Eso
solo afecta al bono de redundancia (β = 0.05), no al criterio de suficiencia.

### P2 · Evolución

**Condiciones.** Base × {penalty, repair, strict} × 30 semillas, 100 × 200. Línea base: búsqueda
aleatoria uniforme con el **mismo presupuesto** (20 100 configuraciones por semilla, aptitud penalty,
mismas 30 semillas). Las curvas son la mediana y el rango intercuartílico de `history[g].best` entre
semillas. Criterio: el AG supera a la aleatoria en ≥ 29/30 semillas.

<!-- tabla:p2_resumen -->
| config | best med. g0 | best med. g10 | best med. g25 | best med. g50 | best med. g100 | best med. g200 | gen_99 med. | gen 6/6 válida med. | alcanzan 6/6 válida | AG > aleatoria (misma semilla) |
|---|---|---|---|---|---|---|---|---|---|---|
| base_penalty | 0.3577 | 0.7627 | 0.9538 | 1.0077 | 1.0115 | 1.0154 | 33.0 | 24.0 | 23/30 | 30/30 |
| base_repair | 0.3726 | 0.7692 | 0.9773 | 1.0077 | 1.0115 | 1.0154 | 33.5 | 26.0 | 25/30 | 30/30 |
| base_strict | 0.3577 | 0.7627 | 0.9807 | 1.0096 | 1.0115 | 1.0154 | 33.0 | 24.0 | 24/30 | 30/30 |

| línea base | n semillas | evaluaciones | máx. mediano | máx. de máx. | media de p95 | media de la media | éxito 6/6 |
|---|---|---|---|---|---|---|---|
| aleatoria uniforme (penalty) | 30 | 20100 | 0.6154 | 0.7692 | 0.2308 | -0.0481 | 0/30 |
<!-- /tabla -->

![P2: curvas de aptitud](../results/exp_figuras/p2_curvas_base.png)

![P2: diversidad](../results/exp_figuras/p2_diversidad.png) ![P2: inválidos](../results/exp_figuras/p2_invalidos.png)

**Interpretación.** **PASA**: el AG supera a la búsqueda aleatoria en 30/30 semillas en los tres modos.
La aleatoria se estanca en un máximo mediano de 0.6154 (la mejor de las 30 llega a 0.7692) y no
alcanza nunca 6/6 (0/30). El AG supera la aptitud 1.0 (6/6 cubiertas) hacia la generación 25-50
(mediana del mejor 1.0077 en g50) y alcanza el 99 % de su aptitud final hacia la generación 33
(`gen_99` mediano 33.0-33.5). De la generación 100 a la 200 la mediana del mejor apenas cambia
(1.0115 → 1.0154). La diversidad cae de forma monótona y la población converge. La media de la
población y el número de inválidos muestran que las restricciones actúan al principio: en la
generación 0 hay en promedio 20.0 de 100 individuos inválidos en penalty y strict (P3), y 0.0 en
repair, porque la población inicial se repara.

**Fallos y efecto sobre la validez.** Que la curva se aplane no prueba optimalidad: la mediana final
(1.0154) queda por debajo del óptimo 1.023077 (P7). No se observó ningún fallo de ejecución.

### P3 · Zonas de desechos

**Condiciones.** Base × 3 modos × 30 semillas (90 ejecuciones). Se cuentan las violaciones finales de
tipo `debris` (§5.4) y el margen mínimo `min_margin_deg = min_{i,z}(d(sat_i, z) − r_z)` sobre todas las
zonas (< 0 = violación; ≈ 0 = restricción activa). La parte de `reducido` está **bloqueada por 1D
(escenario no disponible)**: allí se esperaba una restricción activa (margen mediano < 1°) y el mismo
criterio de 0 violaciones en repair y strict.

<!-- tabla:p3_violaciones -->
| config | ejecuciones | violaciones finales (debris) | ejecuciones con ≥1 | inválidos gen 0 (media de 100) | margen mín. mediano (°) | margen mín. menor (°) |
|---|---|---|---|---|---|---|
| base_penalty | 30 | 0 | 0 | 20.0 | 18.50 | 7.12 |
| base_repair | 30 | 0 | 0 | 0.0 | 18.94 | 0.25 |
| base_strict | 30 | 0 | 0 | 20.0 | 18.42 | 7.12 |
<!-- /tabla -->

![P3/P4: satélites finales sobre zonas y objetos](../results/exp_figuras/p3_mapa_finales.png)

**Interpretación.** **PASA**: 0 violaciones finales de desechos en las 90 ejecuciones, también en penalty
(K = 0.5 > 3/13 + β, §4.3: ninguna violación "se paga" con cobertura). Las restricciones **actúan
durante la búsqueda**: 20.0 de 100 individuos de la generación 0 son inválidos en penalty y strict,
igual que el ≈ 20 % que predice el contrato (§4.5). Pero **no están activas en el óptimo base**: el
margen mínimo mediano de las soluciones finales es de 18.42-18.94°, muy cerca de los 18.76° entre
Australia y el borde de `objeto_b` del contrato. El margen más pequeño observado (0.25° en repair)
corresponde a un satélite que quedó junto al borde de una zona sin violarla. `repair` deja los satélites
que repara a radio + 0.5° del centro, así que en ese modo los márgenes pequeños son de esperar. En esa
semilla las 6 regiones siguen cubiertas (`exp_runs/base.csv`).

**Fallos y efecto sobre la validez.** Ninguno observado (0/90 ejecuciones con violaciones). Esta prueba
no demuestra que el AG maneje bien una restricción **activa**: en base no lo está. Esa evidencia
dependía de `reducido`, bloqueado por 1D.

### P4 · Posiciones ocupadas

**Condiciones.** Las mismas que en P3, con las violaciones de tipo `occupied` (`objeto_a`, `objeto_b`).
Mismo mapa de P3 (contornos violetas discontinuos). La parte de `reducido` está **bloqueada por 1D
(escenario no disponible)**.

<!-- tabla:p4_violaciones -->
| config | ejecuciones | violaciones finales (occupied) | ejecuciones con ≥1 | inválidos gen 0 (media de 100) | margen mín. mediano (°) | margen mín. menor (°) |
|---|---|---|---|---|---|---|
| base_penalty | 30 | 0 | 0 | 20.0 | 18.50 | 7.12 |
| base_repair | 30 | 0 | 0 | 0.0 | 18.94 | 0.25 |
| base_strict | 30 | 0 | 0 | 20.0 | 18.42 | 7.12 |
<!-- /tabla -->

**Interpretación.** **PASA**: 0 violaciones finales de objetos ocupados en las 90 ejecuciones. Las
columnas de inválidos y margen son las de P3, porque se calculan sobre todas las zonas: el margen
mínimo no distingue el tipo de zona. Las mismas salvedades: los objetos ocupados no compiten con
ninguna región por el espacio útil en el escenario base.

**Fallos y efecto sobre la validez.** Ninguno observado.

### P5 · Espacio reducido

**Bloqueada por 1D (escenario no disponible).** Falta `scenarios/reducido.json`.

**Condiciones (implementadas, sin ejecutar).** Campaña `reducido` × 3 modos × 30 semillas, 100 × 200.
El contrato (§4.6) define `reducido` con los radios originales × 1.5 y al menos una zona nueva que corta
el casquete de cobertura completa de una región sin taparlo (ejemplo: `bloqueo_australia_este`).

**Criterio.** Restricción activa: mediana de `min_margin_deg` < 1° en reducido frente a > 10° en base
(en base es 18.42-18.94°, P3); tasa de éxito y caída de aptitud frente a base; 0 violaciones finales en
repair y strict. Salidas previstas: `p5_resumen.md`, boxplot y margen. Cuando 1D publique el escenario,
`python experiments/run_experiments.py --only reducido` genera las tablas sin cambiar código.

### P6 · Escenario inviable

**Bloqueada por 1D (escenario no disponible).** Falta `scenarios/inviable.json`.

**Condiciones (implementadas, sin ejecutar).** Campaña `inviable` × 3 modos × 30 semillas. Según el
contrato (§4.6), la zona `bloqueo_yucatan` (radio 13° > F + r = 12.7°) hace imposible cubrir Yucatán sin
violar.

**Criterio.** Ningún final válido cubre Yucatán (`cov_yucatan == 0`); `final_penalty_fitness ≤ 0.788462`
(oráculo §10); se informa la tasa con brecha < 0.01. El resultado esperado es un **fallo del criterio de
suficiencia** (no hay 6/6 posibles), no un fallo del sistema. El test
`test_inviable_never_covers_yucatan` ya lo comprueba y hoy queda en `skip`.

### P7 · Variación entre ejecuciones

**Condiciones.** Base × 3 modos × 30 semillas (las mismas de P2-P4). Estadísticos de la aptitud final
(penalty), tasa de éxito con IC de Wilson, porcentaje de semillas que cubren cada región y dónde
quedan los satélites redundantes.

<!-- tabla:p7_variacion -->
| config | n | media | sd | mediana | IQR | mín | máx | éxito k/n [IC Wilson 95 %] |
|---|---|---|---|---|---|---|---|---|
| base_penalty | 30 | 0.9864 | 0.0581 | 1.0154 | 1.0077–1.0192 | 0.8577 | 1.0231 | 23/30 [0.59, 0.88] |
| base_repair | 30 | 0.9868 | 0.0743 | 1.0154 | 1.0077–1.0192 | 0.7154 | 1.0231 | 25/30 [0.66, 0.93] |
| base_strict | 30 | 0.9944 | 0.0484 | 1.0154 | 1.0087–1.0192 | 0.8577 | 1.0231 | 24/30 [0.63, 0.90] |

| config | alcanzan el óptimo (brecha < 1e-6) | brecha mediana | brecha máx. |
|---|---|---|---|
| base_penalty | 2/30 | 0.007692 | 0.165385 |
| base_repair | 2/30 | 0.007692 | 0.307692 |
| base_strict | 2/30 | 0.007692 | 0.165385 |
<!-- /tabla -->

Regiones cubiertas (`% de semillas con c == 1.0 (media de c)`):

<!-- tabla:regiones_cubiertas -->
| config | yucatan | amazonia | california | sahel | japon | australia |
|---|---|---|---|---|---|---|
| base_penalty | 100 % (1.000) | 100 % (1.000) | 97 % (0.967) | 93 % (0.933) | 93 % (0.933) | 93 % (0.933) |
| base_repair | 100 % (1.000) | 100 % (1.000) | 97 % (0.967) | 97 % (0.967) | 90 % (0.900) | 93 % (0.933) |
| base_strict | 100 % (1.000) | 100 % (1.000) | 100 % (1.000) | 93 % (0.933) | 97 % (0.967) | 90 % (0.900) |
<!-- /tabla -->

Dónde cae la redundancia (regiones con ≥ 2 satélites que las cubren completas):

<!-- tabla:p7_redundancia -->
| config | regiones con ≥2 satélites que las cubren completas | semillas |
|---|---|---|
| base_penalty | yucatan+australia | 5 |
| base_penalty | amazonia | 3 |
| base_penalty | amazonia+japon | 2 |
| base_penalty | amazonia+sahel | 2 |
| base_penalty | california+australia | 2 |
| base_penalty | sahel | 2 |
| base_penalty | sahel+australia | 2 |
| base_penalty | yucatan+amazonia | 2 |
| base_penalty | yucatan+amazonia+california | 2 |
| base_penalty | yucatan+california | 2 |
| base_penalty | yucatan+sahel | 2 |
| base_penalty | amazonia+australia | 1 |
| base_penalty | amazonia+sahel+australia | 1 |
| base_penalty | sahel+japon | 1 |
| base_penalty | yucatan+amazonia+australia | 1 |
| base_repair | yucatan+sahel | 4 |
| base_repair | amazonia+japon | 3 |
| base_repair | yucatan+amazonia | 3 |
| base_repair | amazonia+australia | 2 |
| base_repair | amazonia+sahel | 2 |
| base_repair | california+sahel | 2 |
| base_repair | japon | 2 |
| base_repair | sahel | 2 |
| base_repair | yucatan+california | 2 |
| base_repair | yucatan+japon | 2 |
| base_repair | amazonia | 1 |
| base_repair | california+australia | 1 |
| base_repair | california+japon | 1 |
| base_repair | yucatan+amazonia+california+sahel | 1 |
| base_repair | yucatan+australia | 1 |
| base_repair | yucatan+california+australia | 1 |
| base_strict | yucatan+australia | 5 |
| base_strict | yucatan+sahel | 4 |
| base_strict | amazonia | 3 |
| base_strict | amazonia+sahel | 2 |
| base_strict | california+australia | 2 |
| base_strict | sahel | 2 |
| base_strict | yucatan+amazonia | 2 |
| base_strict | yucatan+amazonia+california | 2 |
| base_strict | yucatan+california | 2 |
| base_strict | amazonia+australia | 1 |
| base_strict | amazonia+california+sahel | 1 |
| base_strict | amazonia+japon | 1 |
| base_strict | sahel+australia | 1 |
| base_strict | yucatan | 1 |
| base_strict | yucatan+amazonia+australia | 1 |
<!-- /tabla -->

![P7: boxplot](../results/exp_figuras/p7_boxplot.png)

**Interpretación.** La mediana es la misma en los tres modos (1.0154), pero la dispersión es real: las
semillas van de 0.7154 a 1.0231 en repair. La tasa de éxito es de 23/30 (penalty), 25/30 (repair) y
24/30 (strict), con intervalos de Wilson que se solapan. Solo 2/30 semillas por modo alcanzan el óptimo
1.023077 (brecha mediana 0.007692). Las regiones Alta (Yucatán, Amazonía) se cubren en el 100 % de las
semillas en los tres modos. Las que se pierden son de prioridad Media o Normal (California, Sahel,
Japón, Australia: 90-100 %). Eso es coherente con los pesos: perder una Alta cuesta más. La tabla de
redundancia muestra **óptimos locales distintos**: la combinación del óptimo (`yucatan+amazonia`)
aparece solo en 2-3 semillas por modo, y los satélites extra caen en muchas combinaciones
(`yucatan+australia`, `yucatan+sahel`, `amazonia+japon`…). El cruce por índice y el bono pequeño
(β = 0.05) dan poca presión para mover la redundancia hacia las regiones Alta.

**Fallos y efecto sobre la validez.** Entre 5 y 7 semillas de cada 30 **no cumplen el criterio de
suficiencia** (no cubren 6/6), aunque todas son válidas. La peor (repair, semilla 68, 0.715385) deja sin
cubrir Sahel y Japón (fila de `exp_runs/base.csv`), pero tiene redundancia en las dos regiones Alta. Una sola ejecución no basta para garantizar una solución suficiente. Con estos
parámetros conviene ejecutar varias semillas y quedarse con la mejor, o usar una población mayor
(P10).

## 4. Pruebas propias

### P8 · penalty vs repair vs strict

**Condiciones.** Las 90 ejecuciones base de P2-P7 (mismas semillas en los tres modos). Para cada modo:
éxito con IC de Wilson, aptitud penalty mediana y media, finales válidas, generación mediana en la que
el mejor es 6/6 y válido, y la diferencia de medianas frente a penalty con IC bootstrap al 95 %.
La comparación en `reducido` e `inviable`, donde las restricciones sí muerden, está **bloqueada por 1D
(escenario no disponible)**.

<!-- tabla:p8_modos -->
| escenario | modo | éxito [IC 95 %] | aptitud penalty mediana | media | válidas | gen 6/6 válida mediana | Δ mediana vs penalty [IC bootstrap 95 %] |
|---|---|---|---|---|---|---|---|
| base | penalty | 23/30 [0.59, 0.88] | 1.0154 | 0.9864 | 30/30 | 24.0 | — |
| base | repair | 25/30 [0.66, 0.93] | 1.0154 | 0.9868 | 30/30 | 26.0 | +0.0000 [-0.0038, +0.0077] |
| base | strict | 24/30 [0.63, 0.90] | 1.0154 | 0.9944 | 30/30 | 24.0 | +0.0000 [-0.0038, +0.0058] |
<!-- /tabla -->

**Interpretación.** En el escenario base **los tres modos son equivalentes**: las tres medianas valen
1.0154, los IC bootstrap de la diferencia contienen 0 (repair − penalty: [-0.0038, +0.0077];
strict − penalty: [-0.0038, +0.0058]), los intervalos de Wilson del éxito se solapan y las 30/30
finales son válidas en los tres. La velocidad también es parecida: el mejor es 6/6 válido en la
generación mediana 24.0 (penalty, strict) y 26.0 (repair). Era lo esperable, porque las restricciones
no están activas en el óptimo base (P3). El manejo de restricciones solo cambia la fase inicial: con
repair no hay inválidos (P2). La pregunta de qué modo conviene cuando la restricción muerde queda
pendiente de `reducido`/`inviable`.

**Fallos y efecto sobre la validez.** Ninguno. Una diferencia real menor que ≈ 0.008 no se distinguiría
con 30 semillas (ancho de los IC).

### P9 · Sensibilidad al footprint

**Condiciones.** Copias en memoria de base con F ∈ {5, 7.5, 10, 12.5, 15, 20}° (id `base_f<F>`), modo
repair, 100 generaciones (P = 100), 30 semillas. F = 5 coincide con `footprint_chico` (§4.6) y F = 20
supera el umbral trivial de 18.2° (§4.5). El óptimo 1.023077 solo es oráculo para F = 5 y F = 10 (§10).

<!-- tabla:p9_footprint -->
| F (°) | config | gens | éxito [IC 95 %] | aptitud mediana | mín | máx | = 1.023077 | gen 6/6 válida med. | best gen 0 (media) | regiones redundantes (media) |
|---|---|---|---|---|---|---|---|---|---|---|
| 5.0 | base_f5_repair | 100 | 10/30 [0.19, 0.51] | 0.9346 | 0.7692 | 1.0115 | 0/30 | 50.0 | 0.2360 | 0.57 |
| 7.5 | base_f7_5_repair | 100 | 22/30 [0.56, 0.86] | 1.0096 | 0.8538 | 1.0231 | 1/30 | 36.5 | 0.2970 | 1.43 |
| 10.0 | base_f10_repair | 100 | 25/30 [0.66, 0.93] | 1.0115 | 0.7154 | 1.0231 | 2/30 | 26.0 | 0.3670 | 1.70 |
| 12.5 | base_f12_5_repair | 100 | 27/30 [0.74, 0.97] | 1.0192 | 0.9462 | 1.0231 | 4/30 | 19.0 | 0.4358 | 1.83 |
| 15.0 | base_f15_repair | 100 | 26/30 [0.70, 0.95] | 1.0192 | 0.8577 | 1.0231 | 10/30 | 16.5 | 0.5056 | 2.10 |
| 20.0 | base_f20_repair | 100 | 30/30 [0.89, 1.00] | 1.0346 | 1.0269 | 1.0385 | 0/30 | 10.0 | 0.6702 | 3.63 |
<!-- /tabla -->

![P9: footprint](../results/exp_figuras/p9_footprint.png)

**Interpretación.** La dificultad depende mucho de F. Con F = 5 el éxito cae a 10/30 [0.19, 0.51] y
ninguna semilla alcanza 1.023077: cubrir completa exige d ≤ 2.3°, y la señal de la aptitud es muy
escasa (mejor de la generación 0: 0.2360 de media). Entre F = 7.5 y 15 el éxito sube de 22/30 a
26-27/30 y llegar a 6/6 válida cuesta cada vez menos (mediana de la generación 36.5 → 16.5). Con F = 20
se cumple 30/30 y la aptitud mínima ya es 1.0269, **por encima del óptimo de F = 10**: un satélite
cubre dos regiones (Yucatán-California), sobran satélites y la redundancia media sube a 3.63 regiones.
El problema se trivializa, como anticipa el contrato. La columna "= 1.023077" vale 0/30 en F = 20
porque allí el máximo es mayor (máx. observado 1.0385), no porque falle. F = 10 queda en la zona
intermedia: no es trivial y tampoco es imposible. Con 100 generaciones logra el mismo éxito (25/30) que
con 200 en P7, otra señal de que la segunda mitad de las generaciones aporta poco.

**Fallos y efecto sobre la validez.** En F = 5, 20/30 ejecuciones no cumplen el criterio de suficiencia:
el `footprint_chico` es difícil para estos parámetros. Es una limitación del AG, no un error. Todas
las soluciones siguen siendo válidas (0 violaciones).

### P10 · Sensibilidad al tamaño de población (presupuesto fijo)

**Condiciones.** Base, repair, 30 semillas, P ∈ {20, 50, 100, 200} con gens = 20 000 / P, de modo que
P·(gens + 1) ≈ 20 100 evaluaciones en todas. El `--bench` proyectó menos de 30 min con 16 procesos, así
que **no se aplicó la regla de corte** del presupuesto (§1.4 del plan). La configuración P = 100 es la
misma que `base_repair` (mismas semillas y resultados idénticos: 25/30 en ambas tablas).

<!-- tabla:p10_poblacion -->
| P | gens | evaluaciones | éxito [IC 95 %] | aptitud mediana | IQR | óptimo alcanzado | gen_99 med. | diversidad final media (°) |
|---|---|---|---|---|---|---|---|---|
| 20 | 1000 | 20020 | 5/30 [0.07, 0.34] | 0.8538 | 0.7279–0.8654 | 0/30 | 135.0 | 5.36 |
| 50 | 400 | 20050 | 15/30 [0.33, 0.67] | 0.9788 | 0.8654–1.0154 | 6/30 | 46.5 | 6.56 |
| 100 | 200 | 20100 | 25/30 [0.66, 0.93] | 1.0154 | 1.0077–1.0192 | 2/30 | 33.5 | 7.34 |
| 200 | 100 | 20200 | 30/30 [0.89, 1.00] | 1.0192 | 1.0163–1.0231 | 9/30 | 31.5 | 7.95 |
<!-- /tabla -->

![P10: población](../results/exp_figuras/p10_poblacion.png)

**Interpretación.** A presupuesto fijo, **más población y menos generaciones es mejor**: el éxito sube de
5/30 (P = 20, 1000 generaciones) a 15/30, 25/30 y **30/30 con P = 200** (100 generaciones), y P = 200
alcanza el óptimo en 9/30 semillas, frente a 2/30 con P = 100. Con P = 20 el AG converge pronto a un
óptimo local (diversidad final media 5.36°) y 1000 generaciones no lo sacan de ahí. La diversidad final
crece con P (5.36° → 7.95°). La curva mediana frente a evaluaciones muestra que P = 200 empieza más
lento pero termina más alto. El `DEFAULT_PARAMS` del contrato (100 × 200) queda en el lado explotador:
para la misma cantidad de cómputo, 200 × 100 da soluciones suficientes con mayor fiabilidad.

**Fallos y efecto sobre la validez.** Con P = 20 solo 5/30 ejecuciones son suficientes. No es un
error, pero sí la razón principal de las fallas de P7: la convergencia prematura. Todas las
soluciones son válidas.

### P11 · Revalidación base → escenarios derivados

**Bloqueada por 1D (escenario no disponible).** No existe ninguno de los 5 escenarios derivados.

**Condiciones (implementadas, sin ejecutar).** `revalidate(exp_json/base_repair_s42.json, scenarios/<d>.json)`
para d ∈ {reducido, inviable, prioridad_cambiada, menos_sats, footprint_chico}, sin reoptimizar. Se
escribe `results/exp_reval/reval_base_repair_s42__<d>.json` y la tabla `p11_revalidacion`.

**Criterio (coherencia con §4.6).** `prioridad_cambiada`: `still_valid = true` (solo cambian pesos) y la
aptitud cambia. `menos_sats`: `still_valid = false` con razón `n_sats: 8 != 4`. `inviable`: el satélite de
Yucatán cae dentro de `bloqueo_yucatan`, así que `still_valid = false` con violaciones. `reducido`:
depende de si algún satélite queda dentro de las zonas agrandadas o nuevas. `footprint_chico`: sigue
válida pero pierde regiones (`lost_regions` no vacío), porque cubrir completa exige d ≤ 2.3°.

## 5. Hallazgos transversales

1. **Las restricciones no están activas en el óptimo base** (contrato §4.5). Actúan durante la búsqueda
   (20.0 de 100 inválidos en la generación 0, P3), pero las soluciones finales quedan a 18.42-18.94° de
   la zona más cercana (margen mediano). Por eso P3, P4 y P8 en base muestran 0 violaciones en todos los
   modos y modos equivalentes. La evidencia con restricción activa dependía de `reducido` e `inviable`
   (bloqueados por 1D).
2. **El AG es claramente mejor que el azar** (30/30 semillas, P2), pero **no es fiable en una sola
   ejecución**: entre 23/30 y 25/30 de éxito según el modo, y solo 2/30 llegan al óptimo (P7). La causa
   dominante es la convergencia prematura: los dos satélites extra se quedan en regiones de prioridad baja
   o en ninguna, y el bono β = 0.05 da poca presión para moverlos (P1, tabla de redundancia de P7). A
   igual presupuesto, una población mayor lo corrige (P10: 30/30 con P = 200).
3. **Que la curva se aplane no prueba optimalidad.** Las medianas se estancan en 1.0154 desde la
   generación 100 (P2), por debajo del óptimo 1.023077. Los oráculos de §10 y la brecha son lo que
   permite afirmarlo.
4. **Limitaciones del modelo** que se notan en los datos (para 4A): la cobertura de una región es la del
   mejor satélite (máximo, §5.2), así que dos satélites parciales no suman. La penalización cuenta
   violaciones y no mide su profundidad. El cruce por índice trata los satélites como una lista ordenada
   aunque son un conjunto, y con F ≥ 18.2° el problema se vuelve trivial (P9).
5. **Rendimiento (hallazgo de cómputo).** Medido con `--bench` en un solo proceso: una ejecución
   100 × 200 tarda 9.5 s (penalty), 16.1 s (repair) y 14.2 s (strict) (tabla de tiempos). El plan
   estimaba 3-6 s. El cuello de botella es `model.violations`, que recorre satélites y zonas en un bucle
   escalar de Python y se llama en cada evaluación de aptitud y en `stats_fn`. No se optimizó aquí
   (pertenece a `src/`); queda como propuesta para su dueño (1A). La campaña completa compartió la
   máquina con otros procesos que usaban casi toda la CPU, así que los tiempos de reloj de la tabla son
   pesimistas (ver la nota de la sección 1).
6. **Reproducibilidad verificada.** Las 20 ejecuciones representativas se re-ejecutaron y coincidieron
   bit a bit (si no, el programa aborta con código 3). `base_repair_s42` coincide con el resultado de la
   Ola 2 aunque se generó con otra versión de numpy (P1). La campaña P = 100 de P10 reproduce
   `base_repair` de P7.

Resultados completos representativos (validados por `tests/test_contract.py`):

<!-- tabla:representativas -->
| archivo | config | semilla | rol | aptitud penalty |
|---|---|---|---|---|
| `exp_json/base_penalty_s45.json` | base_penalty | 45 | worst | 0.857692 |
| `exp_json/base_penalty_s48.json` | base_penalty | 48 | median | 1.015385 |
| `exp_json/base_penalty_s50.json` | base_penalty | 50 | best | 1.023077 |
| `exp_json/base_repair_s42.json` | base_repair | 42 | p1 | 1.007692 |
| `exp_json/base_repair_s53.json` | base_repair | 53 | best | 1.023077 |
| `exp_json/base_repair_s68.json` | base_repair | 68 | worst | 0.715385 |
| `exp_json/base_repair_s69.json` | base_repair | 69 | median | 1.015385 |
| `exp_json/base_strict_s45.json` | base_strict | 45 | worst | 0.857692 |
| `exp_json/base_strict_s48.json` | base_strict | 48 | median | 1.015385 |
| `exp_json/base_strict_s50.json` | base_strict | 50 | best | 1.023077 |
| `exp_json/base_f5_repair_s49.json` | base_f5_repair | 49 | median | 0.934615 |
| `exp_json/base_f7_5_repair_s43.json` | base_f7_5_repair | 43 | median | 1.011538 |
| `exp_json/base_f10_repair_s65.json` | base_f10_repair | 65 | median | 1.011538 |
| `exp_json/base_f12_5_repair_s44.json` | base_f12_5_repair | 44 | median | 1.019231 |
| `exp_json/base_f15_repair_s59.json` | base_f15_repair | 59 | median | 1.019231 |
| `exp_json/base_f20_repair_s70.json` | base_f20_repair | 70 | median | 1.034615 |
| `exp_json/base_p20_repair_s48.json` | base_p20_repair | 48 | median | 0.853846 |
| `exp_json/base_p50_repair_s47.json` | base_p50_repair | 47 | median | 1.003846 |
| `exp_json/base_p100_repair_s69.json` | base_p100_repair | 69 | median | 1.015385 |
| `exp_json/base_p200_repair_s63.json` | base_p200_repair | 63 | median | 1.019231 |
<!-- /tabla -->
