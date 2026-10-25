"""Algoritmo genético generacional (§6.4, §7)."""
from typing import Callable
import numpy as np

from astroshield import geometry

DEFAULT_PARAMS: dict = {
    "pop_size": 100, "gens": 200, "tournament_k": 3, "p_crossover": 0.9,
    "blx_alpha": 0.5, "p_swap": 0.5, "p_mut": 0.2, "sigma_mut": 5.0,
    "elitism": 2, "seed": None,
}

FitnessFn = Callable[[np.ndarray], float]                         # sats (n,2) -> float (puede ser -inf)
RepairFn = Callable[[np.ndarray, np.random.Generator], np.ndarray]  # sats -> sats nuevo
StatsFn = Callable[[np.ndarray, np.ndarray], dict]                # (pop (P,n,2), fits (P,)) -> dict


def run_ga(
    fitness_fn: FitnessFn,
    n_sats: int,
    params: dict | None,
    rng: np.random.Generator,
    repair_fn: RepairFn | None = None,
    *,
    initial: np.ndarray | None = None,
    stats_fn: StatsFn | None = None,
) -> tuple[np.ndarray, list[dict]]:
    """Algoritmo genético generacional que maximiza fitness_fn.

    params: se combina con DEFAULT_PARAMS. Una clave desconocida lanza ValueError.
      "seed" se acepta y se ignora: la aleatoriedad viene SOLO de rng.
    initial: array opcional (m, n_sats, 2) con m <= pop_size. Reemplaza a los primeros m individuos
      de la población inicial (se normaliza y, si hay repair_fn, se repara).
    stats_fn: si se da, su dict se combina con cada entrada de history (puede sobrescribir n_invalid).
      run.py lo usa para n_invalid, n_covered, best_coverage y best_n_violations.
    No importa model.py. Sí puede importar geometry.py.

    Algoritmo (§7). Devuelve (best, history):
      best: (n_sats, 2), el mejor individuo visto en toda la ejecución (con elitism >= 1 coincide
            con history[-1]["best_sats"]).
      history: lista de longitud gens + 1 (gen 0 = población inicial ya reparada). Cada entrada es
        {"gen": int, "best": float|None, "mean": float|None, "worst": float|None,
         "diversity": float, "n_invalid": int, "n_covered": int|None,
         "best_sats": list[list[float]]} + lo que añada stats_fn.
        best/mean/worst se calculan solo sobre aptitudes finitas; si no hay ninguna, valen None.
        Sin stats_fn: n_invalid = número de aptitudes no finitas; n_covered = None.
    Pre: n_sats >= 1; pop_size >= 2; 0 <= elitism < pop_size; gens >= 0; probabilidades en [0, 1];
      tournament_k >= 1; sigma_mut >= 0. Si no se cumple, lanza ValueError.
    Post: misma semilla y mismos argumentos ⇒ best e history idénticos.
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    for k in (params or {}):
        if k not in DEFAULT_PARAMS:
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
