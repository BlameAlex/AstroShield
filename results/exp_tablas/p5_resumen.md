| modo | margen mín. mediano reducido (°) | margen mín. mediano base (°) | restricción activa (< 1° vs > 10°) | éxito reducido [IC 95 %] | éxito base | aptitud mediana reducido | aptitud mediana base | caída de la mediana | violaciones finales | 0 violaciones (repair/strict) |
|---|---|---|---|---|---|---|---|---|---|---|
| penalty | 4.46 | 18.50 | FALLA | 24/30 [0.63, 0.90] | 23/30 | 1.0096 | 1.0154 | 0.0058 | 0 | — |
| repair | 1.53 | 18.94 | FALLA | 27/30 [0.74, 0.97] | 25/30 | 1.0173 | 1.0154 | -0.0019 | 0 | PASA |
| strict | 4.05 | 18.42 | FALLA | 27/30 [0.74, 0.97] | 24/30 | 1.0135 | 1.0154 | 0.0019 | 0 | PASA |

| config | n | media | sd | mediana | IQR | mín | máx | éxito k/n [IC Wilson 95 %] |
|---|---|---|---|---|---|---|---|---|
| reducido_penalty | 30 | 0.9940 | 0.0431 | 1.0096 | 1.0038–1.0154 | 0.8538 | 1.0231 | 24/30 [0.63, 0.90] |
| reducido_repair | 30 | 1.0051 | 0.0384 | 1.0173 | 1.0125–1.0192 | 0.8692 | 1.0231 | 27/30 [0.74, 0.97] |
| reducido_strict | 30 | 1.0050 | 0.0318 | 1.0135 | 1.0115–1.0192 | 0.8731 | 1.0231 | 27/30 [0.74, 0.97] |

| config | alcanzan el óptimo (brecha < 1e-6) | brecha mediana | brecha máx. |
|---|---|---|---|
| reducido_penalty | 3/30 | 0.013462 | 0.169231 |
| reducido_repair | 3/30 | 0.005769 | 0.153846 |
| reducido_strict | 4/30 | 0.009615 | 0.150000 |
