"""Métricas por ejecución, agregados y estadística de los experimentos (solo numpy)."""
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from astroshield import geometry, model  # noqa: E402

# Contrato 1.0.2 §10. Solo valen con F < 18.2° (régimen de un satélite por región): base_f20 no tiene oráculo.
ORACLES = {"base": 1.023077, "inviable": 0.796154, "menos_sats": 0.769231, "reducido": 1.023077,
           "prioridad_cambiada": 1.021429, "footprint_chico": 1.023077, "base_f5": 1.023077, "base_f10": 1.023077}
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

def read_csv(path: Path) -> list[dict]:
    import csv

    def parse(s):
        if s == "":
            return None
        if s in ("True", "False"):
            return s == "True"
        for cast in (int, float):
            try:
                return cast(s)
            except ValueError:
                pass
        return s

    with open(path, newline="", encoding="utf-8") as f:
        return [{k: parse(v) for k, v in r.items()} for r in csv.DictReader(f)]


def _f(v, nd=4) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    if isinstance(v, bool):
        return "sí" if v else "no"
    if isinstance(v, int):
        return str(v)
    return f"{v:.{nd}f}"


def md_table(header: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def _groups(rows: list[dict], key="config") -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r[key], []).append(r)
    return out


def region_ids(rows: list[dict]) -> list[str]:
    return [k[4:] for k in rows[0] if k.startswith("cov_") and k != "cov_weighted"]


def success(r: dict, n_regions: int) -> bool:
    """Criterio de suficiencia del Entregable 1 (§10): válida y todas las regiones cubiertas."""
    return bool(r["valid"]) and r["n_covered"] == n_regions


def _q(vals, p):
    vals = [v for v in vals if v is not None]
    return float(np.percentile(vals, p)) if vals else None


def _stats_cells(rs: list[dict], n_reg: int) -> list:
    fit = np.array([r["final_penalty_fitness"] for r in rs], dtype=float)
    k = sum(success(r, n_reg) for r in rs)
    lo, hi = wilson(k, len(rs))
    return [len(rs), _f(fit.mean()), _f(fit.std(ddof=1) if len(fit) > 1 else 0.0), _f(float(np.median(fit))),
            f"{_f(_q(fit, 25))}–{_f(_q(fit, 75))}", _f(fit.min()), _f(fit.max()),
            f"{k}/{len(rs)} [{lo:.2f}, {hi:.2f}]"]


STATS_HEADER = ["config", "n", "media", "sd", "mediana", "IQR", "mín", "máx", "éxito k/n [IC Wilson 95 %]"]


def t_p1(out: Path) -> str | None:
    import json
    p = out / "exp_json" / "base_repair_s42.json"
    if not p.exists():
        return None
    res = json.loads(p.read_text(encoding="utf-8"))
    sc = res["scenario"]
    ids = [r["id"] for r in sc["regions"]]
    sats = np.asarray(res["final"]["sats"], dtype=float)
    cm = model.coverage_matrix(sats, sc)
    rows = []
    for i, s in enumerate(sats):
        full = [ids[k] for k in range(len(ids)) if cm[k, i] == 1.0]
        part = [f"{ids[k]} ({cm[k, i]:.3f})" for k in range(len(ids)) if 0 < cm[k, i] < 1.0]
        rows.append([i, f"{s[0]:.3f}", f"{s[1]:.3f}", ", ".join(full) or "—", ", ".join(part) or "—"])
    t = md_table(["sat", "lat", "lon", "cubre completa", "cubre parcial (c)"], rows)
    cov = res["final"]["coverage"]
    fpf = model.fitness(sats, sc, "penalty")
    t += "\n" + md_table(["región", "prioridad", "cobertura final", "cobertura inicial"],
                         [[r["id"], r["priority"], _f(cov[r["id"]], 6), _f(res["initial"]["coverage"][r["id"]], 6)]
                          for r in sc["regions"]])
    n_cov = sum(1 for v in cov.values() if v == 1.0)
    t += "\n" + md_table(["valid", "cubiertas", "aptitud inicial", "aptitud final", "óptimo (§10)", "brecha",
                          "violaciones finales"],
                         [[_f(res["valid"]), f"{n_cov}/{len(ids)}", _f(res["initial"]["fitness"], 6),
                           _f(res["final"]["fitness"], 6), _f(ORACLES["base"], 6),
                           _f(gap_opt("base", fpf), 6), len(res["final"]["violations"])]])
    ref = out / "base_repair_s42.json"
    if ref.exists():
        r0 = json.loads(ref.read_text(encoding="utf-8"))
        same = r0["final"]["sats"] == res["final"]["sats"] and r0["final"]["fitness"] == res["final"]["fitness"]
        t += (f"\nComparación con `results/base_repair_s42.json` (Ola 2, numpy {r0['env']['numpy']}): "
              f"misma configuración final y aptitud = **{_f(same)}**.\n")
    return t


def t_p2(out: Path, base: list[dict], curves: list[dict], rnd: list[dict]) -> str:
    by_cfg = _groups(curves)
    rnd_by_seed = {r["seed"]: r["final_penalty_fitness"] for r in rnd}
    rows = []
    for cfg, rs in _groups(base).items():
        c = by_cfg.get(cfg, [])
        G = len(c) - 1
        marks = [g for g in (0, 10, 25, 50, 100, G) if 0 <= g <= G]
        beats = sum(1 for r in rs if r["seed"] in rnd_by_seed and r["final_penalty_fitness"] > rnd_by_seed[r["seed"]])
        rows.append([cfg] + [_f(c[g]["best_median"]) for g in marks]
                    + [_f(_q([r["gen_99"] for r in rs], 50), 1),
                       _f(_q([r["gen_all_covered_valid"] for r in rs], 50), 1),
                       f"{sum(r['gen_all_covered_valid'] is not None for r in rs)}/{len(rs)}",
                       f"{beats}/{len(rs)}"])
    hdr = (["config"] + [f"best med. g{g}" for g in marks]
           + ["gen_99 med.", "gen 6/6 válida med.", "alcanzan 6/6 válida", "AG > aleatoria (misma semilla)"])
    t = md_table(hdr, rows)
    if rnd:
        fx = np.array([r["final_penalty_fitness"] for r in rnd])
        t += "\n" + md_table(
            ["línea base", "n semillas", "evaluaciones", "máx. mediano", "máx. de máx.", "media de p95",
             "media de la media", "éxito 6/6"],
            [["aleatoria uniforme (penalty)", len(rnd), rnd[0]["n_evals"], _f(float(np.median(fx))), _f(fx.max()),
              _f(float(np.mean([r["fit_p95"] for r in rnd]))), _f(float(np.mean([r["fit_mean"] for r in rnd]))),
              f"{sum(success(r, 6) for r in rnd)}/{len(rnd)}"]])
    return t


def t_viol(rows_by_c: dict[str, list[dict]], kind: str) -> str:
    out = []
    for c, rows in rows_by_c.items():
        for cfg, rs in _groups(rows).items():
            col = f"n_viol_{kind}"
            tot = sum(r[col] for r in rs)
            n_with = sum(r[col] > 0 for r in rs)
            out.append([cfg, len(rs), tot, n_with, _f(float(np.mean([r["gen0_n_invalid"] for r in rs])), 1),
                        _f(_q([r["min_margin_deg"] for r in rs], 50), 2),
                        _f(min(r["min_margin_deg"] for r in rs), 2)])
    return md_table(["config", "ejecuciones", f"violaciones finales ({kind})", "ejecuciones con ≥1",
                     "inválidos gen 0 (media de 100)", "margen mín. mediano (°)", "margen mín. menor (°)"], out)


def t_p7(rows: list[dict]) -> str:
    n_reg = len(region_ids(rows))
    t = md_table(STATS_HEADER, [[cfg] + _stats_cells(rs, n_reg) for cfg, rs in _groups(rows).items()])
    opt = [[cfg, f"{sum(1 for r in rs if r['gap_opt'] is not None and abs(r['gap_opt']) < 1e-6)}/{len(rs)}",
            _f(_q([r["gap_opt"] for r in rs], 50), 6), _f(max(r["gap_opt"] for r in rs), 6)]
           for cfg, rs in _groups(rows).items() if rs[0]["gap_opt"] is not None]
    if opt:
        t += "\n" + md_table(["config", "alcanzan el óptimo (brecha < 1e-6)", "brecha mediana", "brecha máx."], opt)
    return t


def t_regions(rows_by_c: dict[str, list[dict]]) -> str:
    """Escenario × modo: % de semillas con c == 1.0 (media de c) por región y 6/6 cubiertas."""
    out, ids = [], None
    for rows in rows_by_c.values():
        ids = region_ids(rows)
        for cfg, rs in _groups(rows).items():
            cells = []
            for i in ids:
                vals = [r[f"cov_{i}"] for r in rs]
                cells.append(f"{100 * sum(v == 1.0 for v in vals) / len(vals):.0f} % ({np.mean(vals):.3f})")
            n_all = sum(r["n_covered"] == len(ids) for r in rs)
            out.append([rs[0]["scenario_id"], rs[0]["mode"]] + cells + [f"{n_all}/{len(rs)}"])
    return md_table(["escenario", "modo"] + ids + ["6/6 cubiertas"], out)


def t_redundancy(rows: list[dict]) -> str:
    ids = region_ids(rows)
    out = []
    for cfg, rs in _groups(rows).items():
        pats: dict[str, int] = {}
        for r in rs:
            key = "+".join(i for i in ids if r[f"redundancy_{i}"]) or "(ninguna)"
            pats[key] = pats.get(key, 0) + 1
        for key, n in sorted(pats.items(), key=lambda kv: (-kv[1], kv[0])):
            out.append([cfg, key, n])
    return md_table(["config", "regiones con ≥2 satélites que las cubren completas", "semillas"], out)


P5_MARGIN_ACTIVE = 1.0      # mediana de min_margin_deg en reducido por debajo de esto ⇒ restricción activa
P5_MARGIN_BASE = 10.0       # ... y en base por encima de esto (allí no está activa, §4.5)
P6_CAP = ORACLES["inviable"]
P6_GAP = 0.01


def _verdict(ok: bool) -> str:
    return "PASA" if ok else "FALLA"


def t_p5(red: list[dict], base: list[dict]) -> str:
    """P5: restricción activa en reducido (mediana del margen < 1° frente a > 10° en base), por modo."""
    n_reg = len(region_ids(red))
    bm = _groups(base, "mode")
    out = []
    for m, rs in _groups(red, "mode").items():
        bs = bm.get(m, [])
        med_r = _q([r["min_margin_deg"] for r in rs], 50)
        med_b = _q([r["min_margin_deg"] for r in bs], 50)
        active = "—" if med_b is None else _verdict(med_r < P5_MARGIN_ACTIVE and med_b > P5_MARGIN_BASE)
        fit_r = float(np.median([r["final_penalty_fitness"] for r in rs]))
        fit_b = float(np.median([r["final_penalty_fitness"] for r in bs])) if bs else None
        k = sum(success(r, n_reg) for r in rs)
        lo, hi = wilson(k, len(rs))
        n_viol = sum(r["n_viol_debris"] + r["n_viol_occupied"] for r in rs)
        out.append([m, _f(med_r, 2), _f(med_b, 2), active, f"{k}/{len(rs)} [{lo:.2f}, {hi:.2f}]",
                    f"{sum(success(r, n_reg) for r in bs)}/{len(bs)}" if bs else "—",
                    _f(fit_r), _f(fit_b), _f(None if fit_b is None else fit_b - fit_r), n_viol,
                    "—" if m == "penalty" else _verdict(n_viol == 0)])
    t = md_table(["modo", "margen mín. mediano reducido (°)", "margen mín. mediano base (°)",
                  f"restricción activa (< {P5_MARGIN_ACTIVE:g}° vs > {P5_MARGIN_BASE:g}°)", "éxito reducido [IC 95 %]",
                  "éxito base", "aptitud mediana reducido", "aptitud mediana base", "caída de la mediana",
                  "violaciones finales", "0 violaciones (repair/strict)"], out)
    return t + "\n" + t_p7(red)


def t_margin_zones(fin: list[dict], sc: dict) -> str:
    """Zona que fija min_margin_deg en cada ejecución (desde finales_<c>.csv), por configuración."""
    sats: dict[tuple, list] = {}
    for r in fin:
        sats.setdefault((r["config"], r["seed"]), []).append([r["lat"], r["lon"]])
    zones = sc["debris_zones"] + sc["occupied"]
    zl = np.array([[z["lat"], z["lon"]] for z in zones], dtype=float)
    zr = np.array([z["radius_deg"] for z in zones], dtype=float)
    agg: dict[tuple, list[float]] = {}
    for (cfg, _), s in sats.items():
        s = np.asarray(s, dtype=float)
        d = geometry.central_angle(s[:, None, 0], s[:, None, 1], zl[None, :, 0], zl[None, :, 1]) - zr[None, :]
        j = int(np.unravel_index(d.argmin(), d.shape)[1])
        agg.setdefault((cfg, zones[j]["id"]), []).append(float(d.min()))
    rows = [[cfg, z, len(v), _f(float(np.median(v)), 2), _f(min(v), 2), sum(x < P5_MARGIN_ACTIVE for x in v)]
            for (cfg, z), v in sorted(agg.items(), key=lambda kv: (kv[0][0], -len(kv[1]), kv[0][1]))]
    return md_table(["config", "zona que fija el margen mínimo", "ejecuciones", "margen mediano (°)",
                     "margen menor (°)", f"< {P5_MARGIN_ACTIVE:g}°"], rows)


def t_p6(inv: list[dict]) -> str:
    """P6: ningún final válido toca Yucatán y ninguna aptitud supera el óptimo de §10 (0.796154 en 1.0.2), por modo."""
    n_reg = len(region_ids(inv))
    out = []
    for m, rs in _groups(inv, "mode").items():
        val = [r for r in rs if r["valid"]]
        yuc0 = sum(r["cov_yucatan"] == 0.0 for r in val)
        fit = [r["final_penalty_fitness"] for r in rs]
        capped = sum(f <= P6_CAP + 1e-9 for f in fit)
        k = sum(r["gap_opt"] is not None and r["gap_opt"] < P6_GAP for r in rs)
        lo, hi = wilson(k, len(rs))
        out.append([m, len(rs), f"{len(val)}/{len(rs)}", f"{yuc0}/{len(val)}", _f(max(fit), 6),
                    f"{capped}/{len(rs)}", f"{k}/{len(rs)} [{lo:.2f}, {hi:.2f}]",
                    f"{sum(success(r, n_reg) for r in rs)}/{len(rs)}",
                    _verdict(yuc0 == len(val) and capped == len(rs))])
    t = md_table(["modo", "ejecuciones", "válidas", "válidas con cov_yucatan = 0", "aptitud penalty máx.",
                  f"≤ {P6_CAP:g}", f"brecha < {P6_GAP:g} [IC 95 %]", "éxito 6/6", "veredicto"], out)
    return t + "\n" + t_p7(inv)


def p11_expected(row: dict) -> str:
    """Coherencia de una revalidación con lo esperado en §4.6 (P11). '—' si §4.6 no fija resultado."""
    sc, zones = row["scenario"], (row.get("violated_zones") or "").split()
    if sc == "prioridad_cambiada":
        return _verdict(row["still_valid"] and row["fitness_after"] != row["fitness_before"])
    if sc == "menos_sats":
        return _verdict(not row["still_valid"] and "n_sats" in (row["reasons"] or ""))
    if sc == "inviable":
        return _verdict(not row["still_valid"] and "bloqueo_yucatan" in zones)
    if sc == "footprint_chico":
        return _verdict(row["still_valid"] and bool(row["lost_regions"]))
    return _verdict(row["still_valid"] == (row["n_violations"] == 0))   # reducido: solo consistencia


def t_p11(rv: list[dict]) -> str:
    return md_table(
        ["escenario nuevo", "still_valid", "razones", "zonas violadas", "aptitud antes", "aptitud después",
         "perdidas", "ganadas", "coherente con §4.6"],
        [[r["scenario"], _f(r["still_valid"]), r["reasons"] or "—", r.get("violated_zones") or "—",
          _f(r["fitness_before"], 6), _f(r["fitness_after"], 6), r["lost_regions"] or "—",
          r["gained_regions"] or "—", p11_expected(r)] for r in rv])


def t_p8(rows_by_c: dict[str, list[dict]]) -> str:
    out = []
    for c, rows in rows_by_c.items():
        g = _groups(rows, "mode")
        n_reg = len(region_ids(rows))
        pen = [r["final_penalty_fitness"] for r in g.get("penalty", [])]
        for m, rs in g.items():
            fit = [r["final_penalty_fitness"] for r in rs]
            k = sum(success(r, n_reg) for r in rs)
            lo, hi = wilson(k, len(rs))
            ci = "—"
            if m != "penalty" and pen:
                a, b = bootstrap_diff_median(fit, pen)
                ci = f"{float(np.median(fit) - np.median(pen)):+.4f} [{a:+.4f}, {b:+.4f}]"
            out.append([c, m, f"{k}/{len(rs)} [{lo:.2f}, {hi:.2f}]", _f(float(np.median(fit))),
                        _f(float(np.mean(fit))), f"{sum(r['valid'] for r in rs)}/{len(rs)}",
                        _f(_q([r["gen_all_covered_valid"] for r in rs], 50), 1), ci])
    return md_table(["escenario", "modo", "éxito [IC 95 %]", "aptitud penalty mediana", "media", "válidas",
                     "gen 6/6 válida mediana", "Δ mediana vs penalty [IC bootstrap 95 %]"], out)


def t_p9(rows: list[dict], curves: list[dict]) -> str:
    n_reg = len(region_ids(rows))
    last = {}
    for c in curves:
        last[c["config"]] = c
    out = []
    for cfg, rs in sorted(_groups(rows).items(), key=lambda kv: kv[1][0]["footprint_deg"]):
        fit = [r["final_penalty_fitness"] for r in rs]
        k = sum(success(r, n_reg) for r in rs)
        lo, hi = wilson(k, len(rs))
        opt = sum(1 for r in rs if abs(r["final_penalty_fitness"] - ORACLES["base"]) < 1e-6)
        out.append([_f(rs[0]["footprint_deg"], 1), cfg, rs[0]["gens"], f"{k}/{len(rs)} [{lo:.2f}, {hi:.2f}]",
                    _f(float(np.median(fit))), _f(min(fit)), _f(max(fit)), f"{opt}/{len(rs)}",
                    _f(_q([r["gen_all_covered_valid"] for r in rs], 50), 1),
                    _f(float(np.mean([r["gen0_best"] for r in rs]))),
                    _f(float(np.mean([sum(r[f'redundancy_{i}'] for i in region_ids(rows)) for r in rs])), 2)])
    return md_table(["F (°)", "config", "gens", "éxito [IC 95 %]", "aptitud mediana", "mín", "máx",
                     "= 1.023077", "gen 6/6 válida med.", "best gen 0 (media)", "regiones redundantes (media)"], out)


def t_p10(rows: list[dict], curves: list[dict]) -> str:
    n_reg = len(region_ids(rows))
    last = {}
    for c in curves:
        last[c["config"]] = c
    out = []
    for cfg, rs in sorted(_groups(rows).items(), key=lambda kv: kv[1][0]["pop_size"]):
        fit = [r["final_penalty_fitness"] for r in rs]
        k = sum(success(r, n_reg) for r in rs)
        lo, hi = wilson(k, len(rs))
        opt = sum(1 for r in rs if r["gap_opt"] is not None and abs(r["gap_opt"]) < 1e-6)
        out.append([rs[0]["pop_size"], rs[0]["gens"], rs[0]["n_evals"], f"{k}/{len(rs)} [{lo:.2f}, {hi:.2f}]",
                    _f(float(np.median(fit))), f"{_f(_q(fit, 25))}–{_f(_q(fit, 75))}", f"{opt}/{len(rs)}",
                    _f(_q([r["gen_99"] for r in rs], 50), 1),
                    _f(last[cfg].get("diversity_mean"), 2) if cfg in last else "—"])
    return md_table(["P", "gens", "evaluaciones", "éxito [IC 95 %]", "aptitud mediana", "IQR", "óptimo alcanzado",
                     "gen_99 med.", "diversidad final media (°)"], out)


def t_reps(out: Path) -> str | None:
    p = out / "exp_meta" / "representativas.csv"
    if not p.exists():
        return None
    rows = read_csv(p)
    return md_table(["archivo", "config", "semilla", "rol", "aptitud penalty"],
                    [[f"`exp_json/{r['file']}`", r["config"], r["seed"], r["roles"], _f(r["final_penalty_fitness"], 6)]
                     for r in rows])


def t_times(out: Path) -> str | None:
    p = out / "exp_meta" / "tiempos.csv"
    rows = []
    if p.exists():
        rows += [[r["campaign"], r.get("n_tasks"), _f(r.get("cpu_s"), 1), _f(r.get("mean_task_s"), 2),
                  _f(r.get("wall_s"), 1), r.get("jobs") or "—"] for r in read_csv(p)]
    b = out / "exp_meta" / "bench.csv"
    t = ""
    if rows:
        t += md_table(["campaña", "ejecuciones", "Σ tiempo por ejecución (s)", "s por ejecución (media)",
                       "reloj total (s)", "procesos"], rows)
    b0 = out / "exp_meta" / "bench_inicial.txt"     # salida literal del primer --bench (antes de la corrida)
    if b0.exists():
        rows0 = [ln.rsplit(":", 1) for ln in b0.read_text(encoding="utf-8").splitlines() if ":" in ln]
        t += "\n" + md_table(["primer --bench (1 proceso, exp_meta/bench_inicial.txt)", "segundos"],
                             [[w.strip(), s.strip().removesuffix(" s")] for w, s in rows0])
    if b.exists():
        t += "\n" + md_table(["último --bench (1 proceso, exp_meta/bench.csv)", "segundos"],
                             [[r["what"], _f(r["seconds"], 1)] for r in read_csv(b)])
    return t or None


def write_tables(out: Path) -> list[Path]:
    """Escribe exp_tablas/*.md a partir de exp_runs/*.csv (y exp_json/exp_meta). Devuelve las rutas escritas."""
    out = Path(out)
    runs = out / "exp_runs"
    load = lambda n: read_csv(runs / f"{n}.csv") if (runs / f"{n}.csv").exists() else []  # noqa: E731
    base, red, inv = load("base"), load("reducido"), load("inviable")
    fp, pop, rnd = load("footprint"), load("poblacion"), load("aleatoria")
    feasible = {c: r for c, r in (("base", base), ("reducido", red)) if r}
    allm = {c: r for c, r in (("base", base), ("reducido", red), ("inviable", inv)) if r}
    tables: dict[str, str | None] = {"p1_config": t_p1(out), "representativas": t_reps(out), "tiempos": t_times(out)}
    if base:
        tables["p2_resumen"] = t_p2(out, base, load("curvas_base"), rnd)
        tables["p7_variacion"] = t_p7(base)
        tables["p7_redundancia"] = t_redundancy(base)
    if feasible:
        tables["p3_violaciones"] = t_viol(feasible, "debris")
        tables["p4_violaciones"] = t_viol(feasible, "occupied")
    others = {c: r for c in ("prioridad_cambiada", "menos_sats", "footprint_chico") if (r := load(c))}
    allr = {**allm, **others}
    if others:
        tables["otros_escenarios"] = "\n".join(t_p7(r) for r in others.values())
    if allm:
        tables["regiones_cubiertas"] = t_regions(allr)
        tables["p8_modos"] = t_p8(allm)
    if red:
        tables["p5_resumen"] = t_p5(red, base)
        sc_red = ROOT / "scenarios" / "reducido.json"
        if (runs / "finales_reducido.csv").exists() and sc_red.exists():
            tables["p5_zonas"] = t_margin_zones(load("finales_reducido"), model.load_scenario(sc_red))
    if inv:
        tables["p6_resumen"] = t_p6(inv)
    if fp:
        tables["p9_footprint"] = t_p9(fp, load("curvas_footprint"))
    if pop:
        tables["p10_poblacion"] = t_p10(pop, load("curvas_poblacion"))
    if (runs / "reval.csv").exists():
        tables["p11_revalidacion"] = t_p11(read_csv(runs / "reval.csv"))
    dest = out / "exp_tablas"
    dest.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in tables.items():
        if text:
            p = dest / f"{name}.md"
            p.write_text(text, encoding="utf-8", newline="\n")
            written.append(p)
    return written


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
