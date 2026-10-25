"""Campañas de experimentos de AstroShield (Entregable 3).

Uso:
    python experiments/run_experiments.py --bench
    python experiments/run_experiments.py --all --jobs 16
    python experiments/run_experiments.py --all --verify
    python experiments/run_experiments.py --quick --only base --out <dir>

Cada ejecución es una función pura de (escenario, modo, params, semilla): run() crea
default_rng(seed) por dentro, así que el resultado no depende de --jobs ni del orden.
"""
import argparse
import copy
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:  # mismo criterio que el shim run.py de la raíz
    sys.path.insert(0, str(ROOT / "src"))

from astroshield import model  # noqa: E402

SEEDS = list(range(42, 72))
QUICK_SEEDS = SEEDS[:3]
MODES = ("penalty", "repair", "strict")
ORACLES = {"base": 1.023077, "inviable": 0.788462, "menos_sats": 0.769231,
           "footprint_chico": 1.023077, "base_f5": 1.023077, "base_f10": 1.023077}
FOOTPRINTS = (5.0, 7.5, 10.0, 12.5, 15.0, 20.0)
POPS = (20, 50, 100, 200)
POP_BUDGET = 20000          # gens = POP_BUDGET / P  ->  P·(gens+1) ≈ 20 100 evaluaciones
FOOTPRINT_GENS = 100
RANDOM_EVALS = 20100        # mismo presupuesto que el AG por defecto: 100 · (200 + 1)
DERIVED = ("reducido", "inviable", "prioridad_cambiada", "menos_sats", "footprint_chico")
CAMPAIGNS = ("base", "reducido", "inviable", "footprint", "poblacion", "aleatoria")

# --quick: lo que corren los tests (segundos, no minutos)
QUICK_PARAMS = {"pop_size": 30, "gens": 10}
QUICK_FOOTPRINTS = (7.5,)
QUICK_POPS = (10, 30)
QUICK_POP_BUDGET = 320
QUICK_RANDOM_EVALS = 330


def scenario_path(name: str) -> Path:
    return ROOT / "scenarios" / f"{name}.json"


def footprint_variant(sc: dict, f: float) -> dict:
    """Copia en memoria de `sc` con footprint_deg = f e id base_f<F> (punto → guion bajo)."""
    v = copy.deepcopy(sc)
    v["footprint_deg"] = float(f)
    v["id"] = f"base_f{f:g}".replace(".", "_")
    return v


def _task(campaign, config, scenario, mode, params, seed):
    return {"campaign": campaign, "config": config, "scenario": scenario,
            "mode": mode, "params": dict(params), "seed": int(seed)}


def campaign_tasks(name: str, quick: bool = False) -> list[dict]:
    """Lista ordenada de tareas de una campaña. Vacía si falta el escenario derivado (1D)."""
    seeds = QUICK_SEEDS if quick else SEEDS
    ga_params = dict(QUICK_PARAMS) if quick else {}
    if name in ("base", "reducido", "inviable"):
        path = scenario_path(name)
        if not path.exists():
            return []
        sc = model.load_scenario(path)
        return [_task(name, f"{sc['id']}_{m}", sc, m, ga_params, s) for m in MODES for s in seeds]
    base = model.load_scenario(scenario_path("base"))
    if name == "footprint":
        fs = QUICK_FOOTPRINTS if quick else FOOTPRINTS
        params = ga_params if quick else {"gens": FOOTPRINT_GENS}
        out = []
        for f in fs:
            v = footprint_variant(base, f)
            out += [_task(name, f"{v['id']}_repair", v, "repair", params, s) for s in seeds]
        return out
    if name == "poblacion":
        pops, budget = (QUICK_POPS, QUICK_POP_BUDGET) if quick else (POPS, POP_BUDGET)
        out = []
        for p in pops:
            params = {"pop_size": p, "gens": budget // p}
            out += [_task(name, f"base_p{p}_repair", base, "repair", params, s) for s in seeds]
        return out
    if name == "aleatoria":
        n = QUICK_RANDOM_EVALS if quick else RANDOM_EVALS
        return [_task(name, "base_aleatoria", base, "penalty", {"n_evals": n}, s) for s in seeds]
    raise ValueError(f"campaña desconocida: {name}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Campañas de experimentos de AstroShield (Entregable 3).")
    p.add_argument("--all", action="store_true", help="ejecuta todas las campañas disponibles")
    p.add_argument("--only", default=None, help="campañas separadas por coma: " + ",".join(CAMPAIGNS))
    p.add_argument("--quick", action="store_true", help="3 semillas y presupuestos mínimos (tests)")
    p.add_argument("--bench", action="store_true", help="mide 1 ejecución por modo y proyecta el tiempo total")
    p.add_argument("--verify", action="store_true", help="re-ejecuta y compara hashes de exp_runs/*.csv")
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="procesos en paralelo")
    p.add_argument("--out", default=str(ROOT / "results"), help="directorio raíz de salida")
    return p


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
