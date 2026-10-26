# AstroShield

Algoritmo evolutivo para diseñar una constelación de 8 satélites que observe seis regiones de la Tierra, respetando zonas de desechos espaciales y posiciones ocupadas, con visualización en un globo 3D.

## Requisitos

- Python ≥ 3.11 (numpy; matplotlib solo para los experimentos).
- Navegador moderno para la visualización. Node ≥ 18 solo si se quieren correr las pruebas de `viz/`.

## Instalación

```bash
python -m venv .venv
. .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -e ".[dev,exp]"
```

## Ejecutar el algoritmo

```bash
python run.py --scenario scenarios/base.json --gens 200 --seed 42 --mode repair --out results/
```

- `--scenario`: ruta a un escenario de `scenarios/` (`base`, `reducido`, `inviable`, `prioridad_cambiada`, `menos_sats`, `footprint_chico`).
- `--mode`: tratamiento de restricciones. `penalty` resta K = 0.5 por violación, `repair` mueve los satélites fuera de las zonas y `strict` descarta toda configuración inválida.
- Opcionales: `--pop` (tamaño de población), `--params` (JSON con hiperparámetros) e `--id` (nombre del resultado).

Genera `results/<escenario>_<modo>_s<semilla>.json` con la configuración inicial (mejor de la generación 0), la final, sus coberturas y violaciones, y el historial por generación. Si la mejor solución viola alguna restricción, el resultado queda marcado con `"valid": false`. Una ejecución de 200 generaciones con población 100 tarda entre 10 y 20 s.

## Ver la constelación en 3D

```bash
python -m http.server 8000        # desde la raíz del repositorio
```

Abrir `http://localhost:8000/viz/` y elegir un resultado en el desplegable, o pasar uno con `?file=`:
`http://localhost:8000/viz/?file=../results/base_repair_s42.json`.

El globo muestra las regiones (cubiertas, parciales y sin cubrir), los satélites con su área de cobertura, las zonas de desechos y los objetos ocupados. Permite comparar la configuración inicial con la final y reproducir la evolución generación por generación. Detalles en [`viz/README.md`](viz/README.md).

## Cambio de condiciones

Revalida una solución previa contra un escenario nuevo y, opcionalmente, vuelve a optimizar sembrando la población con ella:

```bash
python -m astroshield.revalidate --result results/base_repair_s42.json --scenario scenarios/inviable.json --out results/
python -m astroshield.revalidate --result results/base_repair_s42.json --scenario scenarios/inviable.json --reoptimize --gens 200 --mode repair --out results/
```

El reporte indica si la solución sigue siendo válida, la aptitud antes y después y las regiones que se pierden.

## Pruebas

```bash
pytest                     # modelo, algoritmo, restricciones, CLI, revalidación y contrato
pytest experiments         # pruebas de la campaña de experimentos
node --test viz/tests/     # visualización (opcional)
```

## Experimentos (Entregable 3)

```bash
python experiments/run_experiments.py --quick --only base --out /tmp/astro   # prueba rápida, 3 semillas, fuera del repo
python experiments/run_experiments.py --only reducido,inviable --jobs 8
python experiments/run_experiments.py --all --jobs 16                 # campaña completa
python experiments/run_experiments.py --tables                        # regenera tablas y figuras desde exp_runs/
python experiments/report.py --check                                  # comprueba que docs/03_pruebas.md esté sincronizado
```

Sin `--out` escriben en `results/exp_*` y reemplazan los datos versionados; usar `--out` para pruebas. Con 16 procesos, `reducido` e `inviable` (180 ejecuciones) tardan unos 8 min; `--all` se estima en unos 20 min. `--bench` proyecta el tiempo antes de lanzar. `--verify` vuelve a ejecutar y compara hashes, pero la igualdad bit a bit solo está garantizada con la misma versión de numpy con que se generaron los datos (ver `results/exp_meta/entorno.txt`).

## Documentación

- [`docs/enunciado.md`](docs/enunciado.md): planteamiento del proyecto.
- [`docs/contratos.md`](docs/contratos.md): contrato técnico (formatos, firmas, fórmulas, esquemas y oráculos), versión 1.0.2.
- [`docs/01_definicion.md`](docs/01_definicion.md): Entregable 1, definición del problema.
- [`docs/03_pruebas.md`](docs/03_pruebas.md): Entregable 3, pruebas y validación.

## Estructura

```
src/astroshield/   geometría, modelo, algoritmo genético, restricciones, CLI y revalidación
run.py             lanzador de la CLI
tests/             pruebas (pytest)
schemas/           esquemas JSON de escenario y resultado
scenarios/         escenario base y derivados
results/           resultados de ejecuciones, revalidaciones y experimentos (exp_*)
experiments/       campañas, análisis, figuras y su documento
viz/               visualización 3D (globe.gl)
docs/              documentación y entregables
```

Estado: Olas 0 a 3 integradas. Falta la Ola 4: análisis de resultados (`docs/04_analisis.md`) y declaración de uso de IA (`docs/uso_ia.md`).
