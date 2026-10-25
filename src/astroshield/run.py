"""Stub del contrato (§6.6): firmas y constantes; lo implementa 2A."""
from pathlib import Path
import numpy as np

MODES = ("penalty", "repair", "strict")
MODE_TO_FITNESS = {"penalty": "penalty", "repair": "penalty", "strict": "strict"}


def run(scenario: str | Path | dict, mode: str = "penalty", params: dict | None = None,
        seed: int = 42, run_id: str | None = None,
        initial: np.ndarray | None = None) -> dict:
    """Ejecuta el AG y devuelve un dict que cumple result.schema.json (no escribe a disco).

    rng = np.random.default_rng(seed). fitness_fn = partial(model.fitness, sc=sc, mode=MODE_TO_FITNESS[mode]).
    repair_fn = (lambda s, r: constraints.repair(s, sc, r)) solo si mode == "repair".
    stats_fn calcula sobre la población: n_invalid (individuos con len(violations) > 0); y para el
      best = argmax(fits) (primer índice): n_covered (#regiones con coverage == 1.0), best_coverage y best_n_violations.
    initial = snapshot(history[0]["best_sats"]); final = snapshot(best); ambos en el modo de aptitud de la ejecución.
    valid = (len(final["violations"]) == 0) and (len(final["sats"]) == sc["n_sats"]).
    run_id por defecto: f"{sc['id']}_{mode}_s{seed}". params guardados = DEFAULT_PARAMS combinados con params, con "seed": seed.
    env = {"python": platform.python_version(), "numpy": np.__version__}.
    Raises ValueError si mode no está en MODES.
    """
    raise NotImplementedError


def save_result(result: dict, out_dir: str | Path = "results") -> Path:
    """Escribe out_dir/<result['id']>.json (indent=2, ensure_ascii=False) y devuelve la ruta. Crea out_dir si no existe."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    """CLI:
      python run.py --scenario scenarios/base.json --gens 200 --seed 42 --mode penalty|repair|strict
                    --out results/ [--pop 100] [--params params.json] [--id NOMBRE]
    Precedencia: DEFAULT_PARAMS < --params (JSON) < --gens/--pop.
    Imprime una línea: id, valid, final fitness, cubiertas k/R y la ruta.
    Código de salida 0 si la ejecución termina (aunque valid sea false); 2 en errores de argumentos o de escenario.
    """
    raise NotImplementedError
