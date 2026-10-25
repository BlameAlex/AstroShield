"""Pruebas para astroshield.revalidate (contrato §6.7)."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import numpy as np
import pytest

from astroshield import CONTRACT_VERSION, geometry, model, revalidate

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "scenarios" / "base.json"
MOCK_PATH = ROOT / "results" / "mock.json"
RESULT_SCHEMA = json.loads((ROOT / "schemas" / "result.schema.json").read_text(encoding="utf-8"))
FAST = {"gens": 10, "pop_size": 20}
CLAVES_REVAL = {
    "contract_version", "result_id", "old_scenario_id", "new_scenario_id", "still_valid", "reasons",
    "violations", "fitness_before", "fitness_after", "coverage_before", "coverage_after",
    "lost_regions", "gained_regions",
}


def _base():
    return json.loads(BASE.read_text(encoding="utf-8"))


def _derivado(nombre):
    """scenarios/<nombre>.json si 1D ya lo entregó; si no, la misma definición (§4.6, plan 1D.3) en memoria."""
    ruta = ROOT / "scenarios" / f"{nombre}.json"
    if ruta.exists():
        return json.loads(ruta.read_text(encoding="utf-8"))
    sc = _base()
    sc["id"] = nombre
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
                r["priority"], r["weight"] = "Alta", 3
            elif r["id"] == "california":
                r["priority"], r["weight"] = "Normal", 1
    elif nombre == "menos_sats":
        sc["n_sats"] = 4
    elif nombre == "footprint_chico":
        sc["footprint_deg"] = 5.0
    else:
        raise ValueError(nombre)
    return sc


def _ruta_derivado(nombre, tmp_path):
    ruta = ROOT / "scenarios" / f"{nombre}.json"
    if ruta.exists():
        return ruta
    ruta = tmp_path / f"{nombre}.json"
    ruta.write_text(json.dumps(_derivado(nombre)), encoding="utf-8")
    return ruta


def _codigo(argv):
    """Código de salida de main, venga por return o por SystemExit (argparse)."""
    try:
        return revalidate.main(argv)
    except SystemExit as e:
        return e.code


@pytest.fixture
def mock_result():
    return json.loads(MOCK_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def mock_sats(mock_result):
    return np.array(mock_result["final"]["sats"], dtype=float)


# --- revalidate (R1–R8) -----------------------------------------------------

def test_mock_contra_base_sigue_valido(mock_result):
    res = revalidate.revalidate(mock_result, BASE)
    assert res["still_valid"] is True
    assert res["reasons"] == []
    assert res["violations"] == []
    assert res["fitness_before"] == pytest.approx(1.011538, abs=1e-6)
    assert res["fitness_after"] == pytest.approx(1.011538, abs=1e-6)
    assert res["lost_regions"] == []
    assert res["gained_regions"] == []


def test_acepta_ruta_y_dict(mock_result):
    assert revalidate.revalidate(MOCK_PATH, _base()) == revalidate.revalidate(mock_result, BASE)


def test_zona_nueva_invalida(mock_result):
    res = revalidate.revalidate(mock_result, _derivado("inviable"))
    assert res["still_valid"] is False
    assert res["reasons"] == ["violations: 2"]
    assert [(v["sat"], v["zone_id"]) for v in res["violations"]] == [(1, "bloqueo_yucatan"), (7, "bloqueo_yucatan")]
    assert res["violations"][0]["distance_deg"] == pytest.approx(1.765946, abs=1e-6)
    assert res["violations"][1]["distance_deg"] == pytest.approx(3.132795, abs=1e-6)
    assert res["fitness_after"] == pytest.approx(0.011538, abs=1e-6)
    # La zona nueva invalida, pero la cobertura geométrica no cambia: invalidez ≠ pérdida de cobertura.
    assert res["lost_regions"] == []


def test_zonas_agrandadas(mock_result):
    res = revalidate.revalidate(mock_result, _derivado("reducido"))
    assert res["still_valid"] is False
    assert len(res["violations"]) == 1
    v = res["violations"][0]
    assert (v["sat"], v["zone_id"]) == (0, "atlantico_norte")
    assert v["distance_deg"] == pytest.approx(14.353697, abs=1e-6)
    assert v["radius_deg"] == pytest.approx(18.0)
    assert res["fitness_after"] == pytest.approx(0.511538, abs=1e-6)


def test_n_sats_distinto(mock_result):
    res = revalidate.revalidate(mock_result, _derivado("menos_sats"))
    assert res["still_valid"] is False
    assert "n_sats: 8 != 4" in res["reasons"]
    assert res["fitness_after"] == pytest.approx(1.011538, abs=1e-6)  # se reporta con los 8, sin recortar


def test_prioridad_cambiada_sigue_valida(mock_result):
    res = revalidate.revalidate(mock_result, _derivado("prioridad_cambiada"))
    assert res["still_valid"] is True
    assert res["fitness_after"] == pytest.approx(1 + 0.05 * 3 / 14, abs=1e-6)
    assert res["fitness_after"] == pytest.approx(1.010714, abs=1e-6)


def test_footprint_chico_pierde_redundancia(mock_result):
    res = revalidate.revalidate(mock_result, _derivado("footprint_chico"))
    assert res["still_valid"] is True
    assert res["lost_regions"] == []
    assert res["coverage_after"]["yucatan"] == 1.0
    assert res["fitness_after"] == pytest.approx(1.0, abs=1e-9)


def test_footprint_4_6_pierde_regiones(mock_result):
    sc = _base()
    sc["id"], sc["footprint_deg"] = "footprint_4_6", 4.6               # completa si d ≤ 1.9°
    res = revalidate.revalidate(mock_result, sc)
    assert res["lost_regions"] == ["sahel", "japon"]                  # d = 2.179° y 2.041°
    assert res["gained_regions"] == []


# --- _adapt_sats (R9–R12) ---------------------------------------------------

def test_adapt_mismo_tamano(mock_sats):
    out = revalidate._adapt_sats(mock_sats, _base(), np.random.default_rng(0))
    assert np.array_equal(out, mock_sats)


def test_adapt_subconjunto_greedy(mock_sats):
    sc = _derivado("menos_sats")
    out = revalidate._adapt_sats(mock_sats, sc, np.random.default_rng(0))
    assert np.array_equal(out, mock_sats[[1, 2, 3, 5]])
    w = np.array([r["weight"] for r in sc["regions"]], dtype=float)
    cobertura = float(w @ model.coverage_matrix(out, sc).max(axis=1) / w.sum())
    assert cobertura == pytest.approx(10 / 13, abs=1e-9)
    assert cobertura == pytest.approx(0.769231, abs=1e-6)            # el óptimo de §10


def test_adapt_rellena(mock_sats):
    sc = dict(_base(), n_sats=10)
    out = revalidate._adapt_sats(mock_sats, sc, np.random.default_rng(42))
    assert out.shape == (10, 2)
    assert np.array_equal(out[:8], mock_sats)
    assert np.array_equal(out[8:], geometry.sample_sphere(2, np.random.default_rng(42)))


@pytest.mark.parametrize("n", [4, 8, 10])
def test_adapt_no_muta(mock_sats, n):
    copia = mock_sats.copy()
    revalidate._adapt_sats(mock_sats, dict(_base(), n_sats=n), np.random.default_rng(0))
    assert np.array_equal(mock_sats, copia)


# --- reoptimize (R13–R17) ---------------------------------------------------

def test_reoptimize_sembrado_mejora_o_iguala(mock_result):
    res = revalidate.reoptimize(mock_result, BASE, params={"gens": 5, "pop_size": 20})
    jsonschema.Draft202012Validator(RESULT_SCHEMA).validate(res)
    assert res["history"][0]["best"] >= 1.011538 - 1e-6              # la semilla está en gen 0
    assert res["final"]["fitness"] >= res["initial"]["fitness"]


def test_reoptimize_id_por_defecto(mock_result):
    res = revalidate.reoptimize(mock_result, BASE, params={"gens": 1, "pop_size": 10}, seed=42)
    assert res["id"] == "base_penalty_s42_from_mock"
    assert res["mode"] == "penalty"                                  # heredado de mock


def test_reoptimize_inviable_repair(mock_result):
    res = revalidate.reoptimize(mock_result, _derivado("inviable"), mode="repair", params=FAST)
    assert res["valid"] is True
    assert res["final"]["fitness"] <= 0.788462 + 1e-9
    assert res["final"]["coverage"]["yucatan"] == 0.0


def test_reoptimize_menos_sats_optimo_inmediato(mock_result):
    res = revalidate.reoptimize(mock_result, _derivado("menos_sats"), params={"gens": 0, "pop_size": 10})
    assert res["history"][0]["best"] == pytest.approx(0.769231, abs=1e-6)  # el greedy ya es óptimo
    assert len(res["final"]["sats"]) == 4


def test_reoptimize_reproducible(mock_result):
    args = (mock_result, _derivado("inviable"))
    kw = {"mode": "repair", "params": {"gens": 3, "pop_size": 10}, "seed": 5}
    assert revalidate.reoptimize(*args, **kw) == revalidate.reoptimize(*args, **kw)


# --- CLI y formato (R18–R21) ------------------------------------------------

def test_cli_revalidate_escribe_reval(tmp_path):
    code = revalidate.main(["--result", str(MOCK_PATH), "--scenario", str(_ruta_derivado("inviable", tmp_path)),
                            "--out", str(tmp_path)])
    assert code == 0
    reval = json.loads((tmp_path / "reval_mock__inviable.json").read_text(encoding="utf-8"))
    assert reval["still_valid"] is False


def test_cli_reoptimize(tmp_path):
    code = revalidate.main(["--result", str(MOCK_PATH), "--scenario", str(_ruta_derivado("inviable", tmp_path)),
                            "--reoptimize", "--gens", "3", "--seed", "1", "--out", str(tmp_path)])
    assert code == 0
    assert (tmp_path / "reval_mock__inviable.json").exists()
    res = json.loads((tmp_path / "inviable_penalty_s1_from_mock.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(RESULT_SCHEMA).validate(res)


def test_cli_errores_codigo_2(tmp_path):
    assert _codigo(["--result", str(tmp_path / "no_existe.json"), "--scenario", str(BASE),
                    "--out", str(tmp_path)]) == 2
    assert _codigo(["--result", str(MOCK_PATH), "--scenario", str(BASE), "--mode", "foo",
                    "--out", str(tmp_path)]) == 2


def test_reval_claves_exactas(mock_result):
    res = revalidate.revalidate(mock_result, BASE)
    assert set(res) == CLAVES_REVAL
    assert res["contract_version"] == CONTRACT_VERSION
    assert (res["result_id"], res["old_scenario_id"], res["new_scenario_id"]) == ("mock", "base", "base")
    json.dumps(res, allow_nan=False)
