"""Tests de los experimentos (Ola 3A). Se ejecutan con `pytest experiments`."""
import copy
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
    assert analysis.gap_opt("inviable", 0.788462) == pytest.approx(0.0, abs=1e-12)
    assert analysis.gap_opt("prioridad_cambiada", 0.9) is None


def test_wilson_bounds():
    lo, hi = analysis.wilson(30, 30)
    assert lo == pytest.approx(0.886, abs=1e-3) and hi == pytest.approx(1.0, abs=1e-3)
    lo, hi = analysis.wilson(0, 30)
    assert lo == pytest.approx(0.0, abs=1e-3) and hi == pytest.approx(0.114, abs=1e-3)
    lo, hi = analysis.wilson(15, 30)
    assert (lo + hi) / 2 == pytest.approx(0.5, abs=1e-3)


def test_bootstrap_reproducible():
    a = np.linspace(0.9, 1.0, 30)
    b = np.linspace(0.8, 1.0, 30)
    assert analysis.bootstrap_diff_median(a, b) == analysis.bootstrap_diff_median(a, b)
    lo, hi = analysis.bootstrap_diff_median(a, b)
    assert lo <= np.median(a) - np.median(b) <= hi
