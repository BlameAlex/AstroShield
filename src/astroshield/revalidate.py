"""Stub del contrato (§6.7): firmas y constantes; lo implementa 2C."""
from pathlib import Path
import numpy as np


def revalidate(result: dict | str | Path, new_scenario: dict | str | Path) -> dict:
    """Evalúa la solución final de un resultado bajo un escenario nuevo, sin optimizar.

    El escenario de antes es result["scenario"] (va embebido). Las aptitudes se calculan SIEMPRE en
    modo penalty, para que sean finitas y comparables.
    Devuelve:
      {"contract_version": str, "result_id": str, "old_scenario_id": str, "new_scenario_id": str,
       "still_valid": bool,                 # sin violaciones nuevas y con n_sats correcto
       "reasons": list[str],                # p. ej. ["violations: 2", "n_sats: 8 != 4"]; [] si sigue siendo válida
       "violations": list[dict],            # bajo el escenario nuevo, con el formato de §6.3
       "fitness_before": float, "fitness_after": float,
       "coverage_before": dict[str, float], "coverage_after": dict[str, float],
       "lost_regions": list[str],           # cubiertas (==1.0) antes y no cubiertas después
       "gained_regions": list[str]}
    """
    raise NotImplementedError


def reoptimize(result: dict | str | Path, new_scenario: dict | str | Path, mode: str | None = None,
               params: dict | None = None, seed: int = 42, run_id: str | None = None) -> dict:
    """Vuelve a optimizar sembrando la población con la solución anterior.

    Llama a run.run(new_scenario, mode or result["mode"], params, seed, run_id,
    initial=prev[None, ...]), donde prev es result["final"]["sats"] adaptado a n_sats:
    si n_sats nuevo < anterior, toma un subconjunto greedy por mayor aporte a la cobertura ponderada;
    si es mayor, completa con sample_sphere. run_id por defecto: f"{new_id}_{mode}_s{seed}_from_{result_id}".
    Devuelve un dict con result.schema.json.
    """
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    """python -m astroshield.revalidate --result results/X.json --scenario scenarios/Y.json
         [--reoptimize --gens N --seed S --mode M] [--out results/]
    Escribe results/reval_<result_id>__<new_scenario_id>.json y, con --reoptimize, también el nuevo resultado.
    """
    raise NotImplementedError
