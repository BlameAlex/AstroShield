import pytest
from astroshield.model import load_scenario
from astroshield.ga import run_ga

def test_run_ga_basic():
    sc = load_scenario("scenarios/base.json")
    result = run_ga(sc, generations=2, population_size=4)
    assert isinstance(result, dict)
    assert "best_solution" in result
    assert "best_fitness" in result