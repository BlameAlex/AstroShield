"""Tests del contrato (docs/contratos.md): firmas, constantes, esquemas y archivos JSON."""
import importlib
import inspect
import re

import pytest

from astroshield import CONTRACT_VERSION


# --- Firmas y constantes (§6, §8) -----------------------------------------

FIRMAS = {
    "geometry.wrap_lon": "(lon)",
    "geometry.central_angle": "(lat1, lon1, lat2, lon2)",
    "geometry.latlon_to_xyz": "(lat, lon, r=1.0)",
    "geometry.sample_sphere": "(n, rng)",
    "geometry.normalize_latlon": "(sats)",
    "model.load_scenario": "(source)",
    "model.coverage_matrix": "(sats, sc)",
    "model.coverage": "(sats, sc)",
    "model.violations": "(sats, sc)",
    "model.fitness": "(sats, sc, mode='penalty')",
    "model.snapshot": "(sats, sc, mode='penalty')",
    "ga.run_ga": "(fitness_fn, n_sats, params, rng, repair_fn=None, *, initial=None, stats_fn=None)",
    "constraints.repair": "(sats, sc, rng, margin_deg=0.5, max_tries=20)",
    "run.run": "(scenario, mode='penalty', params=None, seed=42, run_id=None, initial=None)",
    "run.save_result": "(result, out_dir='results')",
    "run.main": "(argv=None)",
    "revalidate.revalidate": "(result, new_scenario)",
    "revalidate.reoptimize": "(result, new_scenario, mode=None, params=None, seed=42, run_id=None)",
    "revalidate.main": "(argv=None)",
}


def _sin_anotaciones(fn):
    sig = inspect.signature(fn)
    ps = [p.replace(annotation=inspect.Parameter.empty) for p in sig.parameters.values()]
    return str(sig.replace(parameters=ps, return_annotation=inspect.Signature.empty))


@pytest.mark.parametrize("ruta, esperada", FIRMAS.items())
def test_firma_publica(ruta, esperada):
    modulo, nombre = ruta.split(".")
    fn = getattr(importlib.import_module(f"astroshield.{modulo}"), nombre)
    assert _sin_anotaciones(fn) == esperada


def test_constantes_del_contrato():
    geometry, model, ga, run = (importlib.import_module(f"astroshield.{m}") for m in ("geometry", "model", "ga", "run"))
    assert re.fullmatch(r"1\.\d+\.\d+", CONTRACT_VERSION)
    assert geometry.EARTH_RADIUS_KM == 6371.0
    assert model.PRIORITY_WEIGHTS == {"Alta": 3, "Media": 2, "Normal": 1}
    assert model.FITNESS_MODES == ("penalty", "strict")
    assert run.MODES == ("penalty", "repair", "strict")
    assert run.MODE_TO_FITNESS == {"penalty": "penalty", "repair": "penalty", "strict": "strict"}
    assert ga.DEFAULT_PARAMS == {
        "pop_size": 100, "gens": 200, "tournament_k": 3, "p_crossover": 0.9,
        "blx_alpha": 0.5, "p_swap": 0.5, "p_mut": 0.2, "sigma_mut": 5.0,
        "elitism": 2, "seed": None,
    }
