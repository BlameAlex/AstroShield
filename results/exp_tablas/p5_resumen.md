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
