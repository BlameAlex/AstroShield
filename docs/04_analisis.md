# Análisis de resultados

> Contrato vigente: `docs/contratos.md` v1.0.2. Cada cifra cita entre paréntesis el archivo de `results/` o del contrato de donde sale. Los óptimos se rotulan como **oráculo analítico** (contrato §10) y los valores de §4.5 como **valor de planeación**. No se usa `results/mock.json` como evidencia (es sintético).

## Resumen

- **Corrida canónica** (`base`, `repair`, semilla 42): válida, 6/6 regiones cubiertas, aptitud 1.007692 frente al oráculo analítico 1.023077, brecha 0.015385 (`results/exp_tablas/p1_config.md`).
- **Fiabilidad en 30 semillas**: cumplen el criterio "válida y 6/6" 23/30 (penalty), 25/30 (repair) y 24/30 (strict); solo 2/30 por modo alcanzan el óptimo (`results/exp_tablas/p7_variacion.md`).
- **El AG supera a la búsqueda aleatoria** de igual presupuesto en 30/30 semillas en los tres modos; la aleatoria nunca cubre 6/6 (0/30) (`results/exp_tablas/p2_resumen.md`).
- **Restricciones**: 0 violaciones finales en las 90 ejecuciones base, pero actúan durante la búsqueda: 20.0 de 100 individuos inválidos en la generación 0 en penalty y strict (`results/exp_tablas/p3_violaciones.md`). En el óptimo base no están activas (contrato §4.5).
- **Modos equivalentes en `base`**: medianas iguales (1.0154) y diferencias con IC que contienen 0 (`results/exp_tablas/p8_modos.md`).
- **Sensibilidades**: con F = 5° el éxito cae a 10/30; con población 200 sube a 30/30 a igual presupuesto (`results/exp_tablas/p9_footprint.md`, `results/exp_tablas/p10_poblacion.md`).
- **Pendiente**: no hay campañas de 30 semillas para `reducido` ni `inviable` en `results/` (ver P4 y P5).

## Fuentes de datos

| Prueba | Archivos | Comando que los regenera |
|---|---|---|
| Configuración final (P1) | `results/exp_tablas/p1_config.md`, `results/exp_json/base_repair_s42.json` | `python experiments/run_experiments.py --all --jobs 16` |
| Evolución (P2) | `results/exp_tablas/p2_resumen.md`, `results/exp_figuras/p2_*.png` | ídem |
| Zonas y ocupadas (P3, P4) | `results/exp_tablas/p3_violaciones.md`, `p4_violaciones.md`, `results/exp_figuras/p3_mapa_finales.png` | ídem |
| Variación (P7) | `results/exp_tablas/p7_variacion.md`, `p7_redundancia.md`, `regiones_cubiertas.md`, `results/exp_figuras/p7_boxplot.png` | ídem |
| Modos (P8) | `results/exp_tablas/p8_modos.md` | ídem |
| Footprint y población (P9, P10) | `results/exp_tablas/p9_footprint.md`, `p10_poblacion.md`, figuras `p9_*`, `p10_*` | ídem |
| Revalidación y reoptimización | `results/reval_base_repair_s42__*.json`, `results/inviable_repair_s42_from_base_repair_s42.json` | `python -m astroshield.revalidate --result results/base_repair_s42.json --scenario scenarios/inviable.json --out <carpeta>` |

Las tablas se insertan en `docs/03_pruebas.md` con `python experiments/report.py`. La numeración `p1..p10` de esos archivos es la de las pruebas de `docs/03_pruebas.md`, no la de las preguntas de este documento.

## P1. ¿Qué tan bien se observan las regiones solicitadas en la configuración final?

### Respuesta corta

En la corrida canónica la configuración final es válida, cubre por completo las 6 regiones y no tiene violaciones; su aptitud es 1.007692, a 0.015385 del oráculo analítico (1.023077, brecha relativa ≈ 1.5 %). En 30 semillas, el 77 % (penalty), 83 % (repair) y 80 % (strict) de las ejecuciones cubren las 6 regiones siendo válidas.

### Evidencia

Corrida canónica (`results/exp_tablas/p1_config.md`, `results/exp_json/base_repair_s42.json`):

| Región | Prioridad | Cobertura inicial | Cobertura final |
|---|---|---|---|
| Yucatán | Alta | 0.000000 | 1.000000 |
| Amazonía | Alta | 1.000000 | 1.000000 |
| California | Media | 1.000000 | 1.000000 |
| Sahel | Media | 0.000000 | 1.000000 |
| Japón | Media | 0.502017 | 1.000000 |
| Australia | Normal | 0.000000 | 1.000000 |

| Medida | Valor | Fuente |
|---|---|---|
| Válida / cubiertas / violaciones | sí / 6 de 6 / 0 | `p1_config.md` |
| Aptitud inicial (mejor de la generación 0) | 0.461849 | `p1_config.md` |
| Aptitud final | 1.007692 | `p1_config.md` |
| Óptimo | 1.023077 | oráculo analítico, contrato §10 |
| Brecha absoluta / relativa | 0.015385 / ≈ 1.5 % | `p1_config.md` / cálculo derivado |

Reparto de satélites: uno propio para Australia, Amazonía, Japón, Yucatán y California; dos para Sahel (satélites 3 y 6); el satélite 4, en (−74.802, −55.991), no cubre ninguna región (`p1_config.md`). La corrida reproduce la de la Ola 2 (`results/base_repair_s42.json`) aunque se generó con otra versión de numpy.

Porcentaje de las 30 semillas en que cada región queda cubierta por completo (`results/exp_tablas/regiones_cubiertas.md`):

| Configuración | Yucatán | Amazonía | California | Sahel | Japón | Australia |
|---|---|---|---|---|---|---|
| base_penalty | 100 % | 100 % | 97 % | 93 % | 93 % | 93 % |
| base_repair | 100 % | 100 % | 97 % | 97 % | 90 % | 93 % |
| base_strict | 100 % | 100 % | 100 % | 93 % | 97 % | 90 % |

Ejecuciones válidas con 6/6 (`results/exp_tablas/p7_variacion.md`): penalty 23/30 [IC Wilson 0.59–0.88], repair 25/30 [0.66–0.93], strict 24/30 [0.63–0.90].

Figura: [inicial frente a final](../results/exp_figuras/p1_mapa.png).

### Interpretación

La corrida cumple el criterio de "suficientemente buena" (válida y 6/6, contrato §10). Cada región tiene su propio satélite, como exige la geometría: ningún par de regiones cabe en un footprint de 10° (contrato §4.5).

La brecha de 0.015385 sale entera del bono de redundancia (β = 0.05, Σw = 13). La solución duplica solo Sahel (peso 2): 0.05 · 2/13 = 0.007692, que es lo que excede a 1.0. El óptimo duplica Yucatán y Amazonía (pesos 3 + 3): 0.05 · 6/13 = 0.023077. La diferencia, 0.05 · 4/13 = 0.015385, coincide con la brecha medida (cálculo derivado). El satélite 4 está desperdiciado: pudo ser el segundo satélite de una región Alta.

Las regiones Alta (Yucatán, Amazonía) se cubren en el 100 % de las semillas en los tres modos; las fallas están en regiones Media y Normal, coherente con los pesos 3/2/1.

En el escenario base las restricciones no están activas en el óptimo: la región más cercana a una zona (Australia) está a 18.76° del borde de `objeto_b` y basta estar a 7.3° del centro de una región para cubrirla (contrato §4.5, valor de planeación).

### Límites

- La corrida canónica es una sola semilla; la fiabilidad se juzga con las 30 semillas.
- "Cubierta" significa cobertura exactamente 1.0 (contrato §2): 0.99 cuenta como no cubierta.
- La cobertura combina satélites con el máximo y la parcial es lineal (contrato §5.1 y §5.2); 0.502 en Japón es una aproximación, no un área medida.
- La brecha se compara con un óptimo analítico, no con una búsqueda exhaustiva.

## P2. ¿Cómo cambió la calidad de la solución durante el proceso evolutivo?

### Respuesta corta

La mediana del mejor individuo pasó de 0.36–0.37 en la generación 0 a 1.0154 en la 200, superó 1.0 (6/6 cubiertas) entre las generaciones 25 y 50 y alcanzó el 99 % de su valor final hacia la generación 33. Después se aplana por debajo del óptimo. El AG superó a la búsqueda aleatoria en 30/30 semillas.

### Evidencia

Mediana del mejor entre 30 semillas (`results/exp_tablas/p2_resumen.md`):

| Configuración | g0 | g10 | g25 | g50 | g100 | g200 | gen_99 med. | gen 6/6 válida med. |
|---|---|---|---|---|---|---|---|---|
| base_penalty | 0.3577 | 0.7627 | 0.9538 | 1.0077 | 1.0115 | 1.0154 | 33.0 | 24.0 |
| base_repair | 0.3726 | 0.7692 | 0.9773 | 1.0077 | 1.0115 | 1.0154 | 33.5 | 26.0 |
| base_strict | 0.3577 | 0.7627 | 0.9807 | 1.0096 | 1.0115 | 1.0154 | 33.0 | 24.0 |

Búsqueda aleatoria con el mismo presupuesto (20 100 configuraciones por semilla, penalty): máximo mediano 0.6154, mejor de las 30 semillas 0.7692, media de la media −0.0481, media del percentil 95 0.2308, éxito 6/6 en 0/30 (`p2_resumen.md`). Valores de planeación del contrato §4.5 (Monte Carlo de 20 000 configuraciones): media −0.047, p95 0.231, máximo 0.615; coinciden con lo medido.

Inválidos en la generación 0: 20.0 de 100 en penalty y strict, 0.0 en repair (`results/exp_tablas/p3_violaciones.md`). El contrato §4.5 predice ≈ 20 %.

Figuras: [curvas de aptitud](../results/exp_figuras/p2_curvas_base.png), [diversidad](../results/exp_figuras/p2_diversidad.png), [inválidos](../results/exp_figuras/p2_invalidos.png).

### Interpretación

- **Mejora real, no azar**: el AG gana a la aleatoria en 30/30 semillas y esta nunca llega a 6/6.
- **Elitismo**: con `elitism = 2` el mejor es no decreciente por construcción (contrato §9.2, invariante 3), por eso las curvas del mejor solo suben o se aplanan.
- **Fase rápida y meseta**: casi todo el avance ocurre antes de la generación ~50; de la 100 a la 200 la mediana apenas pasa de 1.0115 a 1.0154.
- **Diversidad**: cae de forma monótona (`p2_diversidad.png`) y la población converge. Es consistente con la meseta: con poca diversidad, el cruce y la mutación (σ = 5°, del orden de los 7.3° del casquete útil, contrato §8) ya no producen cambios que mejoren. Que la mutación y el cruce por intercambio o BLX sean los responsables es una interpretación de diseño; las pruebas hechas no aíslan cada operador.
- **Repair**: elimina los inválidos de la generación 0 porque repara la población inicial, pero no acelera de forma apreciable (6/6 válida en la generación mediana 26.0 frente a 24.0).

### Límites

- Aplanarse no prueba optimalidad: la mediana final (1.0154) está por debajo de 1.023077. Solo el oráculo permite afirmarlo.
- Las curvas son medianas entre semillas; una ejecución individual puede mejorar a saltos o estancarse antes.
- No se hicieron experimentos que varíen un operador a la vez (cruce, mutación, selección).

## P3. ¿Qué diferencias se encontraron entre distintas ejecuciones?

### Respuesta corta

Hay mucha variación entre semillas aunque la mediana sea la misma: la aptitud final va de 0.7154 a 1.0231 en repair, y solo 2/30 ejecuciones por modo alcanzan el óptimo. Entre 5 y 7 de cada 30 ejecuciones no logran 6/6, aunque todas son válidas.

### Evidencia

Aptitud final (penalty), 30 semillas por modo (`results/exp_tablas/p7_variacion.md`):

| Configuración | Media | Desv. est. | Mediana | IQR | Mín | Máx | Éxito [IC Wilson 95 %] |
|---|---|---|---|---|---|---|---|
| base_penalty | 0.9864 | 0.0581 | 1.0154 | 1.0077–1.0192 | 0.8577 | 1.0231 | 23/30 [0.59, 0.88] |
| base_repair | 0.9868 | 0.0743 | 1.0154 | 1.0077–1.0192 | 0.7154 | 1.0231 | 25/30 [0.66, 0.93] |
| base_strict | 0.9944 | 0.0484 | 1.0154 | 1.0087–1.0192 | 0.8577 | 1.0231 | 24/30 [0.63, 0.90] |

Brecha frente al óptimo (`p7_variacion.md`): alcanzan el óptimo 2/30 en cada modo; brecha mediana 0.007692; brecha máxima 0.165385 (penalty y strict) y 0.307692 (repair).

Dónde cae la redundancia (`results/exp_tablas/p7_redundancia.md`): la combinación del óptimo, Yucatán + Amazonía, aparece en 2 semillas en penalty, 3 en repair y 2 en strict; los satélites extra caen en muchas otras combinaciones (por ejemplo Yucatán + Australia en 5 semillas de penalty y de strict, Yucatán + Sahel en 4 de repair y de strict).

Figura: [boxplot de aptitud final](../results/exp_figuras/p7_boxplot.png).

### Interpretación

- Las medianas coinciden (1.0154) y los IC de Wilson del éxito se solapan, así que no hay un modo claramente más estable. Strict tiene la menor desviación (0.0484), pero con 30 semillas esa diferencia no es concluyente.
- La peor ejecución (repair, semilla 68, 0.715385) deja Sahel y Japón sin cubrir. Se explica con la fórmula: (3 + 3 + 2 + 1)/13 + 0.05 · 6/13 = 0.7154, es decir, 4 regiones cubiertas y redundancia en las dos Alta (cálculo derivado).
- Hay óptimos locales distintos. El bono de redundancia es pequeño (β = 0.05) y da poca presión para mover los satélites sobrantes hacia las regiones Alta; el cruce por índice trata los satélites como una lista ordenada aunque son un conjunto (contrato §3).
- Las regiones perdidas son de prioridad Media o Normal, nunca Alta (`regiones_cubiertas.md`).

### Límites

- Con 30 semillas, diferencias menores que ≈ 0.008 de aptitud no se distinguen (ancho de los IC bootstrap en `p8_modos.md`).
- Todas las semillas son las mismas en los tres modos (números aleatorios comunes), lo que reduce la varianza de las comparaciones pero no la de cada modo.
- La causa de las fallas (convergencia prematura, ver P6 y la prueba de población) es una interpretación apoyada en la prueba de población, no un resultado aislado.

## P4. ¿Qué efecto tuvieron las restricciones espaciales sobre la solución?

### Respuesta corta

En el escenario base, ninguno sobre la solución final: 0 violaciones en las 90 ejecuciones. Sí actúan durante la búsqueda: 20.0 de 100 individuos son inválidos en la generación 0 en penalty y strict. El efecto sobre soluciones finales con restricciones activas (`reducido`, `inviable`) no se puede cuantificar con campañas de 30 semillas porque no existen en `results/`.

### Evidencia

Violaciones finales y márgenes en `base`, 30 semillas por modo (`results/exp_tablas/p3_violaciones.md` y `p4_violaciones.md`, idénticas en las columnas comunes porque el margen se calcula sobre todas las zonas):

| Configuración | Violaciones finales (desechos / ocupadas) | Ejecuciones con ≥ 1 | Inválidos gen 0 (media de 100) | Margen mínimo mediano (°) | Margen mínimo menor (°) |
|---|---|---|---|---|---|
| base_penalty | 0 / 0 | 0 | 20.0 | 18.50 | 7.12 |
| base_repair | 0 / 0 | 0 | 0.0 | 18.94 | 0.25 |
| base_strict | 0 / 0 | 0 | 20.0 | 18.42 | 7.12 |

Margen = `d(satélite, centro de la zona) − radio de la zona`, el mínimo sobre todos los satélites y zonas (`docs/03_pruebas.md`, P3). Negativo sería una violación; cercano a 0, una restricción activa.

Valor de planeación (contrato §4.5): la región más cercana a una zona es Australia, a 18.76° del borde de `objeto_b`; basta estar a 7.3° del centro para cubrir completa una región. Penalización K = 0.5 > 3/13 + β = 0.281 (contrato §4.3).

Figura: [satélites finales sobre zonas y objetos](../results/exp_figuras/p3_mapa_finales.png).

**Revalidación y reoptimización con escenarios derivados** (archivos existentes en `results/`):

> **PENDIENTE (completar con la salida de la revalidación):** pegar aquí, por cada archivo `results/reval_base_repair_s42__<escenario>.json` (reducido, inviable, menos_sats, footprint_chico, prioridad_cambiada), los valores `still_valid`, `reasons`, `fitness_before`, `fitness_after`, `lost_regions` y `gained_regions`.

### Interpretación

- El margen mediano de las soluciones finales (18.42–18.94°) es casi el del contrato (18.76°): las zonas no estorban a las regiones en el óptimo base.
- Por eso los tres modos son equivalentes en `base` (ver la comparación de modos en `p8_modos.md`: medianas iguales y diferencias con IC que contienen 0). Penalty no necesita reparar porque ninguna violación "se paga" con cobertura (K > 3/13 + β).
- El margen más pequeño observado (0.25° en repair) es esperable: `repair` coloca los satélites movidos a radio + 0.5° del centro de la zona (contrato §6.5). En esa semilla las 6 regiones siguen cubiertas (`docs/03_pruebas.md`, P3).
- Las restricciones sí moldean la búsqueda: con penalty y strict nacen ≈ 20 % de individuos inválidos y el AG los descarta; con repair nacen todos válidos.

### Límites

- Esta evidencia no prueba que el AG maneje bien una restricción **activa**: en `base` no lo está. Las campañas de 30 semillas para `reducido` e `inviable` están descritas en `docs/03_pruebas.md` (P5, P6) como bloqueadas por la falta de escenarios al momento de ejecutarlas; los escenarios ya existen en `scenarios/`, pero no se ejecutaron y no hay tablas de ellas.
- El criterio de "restricción activa" que planteó la prueba (mediana del margen < 1° en `reducido`) no se verificó.

## P5. ¿Qué sucede cuando el sistema no puede satisfacer todas las condiciones?

### Respuesta corta

Por diseño del escenario `inviable`, cubrir Yucatán es imposible sin violar una zona, así que el mejor resultado válido cubre 5 de 6 regiones. El óptimo analítico de ese escenario es 0.796154 y el AG no debería "comprar" Yucatán con una violación porque la penalización es mayor que la ganancia. Los números reales de ejecuciones sobre `inviable` están pendientes de completar.

### Evidencia

- **Oráculo analítico** (contrato v1.0.2 §4.6 y §10): `bloqueo_yucatan` de radio 13.0° > F + r = 12.7°, así que todo punto desde el que se vería Yucatán está prohibido. Óptimo válido = (13 − 3)/13 + 0.05 · 7/13 = 0.796154, con 5 regiones cubiertas y 3 satélites sobrantes.
- **Por qué no conviene violar**: cubrir Yucatán aportaría como máximo 3/13 = 0.231 y cada violación cuesta K = 0.5 (contrato §4.3: K > 3/13 + β = 0.281).
- Reoptimización existente: `results/inviable_repair_s42_from_base_repair_s42.json`.

> **PENDIENTE (completar con los números reales):** de `results/inviable_repair_s42_from_base_repair_s42.json` indicar `valid`, `final.fitness`, `final.coverage.yucatan` y número de violaciones finales; de `results/reval_base_repair_s42__inviable.json` indicar `still_valid`, `reasons` y `lost_regions`. Comparar `final.fitness` con 0.796154.

### Interpretación

- Cuando el escenario no admite 6/6, el criterio de "suficientemente buena" (válida y 6/6) no se puede cumplir. Eso es un resultado esperable del problema, no un error del sistema.
- La solución base revalidada contra `inviable` deja de ser válida si el satélite de Yucatán cae dentro de `bloqueo_yucatan`; reoptimizar la reubica fuera de la zona a costa de perder Yucatán (se confirma con los números pendientes de arriba).
- El sistema distingue "inviable en cobertura" de "inviable en colocación": colocar satélites sin violar siempre es posible (contrato §6.5), lo imposible es cubrir Yucatán.

### Límites

- `docs/03_pruebas.md` cita como óptimo de `inviable` el valor 0.788462, tomado del contrato v1.0.1. El contrato vigente v1.0.2 lo corrige a 0.796154 (sobran 3 satélites, no 2). Este documento usa 0.796154.
- No existe campaña de 30 semillas sobre `inviable`; con una sola reoptimización (semilla 42) no se puede hablar de tasas.

## P6. ¿Qué limitaciones tiene el criterio utilizado para evaluar las configuraciones?

### Respuesta corta

El criterio es simple y reproducible, pero tiene seis límites verificables: cobertura combinada con el máximo, cobertura parcial lineal, éxito binario que no distingue la redundancia, penalización que cuenta violaciones sin medir su profundidad, pesos arbitrarios y un modelo geométrico sin órbitas ni tiempo. Además es sensible al footprint y al tamaño de población.

### Evidencia

| Limitación | Dato que la respalda |
|---|---|
| Cobertura por máximo, no por unión de áreas (contrato §5.2) | Dos satélites parciales sobre una región no suman |
| Cobertura parcial lineal (contrato §5.1) | 0.502 en Japón en la configuración inicial es una aproximación |
| Éxito binario "válida y 6/6" | La corrida canónica (1.007692) y la óptima (1.023077) cuentan igual como éxito (`p1_config.md`, `p7_variacion.md`) |
| La redundancia pesa poco (β = 0.05) | La combinación óptima Yucatán + Amazonía aparece en 2–3 de 30 semillas por modo (`p7_redundancia.md`) |
| Penalización por conteo, sin profundidad | Una violación leve cuesta K = 0.5 igual que una profunda (contrato §5.5); no hay gradiente para salir de una zona |
| Cruce y diversidad por índice | Los satélites son un conjunto no ordenado, el cruce los trata como lista (contrato §3) |
| Pesos 3/2/1 y β = 0.05 elegidos por diseño | El contrato los justifica con cotas (β < 1/13, K > 0.281), pero no se probaron otros valores |
| Sin altitud, órbitas ni tiempo | Un satélite es un punto subsatelital fijo (contrato §3) |
| Sensible al footprint | F = 5° → éxito 10/30 [0.19, 0.51], ninguna semilla llega a 1.023077; F = 20° → 30/30, pero el óptimo sube y el problema se trivializa, con aptitud máxima 1.0385 (`results/exp_tablas/p9_footprint.md`) |
| Sensible al tamaño de población | A igual presupuesto: P = 20 → 5/30; P = 100 → 25/30; P = 200 → 30/30 (`results/exp_tablas/p10_poblacion.md`) |

Figuras: [footprint](../results/exp_figuras/p9_footprint.png), [población](../results/exp_figuras/p10_poblacion.png).

### Interpretación

- El criterio de suficiencia mide si se cubre, no si se cubre bien: la diferencia entre 1.0077 y 1.0231 (solo redundancia) no cambia el veredicto.
- Los oráculos del contrato son válidos para F < 18.2° (contrato §10). Con F = 20° el valor 1.023077 deja de ser cota superior, y por eso en `p9_footprint.md` la columna "= 1.023077" vale 0/30 aunque el desempeño sea el mejor.
- Los parámetros por defecto (100 × 200) quedan del lado explotador: para el mismo cómputo, más población y menos generaciones da más éxito.

### Límites

- Las limitaciones de diseño (primeras seis filas) se apoyan en el contrato, no en un experimento que las aísle; solo la sensibilidad al footprint y a la población se midió.
- No se comparó este criterio con otro criterio alternativo de cobertura.

## P7. ¿Qué evidencia permite afirmar que una solución es mejor que otra?

### Respuesta corta

Se compara en este orden: primero la validez (sin violaciones y con el número correcto de satélites), después que cubra las 6 regiones, después la aptitud y por último la brecha frente al oráculo analítico. Para comparar métodos no basta una corrida: se usan las 30 semillas con medianas, intervalos y conteos de éxito.

### Evidencia

- **Entre dos corridas reales** (`results/exp_tablas/representativas.md`, todas en repair salvo indicación): la semilla 53 alcanza 1.023077 (el óptimo: 6/6 y redundancia en Yucatán y Amazonía); la semilla 42 llega a 1.007692 (6/6, redundancia solo en Sahel); la semilla 68 queda en 0.715385 (4 de 6 regiones, sin Sahel ni Japón). Las tres son válidas. Lo que las distingue es cuántas regiones cubren y dónde queda la redundancia.
- **Entre modos** (`results/exp_tablas/p8_modos.md`): diferencia de medianas frente a penalty +0.0000 [−0.0038, +0.0077] en repair y +0.0000 [−0.0038, +0.0058] en strict (IC bootstrap 95 %). No hay evidencia de que un modo sea mejor en `base`.
- **Entre tamaños de población** (`results/exp_tablas/p10_poblacion.md`): P = 200 tiene mediana 1.0192 (IQR 1.0163–1.0231) y alcanza el óptimo en 9/30; P = 100, mediana 1.0154 (IQR 1.0077–1.0192) y 2/30; P = 20, mediana 0.8538 y 0/30. Los éxitos de P = 20 [0.07, 0.34] y P = 200 [0.89, 1.00] no se solapan.
- **Entre AG y azar** (`p2_resumen.md`): el AG gana en 30/30 semillas; la aleatoria no logra 6/6 en ninguna.

### Interpretación

- Una solución es mejor si es válida, cubre más regiones o más peso, y no tiene menos aptitud; con empate, la que cubre redundancia en regiones Alta.
- Para afirmar que un **método** es mejor hace falta que los intervalos no se solapen o que haya una diferencia de medianas con IC que excluya el 0. P = 200 frente a P = 20 cumple; P = 200 frente a P = 100 solo está apoyada por la mediana, el IQR y el conteo de óptimos, porque sus IC de éxito sí se solapan (0.89–0.93).
- Las cifras de una solución se pueden recomputar desde `final.sats` con el modelo (contrato §9.2, invariante 7), de modo que la comparación no depende de lo que cada programa reporta.

### Límites

- Una sola corrida (por ejemplo la semilla 42) no sustenta afirmaciones sobre métodos.
- La aptitud depende de pesos y β elegidos por diseño; un orden distinto de prioridades podría reordenar las soluciones (el escenario `prioridad_cambiada` existe, pero no hay campaña sobre él).
- Con 30 semillas no se distinguen diferencias de aptitud menores que ≈ 0.008.
