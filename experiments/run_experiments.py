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
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:  # mismo criterio que el shim run.py de la raíz
    sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

import analysis  # noqa: E402
from astroshield import CONTRACT_VERSION, model  # noqa: E402
from astroshield.geometry import sample_sphere  # noqa: E402
from astroshield.revalidate import revalidate  # noqa: E402
from astroshield.run import run, save_result  # noqa: E402

SEEDS = list(range(42, 72))
QUICK_SEEDS = SEEDS[:3]
MODES = ("penalty", "repair", "strict")
ORACLES = analysis.ORACLES
FOOTPRINTS = (5.0, 7.5, 10.0, 12.5, 15.0, 20.0)
POPS = (20, 50, 100, 200)
POP_BUDGET = 20000          # gens = POP_BUDGET / P  ->  P·(gens+1) ≈ 20 100 evaluaciones
FOOTPRINT_GENS = 100
RANDOM_EVALS = 20100        # mismo presupuesto que el AG por defecto: 100 · (200 + 1)
DERIVED = ("reducido", "inviable", "prioridad_cambiada", "menos_sats", "footprint_chico")
SCENARIO_CAMPAIGNS = ("base", "reducido", "inviable", "prioridad_cambiada", "menos_sats", "footprint_chico")
CAMPAIGNS = SCENARIO_CAMPAIGNS + ("footprint", "poblacion", "aleatoria")

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
    if name in SCENARIO_CAMPAIGNS:
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
        step = QUICK_PARAMS["pop_size"] if quick else 100
        return [_task(name, "base_aleatoria", base, "penalty", {"n_evals": n, "step": step}, s)
                for s in seeds]
    raise ValueError(f"campaña desconocida: {name}")


def _random_run(sc: dict, n_evals: int, seed: int, batch: int = 2000) -> tuple[np.ndarray, np.ndarray]:
    """(aptitudes penalty en orden de muestreo, mejor configuración). RNG propio default_rng(seed)."""
    rng = np.random.default_rng(seed)
    n = sc["n_sats"]
    out = np.empty(n_evals, dtype=float)
    best, best_fit = None, -np.inf
    for k in range(0, n_evals, batch):
        m = min(batch, n_evals - k)
        pop = sample_sphere(m * n, rng).reshape(m, n, 2)
        out[k:k + m] = [model.fitness(s, sc, "penalty") for s in pop]
        j = int(np.argmax(out[k:k + m]))
        if out[k + j] > best_fit:
            best, best_fit = pop[j].copy(), out[k + j]
    return out, best


def random_fitnesses(sc: dict, n_evals: int, seed: int, batch: int = 2000) -> np.ndarray:
    """Aptitud penalty de n_evals configuraciones uniformes (línea base del AG), en orden de muestreo.

    Usa model.fitness, no una copia de la fórmula.
    """
    return _random_run(sc, n_evals, seed, batch)[0]


def random_search(sc: dict, n_evals: int, seed: int, batch: int = 2000) -> float:
    """Mejor aptitud penalty de n_evals configuraciones aleatorias uniformes."""
    return float(random_fitnesses(sc, n_evals, seed, batch).max())


def run_id(t: dict) -> str:
    return f"{t['config']}_s{t['seed']}"


def run_task(t: dict) -> tuple[dict, dict, list]:
    """Ejecuta una tarea y devuelve (fila CSV, curvas, sats finales). Nivel de módulo: picklable (spawn)."""
    if t["campaign"] == "aleatoria":
        fits, best = _random_run(t["scenario"], t["params"]["n_evals"], t["seed"])
        return (analysis.random_row(t, fits, best), analysis.random_curves(fits, t["params"]["step"]),
                best.tolist())
    res = run(t["scenario"], t["mode"], t["params"], t["seed"], run_id=run_id(t))
    return analysis.run_row(res, t), analysis.run_curves(res), res["final"]["sats"]


def _timed_task(t: dict):
    t0 = time.perf_counter()
    out = run_task(t)
    return out, time.perf_counter() - t0


def _pmap(fn, items, jobs: int) -> list:
    """map ordenado; en paralelo con ProcessPoolExecutor si jobs > 1 (el orden no cambia el resultado)."""
    if jobs <= 1 or len(items) <= 1:
        return [fn(x) for x in items]
    with ProcessPoolExecutor(max_workers=min(jobs, len(items))) as ex:
        return list(ex.map(fn, items, chunksize=1))


# --- CSV deterministas --------------------------------------------------------

def _fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        return "" if v != v else repr(v)   # repr: 17 cifras, hash estable
    return str(v)


def write_csv(rows: list[dict], path: Path) -> None:
    cols: list[str] = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            w.writerow([_fmt(r.get(c)) for c in cols])


def _parse(s: str):
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


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return [{k: _parse(v) for k, v in r.items()} for r in csv.DictReader(f)]


def merge_csv(rows: list[dict], path: Path, key: str, merge: bool = True) -> list[dict]:
    """Escribe rows en path; con merge conserva las filas previas cuyo `key` no aparece en rows (--only)."""
    new = {r[key] for r in rows}
    old = [r for r in read_csv(path) if r[key] not in new] if merge and path.exists() else []
    write_csv(old + rows, path)
    return old + rows


def file_hash(path: Path) -> str:
    """sha256 con fin de línea normalizado a LF (git en Windows puede convertir a CRLF)."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# --- Campañas -----------------------------------------------------------------

def run_campaigns(names: list[str], quick: bool, jobs: int, out: Path) -> dict:
    """Ejecuta las campañas en un solo pool y escribe exp_runs/<c>.csv, curvas_<c>.csv y finales_<c>.csv."""
    tasks = [t for n in names for t in campaign_tasks(n, quick)]
    t0 = time.perf_counter()
    results = _pmap(_timed_task, tasks, jobs)
    wall = time.perf_counter() - t0
    by_c: dict[str, list] = {}
    for t, ((row, curve, sats), secs) in zip(tasks, results):
        by_c.setdefault(t["campaign"], []).append((t, row, curve, sats, secs))
    runs_dir = out / "exp_runs"
    for c, items in by_c.items():
        write_csv([row for _, row, _, _, _ in items], runs_dir / f"{c}.csv")
        write_csv(analysis.aggregate_curves([(t["config"], curve) for t, _, curve, _, _ in items]),
                  runs_dir / f"curvas_{c}.csv")
        write_csv([{"config": t["config"], "seed": t["seed"], "sat": i, "lat": float(s[0]), "lon": float(s[1])}
                   for t, _, _, sats, _ in items for i, s in enumerate(sats)], runs_dir / f"finales_{c}.csv")
    times = [{"campaign": c, "n_tasks": len(items), "cpu_s": sum(x[4] for x in items),
              "mean_task_s": sum(x[4] for x in items) / len(items)} for c, items in by_c.items()]
    times.append({"campaign": "TOTAL " + "+".join(by_c), "n_tasks": len(tasks), "cpu_s": sum(r["cpu_s"] for r in times),
                  "wall_s": wall, "jobs": jobs})
    return {"by_campaign": by_c, "times": times}


# --- Representativas y determinismo ------------------------------------------

class DeterminismError(RuntimeError):
    pass


def pick_representatives(rows: list[dict], roles=("best", "median", "worst")) -> list[tuple[str, str, int]]:
    """[(config, rol, seed)] por configuración. Orden estable por (aptitud penalty, semilla)."""
    by_cfg: dict[str, list[dict]] = {}
    for r in rows:
        by_cfg.setdefault(r["config"], []).append(r)
    out = []
    for cfg, rs in by_cfg.items():
        asc = sorted(rs, key=lambda r: (r["final_penalty_fitness"], r["seed"]))
        desc = sorted(rs, key=lambda r: (-r["final_penalty_fitness"], r["seed"]))
        pick = {"best": desc[0], "median": asc[len(asc) // 2], "worst": asc[0]}
        out += [(cfg, role, int(pick[role]["seed"])) for role in roles]
    return out


def verify_representative(res: dict, row: dict, sats: list) -> None:
    """Exige igualdad bit a bit entre la re-ejecución y la primera pasada; si no, DeterminismError."""
    fpf = model.fitness(np.asarray(res["final"]["sats"], dtype=float), res["scenario"], "penalty")
    if (fpf != row["final_penalty_fitness"] or res["final"]["fitness"] != row["final_fitness"]
            or res["final"]["sats"] != [list(map(float, s)) for s in sats]):
        raise DeterminismError(f"{res['id']}: la re-ejecución no coincide con la fila CSV")


def _run_full(t: dict) -> dict:
    return run(t["scenario"], t["mode"], t["params"], t["seed"], run_id=run_id(t))


def save_representatives(by_c: dict, jobs: int, out: Path, merge: bool = False) -> list[dict]:
    """Re-ejecuta mejor/mediana/peor (base, reducido, inviable), mediana (sensibilidad) y base_repair_s42."""
    wanted: dict[tuple[str, int], list[str]] = {}
    for c, items in by_c.items():
        if c == "aleatoria":
            continue
        roles = ("best", "median", "worst") if c in ("base", "reducido", "inviable") else ("median",)
        for cfg, role, seed in pick_representatives([row for _, row, _, _, _ in items], roles):
            wanted.setdefault((cfg, seed), []).append(role)
    if "base" in by_c:
        wanted.setdefault(("base_repair", 42), []).append("p1")
    index = {(t["config"], t["seed"]): (t, row, sats) for items in by_c.values() for t, row, _, sats, _ in items}
    keys = [k for k in index if k in wanted]          # orden de tareas
    results = _pmap(_run_full, [index[k][0] for k in keys], jobs)
    table = []
    for k, res in zip(keys, results):
        t, row, sats = index[k]
        verify_representative(res, row, sats)
        path = save_result(res, out / "exp_json")
        table.append({"config": k[0], "seed": k[1], "roles": "+".join(wanted[k]),
                      "final_penalty_fitness": row["final_penalty_fitness"], "file": path.name})
    path = out / "exp_meta" / "representativas.csv"
    merge_csv(table, path, "config", merge)
    return table


# --- Revalidación (P11) ------------------------------------------------------

def run_revalidations(out: Path) -> list[dict]:
    """exp_json/base_repair_s42.json → cada escenario derivado disponible; salta los que falten (1D)."""
    src = out / "exp_json" / "base_repair_s42.json"
    rows = []
    if not src.exists():
        return rows
    for d in DERIVED:
        path = scenario_path(d)
        if not path.exists():
            continue
        rv = revalidate(src, path)
        dest = out / "exp_reval" / f"reval_{rv['result_id']}__{rv['new_scenario_id']}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(rv, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        rows.append({"scenario": d, "still_valid": rv["still_valid"], "reasons": "; ".join(rv["reasons"]),
                     "fitness_before": rv["fitness_before"], "fitness_after": rv["fitness_after"],
                     "lost_regions": " ".join(rv["lost_regions"]), "gained_regions": " ".join(rv["gained_regions"]),
                     "n_violations": len(rv["violations"]),
                     "violated_zones": " ".join(sorted({v["zone_id"] for v in rv["violations"]}))})
    if rows:
        write_csv(rows, out / "exp_runs" / "reval.csv")
    return rows


# --- Metadatos ----------------------------------------------------------------

def _git(*args) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "?"


def write_meta(out: Path, argv: list[str], jobs: int, times: list[dict] | None, names: list[str],
               merge: bool = False, clean: bool | None = None) -> None:
    """entorno.txt, sha256.txt y tiempos.csv. Con merge (--only) conserva lo de las otras campañas.

    clean: estado de git ANTES de ejecutar (al final el árbol ya tiene los CSV nuevos).
    """
    meta = out / "exp_meta"
    meta.mkdir(parents=True, exist_ok=True)
    import matplotlib
    lines = ["campaigns: " + ",".join(names), f"python: {platform.python_version()}", f"numpy: {np.__version__}",
             f"matplotlib: {matplotlib.__version__}", f"platform: {platform.platform()}",
             f"cpu_count: {os.cpu_count()}", f"jobs: {jobs}", f"contract_version: {CONTRACT_VERSION}",
             f"git_commit: {_git('rev-parse', 'HEAD')}",
             f"git_status_clean: {_git('status', '--porcelain') == '' if clean is None else clean}",
             "command: python experiments/run_experiments.py " + " ".join(argv),
             "missing_scenarios: " + ",".join(d for d in DERIVED if not scenario_path(d).exists())]
    env = meta / "entorno.txt"
    text = "\n".join(lines) + "\n"
    if merge and env.exists():   # un bloque por invocación; se reemplaza el de las mismas campañas
        old = [b.strip("\n") for b in env.read_text(encoding="utf-8").split("\n\n")
               if b.strip() and lines[0] not in b.splitlines()]
        text = "\n\n".join(old + [text.rstrip("\n")]) + "\n"
    env.write_text(text, encoding="utf-8")
    sha = meta / "sha256.txt"
    mine = {f"{p}{c}.csv" for c in names for p in ("", "curvas_", "finales_")} | {"reval.csv"}
    hashes = {}
    if merge and sha.exists():   # hashes previos de las campañas que esta invocación no reescribió
        hashes = {n: h for h, n in (ln.split(maxsplit=1) for ln in sha.read_text(encoding="utf-8").splitlines()
                                    if ln.strip())}
    hashes.update({f"exp_runs/{p.name}": file_hash(p) for p in sorted((out / "exp_runs").glob("*.csv"))
                   if not merge or p.name in mine or f"exp_runs/{p.name}" not in hashes})
    sha.write_text("".join(f"{h}  {n}\n" for n, h in sorted(hashes.items())), encoding="utf-8")
    if times is not None:
        merge_csv(times, meta / "tiempos.csv", "campaign", merge)


def verify_hashes(names: list[str], quick: bool, jobs: int, out: Path) -> int:
    """Re-ejecuta las campañas en un directorio temporal y compara los sha256 con exp_meta/sha256.txt."""
    ref = {}
    for line in (out / "exp_meta" / "sha256.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            h, name = line.split(maxsplit=1)
            ref[name] = h
    with tempfile.TemporaryDirectory() as tmp:
        run_campaigns(names, quick, jobs, Path(tmp))
        bad = 0
        for p in sorted((Path(tmp) / "exp_runs").glob("*.csv")):
            name = f"exp_runs/{p.name}"
            ok = ref.get(name) == file_hash(p)
            bad += not ok
            print(f"{'OK ' if ok else 'DIF'} {name}")
    return 0 if bad == 0 else 1


# --- Bench ----------------------------------------------------------------------

def bench(jobs: int, out: Path) -> list[dict]:
    """1 ejecución 100×200 por modo (base, s=42) + 1 aleatoria; proyecta el tiempo de --all."""
    base = model.load_scenario(scenario_path("base"))
    per_eval = {}
    rows = []
    for m in MODES:
        t0 = time.perf_counter()
        run(base, m, {}, 42)
        s = time.perf_counter() - t0
        per_eval[m] = s / 20100
        rows.append({"what": f"run base {m} 100x200", "seconds": s})
    t0 = time.perf_counter()
    _random_run(base, RANDOM_EVALS, 42)
    s = time.perf_counter() - t0
    per_eval["aleatoria"] = s / RANDOM_EVALS
    rows.append({"what": "aleatoria 20100", "seconds": s})
    cpu = 0.0
    for n in CAMPAIGNS:
        for t in campaign_tasks(n):
            key = "aleatoria" if n == "aleatoria" else t["mode"]
            evals = t["params"].get("n_evals") or t["params"].get("pop_size", 100) * (t["params"].get("gens", 200) + 1)
            cpu += per_eval[key] * evals
    rows.append({"what": "proyeccion cpu --all (s)", "seconds": cpu})
    rows.append({"what": f"proyeccion reloj --all con {jobs} procesos (s)", "seconds": cpu / jobs})
    write_csv(rows, out / "exp_meta" / "bench.csv")
    for r in rows:
        print(f"{r['what']}: {r['seconds']:.1f} s")
    return rows


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Campañas de experimentos de AstroShield (Entregable 3).")
    p.add_argument("--all", action="store_true", help="ejecuta todas las campañas disponibles")
    p.add_argument("--only", default=None, help="campañas separadas por coma: " + ",".join(CAMPAIGNS))
    p.add_argument("--quick", action="store_true", help="3 semillas y presupuestos mínimos (tests)")
    p.add_argument("--bench", action="store_true", help="mide 1 ejecución por modo y proyecta el tiempo total")
    p.add_argument("--verify", action="store_true", help="re-ejecuta y compara hashes de exp_runs/*.csv")
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="procesos en paralelo")
    p.add_argument("--out", default=str(ROOT / "results"), help="directorio raíz de salida")
    p.add_argument("--reval", action="store_true", help="solo P11: revalida exp_json/base_repair_s42.json")
    p.add_argument("--tables", action="store_true", help="solo regenera tablas y figuras desde exp_runs/")
    p.add_argument("--no-figs", action="store_true", help="no genera figuras (implícito con --quick)")
    p.add_argument("--seeds", type=int, default=None, help="usa solo las primeras N semillas (42, 43, …)")
    return p


def make_outputs(out: Path, figs: bool) -> None:
    analysis.write_tables(out)
    if figs:
        import plots
        plots.make_all(out)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    args = build_parser().parse_args(argv)
    clean = _git("status", "--porcelain") == ""
    out = Path(args.out)
    if args.seeds:
        global SEEDS
        SEEDS = SEEDS[:args.seeds]
    if args.bench:
        bench(args.jobs, out)
        return 0
    if args.tables:
        make_outputs(out, figs=not args.no_figs)
        return 0
    if args.reval:
        rows = run_revalidations(out)
        print(f"P11: {len(rows)} revalidaciones en {out / 'exp_reval'}")
        make_outputs(out, figs=False)
        return 0 if rows else 1
    if args.all:
        names = list(CAMPAIGNS)
    elif args.only:
        names = [n.strip() for n in args.only.split(",") if n.strip()]
        unknown = set(names) - set(CAMPAIGNS)
        if unknown:
            print(f"campañas desconocidas: {sorted(unknown)}", file=sys.stderr)
            return 2
    else:
        build_parser().print_help()
        return 2
    skipped = [n for n in names if not campaign_tasks(n, args.quick)]
    for n in skipped:
        print(f"[omitida] {n}: falta scenarios/{n}.json (bloqueada por 1D)")
    names = [n for n in names if n not in skipped]
    if args.verify:
        return verify_hashes(names, args.quick, args.jobs, out)
    t0 = time.perf_counter()
    camp = run_campaigns(names, args.quick, args.jobs, out)
    print(f"campañas {names}: {time.perf_counter() - t0:.1f} s")
    t1 = time.perf_counter()
    try:
        reps = save_representatives(camp["by_campaign"], args.jobs, out, merge=not args.all)
    except DeterminismError as e:
        print(f"ERROR de determinismo: {e}", file=sys.stderr)
        return 3
    camp["times"].append({"campaign": "representativas " + "+".join(names), "n_tasks": len(reps),
                          "wall_s": time.perf_counter() - t1, "jobs": args.jobs})
    print(f"representativas: {len(reps)} JSON en {time.perf_counter() - t1:.1f} s (determinismo OK)")
    run_revalidations(out)
    write_meta(out, argv, args.jobs, camp["times"], names, merge=not args.all, clean=clean)
    make_outputs(out, figs=not (args.quick or args.no_figs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
