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

_Pendiente._

## 2. Qué significa que una región esté cubierta

_Pendiente._

## 3. Calidad de una configuración y prioridades

_Pendiente._

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
