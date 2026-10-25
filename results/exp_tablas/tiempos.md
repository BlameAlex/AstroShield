| campaña | ejecuciones | Σ tiempo por ejecución (s) | s por ejecución (media) | reloj total (s) | procesos |
|---|---|---|---|---|---|
| base | 90 | 10485.5 | 116.51 | — | — |
| footprint | 180 | 13913.7 | 77.30 | — | — |
| poblacion | 120 | 16828.5 | 140.24 | — | — |
| aleatoria | 30 | 1767.9 | 58.93 | — | — |
| TOTAL | 420 | 42995.5 | — | 2849.5 | 16 |
| representativas | 20 | — | — | 231.9 | 16 |
| reducido | 90 | 3809.9 | 42.33 | — | — |
| inviable | 90 | 3942.2 | 43.80 | — | — |
| TOTAL reducido+inviable | 180 | 7752.1 | — | 489.6 | 16 |
| representativas reducido+inviable | 18 | — | — | 55.0 | 16 |

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
