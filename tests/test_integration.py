"""Pruebas de integración, CLI y validación de resultados (§6.6, §9, §10)."""
import json
from pathlib import Path

import jsonschema
import pytest

from astroshield import CONTRACT_VERSION
from astroshield.run import MODES, main, run, save_result

ROOT = Path(__file__).resolve().parents[1]
RESULT_SCHEMA = json.loads((ROOT / "schemas" / "result.schema.json").read_text(encoding="utf-8"))
SCENARIO_SCHEMA = json.loads((ROOT / "schemas" / "scenario.schema.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("mode", MODES)
def test_run_modes_schema_and_basic_structure(mode):
    res = run(ROOT / "scenarios" / "base.json", mode=mode, params={"gens": 2, "pop_size": 10}, seed=42)

    # Validación formal contra esquemas
    jsonschema.validate(res, RESULT_SCHEMA)
    jsonschema.validate(res["scenario"], SCENARIO_SCHEMA)

    assert res["contract_version"] == CONTRACT_VERSION
    assert res["mode"] == mode
    assert res["seed"] == 42
    assert isinstance(res["valid"], bool)
    assert len(res["history"]) == 3  # gen 0, 1, 2
    assert res["params"]["gens"] == 2
    assert res["params"]["pop_size"] == 10
    assert res["params"]["seed"] == 42


def test_save_result_strict_json(tmp_path):
    res = run(ROOT / "scenarios" / "base.json", mode="penalty", params={"gens": 1, "pop_size": 10}, seed=42)
    saved_path = save_result(res, out_dir=tmp_path)

    assert saved_path.exists()
    assert saved_path.name == f"{res['id']}.json"

    # Verificar que el contenido es JSON estricto y se valida
    loaded = json.loads(saved_path.read_text(encoding="utf-8"))
    jsonschema.validate(loaded, RESULT_SCHEMA)
    assert loaded["id"] == res["id"]


def test_cli_main_success(tmp_path, capsys):
    code = main([
        "--scenario", str(ROOT / "scenarios" / "base.json"),
        "--gens", "2",
        "--pop", "10",
        "--seed", "42",
        "--mode", "penalty",
        "--out", str(tmp_path),
    ])
    assert code == 0

    captured = capsys.readouterr()
    assert "base_penalty_s42" in captured.out
    assert "valid=" in captured.out
    assert "covered=" in captured.out


def test_cli_main_invalid_scenario():
    code = main(["--scenario", "scenarios/inexistente.json"])
    assert code == 2


def test_cli_precedence(tmp_path):
    params_file = tmp_path / "custom_params.json"
    params_file.write_text(json.dumps({"gens": 5, "pop_size": 20, "tournament_k": 4}), encoding="utf-8")

    code = main([
        "--scenario", str(ROOT / "scenarios" / "base.json"),
        "--params", str(params_file),
        "--gens", "3",  # debe anular el gens=5 del archivo
        "--seed", "42",
        "--out", str(tmp_path),
    ])
    assert code == 0

    out_file = tmp_path / "base_penalty_s42.json"
    res = json.loads(out_file.read_text(encoding="utf-8"))
    assert res["params"]["gens"] == 3
    assert res["params"]["pop_size"] == 20
    assert res["params"]["tournament_k"] == 4
