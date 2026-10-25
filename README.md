# AstroShield

Algoritmo evolutivo para diseñar una constelación de 8 satélites que observe seis regiones de la Tierra, respetando zonas de desechos espaciales y posiciones ocupadas, con visualización en un globo 3D.

## Instalación y pruebas

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,exp]"
pytest
```

## Documentación

- [`docs/enunciado.md`](docs/enunciado.md): planteamiento del proyecto.
- [`docs/contratos.md`](docs/contratos.md): contrato técnico (formatos, firmas, fórmulas y esquemas).

## Estructura

```
src/astroshield/   geometría, modelo, algoritmo genético, restricciones, CLI y revalidación
tests/             pruebas (pytest)
schemas/           esquemas JSON de escenario y resultado
scenarios/         escenarios (base.json y derivados)
results/           resultados de las ejecuciones (mock.json de ejemplo)
docs/              documentación y entregables
```

Estado: Ola 0 (estructura y contrato). `geometry.py` está implementado; el resto de los módulos son stubs con las firmas del contrato.
