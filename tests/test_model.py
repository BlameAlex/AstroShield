"""Pruebas de model (§5, §6.3) con oráculos calculados a mano sobre el escenario base."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

from astroshield import model

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "scenarios" / "base.json"


@pytest.fixture
def sc():
    return model.load_scenario(BASE)


def centers(sc, ids):
    by_id = {r["id"]: r for r in sc["regions"]}
    return np.array([[by_id[i]["lat"], by_id[i]["lon"]] for i in ids], dtype=float)


def optimum(sc):
    # Un satélite por región y los 2 extra en las regiones Alta (redundancia de peso 6/13).
    return centers(sc, [r["id"] for r in sc["regions"]] + ["yucatan", "amazonia"])


def test_load_scenario_devuelve_copia_profunda(sc):
    original = json.loads(BASE.read_text(encoding="utf-8"))
    copia = model.load_scenario(original)
    copia["regions"][0]["lat"] = 0.0
    assert original["regions"][0]["lat"] == 20.5


@pytest.mark.parametrize("mutar, campo", [
    (lambda s: s.pop("footprint_deg"), "footprint_deg"),
    (lambda s: s.update(contract_version="2.0.0"), "contract_version"),
    (lambda s: s["regions"][0].update(weight=1), "weight"),
    (lambda s: s["regions"][1].update(id="yucatan"), "regions"),
    (lambda s: s["occupied"][0].update(id="atlantico_norte"), "occupied"),
    (lambda s: s["regions"][0].update(lat=95.0), "lat"),
    (lambda s: s["debris_zones"][0].update(radius_deg=0.0), "radius_deg"),
    (lambda s: s.update(n_sats=0), "n_sats"),
])
def test_load_scenario_rechaza_invalidos(sc, mutar, campo):
    malo = copy.deepcopy(sc)
    mutar(malo)
    with pytest.raises(ValueError, match=campo):
        model.load_scenario(malo)


def test_load_scenario_archivo_inexistente():
    with pytest.raises(FileNotFoundError):
        model.load_scenario(ROOT / "scenarios" / "no_existe.json")


def test_coverage_bordes_lineales(sc):
    # F = 10, r = 2.7: completa si d <= 7.3, nula si d >= 12.7, lineal en medio (§5.1).
    lat, lon = 20.5, -89.0
    sats = np.array([[lat + 7.3, lon], [lat + 12.7, lon], [lat + 10.0, lon]])
    c = model.coverage_matrix(sats, sc)
    assert c.shape == (6, 3)
    assert c[0, 0] == pytest.approx(1.0, abs=1e-9)
    assert c[0, 1] == pytest.approx(0.0, abs=1e-9)
    assert c[0, 2] == pytest.approx(0.5, abs=1e-9)


def test_optimo_base_es_oraculo(sc):
    sats = optimum(sc)
    assert all(v == 1.0 for v in model.coverage(sats, sc).values())
    assert model.violations(sats, sc) == []
    assert model.fitness(sats, sc, "penalty") == pytest.approx(1.023077, abs=1e-6)
    assert model.fitness(sats, sc, "strict") == model.fitness(sats, sc, "penalty")


def test_violaciones_orden_y_claves(sc):
    sats = optimum(sc)
    sats[3] = [45.0, -35.0]      # centro de atlantico_norte
    sats[1] = [-15.0, 110.0]     # centro de objeto_b
    v = model.violations(sats, sc)
    assert [(x["sat"], x["zone_id"], x["kind"]) for x in v] == [
        (1, "objeto_b", "occupied"), (3, "atlantico_norte", "debris")]
    assert all(set(x) == {"sat", "zone_id", "kind", "distance_deg", "radius_deg", "depth_deg"} for x in v)
    assert v[1]["depth_deg"] == pytest.approx(12.0, abs=1e-9)


def test_borde_exacto_no_viola(sc):
    # 12° al norte del centro de atlantico_norte por el meridiano: distancia == radio (§5.4, estricta).
    assert model.violations(np.array([[57.0, -35.0]]), sc) == []


def test_fitness_penaliza_y_strict_devuelve_menos_inf(sc):
    sats = optimum(sc)
    base = model.fitness(sats, sc, "penalty")
    sats[6] = [45.0, -35.0]      # el satélite redundante de yucatan entra en atlantico_norte
    pen = model.fitness(sats, sc, "penalty")
    assert pen == pytest.approx(base - 0.05 * 3 / 13 - 0.5, abs=1e-9)
    assert model.fitness(sats, sc, "strict") == -np.inf
    assert model.snapshot(sats, sc, "strict")["fitness"] is None
    with pytest.raises(ValueError):
        model.fitness(sats, sc, "otro")


@pytest.mark.parametrize("ruta", sorted(p.name for p in (ROOT / "results").glob("base_*_s42.json")))
def test_resultados_reales_se_reproducen(ruta):
    res = json.loads((ROOT / "results" / ruta).read_text(encoding="utf-8"))
    sc = model.load_scenario(res["scenario"])
    fit_mode = "strict" if res["mode"] == "strict" else "penalty"
    for bloque in ("initial", "final"):
        snap = res[bloque]
        assert model.snapshot(np.array(snap["sats"]), sc, fit_mode) == snap
