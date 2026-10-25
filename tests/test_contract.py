"""Tests del contrato (docs/contratos.md): firmas, constantes, esquemas y archivos JSON."""
import importlib
import inspect
import json
import re
from pathlib import Path

import jsonschema
import pytest

from astroshield import CONTRACT_VERSION

ROOT = Path(__file__).resolve().parents[1]
ESCENARIOS = sorted((ROOT / "scenarios").glob("*.json"))
MAJOR = CONTRACT_VERSION.split(".")[0]


def _carga(ruta):
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def _esquema(nombre):
    return _carga(ROOT / "schemas" / f"{nombre}.schema.json")


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


# --- Esquemas y escenarios (§4) -------------------------------------------

def test_esquemas_bien_formados():
    for nombre in ("scenario", "result"):
        jsonschema.Draft202012Validator.check_schema(_esquema(nombre))
    ga = importlib.import_module("astroshield.ga")
    assert set(ga.DEFAULT_PARAMS) == set(_esquema("result")["properties"]["params"]["required"])


def _coherencia(sc):
    # Reglas que el esquema no puede expresar (§4.7).
    pesos = importlib.import_module("astroshield.model").PRIORITY_WEIGHTS
    assert sc["contract_version"].split(".")[0] == MAJOR
    assert all(r["weight"] == pesos[r["priority"]] for r in sc["regions"])
    ids = [r["id"] for r in sc["regions"]]
    assert len(ids) == len(set(ids))
    zonas = [z["id"] for z in sc["debris_zones"] + sc["occupied"]]
    assert len(zonas) == len(set(zonas))


@pytest.mark.parametrize("ruta", ESCENARIOS, ids=lambda p: p.stem)
def test_escenario_valida_esquema(ruta):
    jsonschema.validate(_carga(ruta), _esquema("scenario"))


@pytest.mark.parametrize("ruta", ESCENARIOS, ids=lambda p: p.stem)
def test_escenario_coherente(ruta):
    sc = _carga(ruta)
    assert sc["id"] == ruta.stem
    _coherencia(sc)


def test_escenario_base():
    base = _carga(ROOT / "scenarios" / "base.json")
    assert base["contract_version"] == CONTRACT_VERSION
    assert base["n_sats"] == 8 and base["footprint_deg"] == 10.0
    assert sum(r["weight"] for r in base["regions"]) == 13
    assert base["fitness"] == {"k_penalty": 0.5, "redundancy_bonus": 0.05}
    assert (len(base["regions"]), len(base["debris_zones"]), len(base["occupied"])) == (6, 3, 2)
