"""Tests de los experimentos (Ola 3A). Se ejecutan con `pytest experiments`."""
import copy
import shutil
import json
from pathlib import Path

import numpy as np
import pytest

import analysis
import run_experiments as rx
from astroshield import model

ROOT = Path(__file__).resolve().parents[1]
BASE = model.load_scenario(ROOT / "scenarios" / "base.json")


def _hay_escenario(nombre):
    return (ROOT / "scenarios" / f"{nombre}.json").exists()


# --- CLI, semillas y campañas -------------------------------------------------

def test_cli_help():
    with pytest.raises(SystemExit) as e:
        rx.main(["--help"])
    assert e.value.code == 0


def test_seeds_are_30_and_include_42():
    assert len(rx.SEEDS) == 30
    assert 42 in rx.SEEDS
    assert len(set(rx.SEEDS)) == 30


@pytest.mark.parametrize("campana, n", [("base", 90), ("footprint", 180), ("poblacion", 120), ("aleatoria", 30)])
def test_campaign_sizes(campana, n):
    assert len(rx.campaign_tasks(campana, quick=False)) == n


@pytest.mark.parametrize("campana", ["reducido", "inviable"])
def test_campaign_sizes_derived(campana):
    if not _hay_escenario(campana):
        assert rx.campaign_tasks(campana, quick=False) == []
        pytest.skip(f"bloqueada por 1D: falta scenarios/{campana}.json")
    assert len(rx.campaign_tasks(campana, quick=False)) == 90


def test_population_budget_fixed():
    tareas = rx.campaign_tasks("poblacion", quick=False)
    assert {t["params"]["pop_size"] for t in tareas} == {20, 50, 100, 200}
    for t in tareas:
        n_evals = t["params"]["pop_size"] * (t["params"]["gens"] + 1)
        assert abs(n_evals - 20100) <= 0.01 * 20100


def test_footprint_variant_is_copy():
    original = copy.deepcopy(BASE)
    v = rx.footprint_variant(BASE, 7.5)
    assert v["id"] == "base_f7_5"
    assert v["footprint_deg"] == 7.5
    assert BASE == original
    model.load_scenario(v)


# --- Búsqueda aleatoria de referencia ---------------------------------------

def test_random_search_reproducible():
    a = rx.random_search(BASE, 2000, 7)
    b = rx.random_search(BASE, 2000, 7)
    assert a == b
    assert a < 1.023077


def test_random_task_row():
    t = rx.campaign_tasks("aleatoria", quick=True)[0]
    row, curve, sats = rx.run_task(t)
    assert row["n_evals"] == rx.QUICK_RANDOM_EVALS
    assert row["final_penalty_fitness"] == rx.random_search(BASE, rx.QUICK_RANDOM_EVALS, t["seed"])
    assert len(curve["best"]) == rx.QUICK_RANDOM_EVALS // t["params"]["step"]
    assert curve["best"][-1] == row["final_penalty_fitness"]
    assert len(sats) == 8


@pytest.mark.slow
def test_random_search_scale():
    best = rx.random_search(BASE, 20000, 0)
    assert 0.3 <= best <= 1.0   # contrato §4.5: máximo ≈ 0.615 con 20 000 configuraciones


# --- Métricas por ejecución (analysis) ---------------------------------------

MOCK = json.loads((ROOT / "results" / "mock.json").read_text(encoding="utf-8"))
MOCK_TASK = {"campaign": "mock", "config": "mock_penalty"}


def test_run_row_on_mock():
    row = analysis.run_row(MOCK, MOCK_TASK)
    assert row["n_covered"] == 6
    assert row["valid"] is True
    assert row["cov_weighted"] == 1.0
    assert row["final_penalty_fitness"] == pytest.approx(1.011538, abs=1e-6)
    assert row["n_viol_debris"] == 0 and row["n_viol_occupied"] == 0
    assert row["redundancy_yucatan"] is True
    assert not any(row[f"redundancy_{r}"] for r in ("amazonia", "california", "sahel", "japon", "australia"))
    assert row["gen_all_covered_valid"] == 3
    assert row["n_evals"] == 100 * 4


def test_run_row_gen0_violations_mock():
    row = analysis.run_row(MOCK, MOCK_TASK)
    assert row["gen0_best"] == pytest.approx(-0.115385, abs=1e-6)
    assert row["gen0_n_invalid"] == 19


def test_run_curves_mock():
    c = analysis.run_curves(MOCK)
    assert c["best"] == [h["best"] for h in MOCK["history"]]
    assert len(c["diversity"]) == 4


@pytest.mark.parametrize("sats, esperado, tol", [
    ([[45.0, -35.0]], -12.0, 1e-9),      # centro de atlantico_norte
    ([[57.0, -35.0]], 0.0, 1e-9),        # 12° al norte por el meridiano: borde exacto
    ([[-25.0, 133.0]], 18.76, 0.01),     # centro de Australia → borde de objeto_b (§4.5)
])
def test_min_margin_signs(sats, esperado, tol):
    assert analysis.min_margin(np.array(sats), BASE) == pytest.approx(esperado, abs=tol)


def test_gap_uses_oracles():
    assert analysis.gap_opt("base", 1.023077) == pytest.approx(0.0, abs=1e-12)
    assert analysis.gap_opt("inviable", 0.796154) == pytest.approx(0.0, abs=1e-12)
    assert analysis.gap_opt("prioridad_cambiada", 1.021429) == pytest.approx(0.0, abs=1e-12)
    assert analysis.gap_opt("base_f20", 1.038462) is None          # F ≥ 18.2°: sin oráculo (§10)


def test_wilson_bounds():
    lo, hi = analysis.wilson(30, 30)
    assert lo == pytest.approx(0.886, abs=1e-3) and hi == pytest.approx(1.0, abs=1e-3)
    lo, hi = analysis.wilson(0, 30)
    assert lo == pytest.approx(0.0, abs=1e-3) and hi == pytest.approx(0.114, abs=1e-3)
    lo, hi = analysis.wilson(15, 30)
    assert (lo + hi) / 2 == pytest.approx(0.5, abs=1e-3)


def test_determinism_guard_aborts():
    row = analysis.run_row(MOCK, MOCK_TASK)
    rx.verify_representative(MOCK, row, MOCK["final"]["sats"])          # idéntico: no lanza
    malo = dict(row, final_penalty_fitness=row["final_penalty_fitness"] + 1e-12)
    with pytest.raises(rx.DeterminismError):
        rx.verify_representative(MOCK, malo, MOCK["final"]["sats"])


def test_pick_representatives_ties_use_lower_seed():
    rows = [{"config": "c", "seed": s, "final_penalty_fitness": f}
            for s, f in [(42, 1.0), (43, 0.5), (44, 1.0), (45, 0.5), (46, 0.7)]]
    reps = {role: seed for _, role, seed in rx.pick_representatives(rows)}
    assert reps == {"best": 42, "median": 46, "worst": 43}


def test_bootstrap_reproducible():
    a = np.linspace(0.9, 1.0, 30)
    b = np.linspace(0.8, 1.0, 30)
    assert analysis.bootstrap_diff_median(a, b) == analysis.bootstrap_diff_median(a, b)
    lo, hi = analysis.bootstrap_diff_median(a, b)
    assert lo <= np.median(a) - np.median(b) <= hi


# --- Ejecución --quick (paralela = serial, esquema, invariantes) -------------

@pytest.fixture(scope="module")
def quick_out(tmp_path_factory):
    """--quick de base, footprint, poblacion y aleatoria con 2 procesos (y derivados si existen)."""
    out = tmp_path_factory.mktemp("quick") / "results"
    assert rx.main(["--quick", "--all", "--jobs", "2", "--out", str(out)]) == 0
    return out


def test_quick_parallel_equals_serial(quick_out, tmp_path):
    serial = tmp_path / "results"
    assert rx.main(["--quick", "--only", "base", "--jobs", "1", "--out", str(serial)]) == 0
    for name in ("base.csv", "curvas_base.csv", "finales_base.csv"):
        assert (serial / "exp_runs" / name).read_bytes() == (quick_out / "exp_runs" / name).read_bytes()


def test_quick_outputs_schema_valid(quick_out):
    import jsonschema
    schema = json.loads((ROOT / "schemas" / "result.schema.json").read_text(encoding="utf-8"))
    files = sorted((quick_out / "exp_json").glob("*.json"))
    assert any(p.name == "base_repair_s42.json" for p in files)
    for p in files:
        res = json.loads(p.read_text(encoding="utf-8"))
        jsonschema.validate(res, schema)
        sc = model.load_scenario(res["scenario"])
        fsats = np.array(res["final"]["sats"])
        cov = model.coverage(fsats, sc)
        assert all(abs(cov[k] - v) <= 1e-9 for k, v in res["final"]["coverage"].items())
        assert len(model.violations(fsats, sc)) == len(res["final"]["violations"])
        fit = model.fitness(fsats, sc, "strict" if res["mode"] == "strict" else "penalty")
        assert (res["final"]["fitness"] is None and fit == -np.inf) or abs(fit - res["final"]["fitness"]) <= 1e-9


def test_no_non_result_json(quick_out):
    schema = json.loads((ROOT / "schemas" / "result.schema.json").read_text(encoding="utf-8"))
    import jsonschema
    for p in quick_out.glob("exp_*/**/*.json"):
        if p.name.startswith("reval_") or "escenarios" in p.relative_to(quick_out).parts[:-1]:
            continue
        jsonschema.validate(json.loads(p.read_text(encoding="utf-8")), schema)


def test_quick_meta_and_hashes(quick_out):
    lines = (quick_out / "exp_meta" / "sha256.txt").read_text(encoding="utf-8").split()
    assert "exp_runs/base.csv" in lines
    h = lines[lines.index("exp_runs/base.csv") - 1]
    assert h == rx.file_hash(quick_out / "exp_runs" / "base.csv")
    assert "numpy:" in (quick_out / "exp_meta" / "entorno.txt").read_text(encoding="utf-8")


def test_repair_strict_zero_final_violations_quick(quick_out):
    for c in ("base", "reducido"):
        path = quick_out / "exp_runs" / f"{c}.csv"
        if not path.exists():
            continue
        for r in rx.read_csv(path):
            if r["mode"] in ("repair", "strict"):
                assert r["n_viol_debris"] + r["n_viol_occupied"] == 0, (r["config"], r["seed"])


def test_quick_tables_written(quick_out):
    names = {p.stem for p in (quick_out / "exp_tablas").glob("*.md")}
    assert {"p1_config", "p2_resumen", "p3_violaciones", "p4_violaciones", "p7_variacion",
            "regiones_cubiertas", "p8_modos", "p9_footprint", "p10_poblacion"} <= names


def test_plots_on_quick(quick_out):
    import plots
    pngs = {p.name for p in plots.make_all(quick_out)}
    assert {"p1_mapa.png", "p2_curvas_base.png", "p7_boxplot.png", "p9_footprint.png"} <= pngs


def test_report_check_detects_drift(tmp_path):
    import report
    tdir = tmp_path / "tablas"
    tdir.mkdir()
    (tdir / "demo.md").write_text("| a |\n|---|\n| 2 |\n", encoding="utf-8")
    doc = tmp_path / "doc.md"
    doc.write_text("# T\n<!-- tabla:demo -->\n| a |\n|---|\n| 1 |\n<!-- /tabla -->\nfin\n", encoding="utf-8")
    args = ["--doc", str(doc), "--tables", str(tdir)]
    assert report.main(["--check", *args]) == 1
    assert report.main(args) == 0
    assert report.main(["--check", *args]) == 0
    assert "| 2 |" in doc.read_text(encoding="utf-8")


def test_inviable_never_covers_yucatan(quick_out):
    path = quick_out / "exp_runs" / "inviable.csv"
    if not _hay_escenario("inviable"):
        pytest.skip("bloqueada por 1D: falta scenarios/inviable.json")
    for r in rx.read_csv(path):
        if r["valid"]:
            assert r["cov_yucatan"] == 0.0
            assert r["final_penalty_fitness"] <= analysis.P6_CAP + 1e-9


# --- P5, P6 y P11: criterios (filas sintéticas) -------------------------------

def _fila(sc_id, mode, seed, **kw):
    r = {"config": f"{sc_id}_{mode}", "scenario_id": sc_id, "mode": mode, "seed": seed, "valid": True,
         "n_covered": 6, "final_penalty_fitness": 1.0, "min_margin_deg": 18.0, "n_viol_debris": 0,
         "n_viol_occupied": 0, "gap_opt": None, "gen_all_covered_valid": 50}
    r.update({f"cov_{i}": 1.0 for i in ("yucatan", "amazonia", "california", "sahel", "japon", "australia")})
    r.update(kw)
    return r


def _celdas(tabla, modo):
    """Celdas de la fila `modo` de la primera tabla markdown."""
    for ln in tabla.splitlines():
        c = [x.strip() for x in ln.strip("|").split("|")]
        if c[0] == modo:
            return c
    raise AssertionError(modo)


def test_p5_restriccion_activa_vs_base():
    base = [_fila("base", m, s, min_margin_deg=18.5) for m in rx.MODES for s in (42, 43, 44)]
    red = [_fila("reducido", m, s, min_margin_deg=0.6, final_penalty_fitness=0.9) for m in rx.MODES for s in (42, 43, 44)]
    red[0] = dict(red[0], min_margin_deg=5.0)          # una semilla lejos no mueve la mediana
    t = analysis.t_p5(red, base)
    for m in rx.MODES:
        c = _celdas(t, m)
        assert c[1] == "0.60" and c[2] == "18.50" and c[3] == "PASA"
        assert c[8] == "0.1000"                          # caída de la mediana base − reducido
    assert _celdas(t, "penalty")[10] == "—" and _celdas(t, "repair")[10] == "PASA"
    lejos = [dict(r, min_margin_deg=3.0) for r in red]   # mediana ≥ 1°: la restricción no muerde
    assert _celdas(analysis.t_p5(lejos, base), "repair")[3] == "FALLA"
    viol = [dict(r, n_viol_debris=1) if r["mode"] == "strict" else r for r in red]
    assert _celdas(analysis.t_p5(viol, base), "strict")[10] == "FALLA"
    assert _celdas(analysis.t_p5(red, []), "repair")[3] == "—"   # sin base no hay comparación


def test_p6_yucatan_y_tope():
    ok = [_fila("inviable", m, s, n_covered=5, cov_yucatan=0.0, final_penalty_fitness=0.796154,
                gap_opt=analysis.gap_opt("inviable", 0.796154)) for m in rx.MODES for s in (42, 43)]
    t = analysis.t_p6(ok)
    for m in rx.MODES:
        c = _celdas(t, m)
        assert c[3] == "2/2" and c[5] == "2/2" and c[6].startswith("2/2") and c[7] == "0/2" and c[8] == "PASA"
    # un final válido que toca Yucatán, o una aptitud por encima del óptimo, es FALLA
    toca = [dict(r, cov_yucatan=0.4) if r["mode"] == "repair" and r["seed"] == 42 else r for r in ok]
    assert _celdas(analysis.t_p6(toca), "repair")[8] == "FALLA"
    sobre = [dict(r, final_penalty_fitness=0.80) if r["mode"] == "strict" and r["seed"] == 43 else r for r in ok]
    assert _celdas(analysis.t_p6(sobre), "strict")[8] == "FALLA"
    # un final inválido de penalty que toca Yucatán no cuenta para cov_yucatan (no es válido)
    inval = [dict(r, valid=False, cov_yucatan=1.0, final_penalty_fitness=0.52) if r["mode"] == "penalty"
             and r["seed"] == 42 else r for r in ok]
    assert _celdas(analysis.t_p6(inval), "penalty")[8] == "PASA"


@pytest.mark.parametrize("fila, esperado", [
    ({"scenario": "prioridad_cambiada", "still_valid": True, "fitness_before": 1.0, "fitness_after": 0.9}, "PASA"),
    ({"scenario": "prioridad_cambiada", "still_valid": True, "fitness_before": 1.0, "fitness_after": 1.0}, "FALLA"),
    ({"scenario": "menos_sats", "still_valid": False, "reasons": "n_sats: 8 != 4"}, "PASA"),
    ({"scenario": "inviable", "still_valid": False, "violated_zones": "bloqueo_yucatan"}, "PASA"),
    ({"scenario": "inviable", "still_valid": False, "violated_zones": "atlantico_norte"}, "FALLA"),
    ({"scenario": "footprint_chico", "still_valid": True, "lost_regions": "sahel"}, "PASA"),
    ({"scenario": "footprint_chico", "still_valid": True, "lost_regions": None}, "FALLA"),
    ({"scenario": "reducido", "still_valid": False, "n_violations": 1}, "PASA"),
    ({"scenario": "reducido", "still_valid": True, "n_violations": 1}, "FALLA"),
])
def test_p11_coherencia(fila, esperado):
    assert analysis.p11_expected(fila) == esperado


# --- P5, P6, P11 y --only de punta a punta con escenarios §4.6 en memoria ------

def derivado(nombre: str) -> dict:
    """Escenario derivado construido con la receta del contrato §4.6 (solo para tests; 1D publica los reales)."""
    sc = copy.deepcopy(BASE)
    sc.update(id=nombre, name=nombre, description=f"{nombre} (test, receta §4.6)")
    if nombre == "reducido":
        for z in sc["debris_zones"] + sc["occupied"]:
            z["radius_deg"] *= 1.5
        sc["debris_zones"].append({"id": "bloqueo_australia_este", "name": "Bloqueo Australia este",
                                   "lat": -25.0, "lon": 141.0, "radius_deg": 6.0})
    elif nombre == "inviable":
        sc["debris_zones"].append({"id": "bloqueo_yucatan", "name": "Bloqueo Yucatán",
                                   "lat": 20.5, "lon": -89.0, "radius_deg": 13.0})
    elif nombre == "prioridad_cambiada":
        for r in sc["regions"]:
            if r["id"] == "australia":
                r.update(priority="Alta", weight=3)
            elif r["id"] == "california":
                r.update(priority="Normal", weight=1)
    elif nombre == "menos_sats":
        sc["n_sats"] = 4
    elif nombre == "footprint_chico":
        sc["footprint_deg"] = 5.0
    return model.load_scenario(sc)


@pytest.fixture(scope="module")
def derived_out(tmp_path_factory):
    """--quick --only base y luego --only reducido,inviable sobre el MISMO directorio (prueba la fusión)."""
    tmp = tmp_path_factory.mktemp("derivados")
    scen = tmp / "scenarios"
    scen.mkdir()
    for d in rx.DERIVED:
        (scen / f"{d}.json").write_text(json.dumps(derivado(d)), encoding="utf-8")
    (scen / "base.json").write_text(json.dumps(BASE), encoding="utf-8")
    out = tmp / "results"
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(rx, "scenario_path", lambda n: scen / f"{n}.json")
        assert rx.main(["--quick", "--only", "base", "--jobs", "2", "--out", str(out)]) == 0
        primero = {p.name: p.read_text(encoding="utf-8") for p in (out / "exp_meta").iterdir()}
        assert rx.main(["--quick", "--only", "reducido,inviable", "--jobs", "2", "--out", str(out)]) == 0
        # P11 sobre la solución real 100×200 de base (la de --quick no cubre lo suficiente para §4.6)
        shutil.copy(ROOT / "results" / "exp_json" / "base_repair_s42.json", out / "exp_json")
        assert rx.main(["--reval", "--out", str(out)]) == 0
    return out, primero


def test_only_merges_meta(derived_out):
    out, primero = derived_out
    reps = rx.read_csv(out / "exp_meta" / "representativas.csv")
    cfgs = {r["config"] for r in reps}
    assert {f"{c}_{m}" for c in ("base", "reducido", "inviable") for m in rx.MODES} <= cfgs
    assert any(r["roles"] == "p1" or "p1" in r["roles"].split("+") for r in reps)
    camps = {r["campaign"] for r in rx.read_csv(out / "exp_meta" / "tiempos.csv")}
    assert {"base", "reducido", "inviable", "TOTAL base", "TOTAL reducido+inviable"} <= camps
    sha = (out / "exp_meta" / "sha256.txt").read_text(encoding="utf-8")
    for ln in primero["sha256.txt"].splitlines():          # los hashes de base no cambian
        assert ln in sha.splitlines()
    assert "exp_runs/reducido.csv" in sha and "exp_runs/inviable.csv" in sha
    env = (out / "exp_meta" / "entorno.txt").read_text(encoding="utf-8")
    assert "campaigns: base" in env.splitlines() and "campaigns: reducido,inviable" in env.splitlines()


def test_p5_p6_tablas_y_figuras_quick(derived_out):
    import plots
    out, _ = derived_out
    tab = out / "exp_tablas"
    p6 = (tab / "p6_resumen.md").read_text(encoding="utf-8")
    for m in rx.MODES:                                     # imposible cubrir Yucatán: vale aun con --quick
        assert _celdas(p6, m)[8] == "PASA"
    p5 = (tab / "p5_resumen.md").read_text(encoding="utf-8")
    for m in ("repair", "strict"):
        assert _celdas(p5, m)[10] == "PASA"               # 0 violaciones finales con restricción activa
    reg = (tab / "regiones_cubiertas.md").read_text(encoding="utf-8")
    for c in ("base", "reducido", "inviable"):
        for m in rx.MODES:
            assert f"| {c} | {m} |" in reg
    zonas = (tab / "p5_zonas.md").read_text(encoding="utf-8").splitlines()[2:]
    assert sum(int(ln.split("|")[3]) for ln in zonas) == 3 * len(rx.QUICK_SEEDS)   # una zona por ejecución
    pngs = {p.name for p in plots.make_all(out)}
    assert {"p5_boxplot.png", "p5_margen.png", "p6_boxplot.png"} <= pngs


def test_inviable_quick_never_covers_yucatan(derived_out):
    out, _ = derived_out
    rows = rx.read_csv(out / "exp_runs" / "inviable.csv")
    assert len(rows) == 3 * len(rx.QUICK_SEEDS)
    for r in rows:
        assert r["final_penalty_fitness"] <= analysis.P6_CAP + 1e-9
        if r["valid"]:
            assert r["cov_yucatan"] == 0.0


def test_p11_revalidacion(derived_out):
    out, _ = derived_out
    files = sorted(p.name for p in (out / "exp_reval").glob("reval_*.json"))
    assert files == sorted(f"reval_base_repair_s42__{d}.json" for d in rx.DERIVED)
    t = (out / "exp_tablas" / "p11_revalidacion.md").read_text(encoding="utf-8")
    for d in rx.DERIVED:
        assert _celdas(t, d)[-1] == "PASA", d
