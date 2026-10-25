"""Módulo principal de ejecución, integración y CLI de AstroShield (§6.6)."""
import argparse
import functools
import json
from pathlib import Path
import platform
import sys

import numpy as np

from astroshield import CONTRACT_VERSION, constraints, ga, geometry, model

MODES = ("penalty", "repair", "strict")
MODE_TO_FITNESS = {"penalty": "penalty", "repair": "penalty", "strict": "strict"}


# --- API Pública de run (§6.6) --------------------------------------------

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
    if mode not in MODES:
        raise ValueError(f"Modo de ejecución no reconocido: {mode}. Debe ser uno de {MODES}")

    sc = model.load_scenario(scenario)
    rng = np.random.default_rng(seed)

    fitness_fn = functools.partial(model.fitness, sc=sc, mode=MODE_TO_FITNESS[mode])
    repair_fn = (lambda s, r: constraints.repair(s, sc, r)) if mode == "repair" else None

    # Precomputar zonas para conteo rápido de violaciones en población
    all_zones = sc.get("debris_zones", []) + sc.get("occupied", [])
    if all_zones:
        z_lats = np.array([z["lat"] for z in all_zones], dtype=float)[:, None]
        z_lons = np.array([z["lon"] for z in all_zones], dtype=float)[:, None]
        z_rads = np.array([z["radius_deg"] for z in all_zones], dtype=float)[:, None]
    else:
        z_lats, z_lons, z_rads = None, None, None

    def stats_fn(pop: np.ndarray, fits: np.ndarray) -> dict:
        best_idx = int(np.argmax(fits))
        best_ind = pop[best_idx]

        p_size, n_s, _ = pop.shape
        if z_lats is not None:
            flat_sats = pop.reshape(-1, 2)
            dists = geometry.central_angle(flat_sats[None, :, 0], flat_sats[None, :, 1], z_lats, z_lons)
            viol_mask = (dists < z_rads).any(axis=0).reshape(p_size, n_s).any(axis=1)
            n_invalid = int(np.sum(viol_mask))
        else:
            n_invalid = 0

        cov = model.coverage(best_ind, sc)
        n_covered = sum(1 for v in cov.values() if v == 1.0)
        best_n_viols = len(model.violations(best_ind, sc))

        return {
            "n_invalid": int(n_invalid),
            "n_covered": int(n_covered),
            "best_coverage": {k: float(v) for k, v in cov.items()},
            "best_n_violations": int(best_n_viols),
        }

    best, history = ga.run_ga(
        fitness_fn,
        sc["n_sats"],
        params,
        rng,
        repair_fn=repair_fn,
        initial=initial,
        stats_fn=stats_fn,
    )

    init_sats = np.array(history[0]["best_sats"], dtype=float)
    initial_snapshot = model.snapshot(init_sats, sc, mode=MODE_TO_FITNESS[mode])
    final_snapshot = model.snapshot(best, sc, mode=MODE_TO_FITNESS[mode])

    valid = bool((len(final_snapshot["violations"]) == 0) and (len(final_snapshot["sats"]) == sc["n_sats"]))
    actual_run_id = str(run_id) if run_id is not None else f"{sc['id']}_{mode}_s{seed}"

    saved_params = {**ga.DEFAULT_PARAMS, **(params or {})}
    saved_params["seed"] = int(seed)

    env = {"python": platform.python_version(), "numpy": np.__version__}

    return {
        "contract_version": CONTRACT_VERSION,
        "id": actual_run_id,
        "mode": mode,
        "seed": int(seed),
        "valid": valid,
        "env": env,
        "scenario": sc,
        "params": saved_params,
        "initial": initial_snapshot,
        "final": final_snapshot,
        "history": history,
    }


def _native(o):
    """Convierte escalares numpy (np.int64, np.float64, np.bool_) a tipos nativos para json."""
    if isinstance(o, np.generic):
        return o.item()
    raise TypeError(f"Objeto no serializable: {type(o).__name__}")


def save_result(result: dict, out_dir: str | Path = "results") -> Path:
    """Escribe out_dir/<result['id']>.json (indent=2, ensure_ascii=False) y devuelve la ruta. Crea out_dir si no existe."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    out_file = out_path / f"{result['id']}.json"
    content = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False, default=_native)
    out_file.write_text(content, encoding="utf-8")
    return out_file


def main(argv: list[str] | None = None) -> int:
    """CLI:
      python run.py --scenario scenarios/base.json --gens 200 --seed 42 --mode penalty|repair|strict
                    --out results/ [--pop 100] [--params params.json] [--id NOMBRE]
    Precedencia: DEFAULT_PARAMS < --params (JSON) < --gens/--pop.
    Imprime una línea: id, valid, final fitness, cubiertas k/R y la ruta.
    Código de salida 0 si la ejecución termina (aunque valid sea false); 2 en errores de argumentos o de escenario.
    """
    parser = argparse.ArgumentParser(description="Lanzador del algoritmo genético AstroShield.")
    parser.add_argument("--scenario", required=True, help="Ruta al archivo JSON de escenario o id.")
    parser.add_argument("--gens", type=int, default=None, help="Número de generaciones.")
    parser.add_argument("--seed", type=int, default=42, help="Semilla para el generador pseudoaleatorio.")
    parser.add_argument("--mode", choices=MODES, default="penalty", help="Modo de tratamiento de restricciones.")
    parser.add_argument("--out", default="results", help="Directorio de salida.")
    parser.add_argument("--pop", type=int, default=None, help="Tamaño de la población.")
    parser.add_argument("--params", default=None, help="Ruta a un archivo JSON con hiperparámetros.")
    parser.add_argument("--id", dest="run_id", default=None, help="Identificador de la ejecución.")

    try:
        if argv is None:
            args = parser.parse_args()
        else:
            args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2

    # Precedencia: DEFAULT_PARAMS < --params (JSON) < --gens/--pop
    params = {}
    if args.params:
        try:
            params_path = Path(args.params)
            params.update(json.loads(params_path.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"Error al cargar archivo de parámetros {args.params}: {e}", file=sys.stderr)
            return 2

    if args.gens is not None:
        params["gens"] = args.gens
    if args.pop is not None:
        params["pop_size"] = args.pop

    try:
        res = run(args.scenario, mode=args.mode, params=params, seed=args.seed, run_id=args.run_id)
        saved_file = save_result(res, out_dir=args.out)
    except Exception as e:
        print(f"Error durante la ejecución del escenario: {e}", file=sys.stderr)
        return 2

    sc = res["scenario"]
    k = sum(1 for v in res["final"]["coverage"].values() if v == 1.0)
    total_regions = len(sc["regions"])
    fit_val = res["final"]["fitness"]
    fit_str = "None" if fit_val is None else f"{fit_val:.6f}"

    print(f"{res['id']} | valid={res['valid']} | fitness={fit_str} | covered={k}/{total_regions} | {saved_file}")
    return 0
