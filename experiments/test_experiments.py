"""Tests de los experimentos (Ola 3A). Se ejecutan con `pytest experiments`."""
import copy
from pathlib import Path

import pytest

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


@pytest.mark.slow
def test_random_search_scale():
    best = rx.random_search(BASE, 20000, 0)
    assert 0.3 <= best <= 1.0   # contrato §4.5: máximo ≈ 0.615 con 20 000 configuraciones
