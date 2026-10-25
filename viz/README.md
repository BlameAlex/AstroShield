# Visualización 3D de AstroShield

Globo 3D (globe.gl 2.46.2 por CDN, versión fijada; sin npm ni bundler) que muestra un
archivo de resultado del AG (`results/**/*.json`, esquema `schemas/result.schema.json`).

## Cómo abrirla

```bash
python -m http.server 8000          # desde la raíz del repositorio
```

- `http://localhost:8000/viz/` carga `../results/mock.json` (por defecto, contrato §11).
- `http://localhost:8000/viz/?file=../results/base_repair_s42.json` carga otro resultado.
- El desplegable «Resultado» lista los `.json` de `results/` y de sus subdirectorios
  (p. ej. `results/exp_json/`), leyendo el listado HTML de `http.server`; excluye `reval_*`
  y `escenarios/`. Con otro servidor sin listado se oculta y quedan `?file=` y «Abrir JSON…».
- Un archivo sin `history[0].best_sats` (p. ej. `reval_*.json`) muestra un error legible.

## Qué muestra

- Tierra, regiones (verde = cubierta, ámbar = parcial, rojo = no cubierta, según
  `coverage`/`best_coverage` del JSON; no se recalcula), satélites con su footprint,
  zonas de desechos (⚠, naranja) y objetos ocupados (■, violeta). Satélite en magenta si viola
  una zona (solo en gen 0 y final, donde el JSON trae el detalle).
- Reproducción por generación: control deslizante, ⏮ ◀ ▶/⏸ ▶| ⏭, velocidad y teclas
  ←/→, Inicio/Fin, espacio. «Inicial» y «Final» muestran `initial` y `final`.
- Panel: datos de la ejecución, métricas de la vista, curvas mejor/media/peor (los huecos son
  −∞ en strict) y mini curvas de `n_invalid`, `n_covered` y diversidad (clic para saltar a
  una generación), detalle de violaciones.
- «Comparar con inicial»: satélites iniciales como fantasmas y arcos del sat i inicial al sat i
  actual (emparejados por índice; el contrato trata los satélites como conjunto, §3).
- Verificación dibujo ↔ JSON: lee lo que tienen las capas del globo (posición, radio y color
  de cada casquete, posición de cada satélite, zonas) y lo compara con el JSON por región.

## Código y pruebas

- `data.js`: lógica pura (conversión `[lat, lon]` → `{lat, lng}` en `toLL`, cuadros por vista,
  verificación, casquetes, listado). `app.js`: globo y controles. `panel.js`: panel.
  `style.css`: paleta propia (también la usa el globo).
- `node --test viz/tests/`: pruebas de `data.js` con `results/mock.json`, verificación cruzada
  de cobertura contra todos los resultados de `results/` y prueba de que no hay datos fijos
  del escenario en `viz/*.js`.
