"""Pruebas de integración, CLI y validación de resultados (§6.6, §9, §10)."""
import copy
import json
import math
import subprocess
import sys
from pathlib import Path

import jsonschema
import numpy as np
import pytest

from astroshield import CONTRACT_VERSION, constraints, ga, model
from astroshield.run import MODE_TO_FITNESS, MODES, main, run, save_result

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "scenarios" / "base.json"
RESULT_SCHEMA = json.loads((ROOT / "schemas" / "result.schema.json").read_text(encoding="utf-8"))
SCENARIO_SCHEMA = json.loads((ROOT / "schemas" / "scenario.schema.json").read_text(encoding="utf-8"))
MOCK = json.loads((ROOT / "results" / "mock.json").read_text(encoding="utf-8"))
FAST = {"gens": 10, "pop_size": 20}


def _base():
    return json.loads(BASE.read_text(encoding="utf-8"))


def _derivado(nombre):
    """scenarios/<nombre>.json si 1D ya lo entregó; si no, la misma definición (§4.6, plan 1D.3) en memoria."""
    ruta = ROOT / "scenarios" / f"{nombre}.json"
    if ruta.exists():
        return json.loads(ruta.read_text(encoding="utf-8"))
    sc = _base()
    sc["id"] = nombre
    if nombre == "inviable":
        sc["debris_zones"].append({"id": "bloqueo_yucatan", "name": "Bloqueo Yucatán",
                                   "lat": 20.5, "lon": -89.0, "radius_deg": 13.0})
    elif nombre == "menos_sats":
        sc["n_sats"] = 4
    else:
        raise ValueError(nombre)
    return sc


def _codigo(argv):
    """Código de salida de main, venga por return o por SystemExit (argparse)."""
    try:
        return main(argv)
    except SystemExit as e:
        return e.code


def _captura_stats(monkeypatch, sc, mode):
    """stats_fn que run() pasa a run_ga, sin ejecutar el AG."""
    capturado = {}

    def falso_run_ga(fitness_fn, n_sats, params, rng, repair_fn=None, *, initial=None, stats_fn=None):
        capturado["stats_fn"] = stats_fn
        raise RuntimeError("capturado")

    monkeypatch.setattr(ga, "run_ga", falso_run_ga)
    with pytest.raises(RuntimeError, match="capturado"):
        run(sc, mode=mode, params=FAST)
    return capturado["stats_fn"]


# --- run: parámetros y stats_fn (I1–I5) -------------------------------------

def test_modo_invalido():
    with pytest.raises(ValueError):
        run(BASE, mode="foo")


def test_params_combinados_y_seed():
    r = run(BASE, params={"gens": 3, "p_mut": 0.3}, seed=7)
    assert r["params"] == {**ga.DEFAULT_PARAMS, "gens": 3, "p_mut": 0.3, "seed": 7}
    assert r["seed"] == 7


def test_param_desconocido():
    with pytest.raises(ValueError):
        run(BASE, params={"foo": 1})


def test_stats_fn_mejor_y_conteos(monkeypatch):
    sc = model.load_scenario(BASE)
    stats = _captura_stats(monkeypatch, sc, "penalty")
    pop = np.array([MOCK["initial"]["sats"], MOCK["final"]["sats"]], dtype=float)
    fits = np.array([model.fitness(ind, sc) for ind in pop])
    s = stats(pop, fits)
    assert s["n_invalid"] == 1
    assert s["n_covered"] == 6
    assert s["best_coverage"] == {r["id"]: 1.0 for r in sc["regions"]}
    assert s["best_n_violations"] == 0


def test_stats_fn_todos_menos_inf(monkeypatch):
    sc = model.load_scenario(BASE)
    stats = _captura_stats(monkeypatch, sc, "strict")
    pop = np.array([MOCK["initial"]["sats"]] * 3, dtype=float)       # sat 0 dentro de atlantico_norte
    s = stats(pop, np.array([-np.inf] * 3))
    esperado = model.coverage(pop[0], sc)                             # b == 0 (primer índice)
    assert s["best_coverage"] == esperado
    assert s["n_covered"] == sum(v == 1.0 for v in esperado.values())
    assert s["best_n_violations"] == len(model.violations(pop[0], sc))
    assert s["n_invalid"] == 3
    for k in ("n_invalid", "n_covered", "best_n_violations"):
        assert type(s[k]) is int


# --- run: esquema e invariantes 1–6 (I6–I8) ---------------------------------

@pytest.fixture(scope="module", params=MODES)
def resultado(request):
    return run(BASE, mode=request.param, params=FAST, seed=1)


def test_resultado_cumple_esquema(resultado):
    jsonschema.Draft202012Validator(RESULT_SCHEMA).validate(resultado)
    jsonschema.Draft202012Validator(SCENARIO_SCHEMA).validate(resultado["scenario"])
    assert resultado["contract_version"] == CONTRACT_VERSION


def test_invariantes_1_a_6(resultado):
    r, h = resultado, resultado["history"]
    assert len(h) == r["params"]["gens"] + 1
    assert [e["gen"] for e in h] == list(range(len(h)))
    assert r["initial"]["sats"] == h[0]["best_sats"]
    assert r["final"]["sats"] == h[-1]["best_sats"]
    bests = [-math.inf if e["best"] is None else e["best"] for e in h]
    assert all(a <= b for a, b in zip(bests, bests[1:]))
    assert r["valid"] == (len(r["final"]["violations"]) == 0 and len(r["final"]["sats"]) == r["scenario"]["n_sats"])
    ids = [reg["id"] for reg in r["scenario"]["regions"]]
    assert list(r["initial"]["coverage"]) == ids and list(r["final"]["coverage"]) == ids
    assert all(list(e["best_coverage"]) == ids for e in h)
    assert r["params"]["seed"] == r["seed"] == 1


def test_inicial_es_mejor_de_gen0(resultado):
    assert resultado["initial"]["fitness"] == resultado["history"][0]["best"]


# --- valid, reproducibilidad y cableado de repair (I9–I13) ------------------

def _caso_invalido(mode):
    sc = _base()
    sc["fitness"]["k_penalty"] = 0.0
    sats = np.array(MOCK["final"]["sats"], dtype=float)
    sats[0] = [45.0, -30.0]                                           # dentro de atlantico_norte
    return run(sc, mode=mode, params={"gens": 0, "pop_size": 20}, seed=42, initial=sats[None, ...])


def test_valid_false_si_final_viola():
    r = _caso_invalido("penalty")
    assert r["valid"] is False
    assert r["final"]["violations"][0]["zone_id"] == "atlantico_norte"


def test_valid_true_al_reparar():
    r = _caso_invalido("repair")
    assert r["valid"] is True
    assert r["final"]["violations"] == []


def test_reproducible_con_semilla():
    assert run(BASE, "penalty", FAST, 3) == run(BASE, "penalty", FAST, 3)


def test_semillas_distintas_difieren():
    assert run(BASE, "penalty", FAST, 3)["final"]["sats"] != run(BASE, "penalty", FAST, 4)["final"]["sats"]


def test_repair_solo_en_modo_repair(monkeypatch):
    llamadas = {"n": 0}

    def repair_identidad(sats, sc, rng, margin_deg=0.5, max_tries=20):
        llamadas["n"] += 1
        return np.array(sats, dtype=float)

    monkeypatch.setattr(constraints, "repair", repair_identidad)
    for mode in MODES:
        llamadas["n"] = 0
        run(BASE, mode, {"gens": 2, "pop_size": 10}, 0)
        assert (llamadas["n"] > 0) == (mode == "repair"), mode


# --- save_result (I14–I15) --------------------------------------------------

def _no_constantes(c):
    raise AssertionError(f"constante no estricta en JSON: {c}")


def test_save_result_json_estricto(tmp_path):
    r = run(BASE, "strict", {"gens": 2, "pop_size": 10}, 42)
    ruta = save_result(r, out_dir=tmp_path)
    assert ruta == tmp_path / f"{r['id']}.json"
    cargado = json.loads(ruta.read_text(encoding="utf-8"), parse_constant=_no_constantes)
    assert cargado == r
    jsonschema.validate(cargado, RESULT_SCHEMA)


def test_save_result_tipos_numpy(tmp_path):
    r = run(BASE, "penalty", {"gens": 1, "pop_size": 10}, 42)
    r["seed"] = np.int64(42)
    r["final"]["fitness"] = np.float64(r["final"]["fitness"])
    ruta = save_result(r, out_dir=tmp_path / "nuevo")
    assert json.loads(ruta.read_text(encoding="utf-8"))["seed"] == 42


# --- CLI (I16–I19) ----------------------------------------------------------

def test_cli_main_ok(tmp_path, capsys):
    code = main(["--scenario", str(BASE), "--gens", "3", "--pop", "10", "--seed", "1",
                 "--mode", "penalty", "--out", str(tmp_path)])
    assert code == 0
    assert (tmp_path / "base_penalty_s1.json").exists()
    out = capsys.readouterr().out
    assert "valid=" in out and "covered=" in out


def test_cli_precedencia_params(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"gens": 50, "p_mut": 0.3}), encoding="utf-8")
    assert main(["--scenario", str(BASE), "--params", str(p), "--gens", "2", "--pop", "10",
                 "--out", str(tmp_path)]) == 0
    guardado = json.loads((tmp_path / "base_penalty_s42.json").read_text(encoding="utf-8"))
    assert guardado["params"]["gens"] == 2
    assert guardado["params"]["p_mut"] == 0.3


def test_cli_errores_codigo_2(tmp_path):
    malo = tmp_path / "malo.json"
    malo.write_text(json.dumps({"foo": 1}), encoding="utf-8")
    assert _codigo(["--scenario", str(BASE), "--mode", "foo"]) == 2
    assert _codigo(["--scenario", str(tmp_path / "inexistente.json"), "--out", str(tmp_path)]) == 2
    assert _codigo(["--scenario", str(BASE), "--params", str(malo), "--out", str(tmp_path)]) == 2


def test_cli_shim_subproceso(tmp_path):
    p = subprocess.run([sys.executable, "run.py", "--scenario", "scenarios/base.json", "--gens", "2",
                        "--pop", "10", "--out", str(tmp_path), "--id", "demo"],
                       cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert (tmp_path / "demo.json").exists()


# --- Invariante 7 sobre results/*.json versionados (I20, §9.2, §9.4) --------

VERSIONADOS = sorted(p for p in (ROOT / "results").glob("*.json") if not p.name.startswith("reval_"))


def _fit(x):
    return None if x == -math.inf else x


def _cerca(a, b, tol):
    if a is None or b is None:
        return a is b
    return abs(a - b) <= tol


def _mismas_violaciones(guardadas, calculadas, tol):
    assert len(guardadas) == len(calculadas)
    for g, c in zip(guardadas, calculadas):
        assert {k: g[k] for k in ("sat", "zone_id", "kind")} == {k: c[k] for k in ("sat", "zone_id", "kind")}
        for k in ("distance_deg", "radius_deg", "depth_deg"):
            assert _cerca(g[k], c[k], tol), (k, g[k], c[k])


@pytest.mark.parametrize("ruta", VERSIONADOS, ids=lambda p: p.name)
def test_invariante_7_resultados_versionados(ruta):
    r = json.loads(ruta.read_text(encoding="utf-8"))
    tol = 1e-6 if ruta.name == "mock.json" else 1e-9
    sc = model.load_scenario(r["scenario"])
    fmode = MODE_TO_FITNESS[r["mode"]]

    for nombre in ("initial", "final"):
        snap = r[nombre]
        sats = np.array(snap["sats"], dtype=float)
        cov = model.coverage(sats, sc)
        assert list(cov) == list(snap["coverage"])
        assert all(_cerca(snap["coverage"][k], cov[k], tol) for k in cov), nombre
        assert _cerca(snap["fitness"], _fit(model.fitness(sats, sc, fmode)), tol), nombre
        _mismas_violaciones(snap["violations"], model.violations(sats, sc), tol)

    for e in r["history"]:
        sats = np.array(e["best_sats"], dtype=float)
        cov = model.coverage(sats, sc)
        assert all(_cerca(e["best_coverage"][k], cov[k], tol) for k in cov), e["gen"]
        assert e["n_covered"] == sum(v == 1.0 for v in e["best_coverage"].values()), e["gen"]
        assert e["best_n_violations"] == len(model.violations(sats, sc)), e["gen"]
        assert _cerca(e["best"], _fit(model.fitness(sats, sc, fmode)), tol), e["gen"]


# --- Cotas de oráculo (I21–I24, §10) ----------------------------------------

def test_cota_optimo_base():
    r = run(BASE, "repair", {"gens": 30, "pop_size": 40}, 0)
    assert r["valid"]
    assert r["initial"]["fitness"] <= r["final"]["fitness"] <= 1.023077 + 1e-9


def test_cota_optimo_inviable():
    r = run(_derivado("inviable"), "repair", FAST, 0)
    assert r["valid"]
    assert r["final"]["fitness"] <= 0.788462 + 1e-9
    assert r["final"]["coverage"]["yucatan"] == 0.0


def test_cota_optimo_menos_sats():
    r = run(_derivado("menos_sats"), "penalty", FAST, 0)
    assert len(r["final"]["sats"]) == 4
    assert r["final"]["fitness"] <= 0.769231 + 1e-9


def test_strict_final_finito_es_valido():
    r = run(BASE, "strict", FAST, 0)
    if r["final"]["fitness"] is not None:
        assert r["final"]["violations"] == []
