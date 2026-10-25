"""Métricas por ejecución, agregados y estadística de los experimentos (solo numpy)."""
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from astroshield import geometry, model  # noqa: E402

ORACLES = {"base": 1.023077, "inviable": 0.788462, "menos_sats": 0.769231,
           "footprint_chico": 1.023077, "base_f5": 1.023077, "base_f10": 1.023077}
CURVE_KEYS = ("best", "mean", "diversity", "n_invalid", "n_covered")


# --- Métricas por ejecución --------------------------------------------------

def gap_opt(scenario_id: str, value: float | None) -> float | None:
    """Brecha frente al óptimo teórico del contrato §10; None si no hay oráculo."""
    if value is None or scenario_id not in ORACLES:
        return None
    return float(ORACLES[scenario_id] - value)


def min_margin(sats: np.ndarray, sc: dict) -> float | None:
    """min_{i,z} (central_angle(sat_i, z) − radius_z). < 0 ⇒ violación; ≈ 0 ⇒ restricción activa."""
    zones = sc["debris_zones"] + sc["occupied"]
    if not zones:
        return None
    sats = np.asarray(sats, dtype=float)
    zl = np.array([[z["lat"], z["lon"]] for z in zones], dtype=float)
    zr = np.array([z["radius_deg"] for z in zones], dtype=float)
    d = geometry.central_angle(sats[:, None, 0], sats[:, None, 1], zl[None, :, 0], zl[None, :, 1])
    return float((d - zr[None, :]).min())


def _first_gen(history, pred) -> int | None:
    for h in history:
        if pred(h):
            return int(h["gen"])
    return None


def run_row(res: dict, task: dict) -> dict:
    """Una fila de CSV (§1.6 del plan) a partir de un resultado completo de run()."""
    sc = res["scenario"]
    regions = sc["regions"]
    ids = [r["id"] for r in regions]
    w = np.array([r["weight"] for r in regions], dtype=float)
    hist = res["history"]
    sats = np.asarray(res["final"]["sats"], dtype=float)
    cov = res["final"]["coverage"]
    fpf = model.fitness(sats, sc, "penalty")
    kinds = [v["kind"] for v in res["final"]["violations"]]
    n_full = (model.coverage_matrix(sats, sc) == 1.0).sum(axis=1)
    best_final = hist[-1]["best"]
    thr = None if best_final is None else best_final - 0.01 * abs(best_final)
    row = {
        "campaign": task["campaign"], "config": task["config"], "scenario_id": sc["id"],
        "mode": res["mode"], "seed": int(res["seed"]),
        "pop_size": int(res["params"]["pop_size"]), "gens": int(res["params"]["gens"]),
        "footprint_deg": float(sc["footprint_deg"]),
        "n_evals": int(res["params"]["pop_size"]) * (int(res["params"]["gens"]) + 1),
        "valid": bool(res["valid"]),
        "final_fitness": res["final"]["fitness"],
        "final_penalty_fitness": float(fpf),
        "cov_weighted": float(np.sum(w * np.array([cov[i] for i in ids])) / w.sum()),
        "n_covered": int(sum(1 for i in ids if cov[i] == 1.0)),
    }
    row.update({f"cov_{i}": float(cov[i]) for i in ids})
    row.update({
        "n_viol_debris": kinds.count("debris"),
        "n_viol_occupied": kinds.count("occupied"),
        "gen0_n_invalid": int(hist[0]["n_invalid"]),
        "gen0_best": hist[0]["best"],
        "gen_all_covered_valid": _first_gen(
            hist, lambda h: h["best_n_violations"] == 0 and h["n_covered"] == len(ids)),
        "gen_99": None if thr is None else _first_gen(
            hist, lambda h: h["best"] is not None and h["best"] >= thr),
        "gap_opt": gap_opt(sc["id"], fpf),
        "min_margin_deg": min_margin(sats, sc),
    })
    row.update({f"redundancy_{i}": bool(n_full[k] >= 2) for k, i in enumerate(ids)})
    return row


def random_row(task: dict, fits: np.ndarray, best_sats: np.ndarray) -> dict:
    """Fila de la búsqueda aleatoria: mismas columnas clave que run_row donde tienen sentido."""
    sc = task["scenario"]
    ids = [r["id"] for r in sc["regions"]]
    w = np.array([r["weight"] for r in sc["regions"]], dtype=float)
    cov = model.coverage(best_sats, sc)
    kinds = [v["kind"] for v in model.violations(best_sats, sc)]
    row = {
        "campaign": task["campaign"], "config": task["config"], "scenario_id": sc["id"],
        "mode": task["mode"], "seed": int(task["seed"]), "n_evals": int(len(fits)),
        "valid": not kinds,
        "final_penalty_fitness": float(fits.max()),
        "fit_mean": float(fits.mean()), "fit_p95": float(np.percentile(fits, 95)),
        "frac_negative": float(np.mean(fits < 0)),
        "cov_weighted": float(np.sum(w * np.array([cov[i] for i in ids])) / w.sum()),
        "n_covered": int(sum(1 for i in ids if cov[i] == 1.0)),
        "n_viol_debris": kinds.count("debris"), "n_viol_occupied": kinds.count("occupied"),
        "gap_opt": gap_opt(sc["id"], float(fits.max())),
    }
    return row


def random_curves(fits: np.ndarray, step: int) -> dict:
    """Mejor-hasta-ahora y media por bloques de `step` evaluaciones (≈ una generación del AG)."""
    n = (len(fits) // step) * step
    blocks = fits[:n].reshape(-1, step)
    return {"best": [float(v) for v in np.maximum.accumulate(blocks.max(axis=1))],
            "mean": [float(v) for v in blocks.mean(axis=1)]}


def run_curves(res: dict) -> dict:
    """Series por generación que se agregan por configuración (nada pesado vuelve al padre)."""
    return {k: [h[k] for h in res["history"]] for k in CURVE_KEYS}


def _arr(values) -> np.ndarray:
    return np.array([np.nan if v is None else v for v in values], dtype=float)


def aggregate_curves(items: list[tuple[str, dict]]) -> list[dict]:
    """[(config, curve)] → filas config × gen con mediana/p25/p75/mín/máx de best y medias del resto."""
    by_cfg: dict[str, list[dict]] = {}
    for cfg, c in items:
        by_cfg.setdefault(cfg, []).append(c)
    rows = []
    for cfg, curves in by_cfg.items():
        mats = {k: np.vstack([_arr(c[k]) for c in curves]) for k in CURVE_KEYS if all(k in c for c in curves)}
        best = mats["best"]
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)   # columnas todo-NaN (strict sin best)
            q =np.nanpercentile(best, [25, 50, 75], axis=0)
            stats = {"best_p25": q[0], "best_median": q[1], "best_p75": q[2],
                     "best_min": np.nanmin(best, axis=0), "best_max": np.nanmax(best, axis=0)}
            for k in CURVE_KEYS[1:]:
                if k in mats:
                    stats[f"{k}_mean"] = np.nanmean(mats[k], axis=0)
        for g in range(best.shape[1]):
            r = {"config": cfg, "gen": g, "n_runs": best.shape[0]}
            r.update({k: (None if np.isnan(v[g]) else float(v[g])) for k, v in stats.items()})
            rows.append(r)
    return rows


# --- Tablas -----------------------------------------------------------------------

def write_tables(out: Path) -> list[Path]:
    """Escribe exp_tablas/*.md a partir de exp_runs/*.csv. Devuelve las rutas escritas."""
    return []


# --- Estadística --------------------------------------------------------------

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de Wilson al 95 % para una proporción k/n."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (float(max(0.0, c - h)), float(min(1.0, c + h)))


def bootstrap_diff_median(a, b, rng: np.random.Generator | None = None, B: int = 5000,
                          level: float = 0.95) -> tuple[float, float]:
    """IC bootstrap percentil de median(a) − median(b) (remuestreo independiente de cada grupo)."""
    rng = np.random.default_rng(0) if rng is None else rng
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    ma = np.median(a[rng.integers(0, len(a), (B, len(a)))], axis=1)
    mb = np.median(b[rng.integers(0, len(b), (B, len(b)))], axis=1)
    lo, hi = np.percentile(ma - mb, [100 * (1 - level) / 2, 100 * (1 + level) / 2])
    return (float(lo), float(hi))
