"""Stub del contrato (§6.4): firmas y constantes; lo implementa 1B."""
from typing import Callable
import numpy as np

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
    raise NotImplementedError
