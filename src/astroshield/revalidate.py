"""Módulo de revalidación y reoptimización ante cambio de condiciones (contrato §6.7)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Union

import numpy as np

from astroshield import CONTRACT_VERSION, geometry, model, run


def _load_result(result: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
    if isinstance(result, (str, Path)):
        return json.loads(Path(result).read_text(encoding="utf-8"))
    return result


def _covered_set(cov: Dict[str, float]) -> set[str]:
    return {k for k, v in cov.items() if v == 1.0}


def revalidate(
    result: Union[str, Path, Dict[str, Any]],
    new_scenario: Union[str, Path, Dict[str, Any]],
) -> Dict[str, Any]:
    """Evalúa un resultado previo bajo un escenario nuevo sin reoptimizar."""
    res = _load_result(result)
    old_sc = model.load_scenario(res["scenario"])
    new_sc = model.load_scenario(new_scenario)

    sats = np.array(res["final"]["sats"], dtype=float)
    viols = model.violations(sats, new_sc)

    reasons: list[str] = []
    if viols:
        reasons.append(f"violations: {len(viols)}")
    if len(sats) != new_sc["n_sats"]:
        reasons.append(f"n_sats: {len(sats)} != {new_sc['n_sats']}")

    cov_before = model.coverage(sats, old_sc)
    cov_after = model.coverage(sats, new_sc)

    before_set = _covered_set(cov_before)
    after_set = _covered_set(cov_after)

    # Orden de regiones del escenario nuevo seguido de regiones viejas no presentes
    new_ids = [r["id"] for r in new_sc["regions"]]
    old_ids = [r["id"] for r in old_sc["regions"] if r["id"] not in new_ids]
    all_ids = new_ids + old_ids

    lost_regions = [r for r in all_ids if r in before_set and r not in after_set]
    gained_regions = [r for r in all_ids if r in after_set and r not in before_set]

    fit_before = model.fitness(sats, old_sc, mode="penalty")
    fit_after = model.fitness(sats, new_sc, mode="penalty")

    return {
        "contract_version": CONTRACT_VERSION,
        "result_id": res["id"],
        "old_scenario_id": old_sc["id"],
        "new_scenario_id": new_sc["id"],
        "still_valid": len(reasons) == 0,
        "reasons": reasons,
        "violations": viols,
        "fitness_before": fit_before,
        "fitness_after": fit_after,
        "coverage_before": cov_before,
        "coverage_after": cov_after,
        "lost_regions": lost_regions,
        "gained_regions": gained_regions,
    }


def _adapt_sats(
    prev: np.ndarray,
    sc: Dict[str, Any],
    rng: np.random.Generator,
) -> np.ndarray:
    """Adapta satélites anteriores al número requerido por el nuevo escenario."""
    target_n = sc["n_sats"]
    cur_n = len(prev)

    if cur_n == target_n:
        return prev.copy()

    if cur_n < target_n:
        fill = geometry.sample_sphere(target_n - cur_n, rng)
        return np.vstack([prev, fill])

    # Caso cur_n > target_n: selección greedy por cobertura ponderada acumulada
    regions = sc["regions"]
    weights = np.array([r["weight"] for r in regions], dtype=float)
    c_mat = model.coverage_matrix(prev, sc)  # Forma (R, cur_n)

    chosen: list[int] = []
    cur_cov = np.zeros(len(regions), dtype=float)

    for _ in range(target_n):
        best_j = -1
        best_gain = -1.0
        for j in range(cur_n):
            if j in chosen:
                continue
            cand_cov = np.maximum(cur_cov, c_mat[:, j])
            gain = float(weights @ cand_cov)
            if gain > best_gain:
                best_gain = gain
                best_j = j
        chosen.append(best_j)
        cur_cov = np.maximum(cur_cov, c_mat[:, best_j])

    chosen_sorted = sorted(chosen)
    return prev[chosen_sorted].copy()


def reoptimize(
    result: Union[str, Path, Dict[str, Any]],
    new_scenario: Union[str, Path, Dict[str, Any]],
    mode: str | None = None,
    params: Dict[str, Any] | None = None,
    seed: int = 42,
    run_id: str | None = None,
) -> Dict[str, Any]:
    """Reoptimiza un escenario sembrando la solución anterior adaptada."""
    res = _load_result(result)
    sc = model.load_scenario(new_scenario)
    opt_mode = mode or res["mode"]

    rng = np.random.default_rng(seed)
    prev_sats = np.array(res["final"]["sats"], dtype=float)
    adapted = _adapt_sats(prev_sats, sc, rng)

    auto_id = run_id or f"{sc['id']}_{opt_mode}_s{seed}_from_{res['id']}"

    return run.run(
        scenario=sc,
        mode=opt_mode,
        params=params,
        seed=seed,
        run_id=auto_id,
        initial=adapted[None, ...],
    )


def main(argv: list[str] | None = None) -> int:
    """CLI para revalidación y reoptimización."""
    parser = argparse.ArgumentParser(description="Revalidación y reoptimización AstroShield")
    parser.add_argument("--result", required=True, help="Ruta al archivo result.json previo")
    parser.add_argument("--scenario", required=True, help="Ruta al nuevo escenario JSON")
    parser.add_argument("--reoptimize", action="store_true", help="Ejecutar reoptimización")
    parser.add_argument("--gens", type=int, help="Número de generaciones para reoptimizar")
    parser.add_argument("--seed", type=int, default=42, help="Semilla aleatoria")
    parser.add_argument("--mode", choices=run.MODES, help="Modo de aptitud (penalty, repair, strict)")
    parser.add_argument("--out", default="results", help="Directorio de salida")

    try:
        args = parser.parse_args(argv)
        res_data = _load_result(args.result)
        sc_data = model.load_scenario(args.scenario)
    except Exception as e:
        sys.stderr.write(f"Error de entrada: {e}\n")
        return 2

    reval_res = revalidate(res_data, sc_data)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    reval_filename = f"reval_{res_data['id']}__{sc_data['id']}.json"
    reval_path = out_dir / reval_filename
    reval_path.write_text(
        json.dumps(reval_res, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    valid_str = "VÁLIDA" if reval_res["still_valid"] else "INVÁLIDA"
    print(f"Revalidación [{valid_str}]: {res_data['id']} -> {sc_data['id']}")
    print(f"  Fitness: {reval_res['fitness_before']:.6f} -> {reval_res['fitness_after']:.6f}")
    if reval_res["lost_regions"]:
        print(f"  Regiones perdidas: {reval_res['lost_regions']}")
    print(f"  Guardado en: {reval_path}")

    if args.reoptimize:
        opt_params = {}
        if args.gens is not None:
            opt_params["gens"] = args.gens

        reopt_res = reoptimize(
            result=res_data,
            new_scenario=sc_data,
            mode=args.mode,
            params=opt_params,
            seed=args.seed,
        )
        saved_opt_path = run.save_result(reopt_res, out_dir=str(out_dir))
        print(f"  Reoptimizado [{reopt_res['id']}]: valid={reopt_res['valid']} -> {saved_opt_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())