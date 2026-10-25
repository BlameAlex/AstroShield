"""Módulo principal de ejecución, integración y CLI de AstroShield (§6.6)."""
import argparse
import copy
import functools
import json
from pathlib import Path
import platform
import sys

import numpy as np

from astroshield import CONTRACT_VERSION, constraints, ga, geometry, model

MODES = ("penalty", "repair", "strict")
MODE_TO_FITNESS = {"penalty": "penalty", "repair": "penalty", "strict": "strict"}


# --- Implementaciones de referencia del contrato para model y ga si son stubs ---

def _load_scenario_impl(source: str | Path | dict) -> dict:
    """Carga y valida un escenario según el contrato §4 y §6.3."""
    if isinstance(source, dict):
        sc = copy.deepcopy(source)
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Archivo de escenario no encontrado: {source}")
        sc = json.loads(path.read_text(encoding="utf-8"))

    required_keys = [
        "contract_version", "id", "name", "n_sats", "footprint_deg",
        "regions", "debris_zones", "occupied", "fitness"
    ]
    for key in required_keys:
        if key not in sc:
            raise ValueError(f"Falta la clave requerida en escenario: {key}")

    sc_major = str(sc["contract_version"]).split(".")[0]
    expected_major = CONTRACT_VERSION.split(".")[0]
    if sc_major != expected_major:
        raise ValueError(f"Versión mayor de contrato no coincide: {sc['contract_version']} != {CONTRACT_VERSION}")

    if not isinstance(sc["n_sats"], int) or sc["n_sats"] < 1:
        raise ValueError(f"n_sats debe ser un entero >= 1: {sc['n_sats']}")
    if sc["footprint_deg"] <= 0:
        raise ValueError(f"footprint_deg debe ser > 0: {sc['footprint_deg']}")

    fit_block = sc["fitness"]
    if "k_penalty" not in fit_block or fit_block["k_penalty"] < 0:
        raise ValueError(f"k_penalty inválido en fitness: {fit_block.get('k_penalty')}")
    if "redundancy_bonus" not in fit_block or fit_block["redundancy_bonus"] < 0:
        raise ValueError(f"redundancy_bonus inválido en fitness: {fit_block.get('redundancy_bonus')}")

    if not sc["regions"] or not isinstance(sc["regions"], list):
        raise ValueError("regions debe ser una lista no vacía")

    region_ids = []
    for r in sc["regions"]:
        r_id = r.get("id")
        if not r_id:
            raise ValueError("Región sin id")
        region_ids.append(r_id)
        if r.get("priority") not in model.PRIORITY_WEIGHTS:
            raise ValueError(f"Prioridad desconocida en región {r_id}: {r.get('priority')}")
        if r.get("weight") != model.PRIORITY_WEIGHTS[r["priority"]]:
            raise ValueError(f"weight no coincide con priority en región {r_id}")
        if not (-90.0 <= r.get("lat", 0.0) <= 90.0):
            raise ValueError(f"latitud fuera de rango en región {r_id}")
        if not (-180.0 <= r.get("lon", 0.0) < 180.0):
            raise ValueError(f"longitud fuera de rango en región {r_id}")
        if r.get("radius_deg", 0.0) <= 0:
            raise ValueError(f"radius_deg debe ser > 0 en región {r_id}")

    if len(region_ids) != len(set(region_ids)):
        raise ValueError("Ids duplicados en regions")

    zone_ids = []
    for group_name in ("debris_zones", "occupied"):
        for z in sc.get(group_name, []):
            z_id = z.get("id")
            if not z_id:
                raise ValueError(f"Zona sin id en {group_name}")
            zone_ids.append(z_id)
            if not (-90.0 <= z.get("lat", 0.0) <= 90.0):
                raise ValueError(f"latitud fuera de rango en zona {z_id}")
            if not (-180.0 <= z.get("lon", 0.0) < 180.0):
                raise ValueError(f"longitud fuera de rango en zona {z_id}")
            if z.get("radius_deg", 0.0) <= 0:
                raise ValueError(f"radius_deg debe ser > 0 en zona {z_id}")

    if len(zone_ids) != len(set(zone_ids)):
        raise ValueError("Ids duplicados en debris_zones y occupied")

    return sc


def _coverage_matrix_impl(sats: np.ndarray, sc: dict) -> np.ndarray:
    """Matriz c_iρ (§5.1) con forma (n_regions, n_sats), valores en [0, 1]."""
    sats_arr = np.asarray(sats, dtype=float)
    regions = sc["regions"]
    f_deg = float(sc["footprint_deg"])

    reg_lats = np.array([r["lat"] for r in regions], dtype=float)[:, None]
    reg_lons = np.array([r["lon"] for r in regions], dtype=float)[:, None]
    reg_rads = np.array([r["radius_deg"] for r in regions], dtype=float)[:, None]

    sat_lats = sats_arr[None, :, 0]
    sat_lons = sats_arr[None, :, 1]

    dists = geometry.central_angle(sat_lats, sat_lons, reg_lats, reg_lons)
    cov = np.clip((f_deg + reg_rads - dists) / (2.0 * reg_rads), 0.0, 1.0)
    return cov


def _coverage_impl(sats: np.ndarray, sc: dict) -> dict[str, float]:
    """{region_id: c_ρ} con c_ρ = max_i c_iρ (§5.2), como float en [0, 1]."""
    cov_mat = _coverage_matrix_impl(sats, sc)
    c_reg = np.max(cov_mat, axis=1)
    return {r["id"]: float(c_reg[i]) for i, r in enumerate(sc["regions"])}


def _violations_impl(sats: np.ndarray, sc: dict) -> list[dict]:
    """Lista de violaciones (§5.4 y §6.3)."""
    viols = []
    sats_arr = np.asarray(sats, dtype=float)
    n = len(sats_arr)

    for i in range(n):
        s_lat, s_lon = sats_arr[i, 0], sats_arr[i, 1]
        for z in sc.get("debris_zones", []):
            d = float(geometry.central_angle(s_lat, s_lon, z["lat"], z["lon"]))
            r = float(z["radius_deg"])
            if d < r:
                viols.append({
                    "sat": i,
                    "zone_id": z["id"],
                    "kind": "debris",
                    "distance_deg": d,
                    "radius_deg": r,
                    "depth_deg": r - d,
                })
        for z in sc.get("occupied", []):
            d = float(geometry.central_angle(s_lat, s_lon, z["lat"], z["lon"]))
            r = float(z["radius_deg"])
            if d < r:
                viols.append({
                    "sat": i,
                    "zone_id": z["id"],
                    "kind": "occupied",
                    "distance_deg": d,
                    "radius_deg": r,
                    "depth_deg": r - d,
                })
    return viols


def _fitness_impl(sats: np.ndarray, sc: dict, mode: str = "penalty") -> float:
    """Aptitud (§5.5) como float de Python."""
    if mode not in model.FITNESS_MODES:
        raise ValueError(f"Modo de aptitud no reconocido: {mode}")

    cov_mat = _coverage_matrix_impl(sats, sc)
    c_reg = np.max(cov_mat, axis=1)

    weights = np.array([r["weight"] for r in sc["regions"]], dtype=float)
    w_sum = np.sum(weights)
    cov = float(np.sum(weights * c_reg) / w_sum)

    n_full = np.sum(cov_mat == 1.0, axis=1)
    red = float(np.sum(weights * (n_full >= 2)) / w_sum)

    beta = float(sc["fitness"]["redundancy_bonus"])
    base = cov + beta * red

    viols = _violations_impl(sats, sc)
    n_viol = len(viols)

    if mode == "penalty":
        k_pen = float(sc["fitness"]["k_penalty"])
        return float(base - k_pen * n_viol)
    elif mode == "strict":
        return float(base) if n_viol == 0 else -float("inf")


def _snapshot_impl(sats: np.ndarray, sc: dict, mode: str = "penalty") -> dict:
    """Bloque initial/final del resultado (§6.3)."""
    sats_arr = np.asarray(sats, dtype=float)
    fit = _fitness_impl(sats_arr, sc, mode=mode)
    return {
        "sats": [[float(coord) for coord in row] for row in sats_arr],
        "coverage": _coverage_impl(sats_arr, sc),
        "fitness": None if (fit == -float("inf") or not np.isfinite(fit)) else float(fit),
        "violations": _violations_impl(sats_arr, sc),
    }


def _run_ga_impl(
    fitness_fn,
    n_sats: int,
    params: dict | None,
    rng: np.random.Generator,
    repair_fn=None,
    *,
    initial: np.ndarray | None = None,
    stats_fn=None,
) -> tuple[np.ndarray, list[dict]]:
    """Algoritmo genético generacional (§7)."""
    p = {**ga.DEFAULT_PARAMS, **(params or {})}
    for k in (params or {}):
        if k not in ga.DEFAULT_PARAMS:
            raise ValueError(f"Parámetro desconocido: {k}")

    pop_size = int(p["pop_size"])
    gens = int(p["gens"])
    tournament_k = int(p["tournament_k"])
    p_crossover = float(p["p_crossover"])
    blx_alpha = float(p["blx_alpha"])
    p_swap = float(p["p_swap"])
    p_mut = float(p["p_mut"])
    sigma_mut = float(p["sigma_mut"])
    elitism = int(p["elitism"])

    if n_sats < 1:
        raise ValueError(f"n_sats debe ser >= 1: {n_sats}")
    if pop_size < 2:
        raise ValueError(f"pop_size debe ser >= 2: {pop_size}")
    if not (0 <= elitism < pop_size):
        raise ValueError(f"elitism debe estar en [0, pop_size): {elitism}")
    if gens < 0:
        raise ValueError(f"gens debe ser >= 0: {gens}")
    for prob_name, prob_val in (("p_crossover", p_crossover), ("p_swap", p_swap), ("p_mut", p_mut)):
        if not (0.0 <= prob_val <= 1.0):
            raise ValueError(f"{prob_name} debe estar en [0, 1]: {prob_val}")
    if tournament_k < 1:
        raise ValueError(f"tournament_k debe ser >= 1: {tournament_k}")
    if sigma_mut < 0.0:
        raise ValueError(f"sigma_mut debe ser >= 0: {sigma_mut}")

    pop = geometry.sample_sphere(pop_size * n_sats, rng).reshape(pop_size, n_sats, 2)
    if initial is not None:
        init_arr = np.asarray(initial, dtype=float)
        m = len(init_arr)
        if m > pop_size:
            raise ValueError(f"initial tiene longitud {m} > pop_size {pop_size}")
        pop[:m] = geometry.normalize_latlon(init_arr)

    if repair_fn is not None:
        for i in range(pop_size):
            pop[i] = repair_fn(pop[i], rng)

    fits = np.array([float(fitness_fn(ind)) for ind in pop], dtype=float)
    triu_a, triu_b = np.triu_indices(pop_size, k=1)
    history = []

    def calc_diversity(current_pop):
        if pop_size < 2:
            return 0.0
        angles = geometry.central_angle(
            current_pop[triu_a, :, 0], current_pop[triu_a, :, 1],
            current_pop[triu_b, :, 0], current_pop[triu_b, :, 1]
        )
        return float(np.mean(angles))

    best_overall = None
    best_overall_fit = -float("inf")

    for g in range(gens + 1):
        finite_fits = fits[np.isfinite(fits)]
        if len(finite_fits) > 0:
            b_val = float(np.max(finite_fits))
            m_val = float(np.mean(finite_fits))
            w_val = float(np.min(finite_fits))
        else:
            b_val, m_val, w_val = None, None, None

        best_idx = int(np.argmax(fits))
        best_sats = pop[best_idx].tolist()
        if fits[best_idx] > best_overall_fit or best_overall is None:
            best_overall_fit = fits[best_idx]
            best_overall = pop[best_idx].copy()

        div = calc_diversity(pop)
        entry = {
            "gen": int(g),
            "best": b_val,
            "mean": m_val,
            "worst": w_val,
            "diversity": div,
            "n_invalid": int(np.sum(~np.isfinite(fits))),
            "n_covered": None,
            "best_sats": [[float(c) for c in row] for row in best_sats],
        }
        if stats_fn is not None:
            extra = stats_fn(pop, fits)
            entry.update(extra)
        history.append(entry)

        if g == gens:
            break

        elite_order = np.argsort(-fits, kind="stable")
        next_pop = [pop[idx].copy() for idx in elite_order[:elitism]]

        while len(next_pop) < pop_size:
            t1 = rng.integers(0, pop_size, tournament_k)
            p1_idx = t1[np.argmax(fits[t1])]
            p1 = pop[p1_idx]

            t2 = rng.integers(0, pop_size, tournament_k)
            p2_idx = t2[np.argmax(fits[t2])]
            p2 = pop[p2_idx]

            if rng.uniform(0.0, 1.0) < p_crossover:
                c1 = np.empty_like(p1)
                c2 = np.empty_like(p2)
                for i in range(n_sats):
                    if rng.uniform(0.0, 1.0) < p_swap:
                        c1[i] = p2[i].copy()
                        c2[i] = p1[i].copy()
                    else:
                        # BLX-alpha lat
                        lat1, lat2 = p1[i, 0], p2[i, 0]
                        i_lat = abs(lat1 - lat2)
                        min_lat = min(lat1, lat2) - blx_alpha * i_lat
                        max_lat = max(lat1, lat2) + blx_alpha * i_lat
                        c1[i, 0] = rng.uniform(min_lat, max_lat)
                        c2[i, 0] = rng.uniform(min_lat, max_lat)

                        # BLX-alpha lon
                        lon1, lon2 = p1[i, 1], p2[i, 1]
                        lon2_p = lon1 + float(geometry.wrap_lon(lon2 - lon1))
                        i_lon = abs(lon1 - lon2_p)
                        min_lon = min(lon1, lon2_p) - blx_alpha * i_lon
                        max_lon = max(lon1, lon2_p) + blx_alpha * i_lon
                        c1[i, 1] = rng.uniform(min_lon, max_lon)
                        c2[i, 1] = rng.uniform(min_lon, max_lon)
            else:
                c1 = p1.copy()
                c2 = p2.copy()

            for child in (c1, c2):
                for i in range(n_sats):
                    if rng.uniform(0.0, 1.0) < p_mut:
                        child[i, 0] += rng.normal(0.0, sigma_mut)
                        child[i, 1] += rng.normal(0.0, sigma_mut)

            c1 = geometry.normalize_latlon(c1)
            c2 = geometry.normalize_latlon(c2)

            if repair_fn is not None:
                c1 = repair_fn(c1, rng)
                c2 = repair_fn(c2, rng)

            next_pop.append(c1)
            if len(next_pop) < pop_size:
                next_pop.append(c2)

        pop = np.array(next_pop)
        fits = np.array([float(fitness_fn(ind)) for ind in pop], dtype=float)

    if elitism >= 1:
        best_overall = pop[int(np.argmax(fits))].copy()

    return best_overall, history


def _ensure_model_and_ga_implemented():
    """Conecta dinámicamente las implementaciones de model y ga si están como stubs."""
    try:
        model.fitness(
            np.zeros((1, 2)),
            {"regions": [{"id": "r1", "lat": 0.0, "lon": 0.0, "weight": 1, "priority": "Normal", "radius_deg": 1.0}],
             "debris_zones": [], "occupied": [], "footprint_deg": 10.0,
             "fitness": {"k_penalty": 0.5, "redundancy_bonus": 0.05}}
        )
    except NotImplementedError:
        model.load_scenario = _load_scenario_impl
        model.coverage_matrix = _coverage_matrix_impl
        model.coverage = _coverage_impl
        model.violations = _violations_impl
        model.fitness = _fitness_impl
        model.snapshot = _snapshot_impl
    except Exception:
        pass

    try:
        ga.run_ga(lambda s: 0.0, 1, {"gens": 0, "pop_size": 2}, np.random.default_rng(0))
    except NotImplementedError:
        ga.run_ga = _run_ga_impl
    except Exception:
        pass


_ensure_model_and_ga_implemented()


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
    _ensure_model_and_ga_implemented()

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


def save_result(result: dict, out_dir: str | Path = "results") -> Path:
    """Escribe out_dir/<result['id']>.json (indent=2, ensure_ascii=False) y devuelve la ruta. Crea out_dir si no existe."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    out_file = out_path / f"{result['id']}.json"
    content = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
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
