"""Pruebas para astroshield.revalidate (contrato §6.7)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from astroshield import model, revalidate


@pytest.fixture
def mock_result():
    return json.loads(Path("results/mock.json").read_text(encoding="utf-8"))


@pytest.fixture
def base_scenario():
    return json.loads(Path("scenarios/base.json").read_text(encoding="utf-8"))


def test_mock_contra_base_sigue_valido(mock_result, base_scenario):
    res = revalidate.revalidate(mock_result, base_scenario)
    assert res["still_valid"] is True
    assert res["reasons"] == []
    assert res["violations"] == []
    assert res["fitness_before"] == pytest.approx(1.011538, abs=1e-5)
    assert res["fitness_after"] == pytest.approx(1.011538, abs=1e-5)
    assert res["lost_regions"] == []
    assert res["gained_regions"] == []


def test_zona_nueva_invalida(mock_result, base_scenario):
    inviable_sc = json.loads(Path("scenarios/base.json").read_text(encoding="utf-8"))
    inviable_sc["id"] = "inviable"
    inviable_sc["debris_zones"].append({
        "id": "bloqueo_yucatan",
        "name": "Bloqueo Yucatan",
        "lat": 20.5,
        "lon": -89.0,
        "radius_deg": 13.0,
    })

    res = revalidate.revalidate(mock_result, inviable_sc)
    assert res["still_valid"] is False
    assert len(res["violations"]) > 0
    assert any("violations:" in r for r in res["reasons"])


def test_n_sats_distinto(mock_result):
    menos_sats_sc = json.loads(Path("scenarios/base.json").read_text(encoding="utf-8"))
    menos_sats_sc["id"] = "menos_sats"
    menos_sats_sc["n_sats"] = 4

    res = revalidate.revalidate(mock_result, menos_sats_sc)
    assert res["still_valid"] is False
    assert any("n_sats:" in r for r in res["reasons"])


def test_adapt_sats_greedy_y_fill(mock_result, base_scenario):
    prev_sats = np.array(mock_result["final"]["sats"], dtype=float)
    rng = np.random.default_rng(42)

    # Reducción satélites (8 -> 4)
    sc_4 = dict(base_scenario, n_sats=4)
    adapted_4 = revalidate._adapt_sats(prev_sats, sc_4, rng)
    assert len(adapted_4) == 4

    # Aumento satélites (8 -> 10)
    sc_10 = dict(base_scenario, n_sats=10)
    adapted_10 = revalidate._adapt_sats(prev_sats, sc_10, rng)
    assert len(adapted_10) == 10
    assert np.array_equal(adapted_10[:8], prev_sats)


def test_reoptimize_run(mock_result, base_scenario):
    res = revalidate.reoptimize(
        mock_result,
        base_scenario,
        params={"gens": 2, "pop_size": 10},
        seed=42,
    )
    assert res["scenario"]["id"] == base_scenario["id"]
    assert "history" in res
    assert len(res["history"]) == 3


def test_cli_revalidate(tmp_path, mock_result):
    res_path = tmp_path / "result.json"
    res_path.write_text(json.dumps(mock_result), encoding="utf-8")

    code = revalidate.main([
        "--result", str(res_path),
        "--scenario", "scenarios/base.json",
        "--out", str(tmp_path),
    ])
    assert code == 0
    out_reval = tmp_path / f"reval_{mock_result['id']}__base.json"
    assert out_reval.exists()