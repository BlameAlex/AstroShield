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

Tiempo de cómputo medido en esta máquina:

<!-- tabla:tiempos -->
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

PENDIENTE

### P2 · Evolución

PENDIENTE

### P3 · Zonas de desechos

PENDIENTE

### P4 · Posiciones ocupadas

PENDIENTE

### P5 · Espacio reducido

PENDIENTE

### P6 · Escenario inviable

PENDIENTE

### P7 · Variación entre ejecuciones

PENDIENTE

## 4. Pruebas propias

### P8 · penalty vs repair vs strict

PENDIENTE

### P9 · Sensibilidad al footprint

PENDIENTE

### P10 · Sensibilidad al tamaño de población (presupuesto fijo)

PENDIENTE

### P11 · Revalidación base → escenarios derivados

PENDIENTE

## 5. Hallazgos transversales

PENDIENTE
